"""Build results.json for Tucson Grid: both halves' numbers plus Act 4, where the summer money goes.

    python combine.py               # after peak/analysis.py and the outage paper's deck/deck_charts.R
    python combine.py --refresh-cpi # re-pull the 2024 CPI-U average from BLS first

Act 4 puts the two halves side by side without forcing one ranking, because the units differ:
  - Storm outages are priced as what interruptions cost customers each year (LBNL cost model, 2025 dollars), and the
    improvement scenarios are benefits to customers. None include what the improvement would cost to make.
  - The evening ramp is measured in MW. A battery yardstick (NREL's 2024 cost for a 4-hour system, annualized
    straight-line over its 15-year life plus 2.5% a year fixed upkeep, no financing cost, so a floor) shows the order
    of magnitude of covering that MW, moved to 2025 dollars with CPI-U.
  - The hot-day forecast shortfall is shown in MW only. There is no public price for it.
"""
import json
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
PEAK = json.loads((HERE / "peak" / "results.json").read_text(encoding="utf-8"))
OUT = json.loads((HERE / "outages" / "deck" / "numbers.json").read_text(encoding="utf-8"))
CPI_FILE = HERE / "outages" / "data" / "cpi_u_annual.csv"

# Cole, Ramasamy and Turan, "Cost Projections for Utility-Scale Battery Storage: 2025 Update", NREL/TP-6A40-93281,
# June 2025, p. 8: "The 2024 starting point of $334/kWh" for a 4-hour system (2024$). Life and fixed O&M from the
# 2024 ATB utility-scale battery storage page ("15-year lifetime"; "FOM costs are estimated at 2.5% of the capital
# costs in $/kW").
BATTERY = {"usd_per_kwh_2024": 334, "hours": 4, "life_years": 15, "fom_share": 0.025,
           "source": "NREL/TP-6A40-93281 (June 2025), 2024 ATB utility-scale battery storage"}
CPI_2024 = 313.689  # BLS CPI-U (CUUR0000SA0) 2024 annual average, 12 months


def cpi_2024() -> float:
    if "--refresh-cpi" not in sys.argv:
        return CPI_2024
    r = requests.post("https://api.bls.gov/publicAPI/v1/timeseries/data/",
                      json={"seriesid": ["CUUR0000SA0"], "startyear": "2024", "endyear": "2024"}, timeout=60).json()
    vals = [float(d["value"]) for d in r["Results"]["series"][0]["data"] if d["period"] != "M13"]
    return round(sum(vals) / len(vals), 3)


def cpi_2025() -> float:
    rows = CPI_FILE.read_text().splitlines()[1:]
    return next(float(r.split(",")[1]) for r in rows if r.startswith("2025,"))


def solar_growth_same_window() -> float:
    """2026 only runs to Nov 2, and Nov-Dec are low-solar months, so compare Jan 1-Nov 2 in both years."""
    import duckdb
    con = duckdb.connect(str(HERE / "peak" / "data" / "grid.duckdb"), read_only=True)
    end = con.execute("SELECT strftime(max(day), '%m-%d') FROM hourly WHERE utility='TEP' AND year(day)=2026").fetchone()[0]
    s = dict(con.execute(f"""SELECT year(day), avg(solar) FROM hourly WHERE utility='TEP' AND year(day) IN (2025, 2026)
                             AND strftime(day, '%m-%d') <= '{end}' GROUP BY 1""").fetchall())
    con.close()
    return round((s[2026] / s[2025] - 1) * 100, 1)


def paper_checks() -> dict:
    """Numbers the reused outage slides and talk track quote from the paper's charts and tables, recomputed here from
    the outage half's raw files so the talk track can be checked against them."""
    import csv
    from datetime import datetime
    raw = HERE / "outages" / "data"
    # Worst night: 3 PM July 28 to 6 AM July 29, 2023, Arizona time (UTC-7); EAGLE-I times are UTC.
    lo, hi = datetime(2023, 7, 28, 22), datetime(2023, 7, 29, 13)
    with open(raw / "raw" / "eaglei_pima_2023.csv", newline="") as f:
        peak = max(int(float(r["sum"])) for r in csv.DictReader(f)
                   if lo <= datetime.fromisoformat(r["run_start_time"]) <= hi)
    with open(raw / "lbnl_cost_per_event_2013usd.csv", newline="") as f:
        lbnl = {r["customer_class"]: {k: float(v) for k, v in r.items() if k != "customer_class"} for r in csv.DictReader(f)}
    return {"worst_night_peak_customers": peak, "lbnl_cost_per_event_2013usd": lbnl}


def heat_slopes() -> dict:
    s = PEAK["TEP"]["heat"]["slope_above_breakpoint_by_year"]
    return {"heat_slope_mw_per_f_2024_2026": [s["2024"], s["2025"], s["2026"]]}


def act4() -> dict:
    tep = PEAK["TEP"]
    ramp = {r["year"]: r for r in tep["net_load"]["by_year"]}
    hot_peak = tep["heat"]["mean_summer_hot_day_peak_mw"]
    bands = {b["band"]: b for b in tep["forecast"]["daily_peak_by_temp"]}
    hot = [bands["90-100"], bands["100-105"]]
    hot_err = sum(b["mean_err_pct"] * b["days"] for b in hot) / sum(b["days"] for b in hot)

    to_2025 = cpi_2025() / cpi_2024()
    usd_per_kw = BATTERY["usd_per_kwh_2024"] * BATTERY["hours"] * to_2025
    usd_per_kw_year = usd_per_kw * (1 / BATTERY["life_years"] + BATTERY["fom_share"])

    growth_mean = ramp[2026]["mean_daily_max_3h_ramp_mw"] - ramp[2025]["mean_daily_max_3h_ramp_mw"]
    growth_p95 = ramp[2026]["p95_daily_3h_ramp_mw"] - ramp[2025]["p95_daily_3h_ramp_mw"]
    battery_2026 = next(r["battery"] for r in tep["supply_top100_hours"] if r["year"] == 2026)

    prevent, faster, night_full, night_half = OUT["scen"]
    return {
        "dollar_year": 2025,
        "cpi_2024_to_2025": round(to_2025, 4),
        "battery": {**BATTERY, "usd_per_kw_2025": round(usd_per_kw), "usd_per_kw_year_2025": round(usd_per_kw_year, 1)},
        "storms": {
            "customer_cost_per_year": OUT["avg_cost"], "range_low": OUT["sens_lo"], "range_high": OUT["sens_hi"],
            "monsoon_season_cost": OUT["mons_cost"], "worst_year": OUT["worst_year"],
            "benefit_10pct_fewer_interrupted": prevent, "benefit_10pct_faster": faster,
            "benefit_night_at_day_pace": night_full, "benefit_half_night_gap": night_half,
        },
        "ramp": {
            "mean_2025_mw": ramp[2025]["mean_daily_max_3h_ramp_mw"], "mean_2026_mw": ramp[2026]["mean_daily_max_3h_ramp_mw"],
            "growth_mean_mw": round(growth_mean, 1), "growth_p95_mw": round(growth_p95, 1),
            "battery_at_peak_2026_mw": battery_2026,
            "solar_growth_2026_pct": solar_growth_same_window(),
            "window_2026": "Jan 1 to Nov 2 (data cut); ramp growth on the same window in both years differs by under 1 MW",
            "yardstick_growth_mean_per_year": round(growth_mean * 1000 * usd_per_kw_year),
            "yardstick_growth_p95_per_year": round(growth_p95 * 1000 * usd_per_kw_year),
            "yardstick_growth_mean_capex": round(growth_mean * 1000 * usd_per_kw),
        },
        "hot_day_forecast": {
            "mean_err_pct_90_105f": round(hot_err, 2), "days_90_105f": sum(b["days"] for b in hot),
            "mean_hot_day_peak_mw": hot_peak, "shortfall_mw_90_105f": round(-hot_err / 100 * hot_peak),
            "err_pct_110f": bands["110+"]["mean_err_pct"], "days_110f": bands["110+"]["days"],
            "peak_at_110f_2026_mw": tep["growth"]["weather_adjusted_peak_at_110f_mw"]["2026"],
            "shortfall_mw_110f": round(-bands["110+"]["mean_err_pct"] / 100
                                       * tep["growth"]["weather_adjusted_peak_at_110f_mw"]["2026"]),
        },
    }


def act4_chart(a: dict) -> None:
    """Two panels, never one ranking: customer cost and benefits ($M a year) vs the MW at stake and its yardstick."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s, r, h = a["storms"], a["ramp"], a["hot_day_forecast"]
    f, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=150, gridspec_kw={"width_ratios": [1.25, 1]})
    # Customer side on top; the battery yardstick sits apart below a divider, because it is a utility cost, not a
    # customer cost or benefit, and the two should not read as one ranking.
    rows = [("Storm outages, cost to customers", s["customer_cost_per_year"], "#1B2A41", 5.6),
            ("Benefit: 10% fewer customers hit", s["benefit_10pct_fewer_interrupted"], "#5B7FA6", 4.6),
            ("Benefit: 10% faster restoration", s["benefit_10pct_faster"], "#5B7FA6", 3.6),
            ("Benefit: night outages at day pace", s["benefit_night_at_day_pace"], "#5B7FA6", 2.6),
            ("Utility cost yardstick: batteries\nfor one year of ramp growth", r["yardstick_growth_mean_per_year"],
             "#D95926", 0.6)]
    for label, v, c, y in rows:
        ax1.barh(y, v / 1e6, color=c, hatch="//" if y < 1 else None, edgecolor="white" if y < 1 else None)
        ax1.text(v / 1e6 + 1, y, f"${v / 1e6:.1f}M", va="center", fontsize=9)
    ax1.axhline(1.6, color="#5F6B7A", lw=0.8, ls=(0, (4, 3)))
    ax1.text(s["customer_cost_per_year"] / 1e6 * 1.18, 1.75, "customers above, utility below",
             ha="right", va="bottom", fontsize=7.5, color="#5F6B7A")
    ax1.set_yticks([x[3] for x in rows], [x[0] for x in rows], fontsize=9)
    ax1.set_xlabel("$ millions a year (2025 dollars)")
    ax1.set_xlim(0, s["customer_cost_per_year"] / 1e6 * 1.2)
    ax1.set_title("What it costs and what fixes are worth", loc="left", fontsize=11, fontweight="bold", color="#1B2A41")
    mw = [("Hot-day forecast shortfall, 90-105°F", h["shortfall_mw_90_105f"]),
          ("Hot-day forecast shortfall, 110°F+", h["shortfall_mw_110f"]),
          ("Evening ramp growth, 2025 to 2026", r["growth_mean_mw"]),
          ("Ramp growth on the hardest 5% of days", r["growth_p95_mw"]),
          ("Battery output at peak, 2026", r["battery_at_peak_2026_mw"])]
    for i, (label, v) in enumerate(mw[::-1]):
        ax2.barh(i, v, color="#D95926" if "Battery" not in label else "#2E7D5B")
        ax2.text(v + 4, i, f"{v:,.0f} MW", va="center", fontsize=9)
    ax2.set_yticks(range(len(mw)), [x[0] for x in mw[::-1]], fontsize=9)
    ax2.set_xlim(0, max(v for _, v in mw) * 1.25)
    ax2.set_xlabel("Megawatts")
    ax2.set_title("The grid side, in megawatts", loc="left", fontsize=11, fontweight="bold", color="#1B2A41")
    for ax in (ax1, ax2):
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    f.text(0.99, 0.01, "Benefits exclude what each fix would cost. Battery yardstick: NREL 2024 cost, 15-year life, "
           "no financing. Sources: EAGLE-I, LBNL, EIA-930, NREL.", ha="right", fontsize=7, color="#5F6B7A")
    f.tight_layout(rect=(0, 0.03, 1, 1))
    (HERE / "charts").mkdir(exist_ok=True)
    f.savefig(HERE / "charts" / "act4_where_the_money_goes.png", facecolor="white")
    plt.close(f)


if __name__ == "__main__":
    out = {"peak": {k: PEAK.get(k) for k in ("TEP", "APS", "SRP", "arizona", "meta")},
           "outages": {**OUT, "paper_checks": paper_checks()}, "act4": {**act4(), **heat_slopes()}}
    (HERE / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    act4_chart(out["act4"])
    print(json.dumps(out["act4"], indent=2))
