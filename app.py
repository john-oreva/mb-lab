from html import escape
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

import boto3
from botocore.exceptions import BotoCoreError, ClientError

import streamlit as st
from streamlit.components.v1 import html

from market_brief import TICKERS, build_market_brief
from results import build_comparison


st.set_page_config(page_title="Market Breadth Lab", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: #0d131d;
    }
    .block-container {
        max-width: 1080px;
        padding: 3rem 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SECTOR_NAMES = {
    "XLB": "Materials",
    "XLC": "Communication Services",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
}


#function to render a label and its value on opposite sides of a row
def row(label, value, tone=""):
    return (
        f'<div class="row"><span>{escape(str(label))}</span>'
        f'<strong class="{tone}">{escape(str(value))}</strong></div>'
    )


#function to format a return and color it by direction
def return_row(label, value):
    tone = "up" if value > 0 else "down" if value < 0 else ""
    return row(label, f"{value:+.2f}%", tone)


data_root = Path(__file__).resolve().parent / "data"
current = data_root / "current"
data_dir = current.resolve() if current.is_dir() else data_root

csv_names = [f"{ticker.lower()}.csv" for ticker in TICKERS]

if all((data_dir / name).is_file() for name in csv_names):
    brief = build_market_brief(data_dir)
    train, test, comparison = build_comparison(data_dir)
else:
    try:
        client = boto3.client(
            "s3",
            endpoint_url=st.secrets["R2_ENDPOINT_URL"],
            aws_access_key_id=st.secrets["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        response = client.get_object(
            Bucket=st.secrets["R2_BUCKET"],
            Key="latest.zip",
        )
        with response["Body"] as body:
            snapshot_bytes = body.read()

        with TemporaryDirectory() as folder, ZipFile(BytesIO(snapshot_bytes)) as archive:
            snapshot_dir = Path(folder)
            for name in csv_names:
                (snapshot_dir / name).write_bytes(archive.read(name))

            brief = build_market_brief(snapshot_dir)
            train, test, comparison = build_comparison(snapshot_dir)

    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code in {"NoSuchKey", "404"}:
            st.title("Market Breadth Lab")
            st.info("Waiting for the first complete market update.")
        else:
            st.error("Could not read the market snapshot from R2.")
        st.stop()
    except (FileNotFoundError, KeyError, BotoCoreError, BadZipFile):
        st.error("Could not load the market snapshot. Check the R2 settings and bundle.")
        st.stop()

model_columns = comparison.columns.drop("Actual")
actuals = comparison["Actual"]
errors = comparison[model_columns].sub(actuals, axis=0).abs().mean()

spy_return = brief["spy_return"]
up, down, flat = (
    int(brief["sectors_up"]),
    int(brief["sectors_down"]),
    int(brief["sectors_flat"]),
)

if spy_return > 0:
    headline = f"SPY rose. {up} sectors rose with it."
elif spy_return < 0:
    headline = f"SPY fell. {down} sectors fell with it."
else:
    headline = "SPY closed flat."

strip = (
    '<span class="up"></span>' * up
    + '<span class="down"></span>' * down
    + '<span class="flat"></span>' * flat
)
sector_rows = "".join(
    return_row(SECTOR_NAMES.get(symbol, symbol), value)
    for symbol, value in brief["leaders"] + brief["laggards"]
)
result_rows = "".join(row(model, f"{errors[model]:.3f} pp") for model in model_columns)

#build one replay panel per forecast date using the same rows as results
date_options = []
replay_panels = []

for forecast_date in reversed(comparison.index):
    date = forecast_date.strftime("%Y-%m-%d")
    session = comparison.loc[forecast_date]
    next_date = test.loc[forecast_date, "next_date"]
    actual = session["Actual"]

    date_options.append(f'<option value="{date}">{date}</option>')
    forecast_rows = "".join(
        row(model, f"{session[model]:.3f}%") for model in model_columns
    )
    error_rows = "".join(
        row(model, f"{abs(session[model] - actual):.3f} pp") for model in model_columns
    )
    replay_panels.append(
        f"""
        <article class="card replay-session" id="session-{date}" hidden>
          <h2>Forecast as of the {date} close</h2>
          {forecast_rows}
          <details>
            <summary>Reveal the next session’s outcome</summary>
            {row(f"Actual range on {next_date:%Y-%m-%d}", f"{actual:.3f}%")}
            <h3>Absolute error</h3>
            {error_rows}
          </details>
        </article>
        """
    )

brief_date = escape(brief["date"])
has_brief_replay = any(date.strftime("%Y-%m-%d") == brief["date"] for date in comparison.index)
replay_button = "Replay this session →" if has_brief_replay else "Explore past sessions →"

styles = """
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    color: #edf3fa;
    background: #0d131d;
    font: 15px/1.55 "Instrument Sans", system-ui, sans-serif;
}
[hidden] { display: none !important; }
.lab {
    background: #121923;
    border: 1px solid #344258;
    border-radius: 18px;
    overflow: hidden;
}
header {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px 24px;
    padding: 17px clamp(16px, 4%, 32px);
    background: #172232;
    border-bottom: 1px solid #344258;
}
.brand { display: flex; align-items: center; gap: 9px; font-weight: 750; }
.brand-mark { display: inline-flex; align-items: flex-end; gap: 3px; }
.brand-mark i { width: 2px; height: 6px; background: currentColor; border-radius: 1px; }
.brand-mark i:nth-child(2) { height: 14px; }
.brand-mark i:nth-child(3) { height: 10px; }
nav { display: flex; flex-wrap: wrap; gap: 4px; }
button, select, summary { font: inherit; cursor: pointer; }
button {
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 13px;
    color: #b1bfd1;
    background: transparent;
}
button[aria-pressed="true"], button.action {
    color: #acccff;
    background: #243552;
    font-weight: 700;
}
button.action { border-color: #344258; margin-top: 12px; }
button:focus-visible, select:focus-visible, summary:focus-visible {
    outline: 2px solid #acccff;
    outline-offset: 2px;
}
main { padding: 23px clamp(16px, 4%, 32px) 28px; }
.eyebrow {
    color: #b1bfd1;
    font-size: 12px;
    letter-spacing: .09em;
    text-transform: uppercase;
}
h1 { font-size: clamp(26px, 4.2vw, 40px); line-height: 1.12; letter-spacing: -.04em; margin: 7px 0 10px; }
h2 { font-size: 17px; margin: 0 0 10px; }
h3 { font-size: 14px; margin: 12px 0 4px; }
p { color: #b1bfd1; margin: 0 0 17px; }
.grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 14px; }
.card { background: #172232; border: 1px solid #344258; border-radius: 13px; padding: 16px; }
.row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #344258;
    font-variant-numeric: tabular-nums;
}
.row:last-child { border-bottom: 0; }
.row strong { white-space: nowrap; }
.up { color: #68ddbc; }
.down { color: #f394a4; }
.strip { display: flex; gap: 4px; margin: 12px 0 10px; }
.strip span { flex: 1; height: 9px; border-radius: 2px; background: #8899af; }
.strip .up { background: #68ddbc; }
.strip .down { background: #f394a4; }
small { color: #b1bfd1; }
.controls { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
select { color: inherit; background: #172232; border: 1px solid #344258; border-radius: 8px; padding: 7px 10px; }
details { margin-top: 13px; }
summary { color: #acccff; }
@media (max-width: 600px) {
    .grid { grid-template-columns: 1fr; }
    header { gap: 8px; }
}
</style>
"""

markup = f"""
<div class="lab">
  <header>
    <div class="brand">
      <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>
      Market Breadth Lab
    </div>
    <nav aria-label="Dashboard views">
      <button type="button" data-view="brief" aria-pressed="true">Market Brief</button>
      <button type="button" data-view="replay" aria-pressed="false">Replay</button>
      <button type="button" data-view="results" aria-pressed="false">Results</button>
    </nav>
  </header>

  <main>
    <section data-panel="brief">
      <div class="eyebrow">SPY · After the close · {brief_date}</div>
      <h1>{escape(headline)}</h1>
      <p>{escape(brief["summary"])}</p>

      <div class="grid">
        <article class="card">
          <h2>Market participation</h2>
          {return_row("SPY", spy_return)}
          {return_row("Equal-weight benchmark (RSP)", brief["rsp_return"])}
          <div class="strip" aria-hidden="true">{strip}</div>
          <small>{up} sectors rose · {down} fell · {flat} flat</small>
        </article>

        <article class="card">
          <h2>Sector leaders and laggards</h2>
          {sector_rows}
        </article>
      </div>

      <button type="button" class="action" id="open-replay" data-date="{brief_date}">
        {replay_button}
      </button>
    </section>

    <section data-panel="replay" hidden>
      <div class="eyebrow">Historical replay</div>
      <h1>What happened next?</h1>
      <p>Compare the three forecasts, then reveal the actual trading range.</p>
      <div class="controls">
        <label for="forecast-date">Forecast date</label>
        <select id="forecast-date">{"".join(date_options)}</select>
      </div>
      {"".join(replay_panels)}
    </section>

    <section data-panel="results" hidden>
      <div class="eyebrow">Backtest · {len(test)} test sessions</div>
      <h1>Did breadth improve the forecast?</h1>
      <p>
        {len(train)} training sessions ·
        {test.index[0]:%Y-%m-%d} to {test.index[-1]:%Y-%m-%d} test period.
        Lower error is better.
      </p>
      <article class="card">
        <h2>Mean absolute error</h2>
        {result_rows}
        <small>pp = percentage points</small>
      </article>
    </section>
  </main>
</div>
"""

scripts = """
<script>
const tabs = document.querySelectorAll("[data-view]");
const panels = document.querySelectorAll("[data-panel]");
const datePicker = document.getElementById("forecast-date");
const replays = document.querySelectorAll(".replay-session");
const replayButton = document.getElementById("open-replay");

function showView(view) {
    for (const tab of tabs) {
        tab.setAttribute("aria-pressed", String(tab.dataset.view === view));
    }
    for (const panel of panels) {
        panel.hidden = panel.dataset.panel !== view;
    }
}

function showSession() {
    for (const replay of replays) {
        replay.hidden = replay.id !== "session-" + datePicker.value;
        replay.querySelector("details").open = false;
    }
}

for (const tab of tabs) {
    tab.addEventListener("click", () => showView(tab.dataset.view));
}

datePicker.addEventListener("change", showSession);

replayButton.addEventListener("click", () => {
    const date = replayButton.dataset.date;
    if (Array.from(datePicker.options).some(option => option.value === date)) {
        datePicker.value = date;
    }
    showSession();
    showView("replay");
    datePicker.focus();
});

showSession();
</script>
"""

html(styles + markup + scripts, height=820, scrolling=True)