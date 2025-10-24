from fastapi import FastAPI, UploadFile, File
import pandas as pd
from datetime import timedelta

app = FastAPI()

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...)):
    # Read uploaded CSV into DataFrame
    df = pd.read_csv(file.file, parse_dates=['Date'])
    df = df.sort_values(by='Date')

    stocks = df[df['Strike'].isna()]
    results = []

    for i, sell in stocks[stocks['Type'] == 'SELL'].iterrows():
        ticker = sell['Ticker']
        sell_date = sell['Date']
        sell_price = sell['Price']
        qty = sell['Quantity']

        # Match FIFO buy
        buys = stocks[(stocks['Ticker'] == ticker) &
                      (stocks['Type'] == 'BUY') &
                      (stocks['Date'] < sell_date)]
        if buys.empty:
            continue

        first_buy = buys.iloc[0]
        cost_basis = first_buy['Price']
        loss = (sell_price - cost_basis) * qty

        if loss < 0:
            start_window = sell_date - timedelta(days=30)
            end_window = sell_date + timedelta(days=30)
            repurchases = stocks[
                (stocks['Ticker'] == ticker) &
                (stocks['Type'] == 'BUY') &
                (stocks['Date'].between(start_window, end_window)) &
                (stocks['Date'] != first_buy['Date'])
            ]
            if not repurchases.empty:
                total_qty = repurchases['Quantity'].sum()
                disallowed_loss = min(qty, total_qty) * abs(loss / qty)
                results.append({
                    "Ticker": ticker,
                    "SellDate": sell_date.strftime("%Y-%m-%d"),
                    "Loss": round(loss, 2),
                    "DisallowedLoss": round(disallowed_loss, 2),
                    "AdjustedBasisAddedTo": repurchases.iloc[0]['Date'].strftime("%Y-%m-%d")
                })

    return {"wash_sales": results or "No wash sales found"}
