import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from market_brief import TICKERS


ROOT = Path(__file__).resolve().parent
SNAPSHOTS = ROOT / "data" / "snapshots"
CURRENT = ROOT / "data" / "current"


# function to download and validate a complete snapshot before publishing it
def refresh_prices():
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)

    # keep each refresh in its own directory so readers see a complete snapshot
    snapshot = Path(tempfile.mkdtemp(prefix="session-", dir=SNAPSHOTS))
    next_link = snapshot / "publish-link"

    try:
        for index, symbol in enumerate(TICKERS):
            if index > 0:
                time.sleep(2)

            subprocess.run(
                [sys.executable, str(ROOT / "download_prices.py"), symbol],
                cwd=snapshot,
                check=True,
            )

        # run the existing checks on the staged csvs
        for script in ("market_brief.py", "results.py"):
            subprocess.run(
                [sys.executable, str(ROOT / script)],
                cwd=snapshot,
                check=True,
            )

        # switch the pointer only after every download and check succeeds
        next_link.symlink_to(snapshot / "data", target_is_directory=True)
        os.replace(next_link, CURRENT)
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            "Refresh failed. The last published snapshot is still selected, "
            "if one exists."
        ) from error

    print(f"Published complete snapshot at {CURRENT}")


if __name__ == "__main__":
    refresh_prices()