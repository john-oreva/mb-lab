from replay import build_replay


# function to score all forecasts that have a known next-session outcome
def main():
    scored = build_replay().dropna(subset=["forecast", "actual"])

    if scored.empty:
        raise SystemExit("No historical forecasts are ready to score.")

    absolute_errors = (scored["forecast"] - scored["actual"]).abs()

    print("Results | 20-session median baseline")
    print(f"Forecasts scored: {len(scored)}")
    print(f"Mean absolute error: {absolute_errors.mean():.2f} percentage points")


if __name__ == "__main__":
    main()