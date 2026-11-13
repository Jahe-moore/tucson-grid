"""Deep analysis of Arizona's three large balancing areas (TEP, APS, SRP), then a comparison across them.

    python pull.py && python analysis.py

Writes data/grid.duckdb (regenerated each run), results.json (every number the memos quote, keyed by utility, plus
"arizona") and charts/<utility>/*.png and charts/arizona/*.png.

Scope: demand, forecast and generation are balancing-area figures (EIA-930), which cover more than each utility's own
retail customers; sales, customers and reliability are utility-level (EIA-861). Arizona has no daylight saving time, so
local time is UTC-7 all year. EIA labels each value at the end of the hour; hours here are hour-starting (17 = 5-6 PM).
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA, CHARTS = HERE / "data", HERE / "charts"
DATA_END = "2026-11-03 01:00:00"  # the memos' data cut (EIA revises the latest week); raise it to refresh
RNG = np.random.default_rng(7)
R: dict = {}

# Per-utility settings. "fc" is the window where the utility's day-ahead forecast is scored; each window comes from the
# break diagnosis in section 0 (results.json <utility>.breaks and the memos' data notes).
U = {
    "TEP": {"code": "TEPC", "city": "tucson", "fc": ("2023-08-01", DATA_END),
            "why": "Before Aug 2023 the forecast ran ~13% above demand while in-area gas output doubled the same month: "
                   "a change in what the series covers."},
    "APS": {"code": "AZPS", "city": "phoenix", "fc": ("2022-01-01", "2025-01-31 23:00:00"),
            "diverge": ("2025-02-01", DATA_END),
            "why": "In Feb 2025 reported area demand stepped ~600 MW above the forecast overnight in one month and has "
                   "stayed there, while APS's own retail sales rose only 1.5% in 2025: forecast and reported area "
                   "demand diverge, cause unresolved. Scored through Jan 2025; later months reported separately."},
    "SRP": {"code": "SRP", "city": "phoenix", "fc": ("2022-01-01", "2026-02-28 23:00:00"),
            "load_end": "2026-02-28 23:00:00",
            "why": "From Mar 2026 the forecast sits a flat 500-700 MW above reported demand in every hour, and "
                   "weather-adjusted load drops the same year: reported demand stopped covering a block of load. "
                   "Later months are excluded from forecast scoring and growth."},
}
PEER = ("2023-08-01", "2025-01-31")  # all three forecast series stable
NAMES = list(U)
HOURS = ([0, 6, 12, 15, 18, 21], ["12a", "6a", "12p", "3p", "6p", "9p"])

C = {"TEP": "#2a78d6", "APS": "#eb6834", "SRP": "#1baf7a", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
     "grid": "#e1e0d9", "axis": "#c3c2b7", "surface": "#fcfcfb"}
plt.rcParams.update({"figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "axes.edgecolor": C["axis"],
                     "axes.labelcolor": C["ink2"], "xtick.color": C["muted"], "ytick.color": C["muted"],
                     "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
                     "axes.titlecolor": C["ink"], "axes.titlelocation": "left", "lines.linewidth": 2,
                     "legend.frameon": False, "savefig.dpi": 160})


# ---------------------------------------------------------------- load
def load() -> duckdb.DuckDBPyConnection:
    db = DATA / "grid.duckdb"
    db.unlink(missing_ok=True)
    (DATA / "tep.duckdb").unlink(missing_ok=True)  # v1 database name
    con = duckdb.connect(str(db))
    num = lambda c: f"TRY_CAST({c} AS DOUBLE)"  # noqa: E731
    con.execute(f"""
        CREATE TABLE grid AS
        SELECT CASE ba WHEN 'TEPC' THEN 'TEP' WHEN 'AZPS' THEN 'APS' ELSE ba END AS utility,
               strptime(utc_end, '%m/%d/%Y %I:%M:%S %p') - INTERVAL 7 HOUR AS local_end,
               {num('demand_forecast_mw')} AS forecast, {num('demand_mw')} AS demand_raw, {num('demand_adj_mw')} AS demand,
               {num('demand_imputed_mw')} AS demand_imputed, {num('netgen_adj_mw')} AS netgen,
               {num('interchange_adj_mw')} AS interchange, {num('coal_mw')} AS coal, {num('gas_mw')} AS gas,
               {num('solar_mw')} AS solar, {num('wind_mw')} AS wind, {num('battery_mw')} AS battery,
               {num('hydro_mw')} AS hydro
        FROM read_csv('{(DATA / "eia930_arizona.csv").as_posix()}', header=true, all_varchar=true)""")
    con.execute("CREATE TABLE weather (city VARCHAR, local_time TIMESTAMP, temp_f DOUBLE, rh_pct DOUBLE, "
                "dewpoint_f DOUBLE, temp_f_dayahead DOUBLE)")
    for city in ("tucson", "phoenix"):
        con.execute(f"""INSERT INTO weather SELECT '{city}', CAST(local_time AS TIMESTAMP), temp_f, rh_pct, dewpoint_f,
                        temp_f_dayahead FROM read_csv_auto('{(DATA / f"{city}_weather_hourly.csv").as_posix()}')""")
    con.execute(f"CREATE TABLE reliability AS SELECT * FROM read_csv_auto('{(DATA / 'eia861_reliability.csv').as_posix()}')")
    con.execute(f"CREATE TABLE sales AS SELECT * FROM read_csv_auto('{(DATA / 'eia861_sales.csv').as_posix()}')")
    city = " ".join(f"WHEN '{u}' THEN '{v['city']}'" for u, v in U.items())
    cutoff = con.execute(f"SELECT least(max(local_end) - INTERVAL 7 DAY, TIMESTAMP '{DATA_END}') FROM grid").fetchone()[0]
    con.execute(f"""
        CREATE TABLE hourly AS
        SELECT g.*, w.temp_f, w.rh_pct, w.dewpoint_f, w.temp_f_dayahead,
               CAST(g.local_end - INTERVAL 1 HOUR AS DATE) AS day, hour(g.local_end - INTERVAL 1 HOUR) AS hour
        FROM grid g JOIN weather w ON w.city = CASE g.utility {city} END AND w.local_time = g.local_end
        WHERE g.local_end <= TIMESTAMP '{cutoff}'""")
    R["meta"] = {"data_start": str(con.execute("SELECT min(day) FROM hourly").fetchone()[0]),
                 "data_end": str(cutoff)[:10], "peer_window": list(PEER),
                 "forecast_windows": {u: [v["fc"][0], v["fc"][1][:10]] for u, v in U.items()},
                 "window_reasons": {u: v["why"] for u, v in U.items()}}
    return con


HOLIDAYS = set(USFederalHolidayCalendar().holidays("2022-01-01", "2026-12-31").date)
SHAPE_YEAR = {"TEP": 2026, "APS": 2026, "SRP": 2025}  # SRP's 2026 summer is after its coverage change


def full_years(u: str) -> str:
    """SQL filter: drop months after a coverage change and the partial year it leaves behind."""
    end = U[u].get("load_end")
    return f"local_end <= TIMESTAMP '{end}' AND year(day) < {end[:4]}" if end else "TRUE"


def daily(con, u: str) -> pd.DataFrame:
    d = con.execute(f"""
        SELECT day, max(demand) AS peak, avg(demand) AS mean_load,
               CASE WHEN count(forecast) = count(*) THEN max(forecast) END AS fc_peak,  -- full-day forecasts only
               CASE WHEN count(forecast) = count(*) THEN arg_max(hour, forecast) END AS fc_peak_hour,
               arg_max(hour, demand) AS peak_hour,
               max(temp_f) AS tmax, min(temp_f) AS tmin, avg(temp_f) AS tmean, max(temp_f_dayahead) AS tmax_fc,
               avg(dewpoint_f) AS dew, count(*) AS n
        FROM hourly WHERE utility='{u}' GROUP BY day HAVING count(*) >= 22 ORDER BY day""").df()
    d["day"] = pd.to_datetime(d["day"])
    d["weekend"] = ((d.day.dt.dayofweek >= 5) | d.day.dt.date.isin(HOLIDAYS)).astype(float)
    d["year"] = d.day.dt.year
    d["summer"] = d.day.dt.month.isin([6, 7, 8, 9])
    return d.dropna(subset=["peak", "tmax", "mean_load"]).reset_index(drop=True)


def ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((X @ b - y) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return b, float(r2)


def block_picks(m: int, n: int, block: int) -> np.ndarray:
    """n resamples of m ordered units, drawn as runs of `block` consecutive units (moving-block bootstrap)."""
    block = max(1, min(block, m // 5))  # small samples get shorter blocks, so resamples can still differ
    starts = RNG.integers(0, m - block + 1, (n, -(-m // block)))
    return (starts[:, :, None] + np.arange(block)).reshape(n, -1)[:, :m]


def boot_mean(x: np.ndarray, groups: np.ndarray, n: int = 1000, block: int = 14) -> list[float]:
    """95% interval of the mean. Resamples whole groups (days, or heat-wave events with block=1), in runs of `block`
    consecutive groups, because forecast misses persist for days and hours within a day are not independent."""
    codes, inv = np.unique(groups, return_inverse=True)
    sums = np.bincount(inv, weights=x)
    cnts = np.bincount(inv)
    picks = block_picks(len(codes), n, block)
    means = sums[picks].sum(axis=1) / cnts[picks].sum(axis=1)
    return [round(float(np.percentile(means, 2.5)), 2), round(float(np.percentile(means, 97.5)), 2)]


def save(fig, u: str, name: str) -> None:
    (CHARTS / u.lower()).mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(CHARTS / u.lower() / f"{name}.png")
    plt.close(fig)


# ---------------------------------------------------------------- 0. data and breaks
def s0_breaks(con, u: str) -> None:
    q = con.execute(f"""
        WITH h AS (SELECT *, lag(demand_raw, 24) OVER (ORDER BY local_end) AS d24 FROM hourly WHERE utility='{u}')
        SELECT count(*) AS hours, count(*) - count(DISTINCT local_end) AS duplicate_hours,
               datediff('hour', min(local_end), max(local_end)) + 1 - count(DISTINCT local_end) AS missing_hours,
               count(*) FILTER (WHERE forecast IS NULL) AS no_forecast,
               count(*) FILTER (WHERE demand_imputed IS NOT NULL AND demand_imputed <> 0) AS imputed_demand_hours,
               count(*) FILTER (WHERE forecast = demand_raw) AS forecast_equals_actual,
               count(*) FILTER (WHERE forecast = d24) AS forecast_equals_yesterday,
               count(*) FILTER (WHERE demand <> demand_raw) AS adjusted_differs,
               count(*) FILTER (WHERE abs(demand - (netgen - interchange)) > 0.02 * demand) AS balance_breaks_over_2pct
        FROM h""").df().iloc[0]
    m = con.execute(f"""
        SELECT strftime(day, '%Y-%m') AS month, avg(demand_raw) AS demand, avg(forecast) AS forecast,
               100 * avg((forecast - demand_raw) / demand_raw) AS bias_pct, avg(gas) AS gas, avg(-interchange) AS inflow
        FROM hourly WHERE utility='{u}' AND demand_raw > 0 GROUP BY 1 ORDER BY 1""").df()
    b = m.bias_pct.to_numpy()
    k = max(range(3, len(b) - 3), key=lambda i: abs(b[:i].mean() - b[i:].mean()))
    R[u]["breaks"] = {"quality": {k2: int(v) for k2, v in q.items()},
                      "largest_bias_shift": {"at": m.month.iloc[k], "before_pct": round(float(b[:k].mean()), 1),
                                             "after_pct": round(float(b[k:].mean()), 1)},
                      "monthly": m.round(1).to_dict("list"),
                      "forecast_window": R["meta"]["forecast_windows"][u], "window_reason": U[u]["why"]}
    s = con.execute(f"""SELECT year, total_mwh, commercial_mwh, residential_mwh, industrial_mwh, total_customers
                       FROM sales WHERE utility='{u}' ORDER BY year""").df()
    ba = con.execute(f"SELECT year(day) AS year, sum(demand) AS ba_mwh FROM hourly WHERE utility='{u}' GROUP BY 1").df()
    j = s.merge(ba, on="year", how="left").set_index("year")
    pct = lambda col: round(float((j.loc[2025, col] / j.loc[2022, col] - 1) * 100), 1)  # noqa: E731
    R[u]["breaks"]["retail_vs_area"] = {
        "retail_mwh_2022_2025_pct": pct("total_mwh"), "commercial_mwh_2022_2025_pct": pct("commercial_mwh"),
        "residential_mwh_2022_2025_pct": pct("residential_mwh"), "industrial_mwh_2022_2025_pct": pct("industrial_mwh"),
        "customers_2022_2025_pct": pct("total_customers"), "area_mwh_2022_2025_pct": pct("ba_mwh"),
        "retail_share_of_area_2025_pct": round(float(j.loc[2025, "total_mwh"] / j.loc[2025, "ba_mwh"] * 100), 1),
        "customers_2025": int(j.loc[2025, "total_customers"])}
    g = con.execute(f"""
        SELECT CASE WHEN day < DATE '{U[u]['fc'][0]}' THEN 'before window'
                    WHEN local_end > TIMESTAMP '{U[u]['fc'][1]}' THEN 'after window'
                    WHEN day >= DATE '2025-02-01' THEN 'window, Feb 2025 on' ELSE 'window, before Feb 2025' END AS regime,
               hour, avg(demand_raw - forecast) AS gap
        FROM hourly WHERE utility='{u}' GROUP BY 1, 2 ORDER BY 1, 2""").df()
    R[u]["breaks"]["actual_minus_forecast_by_hour_mw"] = {r: grp.gap.round(0).tolist() for r, grp in g.groupby("regime")}
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(pd.PeriodIndex(m.month, freq="M").to_timestamp(), m.bias_pct, color=C[u], marker="o", markersize=3)
    ax.axhline(0, color=C["axis"], linewidth=1)
    for edge in U[u]["fc"]:
        if "2022-01-01" < edge[:10] < R["meta"]["data_end"]:
            ax.axvline(pd.Timestamp(edge[:10]), color=C["muted"], linestyle=(0, (3, 3)), linewidth=1)
    ax.set_title(f"{u}: day-ahead forecast minus actual load, monthly average")
    ax.set_ylabel("Forecast bias (%)")
    ax.text(0.01, 0.03, "Dashed line: edge of the window where the forecast is scored", transform=ax.transAxes,
            color=C["muted"], fontsize=8)
    save(fig, u, "0_forecast_bias_by_month")


# ---------------------------------------------------------------- 2. heat response (runs before growth: sets bp)
def s2_heat(d: pd.DataFrame, u: str) -> float:
    w = d[d.day >= U[u]["fc"][0]].copy() if u == "TEP" else d.copy()  # TEP's level shifts with the 2023 break
    w = w[w.day <= U[u].get("load_end", DATA_END)[:10]].reset_index(drop=True)
    # Year terms absorb load growth (APS grew ~16% in three years), so the temperature slope is not bent by it.
    ylist = sorted(w.year.unique())
    yrs = [(w.year == y).astype(float).to_numpy() for y in ylist[1:]]
    best = None
    for bp in np.arange(65, 95.5, 0.5):
        X = np.column_stack([np.ones(len(w)), w.tmax, np.clip(w.tmax - bp, 0, None), w.weekend] + yrs)
        b, r2 = ols(X, w.peak.to_numpy())
        if best is None or r2 > best[1]:
            best = (float(bp), r2, b)
    bp, r2, b = best
    slope = float(b[1] + b[2])
    s = w[w.summer & (w.tmax >= bp)]
    summer_peak = float(s.peak.mean())
    sy = [(s.year == y).astype(float).to_numpy() for y in ylist[1:]]
    Xs = np.column_stack([np.ones(len(s)), s.tmax, s.tmin, s.dew, s.weekend] + sy)
    bs, r2s = ols(Xs, s.peak.to_numpy())
    by_year = {}
    for y, g in d[d.tmax >= bp].groupby("year"):
        if len(g) > 40:
            by_year[int(y)] = round(float(ols(np.column_stack([np.ones(len(g)), g.tmax, g.weekend]), g.peak.to_numpy())[0][1]), 1)
    thr = float(w[w.summer].tmax.quantile(0.9))
    hot = (w.tmax >= thr).to_numpy()
    gap1 = w.day.diff().dt.days.fillna(0).to_numpy() == 1
    run = np.zeros(len(w), int)
    for i in range(len(w)):
        run[i] = (run[i - 1] + 1 if i and gap1[i] and hot[i - 1] else 1) if hot[i] else 0
    w["run"] = run
    w["event"] = np.cumsum(w.run == 1)  # one id per heat-wave run
    hs = w[w.summer & (w.tmax >= bp)]
    hy = [(hs.year == y).astype(float).to_numpy() for y in ylist[1:]]
    hs = hs.assign(res=hs.peak.to_numpy() - np.column_stack([np.ones(len(hs)), hs.tmax, hs.tmin, hs.dew, hs.weekend] + hy) @ bs)
    waves = {}
    for name, mask in (("not a heat-wave day", hs.run == 0), ("day 1", hs.run == 1), ("day 2", hs.run == 2),
                       ("day 3+", hs.run >= 3)):
        x = hs[mask]
        grp = x.event.to_numpy() if name != "not a heat-wave day" else x.day.astype(str).to_numpy()
        waves[name] = {"days": int(len(x)), "events": int(x.event.nunique()) if name != "not a heat-wave day" else None,
                       "residual_mw": round(float(x.res.mean()), 0),
                       "ci95": boot_mean(x.res.to_numpy(), grp, 2000, block=1 if name != "not a heat-wave day" else 14)
                       if len(x) > 5 else None}
    R[u]["heat"] = {"window_start": str(w.day.min().date()), "breakpoint_f": bp, "fit_r2": round(r2, 3),
                    "mw_per_f_above": round(slope, 1), "mw_per_f_below": round(float(b[1]), 1),
                    "pct_of_mean_summer_peak_per_f": round(slope / summer_peak * 100, 2),
                    "mean_summer_hot_day_peak_mw": round(summer_peak),
                    "summer_model": {"days": int(len(s)), "r2": round(r2s, 3), "mw_per_f_high": round(float(bs[1]), 1),
                                     "mw_per_f_overnight_low": round(float(bs[2]), 1),
                                     "mw_per_f_dewpoint": round(float(bs[3]), 1), "weekend_mw": round(float(bs[4]), 0)},
                    "slope_above_breakpoint_by_year": by_year, "heat_wave_threshold_f": round(thr, 1),
                    "heat_wave_residuals": waves,
                    "summer_peak_hour_share": {f"{int(h)}:00": round(float(v), 3) for h, v in
                                               w[w.summer].peak_hour.value_counts(normalize=True).sort_index().items()
                                               if v >= 0.03}}
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.scatter(w.tmax, w.peak, s=8, color=C[u], alpha=0.3, linewidths=0)
    xs = np.linspace(w.tmax.min(), w.tmax.max(), 200)
    ax.plot(xs, b[0] + b[1] * xs + b[2] * np.clip(xs - bp, 0, None) + float(np.mean([0.0] + list(b[4:]))), color=C["ink"])
    ax.axvline(bp, color=C["muted"], linewidth=1, linestyle=(0, (3, 3)))
    ax.set_title(f"{u}: daily peak load vs daily high in {U[u]['city'].title()}")
    ax.set_xlabel("Daily high temperature (°F)")
    ax.set_ylabel("Daily peak load (MW)")
    ax.text(0.02, 0.93, f"Turns steep near {bp:.0f}°F: +{slope:.0f} MW per °F above (weekday, average year)",
            transform=ax.transAxes, color=C["ink2"], fontsize=9)
    save(fig, u, "2_peak_vs_temperature")
    return bp


# ---------------------------------------------------------------- 1. growth, weather removed
def s1_growth(d: pd.DataFrame, u: str, bp: float) -> None:
    """Year effects in a model of daily load on cooling and heating degrees and weekday/holiday: the change in load
    that weather does not explain. Mean load uses the daily mean temperature; peak uses the daily high."""
    d = d[d.day <= U[u].get("load_end", DATA_END)[:10]]
    years = sorted(d.year.unique())
    def fit(y, temp, base):
        X = np.column_stack([np.ones(len(d)), np.clip(d[temp] - base, 0, None), np.clip(55 - d[temp], 0, None),
                             d.weekend] + [(d.year == yr).astype(float) for yr in years[1:]])
        b, r2 = ols(X, d[y].to_numpy())
        return b, r2
    bm, r2m = fit("mean_load", "tmean", 65.0)
    bk, r2k = fit("peak", "tmax", bp)
    ref_mean = bm[0] + bm[1] * (92 - 65)        # a weekday with a 92F daily mean (a typical July day)
    ref_peak = bk[0] + bk[1] * max(0, 110 - bp)  # a weekday with a 110F high
    em = {years[0]: 0.0, **{y: float(bm[4 + i]) for i, y in enumerate(years[1:])}}
    ek = {years[0]: 0.0, **{y: float(bk[4 + i]) for i, y in enumerate(years[1:])}}
    n_days = d.groupby("year").size()
    short = [y for y in years if n_days[y] < 200]  # a year cut short (SRP 2026: Jan-Feb only) is not comparable
    for y in short:
        em.pop(y), ek.pop(y)
    years = [y for y in years if y not in short]
    R[u]["growth"] = {
        "model_r2": {"mean_load": round(r2m, 3), "peak": round(r2k, 3)},
        "weather_adjusted_mean_load_mw": {int(y): round(ref_mean + v) for y, v in em.items()},
        "weather_adjusted_peak_at_110f_mw": {int(y): round(ref_peak + v) for y, v in ek.items()},
        "mean_load_change_2022_2025_pct": round((em[2025] - em[2022]) / ref_mean * 100, 1),
        "peak_110f_change_2022_2025_pct": round((ek[2025] - ek[2022]) / ref_peak * 100, 1),
        "mean_load_change_2024_latest_pct": round((em[years[-1]] - em[2024]) / (ref_mean + em[2024]) * 100, 1),
        "latest_year": int(years[-1]), "growth_window_end": str(d.day.max().date()),
        "years_dropped_under_200_days": [int(y) for y in short],
        "load_factor_by_year": {int(y): round(float(g.mean_load.mean() / g.peak.max()), 3) for y, g in d.groupby("year")
                                if y < 2026},
        "observed_annual_peak_mw": {int(y): round(float(v)) for y, v in d.groupby("year").peak.max().items()}}
    R[u]["growth"]["note"] = ("2026 runs through the data cut; its year effect uses the days available. TEP's 2022-2023 "
                              "level straddles the Aug 2023 reporting change; SRP stops at Feb 2026 (coverage change).")


# ---------------------------------------------------------------- 3. forecast
def s3_forecast(con, d: pd.DataFrame, u: str, window: tuple | None = None, key: str = "forecast",
                charts: bool = True) -> None:
    lo, hi = window or U[u]["fc"]
    h = con.execute(f"""SELECT day, hour, month(day) AS month, demand_raw AS a, forecast AS f FROM hourly
                       WHERE utility='{u}' AND forecast IS NOT NULL AND demand_raw > 0
                         AND day >= DATE '{lo}' AND local_end <= TIMESTAMP '{hi}'""").df()
    h["ape"] = (h.f - h.a).abs() / h.a * 100
    h["pe"] = (h.f - h.a) / h.a * 100
    g = h.day.astype(str).to_numpy()
    out = {"window": [lo, hi[:10]], "hours": len(h), "mape_pct": round(float(h.ape.mean()), 2),
           "mape_ci95": boot_mean(h.ape.to_numpy(), g), "bias_pct": round(float(h.pe.mean()), 2),
           "bias_ci95": boot_mean(h.pe.to_numpy(), g)}
    bh = h.groupby("hour").agg(mape=("ape", "mean"), bias=("pe", "mean")).round(2)
    out["by_hour"] = {"hour": bh.index.tolist(), **bh.to_dict("list")}
    bm = h.groupby("month").agg(mape=("ape", "mean"), bias=("pe", "mean")).round(2)
    out["by_month"] = {"month": bm.index.tolist(), **bm.to_dict("list")}
    out["mape_by_year"] = {int(k): v for k, v in h.groupby(pd.to_datetime(h.day).dt.year).ape.mean().round(2).items()}
    w = d[(d.day >= lo) & (d.day <= hi[:10])].dropna(subset=["fc_peak"]).copy()
    w["err"] = (w.fc_peak - w.peak) / w.peak * 100
    out["daily_peak_by_temp"] = []
    for a, b in [(-99, 80), (80, 90), (90, 100), (100, 105), (105, 110), (110, 130)]:
        x = w[(w.tmax >= a) & (w.tmax < b)]
        if len(x) >= 10:
            out["daily_peak_by_temp"].append({
                "band": f"<{b}" if a < 0 else (f"{a}+" if b > 120 else f"{a}-{b}"), "days": int(len(x)),
                "mean_err_pct": round(float(x.err.mean()), 2), "ci95": boot_mean(x.err.to_numpy(), x.day.astype(str).to_numpy(), 1000),
                "under_by_3pct_share": round(float((x.err < -3).mean()), 3)})
    sw = w[w.summer]
    out["summer_peak_hour_exact_share"] = round(float((sw.peak_hour == sw.fc_peak_hour).mean()), 3)
    out["summer_peak_hour_within_1_share"] = round(float(((sw.peak_hour - sw.fc_peak_hour).abs() <= 1).mean()), 3)
    out["daily_peak_err_weekday_pct"] = round(float(w[w.weekend == 0].err.mean()), 2)
    out["daily_peak_err_weekend_holiday_pct"] = round(float(w[w.weekend == 1].err.mean()), 2)
    # Persistence: is today's miss predictable from the miss two days back (known when the next forecast is made)?
    dm = h.groupby("day").pe.mean()
    dm.index = pd.to_datetime(dm.index)
    dm = dm.asfreq("D")
    lag = dm.shift(2)
    ok = dm.notna() & lag.notna()
    out["daily_bias_corr_with_two_days_back"] = round(float(np.corrcoef(dm[ok], lag[ok])[0, 1]), 2)
    hh = h.assign(lag_bias=pd.to_datetime(h.day).map(lag)).dropna(subset=["lag_bias"])
    days_sorted = np.sort(hh.day.unique())
    cut = days_sorted[len(days_sorted) // 2]
    tr, te = hh[hh.day < cut], hh[hh.day >= cut]
    mape = lambda f, a: float(((f - a).abs() / a).mean() * 100)  # noqa: E731
    k = min(np.arange(0, 1.01, 0.05), key=lambda k: mape(tr.f * (1 - k * tr.lag_bias / 100), tr.a))
    out["bias_correction_out_of_time"] = {
        "k": round(float(k), 2), "fit_on": f"{str(days_sorted[0])[:10]} to {str(cut)[:10]}",
        "tested_on": f"{str(cut)[:10]} to {str(days_sorted[-1])[:10]}",
        "test_mape_published_pct": round(mape(te.f, te.a), 2),
        "test_mape_corrected_pct": round(mape(te.f * (1 - k * te.lag_bias / 100), te.a), 2)}
    s = w[w.summer].dropna(subset=["tmax_fc"]).copy()
    off = float((s.tmax - s.tmax_fc).mean())
    s["surprise"] = s.tmax - s.tmax_fc - off
    ws = {"offset_removed_f": round(off, 2), "corr": round(float(np.corrcoef(s.surprise, s.err)[0, 1]), 2),
          "pct_per_f": round(float(np.polyfit(s.surprise, s.err, 1)[0]), 2)}
    for lo_s, hi_s, name in [(-99, -3, "cooler 3F+"), (-3, 3, "within 3F"), (3, 99, "hotter 3F+")]:
        x = s[(s.surprise >= lo_s) & (s.surprise < hi_s)]
        ws[name] = {"days": int(len(x)), "mean_err_pct": round(float(x.err.mean()), 2)}
    out["weather_surprise_summer"] = ws
    R[u][key] = out
    if not charts:
        return
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(out["by_hour"]["hour"], out["by_hour"]["bias"], color=C[u], width=0.7)
    ax.axhline(0, color=C["axis"], linewidth=1)
    ax.set_xticks(*HOURS)
    ax.set_title(f"{u}: forecast minus actual load by hour of day, {lo[:7]} to {hi[:7]}")
    ax.set_ylabel("Average bias (%)")
    ax.grid(axis="x", visible=False)
    save(fig, u, "3_forecast_bias_by_hour")
    bands = out["daily_peak_by_temp"]
    fig, ax = plt.subplots(figsize=(8, 4))
    xs = np.arange(len(bands))
    vals = [x["mean_err_pct"] for x in bands]
    err = np.array([[v - x["ci95"][0] for v, x in zip(vals, bands)], [x["ci95"][1] - v for v, x in zip(vals, bands)]])
    ax.bar(xs, vals, color=C[u], width=0.6)
    ax.errorbar(xs, vals, yerr=err, fmt="none", ecolor=C["ink2"], elinewidth=1, capsize=3)
    ax.axhline(0, color=C["axis"], linewidth=1)
    ax.set_xticks(xs, [f"{x['band']}°F\n{x['days']} days" for x in bands])
    ax.set_title(f"{u}: daily peak forecast error by daily high (95% intervals)")
    ax.set_ylabel("Forecast minus actual peak (%)")
    ax.grid(axis="x", visible=False)
    save(fig, u, "3_peak_error_by_temperature")


# ---------------------------------------------------------------- 4. solar, net load and the evening ramp
def s4_netload(con, u: str) -> None:
    first = con.execute(f"""SELECT min(day) FILTER (WHERE solar IS NOT NULL), min(day) FILTER (WHERE battery IS NOT NULL),
                            min(day) FILTER (WHERE wind IS NOT NULL) FROM hourly WHERE utility='{u}'""").fetchone()
    t = con.execute(f"""
        WITH h AS (SELECT day, hour, local_end, demand, demand - coalesce(solar, 0) - coalesce(wind, 0) AS net
                   FROM hourly WHERE utility='{u}' AND demand IS NOT NULL AND {full_years(u)}),
             r AS (SELECT day, net - lag(net, 3) OVER (ORDER BY local_end) AS ramp3 FROM h),
             dd AS (SELECT day, arg_max(hour, demand) AS gross_peak_hour, arg_max(hour, net) AS net_peak_hour,
                           max(demand) AS gross_peak, max(net) AS net_peak FROM h GROUP BY day),
             rr AS (SELECT day, max(ramp3) AS max_ramp3 FROM r GROUP BY day)
        SELECT year(dd.day) AS year,
               avg(gross_peak_hour) FILTER (WHERE month(dd.day) BETWEEN 6 AND 9) AS summer_gross_peak_hour,
               avg(net_peak_hour) FILTER (WHERE month(dd.day) BETWEEN 6 AND 9) AS summer_net_peak_hour,
               avg(max_ramp3) AS mean_daily_max_3h_ramp_mw, quantile_cont(max_ramp3, 0.95) AS p95_daily_3h_ramp_mw,
               max(gross_peak) AS gross_peak_mw, max(net_peak) AS net_peak_mw
        FROM dd JOIN rr USING (day) GROUP BY 1 ORDER BY 1""").df()
    sol = con.execute(f"""SELECT year(day) AS year, avg(solar) AS mean_solar_mw, quantile_cont(solar, 0.99) AS p99_solar_mw,
                          avg(solar / demand) FILTER (WHERE hour BETWEEN 11 AND 13) AS midday_solar_share
                          FROM hourly WHERE utility='{u}' AND {full_years(u)} GROUP BY 1 ORDER BY 1""").df()
    R[u]["net_load"] = {"first_reported": {"solar": str(first[0]), "battery": str(first[1]), "wind": str(first[2])},
                        "by_year": t.merge(sol, on="year").round(3).to_dict("records"),
                        "note": "Rooftop solar is behind the meter: measured load is already net of it."}
    hr = con.execute(f"""SELECT hour, avg(demand) AS load, avg(demand - coalesce(solar,0) - coalesce(wind,0)) AS net
                         FROM hourly WHERE utility='{u}' AND month(day) IN (7, 8) AND year(day) = {SHAPE_YEAR[u]}
                         GROUP BY 1 ORDER BY 1""").df()
    R[u]["net_load"]["jul_aug_profile_year"] = SHAPE_YEAR[u]
    R[u]["net_load"]["jul_aug_by_hour"] = hr.round(0).to_dict("list")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(hr.hour, hr.load, color=C[u], label="Load")
    ax.plot(hr.hour, hr.net, color=C["ink2"], linestyle=(0, (4, 2)), label="Load minus utility-scale solar and wind")
    ax.fill_between(hr.hour, hr.net, hr.load, color=C[u], alpha=0.12, linewidth=0)
    ax.set_xticks(*HOURS)
    ax.set_xlim(0, 23)
    ax.set_title(f"{u}: July-August {SHAPE_YEAR[u]}, average hour")
    ax.set_ylabel("MW")
    ax.legend(loc="upper left", fontsize=9)
    save(fig, u, "4_net_load_profile")


# ---------------------------------------------------------------- 5. supply at the peak
def s5_supply(con, u: str) -> None:
    t = con.execute(f"""
        WITH h AS (SELECT *, row_number() OVER (PARTITION BY year(day) ORDER BY demand DESC) AS rk
                   FROM hourly WHERE utility='{u}' AND demand IS NOT NULL AND interchange IS NOT NULL
                     AND {full_years(u)})
        SELECT year(day) AS year, avg(demand) AS load, avg(coal) AS coal, avg(gas) AS gas, avg(solar) AS solar,
               avg(wind) AS wind, avg(battery) AS battery, avg(hydro) AS hydro, avg(-interchange) AS net_inflow,
               avg(-interchange / demand) AS inflow_share, avg(hour) AS mean_hour,
               count(*) FILTER (WHERE battery IS NULL) AS battery_unreported_hours
        FROM h WHERE rk <= 100 GROUP BY 1 ORDER BY 1""").df()
    R[u]["supply_top100_hours"] = t.round(3).to_dict("records")
    pk = con.execute(f"""SELECT year(day) AS year, count(*) FILTER (WHERE demand >= 0.95 * p) AS n
                         FROM hourly JOIN (SELECT year(day) AS y, max(demand) AS p FROM hourly WHERE utility='{u}'
                         GROUP BY 1) ON y = year(day) WHERE utility='{u}' AND {full_years(u)} GROUP BY 1 ORDER BY 1""").df()
    R[u]["hours_within_5pct_of_annual_peak"] = {int(y): int(n) for y, n in zip(pk.year, pk.n)}
    last = t.iloc[-1]
    parts = [(n, float(last[c])) for n, c in [("Gas", "gas"), ("Coal", "coal"), ("Solar", "solar"), ("Wind", "wind"),
                                               ("Battery", "battery"), ("Hydro", "hydro"), ("Net inflow", "net_inflow")]
             if pd.notna(last[c]) and abs(last[c]) >= 5]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ys = np.arange(len(parts))[::-1]
    vals = [v for _, v in parts]
    ax.barh(ys, vals, color=C[u], height=0.6)
    ax.set_yticks(ys, [n for n, _ in parts])
    pad = max(abs(v) for v in vals) * 0.02
    for y, v in zip(ys, vals):
        ax.text(v + (pad if v >= 0 else -pad), y, f"{v:,.0f}", va="center", ha="left" if v >= 0 else "right",
                color=C["ink2"], fontsize=9)
    ax.set_xlim(min(0, min(vals)) * 1.25, max(vals) * 1.15)
    ax.axvline(0, color=C["axis"], linewidth=1)
    ax.set_title(f"{u}: average MW during the 100 highest-load hours of {int(last.year)}")
    ax.grid(axis="y", visible=False)
    save(fig, u, "5_supply_at_peak")


# ---------------------------------------------------------------- 6. reliability
def s6_reliability(con, u: str) -> None:
    r = con.execute(f"SELECT * FROM reliability WHERE utility='{u}' AND standard='ieee' ORDER BY year").df()
    out = {}
    for y, g in r.groupby("year"):
        row = {}
        for _, x in g.iterrows():
            if x.events in ("all", "no_med") and pd.notna(x.saidi_min):
                row[f"saidi_{x.events}"] = round(float(x.saidi_min), 1)
                row[f"saifi_{x.events}"] = round(float(x.saifi), 3)
                row[f"caidi_{x.events}"] = round(float(x.saidi_min / x.saifi), 1) if x.saifi else None
        if "saidi_all" in row and "saidi_no_med" in row:
            row["major_event_minutes"] = round(row["saidi_all"] - row["saidi_no_med"], 1)
        out[int(y)] = row
    R[u]["reliability"] = out


# ---------------------------------------------------------------- Arizona comparison
def arizona(con, days: dict[str, pd.DataFrame]) -> None:
    A: dict = {}
    h = con.execute(f"""SELECT utility, day, abs(forecast - demand_raw) / demand_raw * 100 AS ape FROM hourly
                        WHERE forecast IS NOT NULL AND demand_raw > 0 AND day BETWEEN DATE '{PEER[0]}' AND DATE '{PEER[1]}'""").df()
    h["day"] = h.day.astype(str)
    A["forecast_peer_window"] = {u: {"mape_pct": round(float(h[h.utility == u].ape.mean()), 2),
                                     "ci95": boot_mean(h[h.utility == u].ape.to_numpy(), h[h.utility == u].day.to_numpy())}
                                 for u in NAMES}
    dm = h.pivot_table(index="day", columns="utility", values="ape", aggfunc="mean").dropna()
    for a_, b_ in (("TEP", "SRP"), ("TEP", "APS"), ("SRP", "APS")):
        diff = (dm[a_] - dm[b_]).to_numpy()
        boots = diff[block_picks(len(diff), 2000, 14)].mean(axis=1)
        A["forecast_peer_window"][f"{a_} minus {b_}"] = {
            "mean_pct_points": round(float(diff.mean()), 2),
            "ci95": [round(float(np.percentile(boots, 2.5)), 2), round(float(np.percentile(boots, 97.5)), 2)]}
    tops = {u: set(days[u].nlargest(20, "peak").day.dt.date) for u in NAMES}
    A["shared_top20_peak_days"] = {f"{a_} & {b_}": len(tops[a_] & tops[b_])
                                   for a_, b_ in (("TEP", "SRP"), ("TEP", "APS"), ("SRP", "APS"))}
    A["shared_top20_all_three"] = len(tops["TEP"] & tops["APS"] & tops["SRP"])
    j = days["TEP"][["day", "peak"]].rename(columns={"peak": "TEP"})
    for u in ("APS", "SRP"):
        j = j.merge(days[u][["day", "peak"]].rename(columns={"peak": u}), on="day")
    js = j[j.day.dt.month.isin([6, 7, 8, 9])]
    A["summer_daily_peak_corr"] = {f"{a_} & {b_}": round(float(js[a_].corr(js[b_])), 2)
                                   for a_, b_ in (("TEP", "SRP"), ("TEP", "APS"), ("SRP", "APS"))}
    hp = con.execute("""SELECT utility, hour, avg(demand) AS load FROM hourly WHERE month(day) IN (7, 8)
                        AND year(day) = 2025 GROUP BY 1, 2 ORDER BY 1, 2""").df()
    A["jul_aug_2025_peak_hour"] = {u: int(g.loc[g.load.idxmax(), "hour"]) for u, g in hp.groupby("utility")}
    A["jul_aug_2025_overnight_min_pct_of_peak"] = {u: round(float(g.load.min() / g.load.max() * 100), 1)
                                                   for u, g in hp.groupby("utility")}
    R["arizona"] = A
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for u in NAMES:
        g = R[u]["growth"]["weather_adjusted_mean_load_mw"]
        ys = sorted(g)
        ax.plot(ys, [g[y] / g[ys[0]] * 100 for y in ys], color=C[u], marker="o", markersize=5, label=u)
        ax.text(ys[-1] + 0.08, g[ys[-1]] / g[ys[0]] * 100, u, color=C["ink2"], fontsize=9, va="center")
    ax.axhline(100, color=C["axis"], linewidth=1)
    ax.set_xticks(ys)
    ax.set_xlim(ys[0] - 0.2, ys[-1] + 0.5)
    ax.set_title("Average load with weather removed, 2022 = 100")
    ax.set_ylabel("Index")
    ax.legend(loc="upper left", fontsize=9)
    save(fig, "arizona", "1_weather_adjusted_growth")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    vals = [R[u]["heat"]["pct_of_mean_summer_peak_per_f"] for u in NAMES]
    ax.bar(NAMES, vals, color=[C[u] for u in NAMES], width=0.55)
    for i, (u, v) in enumerate(zip(NAMES, vals)):
        ax.text(i, v + max(vals) * 0.02, f"{v:.2f}%  ({R[u]['heat']['mw_per_f_above']:.0f} MW)", ha="center",
                color=C["ink2"], fontsize=9)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_title("Added peak per °F above each area's breakpoint, % of its hot-day peak")
    ax.set_ylabel("% per °F")
    ax.grid(axis="x", visible=False)
    save(fig, "arizona", "2_heat_sensitivity")
    f = A["forecast_peer_window"]
    vals = [f[u]["mape_pct"] for u in NAMES]
    err = np.array([[v - f[u]["ci95"][0] for u, v in zip(NAMES, vals)], [f[u]["ci95"][1] - v for u, v in zip(NAMES, vals)]])
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(NAMES, vals, color=[C[u] for u in NAMES], width=0.55)
    ax.errorbar(range(3), vals, yerr=err, fmt="none", ecolor=C["ink2"], capsize=4, elinewidth=1)
    for i, v in enumerate(vals):
        ax.text(i + 0.32, v, f"{v:.2f}%", color=C["ink2"], fontsize=9, va="center")
    ax.set_title(f"Day-ahead forecast error, {PEER[0][:7]} to {PEER[1][:7]} (95% intervals)")
    ax.set_ylabel("MAPE (%)")
    ax.grid(axis="x", visible=False)
    save(fig, "arizona", "3_forecast_skill")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for u in NAMES:
        g = hp[hp.utility == u]
        ax.plot(g.hour, g.load / g.load.max() * 100, color=C[u], label=u)
    ax.set_xticks(*HOURS)
    ax.set_xlim(0, 23)
    ax.set_title("July-August 2025 average hour, % of each area's own peak hour")
    ax.set_ylabel("% of peak hour")
    ax.legend(loc="lower right", fontsize=9)
    save(fig, "arizona", "4_daily_shape")


if __name__ == "__main__":
    con = load()
    days = {}
    for u in NAMES:
        R[u] = {}
        s0_breaks(con, u)
        days[u] = daily(con, u)
        bp = s2_heat(days[u], u)
        s1_growth(days[u], u, bp)
        s3_forecast(con, days[u], u)
        if "diverge" in U[u]:
            s3_forecast(con, days[u], u, U[u]["diverge"], "forecast_after_divergence", charts=False)
        s4_netload(con, u)
        s5_supply(con, u)
        s6_reliability(con, u)
        print(u, "done")
    arizona(con, days)
    (HERE / "results.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    print("results.json written")
