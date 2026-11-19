from pathlib import Path

import pandas as pd


SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
TICKERS = ("SPY", "RSP", *SECTORS)


#function to read the latest trading date and return for a ticker
def read_latest_return(symbol, data_dir="data"):
    path = Path(data_dir) / f"{symbol.lower()}.csv"
    prices = pd.read_csv(path, parse_dates=["Date"]).sort_values("Date")
    latest = prices.iloc[-1]
    return latest["Date"], latest["Daily return (%)"]


#function to check that the tickers share a date and print the market brief
def build_market_brief(data_dir="data"):
    latest = {
        symbol: read_latest_return(symbol, data_dir)
        for symbol in TICKERS
    }
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

        #describe how many sectors moved in the same direction as spy
    if spy_return == 0:
        breadth_summary = "SPY was flat."
    else:
        direction = "rose" if spy_return > 0 else "fell"
        same_direction = up if spy_return > 0 else down

        if same_direction >= 8:
            breadth = "broad"
        elif same_direction >= 5:
            breadth = "mixed"
        else:
            breadth = "narrow"

        breadth_summary = (
            f"SPY {direction} {abs(spy_return):.2f}% with {breadth} participation "
            f"({same_direction} of {len(SECTORS)} sectors also {direction})."
        )

    #compare the equal-weight return with the spy return
    spread = rsp_return - spy_return
    if abs(spread) < 0.005:
        weight_summary = "RSP and SPY had nearly identical returns."
    else:
        comparison = "outperformed" if spread > 0 else "lagged"
        weight_summary = f"RSP {comparison} SPY by {abs(spread):.2f} percentage points."

    return {
        "date": f"{session_date:%Y-%m-%d}",
        "summary": f"{breadth_summary} {weight_summary}",
        "spy_return": spy_return,
        "rsp_return": rsp_return,
        "sectors_up": up,
        "sectors_down": down,
        "sectors_flat": flat,
        "top_sector": f"{sector_returns.idxmax()} ({sector_returns.max():+.2f}%)",
        "bottom_sector": f"{sector_returns.idxmin()} ({sector_returns.min():+.2f}%)",
        "leaders": list(sector_returns.nlargest(2).items()),
        "laggards": list(sector_returns.nsmallest(2).items()),
    }

#function to display the market brief in the terminal
def main():
    brief = build_market_brief()
    print(f"Market Brief | {brief['date']}")
    print(brief["summary"])
    print(f"SPY {brief['spy_return']:+.2f}% | RSP {brief['rsp_return']:+.2f}%")
    print(
        f"Sectors: {brief['sectors_up']} up, {brief['sectors_down']} down, "
        f"{brief['sectors_flat']} flat"
    )
    print(f"Top sector ETF: {brief['top_sector']}")
    print(f"Bottom sector ETF: {brief['bottom_sector']}")

if __name__ == "__main__":
    main()