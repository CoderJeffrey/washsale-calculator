import pandas as pd
from datetime import timedelta

# === Step 1: Load your Robinhood trade history CSV ===
# Columns expected: ['Date', 'Type', 'Ticker', 'Quantity', 'Price', 'Strike', 'Expiration']
# Example rows:
# 2025-01-02, BUY, TSLA, 1, 250.0, , 
# 2025-01-10, SELL, TSLA, 1, 240.0, , 
# 2025-02-01, BUY, TSLA, 1, 245.0, , 

df = pd.read_csv("samepls/trades.csv", parse_dates=['Date'])
df = df.sort_values(by='Date')

# === Step 2: Separate stocks vs. options ===
stocks = df[df['Strike'].isna()]        # stocks have no strike/expiry
options = df[~df['Strike'].isna()]      # options have strike/expiry

# === Step 3: Function to detect wash sales for STOCKS only ===
def detect_wash_sales(trades):
    results = []
    for i, sell in trades[trades['Type'] == 'SELL'].iterrows():
        ticker = sell['Ticker']
        sell_date = sell['Date']
        sell_price = sell['Price']
        qty = sell['Quantity']

        # Find the matching buy lots (FIFO)
        buys = trades[(trades['Ticker'] == ticker) &
                      (trades['Type'] == 'BUY') &
                      (trades['Date'] < sell_date)].copy()
        if buys.empty:
            continue

        first_buy = buys.iloc[0]
        cost_basis = first_buy['Price']
        loss = (sell_price - cost_basis) * qty

        # If loss realized
        if loss < 0:
            # Check for repurchases within ±30 days
            start_window = sell_date - timedelta(days=30)
            end_window = sell_date + timedelta(days=30)
            repurchases = trades[
                (trades['Ticker'] == ticker) &
                (trades['Type'] == 'BUY') &
                (trades['Date'].between(start_window, end_window)) &
                (trades['Date'] != first_buy['Date'])
            ]
            if not repurchases.empty:
                total_qty = repurchases['Quantity'].sum()
                disallowed_loss = min(qty, total_qty) * abs(loss / qty)
                results.append({
                    "Ticker": ticker,
                    "SellDate": sell_date.date(),
                    "Loss": round(loss, 2),
                    "DisallowedLoss": round(disallowed_loss, 2),
                    "AdjustedBasisAddedTo": repurchases.iloc[0]['Date'].date()
                })
    return pd.DataFrame(results)

# === Step 4: Apply to stocks only ===
wash_sales = detect_wash_sales(stocks)
print("Detected wash-sale disallowed losses:")
print(wash_sales if not wash_sales.empty else "None found")

# === Step 5: Optional – ignore options with different strikes/expirations ===
# (This script already excludes options, but you could extend it later if needed)
