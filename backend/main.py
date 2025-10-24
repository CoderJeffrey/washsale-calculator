from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import pandas as pd, io, re

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_money(x):
    if pd.isna(x): return 0.0
    s = str(x).strip().replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()$ ")
    # Remove common suffixes and clean the string
    s = re.sub(r'[A-Za-z]+$', '', s)  # Remove trailing letters
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return 0.0

def parse_number(x):
    if pd.isna(x): return 0.0
    s = str(x).replace(",", "").replace("$", "").strip()
    
    # Special case: treat '4S' as 0
    if s == '4S':
        return 0.0
    
    # Remove common suffixes like 'S' for shares, 'K' for thousands, etc.
    s = re.sub(r'[A-Za-z]+$', '', s)  # Remove trailing letters
    try:
        return float(s or 0)
    except ValueError:
        return 0.0

def stock_type(trans_code: str) -> str:
    v = (trans_code or "").strip().lower()
    if v == "buy":  return "BUY"
    if v == "sell": return "SELL"
    return ""  # not a stock trade

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

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...)):
    raw = await file.read()
    df  = pd.read_csv(io.BytesIO(raw))

    # Normalize core fields
    needed = ["Activity Date","Settle Date","Instrument","Description","Trans Code","Quantity","Price","Amount"]
    missing = [c for c in needed if c not in df.columns]
    if missing: raise ValueError(f"Missing columns: {missing}")

    df["Date"]      = choose_date(df)
    df["Ticker"]    = df["Instrument"].astype(str).str.strip().str.upper()
    df["Type"]      = df["Trans Code"].apply(stock_type)
    df["Quantity"]  = df["Quantity"].apply(parse_number)
    df["Price"]     = df["Price"].apply(parse_money)
    df["Amount"]    = df["Amount"].apply(parse_money)

    # Keep only stock rows with a ticker
    stocks = df[(df["Type"].isin(["BUY","SELL"])) & (df["Ticker"] != "")].copy()
    if stocks.empty:
        return {"wash_sales": "No stock rows (Buy/Sell) found."}

    stocks = stocks.sort_values("Date")

    results = []
    for _, sell in stocks[stocks["Type"]=="SELL"].iterrows():
        tkr, sell_date = sell["Ticker"], sell["Date"]
        qty_sold, sell_px = float(sell["Quantity"]), float(sell["Price"])
        if qty_sold <= 0: continue

        prior_buys = stocks[(stocks["Ticker"]==tkr) & (stocks["Type"]=="BUY") & (stocks["Date"] < sell_date) & (stocks["Quantity"]>0)]
        if prior_buys.empty: continue

        fifo_cost = fifo_avg_cost(prior_buys, qty_sold)
        if pd.isna(fifo_cost): continue

        per_share_pl = sell_px - fifo_cost
        total_pl = per_share_pl * qty_sold

        if total_pl < 0:  # loss → check wash window
            start, end = sell_date - timedelta(days=30), sell_date + timedelta(days=30)
            repurchases = stocks[(stocks["Ticker"]==tkr) & (stocks["Type"]=="BUY") & (stocks["Date"].between(start, end))]
            if not repurchases.empty:
                rep_qty = float(repurchases["Quantity"].sum())
                disallowed_shares = min(qty_sold, rep_qty)
                disallowed_loss = round(abs(per_share_pl)*disallowed_shares, 2)
                results.append({
                    "Ticker": tkr,
                    "SellDate": sell_date.strftime("%Y-%m-%d"),
                    "SharesSold": qty_sold,
                    "FIFO_AvgCost": round(fifo_cost, 4),
                    "SellPrice": round(sell_px, 4),
                    "Loss": round(total_pl, 2),
                    "ReplacementSharesInWindow": rep_qty,
                    "DisallowedLoss": disallowed_loss,
                    "AdjustedBasisAddedTo": pd.to_datetime(repurchases.iloc[0]["Date"]).strftime("%Y-%m-%d"),
                })

    return {"wash_sales": results or "No wash sales found"}
