import argparse
import os
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


# function to download daily prices for a ticker from alpha vantage
def download_prices(symbol, api_key):
    try:
        response = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "datatype": "csv",
                "apikey": api_key,
            },
            timeout=30,
        )
    except requests.RequestException:
        raise SystemExit("Could not connect to Alpha Vantage.") from None

    if not response.ok:
        raise SystemExit(f"Alpha Vantage returned HTTP {response.status_code}.")

    csv_text = response.text.lstrip("\ufeff").strip()
    if not csv_text.lower().startswith("timestamp,open,high,low,close,"):
        raise SystemExit(
            "Alpha Vantage did not return a price CSV. Check your key, "
            "daily request limit, and endpoint access."
        )

    prices = pd.read_csv(StringIO(csv_text), parse_dates=["timestamp"])
    prices = prices.rename(
        columns={
            "timestamp": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    return prices.sort_values("Date")


# function to calculate daily returns and save prices for a ticker
def main():
    parser = argparse.ArgumentParser(description="Download daily ETF prices.")
    parser.add_argument("symbol", help="ticker to download, such as SPY or RSP")
    symbol = parser.parse_args().symbol.upper()

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise SystemExit("Set ALPHA_VANTAGE_API_KEY before running this script.")

    prices = download_prices(symbol, api_key)
    if len(prices) < 2:
        raise SystemExit("Need at least two trading days to calculate a return.")

    # compare each closing price with the previous session's close
    prices["Daily return (%)"] = prices["Close"].pct_change() * 100

    output_path = Path("data") / f"{symbol.lower()}.csv"
    output_path.parent.mkdir(exist_ok=True)
    prices.to_csv(output_path, index=False)

    # print the two latest closes so you can verify the last return by hand
    columns = ["Date", "Close", "Daily return (%)"]
    print(prices[columns].tail(2).to_string(index=False))
    print(f"\nSaved {len(prices):,} rows to {output_path}")


if __name__ == "__main__":
    main()