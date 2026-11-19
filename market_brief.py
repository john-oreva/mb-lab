from pathlib import Path

import pandas as pd


SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
TICKERS = ("SPY", "RSP", *SECTORS)


# function to read the latest trading date and return for a ticker
def read_latest_return(symbol):
    path = Path("data") / f"{symbol.lower()}.csv"
    prices = pd.read_csv(path, parse_dates=["Date"]).sort_values("Date")
    latest = prices.iloc[-1]
    return latest["Date"], latest["Daily return (%)"]


# function to check that the tickers share a date and print the market brief
def main():
    latest = {symbol: read_latest_return(symbol) for symbol in TICKERS}
    session_date = latest["SPY"][0]
    mismatched = [symbol for symbol in TICKERS if latest[symbol][0] != session_date]

    if mismatched:
        raise SystemExit(f"Latest trading dates differ from SPY for: {', '.join(mismatched)}")

    spy_return = latest["SPY"][1]
    rsp_return = latest["RSP"][1]
    sector_returns = pd.Series({symbol: latest[symbol][1] for symbol in SECTORS})
    up = (sector_returns > 0).sum()
    down = (sector_returns < 0).sum()
    flat = len(SECTORS) - up - down

    print(f"Market Brief | {session_date:%Y-%m-%d}")
    print(f"SPY {spy_return:+.2f}% | RSP {rsp_return:+.2f}%")
    print(f"Sectors: {up} up, {down} down, {flat} flat")
    print(f"Top sector ETF: {sector_returns.idxmax()} ({sector_returns.max():+.2f}%)")
    print(f"Bottom sector ETF: {sector_returns.idxmin()} ({sector_returns.min():+.2f}%)")


if __name__ == "__main__":
    main()