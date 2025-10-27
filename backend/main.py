from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import pandas as pd, io, re

app = FastAPI()

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helper functions ----------

def parse_money(x):
    if pd.isna(x): return 0.0
    s = str(x).strip().replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()$ ")
    s = re.sub(r'[A-Za-z]+$', '', s)
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return 0.0

def parse_number(x):
    if pd.isna(x): return 0.0
    s = str(x).replace(",", "").replace("$", "").strip()
    if s == "4S":
        return 0.0
    s = re.sub(r'[A-Za-z]+$', '', s)
    try:
        return float(s or 0)
    except ValueError:
        return 0.0

def stock_type(trans_code: str) -> str:
    v = (trans_code or "").strip().lower()
    if v == "buy":  return "BUY"
    if v == "sell": return "SELL"
    return ""

def choose_date(df: pd.DataFrame) -> pd.Series:
    for c in ["Activity Date", "Settle Date"]:
        if c in df.columns:
            s = pd.to_datetime(df[c], errors="coerce", infer_datetime_format=True)
            if not s.isna().all():
                return s
    raise ValueError("Missing Activity Date / Settle Date")

def fifo_avg_cost(prior_buys, qty_needed):
    remaining, total_cost, total_qty = qty_needed, 0.0, 0.0
    for _, lot in prior_buys.sort_values("Date").iterrows():
        take = min(remaining, lot["Quantity"])
        if take <= 0: break
        total_cost += take * lot["Price"]
        total_qty  += take
        remaining  -= take
    return (total_cost / total_qty) if total_qty else float("nan")

# ---------- Option parsing and wash-sale key ----------

def parse_option(desc: str):
    """
    Parse option description like 'AAPL 01/19/2024 150.00 CALL'
    """
    desc = str(desc).upper()
    match = re.search(r'([A-Z]+)\s+(\d{2}/\d{2}/\d{4})\s+([\d\.]+)\s+(CALL|PUT)', desc)
    if match:
        underlying, expiry, strike, right = match.groups()
        return underlying, expiry, float(strike), right
    else:
        return None, None, None, None

def normalize_symbol(row):
    """
    Define a grouping key: identical for stock & equivalent options.
    """
    desc = str(row.get("Description", "")).upper()
    if "CALL" in desc or "PUT" in desc:
        underlying, expiry, strike, right = parse_option(desc)
        if underlying and expiry and strike and right:
            return f"{underlying}_{expiry}_{strike}_{right}"
    return str(row["Ticker"]).upper()

# ---------- Main endpoint ----------

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...)):
    raw = await file.read()
    df = pd.read_csv(io.BytesIO(raw))

    # --- Normalize input columns ---
    needed = ["Activity Date","Settle Date","Instrument","Description","Trans Code","Quantity","Price","Amount"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["Date"] = choose_date(df)
    df["Ticker"] = df["Instrument"].astype(str).str.strip().str.upper()
    df["Type"] = df["Trans Code"].apply(stock_type)
    df["Quantity"] = df["Quantity"].apply(parse_number)
    df["Price"] = df["Price"].apply(parse_money)
    df["Amount"] = df["Amount"].apply(parse_money)
    df["WashKey"] = df.apply(normalize_symbol, axis=1)

    stocks = df[(df["Type"].isin(["BUY","SELL"])) & (df["Ticker"] != "")].copy()
    if stocks.empty:
        return {"wash_sales": "No stock or option transactions found."}

    stocks = stocks.sort_values("Date")
    results = []
    eoy = stocks["Date"].max()

    # --- Loop through each SELL transaction ---
    for _, sell in stocks[stocks["Type"] == "SELL"].iterrows():
        key, sell_date = sell["WashKey"], sell["Date"]
        qty_sold, sell_px = float(sell["Quantity"]), float(sell["Price"])
        if qty_sold <= 0:
            continue

        # --- FIFO cost for this WashKey group ---
        prior_buys = stocks[
            (stocks["WashKey"] == key)
            & (stocks["Type"] == "BUY")
            & (stocks["Date"] < sell_date)
            & (stocks["Quantity"] > 0)
        ]
        if prior_buys.empty:
            continue

        fifo_cost = fifo_avg_cost(prior_buys, qty_sold)
        if pd.isna(fifo_cost):
            continue

        per_share_pl = sell_px - fifo_cost
        total_pl = per_share_pl * qty_sold
        if total_pl >= 0:
            continue  # only analyze losses

        # ---------- IRS wash-sale logic ----------
        start, end = sell_date - timedelta(days=30), sell_date + timedelta(days=30)

        # Pre 30d buys still held at sale
        pre_buys = stocks[
            (stocks["WashKey"] == key)
            & (stocks["Type"] == "BUY")
            & (stocks["Date"] > start)
            & (stocks["Date"] <= sell_date)
        ]
        pre_qty = pre_buys["Quantity"].sum()

        pre_sells = stocks[
            (stocks["WashKey"] == key)
            & (stocks["Type"] == "SELL")
            & (stocks["Date"] > start)
            & (stocks["Date"] <= sell_date)
        ]
        pre_held_at_sale = max(0.0, pre_qty - pre_sells["Quantity"].sum())

        # Post 30d buys
        post_buys = stocks[
            (stocks["WashKey"] == key)
            & (stocks["Type"] == "BUY")
            & (stocks["Date"] > sell_date)
            & (stocks["Date"] <= end)
        ]
        post_qty = post_buys["Quantity"].sum()

        # Replacement = pre-held + post-buys, capped by qty_sold
        replacement_shares = min(qty_sold, pre_held_at_sale + post_qty)

        # Shares still held at EOY
        total_buys_to_eoy = stocks[
            (stocks["WashKey"] == key)
            & (stocks["Type"] == "BUY")
            & (stocks["Date"] <= eoy)
        ]["Quantity"].sum()
        total_sells_to_eoy = stocks[
            (stocks["WashKey"] == key)
            & (stocks["Type"] == "SELL")
            & (stocks["Date"] <= eoy)
        ]["Quantity"].sum()
        still_held_eoy = max(0.0, total_buys_to_eoy - total_sells_to_eoy)

        # Disallowed loss
        disallowed_shares = min(replacement_shares, still_held_eoy)
        disallowed_loss = round(abs(per_share_pl) * disallowed_shares, 2)

        if disallowed_loss > 0:
            results.append({
                "GroupKey": key,
                "Ticker": sell["Ticker"],
                "SellDate": sell_date.strftime("%Y-%m-%d"),
                "SharesSold": qty_sold,
                "Loss": round(total_pl, 2),
                "FIFO_AvgCost": round(fifo_cost, 4),
                "SellPrice": round(sell_px, 4),
                "PreReplacementStillHeldAtSale": pre_held_at_sale,
                "PostReplacementWithin30d": post_qty,
                "ReplacementShares": replacement_shares,
                "StillHeldAtEOY": still_held_eoy,
                "DisallowedLoss": disallowed_loss,
                "Note": (
                    "Loss disallowed because substantially identical positions "
                    "(stock or options) within ±30 days are still held at year-end."
                )
            })

    return {"wash_sales": results or "No wash sales found"}
