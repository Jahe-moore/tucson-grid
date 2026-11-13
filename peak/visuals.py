"""16:9 video visuals for the YouTube episode, drawn from results.json and data/grid.duckdb.

    python analysis.py && python visuals.py

Writes 1920x1080 PNGs to ..\\YouTube\\02_Arizona_Grid\\visuals\\. Dark theme to match the channel's render pipeline;
series colors are the reference palette's dark-mode steps (fixed order: TEP blue, APS orange, SRP aqua).
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "YouTube" / "02_Arizona_Grid" / "visuals"
R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
NAMES = ["TEP", "APS", "SRP"]
C = {"TEP": "#3987e5", "APS": "#d95926", "SRP": "#199e70", "bg": "#0f1115", "ink": "#f0efec", "ink2": "#c3c2b7",
     "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835", "accent": "#ffc43d", "panel": "#1a1d24"}
plt.rcParams.update({"figure.facecolor": C["bg"], "axes.facecolor": C["bg"], "axes.edgecolor": C["axis"],
                     "axes.labelcolor": C["ink2"], "xtick.color": C["muted"], "ytick.color": C["muted"],
                     "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 1, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 20, "axes.titlesize": 34, "axes.titleweight": "bold",
                     "axes.titlecolor": C["ink"], "axes.titlelocation": "left", "axes.titlepad": 24,
                     "lines.linewidth": 4, "legend.frameon": False, "legend.fontsize": 22, "legend.labelcolor": "#f0efec", "xtick.labelsize": 20,
                     "ytick.labelsize": 20, "axes.labelsize": 22, "font.family": "Segoe UI"})
HOURS = ([0, 6, 12, 15, 18, 21], ["12a", "6a", "12p", "3p", "6p", "9p"])
con = duckdb.connect(str(HERE / "data" / "grid.duckdb"), read_only=True)


def fig():
    return plt.figure(figsize=(19.2, 10.8), dpi=100)


def save(f, name: str, source: str = "Source: EIA-930, EIA-861, Open-Meteo. Analysis: Jake Moore") -> None:
    f.text(0.985, 0.025, source, ha="right", color=C["muted"], fontsize=16)
    OUT.mkdir(parents=True, exist_ok=True)
    f.savefig(OUT / f"{name}.png", facecolor=C["bg"])
    plt.close(f)


def ax_main(f, rect=(0.08, 0.13, 0.86, 0.68)):
    return f.add_axes(rect)


def subtitle(f, text):
    f.text(0.08, 0.86, text, color=C["ink2"], fontsize=24)


# 01 pipeline diagram
def v01():
    f = fig()
    ax = f.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, 19.2)
    ax.set_ylim(0, 10.8)
    ax.text(0.8, 9.6, "The system", color=C["ink"], fontsize=40, fontweight="bold")
    ax.text(0.8, 8.9, "Public data in, one decision memo out. Rerun it any week.", color=C["ink2"], fontsize=24)
    steps = [("Pull", "EIA-930 hourly\ngrid data\nEIA-861 sales\nand outages\nweather + day-\nahead forecast"),
             ("Store", "DuckDB:\none hourly table\nper area, joined\nto its weather"),
             ("Check", "duplicates,\ngaps, copied\nforecasts,\nreporting breaks"),
             ("Model", "heat response\ngrowth with\nweather removed\nforecast scoring\nevening ramp"),
             ("Decide", "one memo\nper area, plus\nside by side")]
    w, gap, x0, y0, h = 3.1, 0.55, 0.8, 3.0, 4.6
    for i, (head, body) in enumerate(steps):
        x = x0 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.25",
                                    facecolor=C["panel"], edgecolor=C["accent"] if i == 2 else C["axis"], linewidth=3))
        ax.text(x + w / 2, y0 + h - 0.75, head, ha="center", color=C["accent"] if i == 2 else C["ink"], fontsize=34,
                fontweight="bold")
        ax.text(x + w / 2, y0 + h / 2 - 0.45, body, ha="center", va="center", color=C["ink2"], fontsize=20,
                linespacing=1.45)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + gap - 0.08, y0 + h / 2), xytext=(x + w + 0.08, y0 + h / 2),
                        arrowprops={"arrowstyle": "-|>", "color": C["muted"], "lw": 3, "mutation_scale": 30})
    ax.text(0.8, 1.8, "Three areas: TEP (Tucson), APS and SRP (Phoenix)  ·  Jan 2022 to Nov 2026  ·  "
            "127,000 hourly rows", color=C["muted"], fontsize=22)
    save(f, "01_pipeline")


# 02 three areas peak together
def v02():
    hp = con.execute("""SELECT utility, hour, avg(demand) AS load FROM hourly WHERE month(day) IN (7, 8)
                        AND year(day) = 2025 GROUP BY 1, 2 ORDER BY 1, 2""").df()
    f = fig()
    ax = ax_main(f)
    for u in NAMES:
        g = hp[hp.utility == u]
        ax.plot(g.hour, g.load / g.load.max() * 100, color=C[u], label=u)
        ax.text(23.25, (g.load / g.load.max() * 100).iloc[-1], u, color=C[u], fontsize=24, va="center",
                fontweight="bold")
    ax.axvspan(17, 18, color=C["accent"], alpha=0.12, linewidth=0)
    ax.text(17.5, 101.5, "5-6 PM", ha="center", color=C["accent"], fontsize=22, fontweight="bold")
    ax.set_xticks(*HOURS)
    ax.set_xlim(0, 24.5)
    ax.set_ylim(55, 104)
    ax.set_ylabel("% of the area's own peak hour")
    ax.set_title("Same afternoon, same hour", pad=70)
    subtitle(f, "July-August 2025, average day, each area scaled to its own peak")
    save(f, "02_peak_together")


# 03 peak vs temperature, three panels
def v03():
    f = fig()
    f.text(0.06, 0.9, "Hot days push the peak up, fast", color=C["ink"], fontsize=34, fontweight="bold")
    f.text(0.06, 0.845, "Each dot is one day: the day's high vs the day's peak load", color=C["ink2"], fontsize=24)
    for i, u in enumerate(NAMES):
        ax = f.add_axes((0.06 + i * 0.315, 0.13, 0.27, 0.62))
        d = con.execute(f"""SELECT max(temp_f) AS t, max(demand) AS p FROM hourly WHERE utility='{u}'
                            {"AND day >= DATE '2023-08-01'" if u == "TEP" else ""}
                            {"AND day <= DATE '2026-02-28'" if u == "SRP" else ""} GROUP BY day""").df()
        ax.scatter(d.t, d.p / 1000, s=10, color=C[u], alpha=0.35, linewidths=0)
        h = R[u]["heat"]
        ax.axvline(h["breakpoint_f"], color=C["muted"], linestyle=(0, (4, 4)), linewidth=2)
        ax.set_title(u, color=C[u], fontsize=30, loc="left", pad=12)
        ax.text(0.04, 0.9, f"+{h['mw_per_f_above']:.0f} MW per °F\nabove {h['breakpoint_f']:.0f}°F",
                transform=ax.transAxes, color=C["ink"], fontsize=21, va="top")
        ax.set_xlabel("Daily high (°F)")
        if i == 0:
            ax.set_ylabel("Daily peak (thousand MW)")
    save(f, "03_heat_three_areas")


# 04 heat sensitivity, scaled
def v04():
    f = fig()
    ax = ax_main(f)
    vals = [R[u]["heat"]["pct_of_mean_summer_peak_per_f"] for u in NAMES]
    ax.bar(NAMES, vals, color=[C[u] for u in NAMES], width=0.5)
    for i, (u, v) in enumerate(zip(NAMES, vals)):
        ax.text(i, v + 0.06, f"{v:.1f}% per °F", ha="center", color=C["ink"], fontsize=30, fontweight="bold")
        ax.text(i, v / 2, f"{R[u]['heat']['mw_per_f_above']:.0f} MW", ha="center", color=C["bg"], fontsize=26,
                fontweight="bold")
    ax.set_ylim(0, 2.8)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Added peak per °F, % of hot-day peak")
    ax.set_title("Scaled to their size, they react to heat the same way", pad=70)
    subtitle(f, "Every degree above about 82°F adds roughly 2% to the day's peak")
    save(f, "04_heat_scaled")


# 05 reporting breaks: monthly bias, three panels
def v05():
    f = fig()
    f.text(0.06, 0.9, "Before scoring anything: find where the reporting changed", color=C["ink"], fontsize=34,
           fontweight="bold")
    f.text(0.06, 0.845, "Monthly average of (day-ahead forecast - actual load) / actual load. Shaded months are left out "
           "of forecast scoring", color=C["ink2"], fontsize=22)
    for i, u in enumerate(NAMES):
        ax = f.add_axes((0.11, 0.6 - i * 0.235, 0.86, 0.19))
        m = R[u]["breaks"]["monthly"]
        x = pd.PeriodIndex(m["month"], freq="M").to_timestamp()
        y = np.clip(m["bias_pct"], -20, 35)
        ax.plot(x, y, color=C[u], linewidth=3.5)
        ax.axhline(0, color=C["axis"], linewidth=2)
        lo, hi = R["meta"]["forecast_windows"][u]
        if lo > "2022-01-01":
            ax.axvspan(x.min(), pd.Timestamp(lo), color=C["muted"], alpha=0.18, linewidth=0)
        if hi < R["meta"]["data_end"]:
            ax.axvspan(pd.Timestamp(hi), x.max(), color=C["muted"], alpha=0.18, linewidth=0)
        ax.set_ylim(-20, 36)
        ax.set_yticks([-15, 0, 15, 30], ["-15%", "0", "+15%", "+30%"])
        ax.text(-0.065, 0.5, u, transform=ax.transAxes, color=C[u], fontsize=28, fontweight="bold", ha="right",
                va="center")
        if i < 2:
            ax.set_xticklabels([])
    save(f, "05_reporting_breaks")


# 06 APS gap by hour, before vs after Feb 2025
def v06():
    rows = con.execute("""SELECT CASE WHEN day < DATE '2025-02-01' THEN 'before' ELSE 'after' END AS p, hour,
                          avg(demand_raw - forecast) AS gap FROM hourly WHERE utility='APS'
                          AND day >= DATE '2024-02-01' GROUP BY 1, 2 ORDER BY 1, 2""").df()
    f = fig()
    ax = ax_main(f)
    for p, col, lab in (("before", C["muted"], "Feb 2024-Jan 2025"), ("after", C["APS"], "Feb 2025 on")):
        g = rows[rows.p == p]
        ax.plot(g.hour, g.gap, color=col, label=lab, linewidth=5 if p == "after" else 3)
    ax.axhline(0, color=C["axis"], linewidth=2)
    ax.set_xticks(*HOURS)
    ax.set_xlim(0, 23)
    ax.set_ylabel("Actual load minus forecast (MW)")
    ax.legend(loc="upper center")
    ax.set_title("APS: a steady block at night appears in February 2025", pad=70)
    subtitle(f, "Average gap by hour of day. Shape tells you what kind of change it is; the cause isn't public")
    save(f, "06_aps_gap_shape")


# 07 growth, weather removed
def v07():
    f = fig()
    ax = ax_main(f)
    for u in NAMES:
        g = {int(k): v for k, v in R[u]["growth"]["weather_adjusted_mean_load_mw"].items()}
        ys = sorted(g)
        idx = [g[y] / g[ys[0]] * 100 for y in ys]
        ax.plot(ys, idx, color=C[u], marker="o", markersize=12)
        ax.text(ys[-1] + 0.1, idx[-1], u, color=C[u], fontsize=26, fontweight="bold", va="center")
    ax.axhline(100, color=C["axis"], linewidth=2)
    ax.set_xticks([2022, 2023, 2024, 2025, 2026], ["2022", "2023", "2024", "2025", "2026*"])
    ax.set_xlim(2021.8, 2026.6)
    ax.set_ylabel("Average load, weather removed (2022 = 100)")
    ax.set_title("Growth underneath the weather", pad=70)
    subtitle(f, "* 2026 through Nov 2. SRP stops at 2025 (its reported load changed coverage in March 2026)")
    save(f, "07_growth")


# 08 forecast skill with intervals
def v08():
    a = R["arizona"]["forecast_peer_window"]
    f = fig()
    ax = ax_main(f)
    vals = [a[u]["mape_pct"] for u in NAMES]
    err = np.array([[v - a[u]["ci95"][0] for u, v in zip(NAMES, vals)], [a[u]["ci95"][1] - v for u, v in zip(NAMES, vals)]])
    ax.bar(NAMES, vals, color=[C[u] for u in NAMES], width=0.5)
    ax.errorbar(range(3), vals, yerr=err, fmt="none", ecolor=C["ink"], elinewidth=3, capsize=12, capthick=3)
    for i, v in enumerate(vals):
        ax.text(i + 0.3, v, f"{v:.1f}%", color=C["ink"], fontsize=30, fontweight="bold", va="center")
    ax.set_ylim(0, 5)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Average hourly miss (MAPE, %)")
    ax.set_title("How close the day-ahead forecasts land", pad=70)
    subtitle(f, "Aug 2023 to Jan 2025, when all three report consistently. Lines show the 95% range")
    save(f, "08_forecast_skill")


# 09 TEP peak forecast error by temperature
def v09():
    b = R["TEP"]["forecast"]["daily_peak_by_temp"]
    f = fig()
    ax = ax_main(f)
    xs = np.arange(len(b))
    vals = [x["mean_err_pct"] for x in b]
    err = np.array([[v - x["ci95"][0] for v, x in zip(vals, b)], [x["ci95"][1] - v for v, x in zip(vals, b)]])
    ax.bar(xs, vals, color=C["TEP"], width=0.6)
    ax.errorbar(xs, vals, yerr=err, fmt="none", ecolor=C["ink"], elinewidth=2.5, capsize=8)
    ax.axhline(0, color=C["axis"], linewidth=2)
    ax.set_xticks(xs, [f"{x['band']}°F\n{x['days']} days" for x in b])
    ax.set_ylabel("Peak forecast minus actual (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title("TEP: the day-ahead peak runs a little low on hot days", pad=70)
    subtitle(f, "Aug 2023 to Nov 2026, grouped by the day's high temperature")
    save(f, "09_tep_hot_days")


# 10 APS duck curve + ramp growth
def v10():
    hr = R["APS"]["net_load"]["jul_aug_by_hour"]
    f = fig()
    ax = f.add_axes((0.06, 0.13, 0.55, 0.66))
    ax.plot(hr["hour"], np.array(hr["load"]) / 1000, color=C["APS"], label="Load")
    ax.plot(hr["hour"], np.array(hr["net"]) / 1000, color=C["ink2"], linestyle=(0, (5, 3)),
            label="Load minus utility solar + wind")
    ax.fill_between(hr["hour"], np.array(hr["net"]) / 1000, np.array(hr["load"]) / 1000, color=C["APS"], alpha=0.15,
                    linewidth=0)
    ax.set_xticks(*HOURS)
    ax.set_xlim(0, 23)
    ax.set_ylabel("Thousand MW")
    ax.legend(loc="upper left", fontsize=20)
    ax.set_title("APS, July-August 2026 average day", fontsize=28)
    ax2 = f.add_axes((0.69, 0.13, 0.28, 0.66))
    rows = R["APS"]["net_load"]["by_year"]
    ys = [r["year"] for r in rows]
    vals = [r["mean_daily_max_3h_ramp_mw"] for r in rows]
    ax2.bar([str(y) for y in ys], vals, color=[C["APS"] if y == ys[-1] else C["muted"] for y in ys], width=0.6)
    for i, v in enumerate(vals):
        ax2.text(i, v + 40, f"{v:,.0f}", ha="center", color=C["ink"], fontsize=19)
    ax2.set_title("Evening 3-hour climb, MW", fontsize=28)
    ax2.grid(axis="x", visible=False)
    ax2.tick_params(axis="x", labelsize=17)
    f.text(0.06, 0.9, "Solar fills the middle of the day, then the evening climb doubles", color=C["ink"],
           fontsize=34, fontweight="bold")
    save(f, "10_aps_evening_ramp")


# 11 side-by-side summary table
def v11():
    rows = [("Added peak per °F", [f"{R[u]['heat']['mw_per_f_above']:.0f} MW" for u in NAMES]),
            ("Growth since 2024, weather removed", ["+1.7%", "+10.8%", "+2.6%"]),
            ("Forecast miss, Aug 2023-Jan 2025", [f"{R['arizona']['forecast_peer_window'][u]['mape_pct']:.1f}%" for u in NAMES]),
            ("Evening 3-hour climb, latest year", ["644 MW", "2,104 MW", "1,002 MW"]),
            ("Outage minutes, normal day 2025", ["41.8", "73.1", "49.9"])]
    f = fig()
    ax = f.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, 19.2)
    ax.set_ylim(0, 10.8)
    ax.text(0.8, 9.6, "Side by side", color=C["ink"], fontsize=40, fontweight="bold")
    xs = [10.2, 13.3, 16.4]
    for x, u in zip(xs, NAMES):
        ax.text(x, 8.4, u, ha="center", color=C[u], fontsize=34, fontweight="bold")
    for i, (lab, vals) in enumerate(rows):
        y = 7.2 - i * 1.35
        ax.add_patch(FancyBboxPatch((0.6, y - 0.5), 18.0, 1.05, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    facecolor=C["panel"], edgecolor="none"))
        ax.text(1.0, y, lab, color=C["ink2"], fontsize=26, va="center")
        for x, v in zip(xs, vals):
            ax.text(x, y, v, ha="center", color=C["ink"], fontsize=30, fontweight="bold", va="center")
    ax.text(0.8, 0.55, "Growth: TEP and APS through Nov 2026, SRP through 2025. Forecast: same window for all three.",
            color=C["muted"], fontsize=20)
    save(f, "11_side_by_side")


if __name__ == "__main__":
    for fn in (v01, v02, v03, v04, v05, v06, v07, v08, v09, v10, v11):
        fn()
    print("wrote", len(list(OUT.glob("*.png"))), "visuals to", OUT)
