"""Download every public source this analysis uses, into data/.

    python pull.py            # all sources
    python pull.py weather    # one source: eia930 | weather | eia861 | sales

EIA-930 half-year files cover every U.S. balancing authority (~45 MB each); they are streamed and only the three
Arizona utilities are kept, so nothing large is ever written to disk.
"""
from __future__ import annotations

import csv
import re
import io
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
UA = {"User-Agent": "tep-peak-demand-analysis (public data research)"}
BAS = {"TEPC": "TEP", "AZPS": "APS", "SRP": "SRP"}  # EIA balancing-authority codes
START_YEAR = 2022
END_DATE = date(2026, 11, 9)  # pinned so a rerun reproduces the memos; raise it to refresh
# Weather points: central Tucson for TEP, Phoenix Sky Harbor for SRP and APS (APS also serves Yuma, Flagstaff and
# Prescott; Phoenix carries most of its load, and the memos state the limit).
POINTS = {"tucson": (32.22, -110.97), "phoenix": (33.43, -112.01)}
UTILITY_IDS = {803: "APS", 16572: "SRP", 24211: "TEP"}  # EIA utility numbers
UTILITIES_861 = {"Tucson Electric Power Co": "TEP", "Arizona Public Service Co": "APS",
                 "Salt River Project": "SRP"}


def eia930() -> Path:
    out = DATA / "eia930_arizona.csv"
    today = END_DATE
    halves = [(y, h) for y in range(START_YEAR, today.year + 1) for h in ("Jan_Jun", "Jul_Dec")
              if not (y == today.year and h == "Jul_Dec" and today.month < 7)]
    rows = []
    for y, h in halves:
        url = f"https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_{y}_{h}.csv"
        with requests.get(url, headers=UA, stream=True, timeout=120) as r:
            if r.status_code == 404:
                print(f"  {y} {h}: not published yet")
                continue
            r.raise_for_status()
            lines = (ln.decode("utf-8-sig", "replace") for ln in r.iter_lines() if ln)
            n, pick = 0, None
            for rec in csv.reader(lines):
                if rec and rec[0] == "Balancing Authority":
                    pick = _columns(rec)  # each file has its own header; EIA added fuel columns over time
                    continue
                if pick and rec and rec[0] in BAS:
                    rows.append({k: _sum(rec, idx) for k, idx in pick.items()})
                    n += 1
        print(f"  {y} {h}: {n:,} rows")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _columns(header: list[str]) -> dict[str, list[int]]:
    """Output column -> source column indexes (summed when EIA split one series, e.g. solar with/without battery)."""
    h = [c.strip() for c in header]
    exact = {"ba": "Balancing Authority", "utc_end": "UTC Time at End of Hour", "local_end": "Local Time at End of Hour",
             "demand_forecast_mw": "Demand Forecast (MW)", "demand_mw": "Demand (MW)",
             "demand_adj_mw": "Demand (MW) (Adjusted)", "netgen_adj_mw": "Net Generation (MW) (Adjusted)",
             "interchange_adj_mw": "Total Interchange (MW) (Adjusted)",
             "demand_imputed_mw": "Demand (MW) (Imputed)"}
    out = {k: [h.index(v)] for k, v in exact.items() if v in h}
    fuels = {"coal_mw": "from Coal", "gas_mw": "from Natural Gas", "solar_mw": "from Solar", "wind_mw": "from Wind",
             "battery_mw": "from Battery Storage", "hydro_mw": "from Hydropower"}
    for k, key in fuels.items():
        out[k] = [i for i, c in enumerate(h) if key in c and c.endswith("(Adjusted)")]
    return out


def _sum(rec: list[str], idx: list[int]):
    if len(idx) == 1 and not str(rec[idx[0]]).replace(",", "").replace(".", "").lstrip("-").isdigit():
        return rec[idx[0]]  # text columns (BA, times) and blanks pass through
    vals = [float(rec[i].replace(",", "")) for i in idx if i < len(rec) and rec[i].strip()]
    return sum(vals) if vals else None


def weather() -> list[Path]:
    outs = []
    end = END_DATE.isoformat()
    for name, (lat, lon) in POINTS.items():
        out = DATA / f"{name}_weather_hourly.csv"
        url = ("https://archive-api.open-meteo.com/v1/archive"
               f"?latitude={lat}&longitude={lon}&start_date={START_YEAR}-01-01&end_date={end}"
               "&hourly=temperature_2m,relative_humidity_2m,dew_point_2m"
               "&temperature_unit=fahrenheit&timezone=America%2FPhoenix")
        d = requests.get(url, headers=UA, timeout=120).json()["hourly"]
        obs = pd.DataFrame({"local_time": d["time"], "temp_f": d["temperature_2m"],
                            "rh_pct": d["relative_humidity_2m"], "dewpoint_f": d["dew_point_2m"]}).dropna()
        # What the weather models said the day before (Open-Meteo previous-runs API): a public day-ahead forecast,
        # not the one any utility's planners used, but it separates "hot" from "hotter than expected".
        fc = requests.get("https://previous-runs-api.open-meteo.com/v1/forecast"
                          f"?latitude={lat}&longitude={lon}&start_date={START_YEAR}-01-01&end_date={end}"
                          "&hourly=temperature_2m_previous_day1&temperature_unit=fahrenheit&timezone=America%2FPhoenix",
                          headers=UA, timeout=180).json()["hourly"]
        fc = pd.DataFrame({"local_time": fc["time"], "temp_f_dayahead": fc["temperature_2m_previous_day1"]})
        obs.merge(fc, on="local_time", how="left").to_csv(out, index=False)
        print(f"  {name}: {len(obs):,} hours, day-ahead forecast for {fc.temp_f_dayahead.notna().sum():,}")
        outs.append(out)
    return outs


def sales() -> Path:
    """EIA-861 retail sales (MWh) and customers by sector, per utility and year: an independent check on load growth."""
    out = DATA / "eia861_sales.csv"
    rows = []
    for year in range(2019, END_DATE.year):
        z = _zip_861(year)
        if z is None:
            continue
        zf = zipfile.ZipFile(io.BytesIO(z))
        name = next(n for n in zf.namelist() if n.lower().startswith("sales_ult_cust_") and "_cs_" not in n.lower())
        raw = pd.read_excel(zf.open(name), header=None)
        hdr = raw.index[raw.apply(lambda r: r.astype(str).str.contains("Utility Number").any(), axis=1)][0]
        sector = raw.iloc[hdr - 2].ffill().fillna("").astype(str)
        field = raw.iloc[hdr - 1].fillna("").astype(str)
        names = raw.iloc[hdr].astype(str).tolist()
        df = raw.iloc[hdr + 1:]
        num = df.iloc[:, names.index("Utility Number")].astype(str)
        st = df.iloc[:, names.index("State")].astype(str)
        for uid, util in UTILITY_IDS.items():
            part = df[(num == str(uid)) & (st == "AZ")]
            rec = {"year": year, "utility": util, "parts": len(part)}
            for j in range(len(names)):
                sec, f = sector.iloc[j].strip().lower(), field.iloc[j].strip().lower()
                if sec in ("residential", "commercial", "industrial", "total") and f in ("sales", "customers"):
                    rec[f"{sec}_{'mwh' if f == 'sales' else 'customers'}"] = pd.to_numeric(part.iloc[:, j], errors="coerce").sum()
            rows.append(rec)
        print(f"  sales {year}: ok")
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _zip_861(year: int) -> bytes | None:
    for path in ("zip", "archive/zip"):
        r = requests.get(f"https://www.eia.gov/electricity/data/eia861/{path}/f861{year}.zip", headers=UA, timeout=120)
        if r.ok and r.content[:2] == b"PK":
            return r.content
    return None


def eia861() -> Path:
    """Reliability (SAIDI / SAIFI) for TEP, APS and SRP, one row per utility, year and standard."""
    out = DATA / "eia861_reliability.csv"
    frames = []
    for year in range(2019, END_DATE.year):
        z = _zip_861(year)
        if z is None:
            print(f"  861 {year}: not published")
            continue
        zf = zipfile.ZipFile(io.BytesIO(z))
        name = next((n for n in zf.namelist() if n.lower().startswith("reliability") and n.endswith("xlsx")), None)
        if not name:
            print(f"  861 {year}: no reliability file")
            continue
        raw = pd.read_excel(zf.open(name), header=None)
        hdr = raw.index[raw.apply(lambda r: r.astype(str).str.contains("Utility Name").any(), axis=1)][0]
        # Header bands above the field row: the standard (IEEE / Other) and, from 2021, the event set
        # (all events / without major event days / loss of supply removed). Older files put the event set in the field.
        bands = [raw.iloc[i].ffill().fillna("").astype(str) for i in range(hdr)]
        cols = []
        for j, field in enumerate(raw.iloc[hdr].astype(str)):
            above = " ".join(b.iloc[j] for b in bands)
            std = "ieee" if "IEEE" in above else "other" if "Other" in above else ""
            text = f"{above} {field}".lower()
            ev = ("no_med" if "without" in text else "no_los" if re.search(r"\bloss\b|\blos\b", text) else "all") if std else ""
            kind = ("saidi" if field.startswith("SAIDI") else "saifi" if field.startswith("SAIFI")
                    else "customers" if field.startswith("Number of Customers") else "")
            cols.append((std, ev, kind, field))
        df = raw.iloc[hdr + 1:]
        ucol = next(j for j, c in enumerate(cols) if c[3] == "Utility Name")
        df = df[df.iloc[:, ucol].isin(UTILITIES_861)]
        for _, r in df.iterrows():
            recs: dict = {}
            for j, (std, ev, kind, _) in enumerate(cols):
                if std and kind:
                    key = (std, "all" if kind == "customers" else ev)
                    recs.setdefault(key, {})[kind] = pd.to_numeric(r.iloc[j], errors="coerce")
            cust = {s: v.get("customers") for (s, e), v in recs.items() if e == "all"}
            for (std, ev), v in recs.items():
                if v.get("saidi") is not None or v.get("saifi") is not None:
                    frames.append({"year": year, "utility": UTILITIES_861[r.iloc[ucol]], "standard": std,
                                   "events": ev, "saidi_min": v.get("saidi"), "saifi": v.get("saifi"),
                                   "customers": cust.get(std)})
        print(f"  861 {year}: {len(df)} utilities")
    pd.DataFrame(frames).dropna(subset=["saidi_min", "saifi"], how="all").to_csv(out, index=False)
    return out


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    which = sys.argv[1:] or ["eia930", "weather", "eia861", "sales"]
    for name in which:
        print(name)
        print("  ->", {"eia930": eia930, "weather": weather, "eia861": eia861, "sales": sales}[name]())
