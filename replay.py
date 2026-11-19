import argparse

from pathlib import Path

import pandas as pd


#function to build historical spy forecasts and attach the next session's outcome
def build_replay(data_dir="data"):
    prices = pd.read_csv(Path(data_dir) / "spy.csv", parse_dates=["Date"])
    prices = prices.sort_values("Date").set_index("Date")

    daily_range = (prices["High"] - prices["Low"]) / prices["Close"].shift(1) * 100

    return pd.DataFrame({
        "forecast": daily_range.rolling(20).median(),
        "next_date": prices.index.to_series().shift(-1),
        "actual": daily_range.shift(-1),
    })

#function to compare a past spy range forecast with the actual next session
def main():
    parser = argparse.ArgumentParser(description="Replay a past SPY forecast.")
    parser.add_argument("date", help="forecast date in YYYY-MM-DD format")
    args = parser.parse_args()

    replay = build_replay()

    forecast_date = pd.Timestamp(args.date)
    if forecast_date not in replay.index:
        raise SystemExit("Choose a trading date from data/spy.csv.")

    session = replay.loc[forecast_date]
    if pd.isna(session["forecast"]):
        raise SystemExit("Choose a later date with 20 daily ranges available.")
    if pd.isna(session["actual"]):
        raise SystemExit("Choose an earlier date with a next session in the CSV.")

    error = abs(session["forecast"] - session["actual"])
    print(f"Forecast as of close | {forecast_date:%Y-%m-%d}")
    print(f"Forecast range: {session['forecast']:.2f}%")
    print(f"Actual range on {session['next_date']:%Y-%m-%d}: {session['actual']:.2f}%")
    print(f"Absolute error: {error:.2f} percentage points")


if __name__ == "__main__":
    main()