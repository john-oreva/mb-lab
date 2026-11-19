from pathlib import Path

import argparse
import numpy as np
import pandas as pd

from market_brief import SECTORS
from replay import build_replay


# function to calculate the share of sectors that rose on each complete date
def build_breadth():
    sector_returns = {}

    for symbol in SECTORS:
        path = Path("data") / f"{symbol.lower()}.csv"
        prices = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
        sector_returns[symbol] = prices["Daily return (%)"]

    returns = pd.DataFrame(sector_returns).dropna()
    return returns.gt(0).mean(axis=1).rename("breadth")


# function to fit a regression on earlier dates and predict later dates
def predict_range(train, test, features):
    train_inputs = train[features].assign(intercept=1).to_numpy()
    test_inputs = test[features].assign(intercept=1).to_numpy()

    coefficients, _, _, _ = np.linalg.lstsq(
        train_inputs, train["actual"].to_numpy(), rcond=None
    )
    return np.maximum(test_inputs @ coefficients, 0)


# function to score all three forecasts on the same later dates
def main():
    parser = argparse.ArgumentParser(description="Score or inspect historical forecasts.")
    parser.add_argument("--date", type=pd.Timestamp, help="forecast date in YYYY-MM-DD format")
    args = parser.parse_args()
    sessions = (
        build_replay()
        .join(build_breadth())
        .dropna(subset=["forecast", "actual", "breadth"])
        .sort_index()
    )

    if len(sessions) < 10:
        raise SystemExit("Need at least 10 complete sessions for this first comparison.")

    split = int(len(sessions) * 0.8)
    train = sessions.iloc[:split]
    test = sessions.iloc[split:]

    predictions = {
        "20-session median": test["forecast"],
        "Price only": predict_range(train, test, ["forecast"]),
        "Price + breadth": predict_range(train, test, ["forecast", "breadth"]),
    }

        # line up all three forecasts with the actual range for each test date
    comparison = pd.DataFrame(predictions, index=test.index)
    comparison["Actual"] = test["actual"]

    # show the forecasts and errors for one test date when requested
    if args.date is not None:
        if args.date not in comparison.index:
            raise SystemExit("Choose a forecast date from the test period.")

        row = comparison.loc[args.date]
        next_date = test.loc[args.date, "next_date"]

        print(f"Forecast as of close | {args.date:%Y-%m-%d}")
        print(f"Actual range on {next_date:%Y-%m-%d}: {row['Actual']:.3f}%")

        for label in predictions:
            error = abs(row[label] - row["Actual"])
            print(f"{label}: {row[label]:.3f}% | error: {error:.3f} percentage points")

        return

    print(f"Training sessions: {len(train)}")
    print(f"Test sessions: {len(test)}")
    print(f"Test dates: {test.index[0]:%Y-%m-%d} to {test.index[-1]:%Y-%m-%d}")

    for label, forecast in predictions.items():
        error = (test["actual"] - forecast).abs().mean()
        print(f"{label}: {error:.3f} percentage points MAE")


if __name__ == "__main__":
    main()