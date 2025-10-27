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
    s = re.sub(r'[A-Za-z]+$', '', s)  # remove trailing letters
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return 0.0

def parse_number(x):
    if pd.isna(x): return 0.0
    s = str(x).replace(",", "").replace("$", "").strip()
    if s == "4S":  # special case
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

    stocks = df[(df["Type"].isin(["BUY","SELL"])) & (df["Ticker"] != "")].copy()
    if stocks.empty:
        return {"wash_sales": "No stock rows (Buy/Sell) found."}

    stocks = stocks.sort_values("Date")
    results = []

    # --- Loop through each SELL transaction ---
    for _, sell in stocks[stocks["Type"] == "SELL"].iterrows():
        tkr, sell_date = sell["Ticker"], sell["Date"]
        qty_sold, sell_px = float(sell["Quantity"]), float(sell["Price"])
        if qty_sold <= 0:
            continue

        prior_buys = stocks[
            (stocks["Ticker"] == tkr) &
            (stocks["Type"] == "BUY") &
            (stocks["Date"] < sell_date) &
            (stocks["Quantity"] > 0)
        ]
        if prior_buys.empty:
            continue

        fifo_cost = fifo_avg_cost(prior_buys, qty_sold)
        if pd.isna(fifo_cost):
            continue

        per_share_pl = sell_px - fifo_cost
        total_pl = per_share_pl * qty_sold
        if total_pl >= 0:
            continue  # only look for losses

        # --- New IRS-accurate wash-sale logic ---
        start, end = sell_date - timedelta(days=30), sell_date + timedelta(days=30)

        # 1️⃣ All buys within ±30 days of this loss sale
        buys_in_window = stocks[
            (stocks["Ticker"] == tkr) &
            (stocks["Type"] == "BUY") &
            (stocks["Quantity"] > 0) &
            (stocks["Date"] > start) & (stocks["Date"] <= end)
        ].copy()

        if buys_in_window.empty:
            continue  # no replacement shares

        total_bought = float(buys_in_window["Quantity"].sum())

        # 🔧 Improved "still held today" logic — true current holdings
        total_buys_all = float(stocks[(stocks["Ticker"] == tkr) & (stocks["Type"] == "BUY")]["Quantity"].sum())
        total_sells_all = float(stocks[(stocks["Ticker"] == tkr) & (stocks["Type"] == "SELL")]["Quantity"].sum())
        net_current_position = max(0.0, total_buys_all - total_sells_all)

        # 4️⃣ Compute disallowed loss
        disallowed_shares = min(qty_sold, net_current_position)
        disallowed_loss = round(abs(per_share_pl) * disallowed_shares, 2)
        if disallowed_loss > 0:
            results.append({
                "Ticker": tkr,
                "SellDate": sell_date.strftime("%Y-%m-%d"),
                "SharesSold": qty_sold,
                "Loss": round(total_pl, 2),
                "FIFO_AvgCost": round(fifo_cost, 4),
                "SellPrice": round(sell_px, 4),
                "ReplacementSharesInWindow": total_bought,
                "StillHeldToday": net_current_position,
                "DisallowedLoss": disallowed_loss,
                "Note": "Loss disallowed because replacement shares bought within ±30 days are still held today."
            })

    return {"wash_sales": results or "No wash sales found"}
