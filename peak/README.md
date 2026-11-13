# Arizona Grid Peak Demand: TEP, APS and SRP

A public-data analysis of Arizona's three large balancing areas: what drives the summer peak, how much load is growing
once weather is removed, how accurate each day-ahead load forecast is, how solar and storage are reshaping the evening
ramp, what covers the peak hours, and how reliability compares. One memo per utility, plus a comparison:

| Memo | Focus |
|---|---|
| [MEMO.md](MEMO.md) | Tucson Electric Power |
| [MEMO_APS.md](MEMO_APS.md) | Arizona Public Service |
| [MEMO_SRP.md](MEMO_SRP.md) | Salt River Project |
| [MEMO_ARIZONA.md](MEMO_ARIZONA.md) | All three side by side |

Not affiliated with, endorsed by, or using any information from any of the three utilities.

## Findings

- All three add about 2% of their hot-day peak per °F above 80-84°F, and they peak together in the 5-6 PM hour.
- With weather removed, average load since 2024 grew 10.8% in the AZPS area, 2.6% at SRP and 1.7% at TEP. The AZPS
  area's load is heavily around the clock: its summer overnight low stays at two-thirds of its peak hour.
- Day-ahead forecasts: TEP and SRP are statistically tied (3.0% vs 2.9% MAPE, Aug 2023-Jan 2025) and APS trails by
  about a point. Since February 2025, APS's forecast and its reported area demand have diverged by a steady
  450-700 MW overnight block, cause unresolved.
- APS's average daily three-hour evening ramp doubled to 2,104 MW as utility solar reached 42% of midday load.

## Run it

```
pip install pandas duckdb matplotlib requests openpyxl
python pull.py        # downloads and filters every source into data/ (a few minutes)
python analysis.py    # builds data/grid.duckdb, writes results.json and charts/<utility>/
python build_memos.py # renders the four memos into peak_demand_memos.html
```

`pull.py` is pinned to an end date and `analysis.py` to a data cut (`DATA_END`), so a rerun reproduces the memos.

## Data

| Source | Used for |
|---|---|
| [EIA-930](https://www.eia.gov/electricity/gridmonitor/) hourly balancing-authority files | Load, day-ahead forecast, generation by fuel, interchange and imputation flags for TEPC, AZPS and SRP |
| [EIA-861](https://www.eia.gov/electricity/data/eia861/) | Retail sales and customers by sector; SAIDI, SAIFI and CAIDI with and without major event days |
| [Open-Meteo](https://open-meteo.com/) archive and previous-runs APIs | Hourly temperature, humidity and dew point for Tucson and Phoenix, and the archived day-ahead temperature forecast |

`pull.py` streams each EIA-930 file (about 45 MB, every U.S. area) and keeps only the three Arizona areas.

## Method

- **Reporting breaks first.** Each forecast series is checked month by month, and each break is classified by its
  hour-of-day shape and against EIA-861 retail sales: TEP's forecast is scored from August 2023, SRP's through
  February 2026 (a flat 340-580 MW block appears after it), APS's through January 2025 (reported area demand steps
  about 600 MW above the forecast overnight in February 2025 while APS's retail sales barely move).
- **Growth.** Year effects in a model of daily load on cooling and heating degrees and weekday/holiday.
- **Heat.** Two-segment fit of daily peak on daily high, with year effects so growth does not bend the slope; summer
  model adds overnight low and dew point; heat-wave days compared with what their own weather predicts.
- **Forecast.** Hot days picked by temperature; 95% intervals resample 14-day blocks of days (misses persist); paired daily differences between
  utilities; out-of-time test of a lagged bias correction; weather surprise from the archived day-ahead model with its
  steady offset removed.
- **Net load and supply.** Load minus utility-scale solar and wind; battery figures only from each area's first
  reported hour. Interchange is physical flow across the area boundary, which includes remote and jointly owned plants.

## Files

| File | What it is |
|---|---|
| `MEMO*.md` | The four memos |
| `pull.py` | Downloads every source into `data/` |
| `analysis.py` | DuckDB load, break diagnosis, the six sections per utility, the comparison, charts |
| `results.json` | Every number the memos quote, keyed by utility and `arizona` |
| `charts/` | `tep/`, `aps/`, `srp/` and `arizona/` figures |
| `PLAN.md` | Project plan and rules |
