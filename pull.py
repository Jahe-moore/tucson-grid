"""Re-pull every public source for Tucson Grid.

    python pull.py              # both halves: grid demand, weather, sales and reliability; storm reports, costs, CPI
    python pull.py --outages    # also re-stream EAGLE-I outage files (about 7 GB of national files, Pima rows kept)

Each half keeps its own inputs: peak/data/ (EIA-930, weather with day-ahead forecasts, EIA-861 sales and reliability)
and outages/data/ (EAGLE-I, NOAA, LBNL, CPI, weather with rain and wind). The outage paper reads the reliability
file from peak/data/, so there is one copy.
The two weather files differ in columns and years, so they stay separate. Both pullers pin their end dates.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(folder: str, *args: str) -> None:
    print(f"== {folder}")
    subprocess.run([sys.executable, *args], cwd=HERE / folder, check=True)


if __name__ == "__main__":
    run("peak", "pull.py")
    run("outages", "pull_data.py", *(["--outages"] if "--outages" in sys.argv else []))
