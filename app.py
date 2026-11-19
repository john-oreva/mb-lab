import streamlit as st

from market_brief import build_market_brief
from results import build_comparison


st.set_page_config(page_title="Market Breadth Lab")
st.title("Market Breadth Lab")
st.header("Market Brief")

brief = build_market_brief()

st.caption(f"Trading session · {brief['date']}")
st.write(brief["summary"])

spy_column, rsp_column = st.columns(2)
spy_column.metric("SPY", f"{brief['spy_return']:+.2f}%")
rsp_column.metric("RSP", f"{brief['rsp_return']:+.2f}%")

st.write(
    f"{brief['sectors_up']} sectors up · "
    f"{brief['sectors_down']} down · "
    f"{brief['sectors_flat']} flat"
)
st.write(f"Top sector ETF: {brief['top_sector']}")
st.write(f"Bottom sector ETF: {brief['bottom_sector']}")

st.divider()
st.header("Results")

train, test, comparison = build_comparison()
model_columns = comparison.columns.drop("Actual")

# calculate each model's average error across the same test sessions
errors = comparison[model_columns].sub(comparison["Actual"], axis=0).abs().mean()

st.caption(
    f"{len(train)} training sessions · {len(test)} test sessions · "
    f"Forecast dates {test.index[0]:%Y-%m-%d} to {test.index[-1]:%Y-%m-%d}"
)
st.dataframe(errors.round(3).rename("Mean absolute error (percentage points)").to_frame())

st.divider()
st.header("Replay")

forecast_date = st.selectbox(
    "Forecast date",
    options=comparison.index[::-1].tolist(),
    format_func=lambda date: date.strftime("%Y-%m-%d"),
)

session = comparison.loc[forecast_date]
forecasts = session[model_columns].astype(float)

st.dataframe(forecasts.round(3).rename("Forecast range (%)").to_frame())

if st.checkbox("Reveal the next session's outcome"):
    next_date = test.loc[forecast_date, "next_date"]
    actual = session["Actual"]
    errors = (forecasts - actual).abs()

    st.write(f"Actual range on {next_date:%Y-%m-%d}: **{actual:.3f}%**")
    st.dataframe(errors.round(3).rename("Absolute error (percentage points)").to_frame())