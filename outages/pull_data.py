"""Pull every public source for the Pima County storm-outage analysis into data/.

Run: python pull_data.py           (weather, storm reports, customer mix, outage cost table)
     python pull_data.py --outages  (also re-streams EAGLE-I; about 7 GB of national files, Pima rows kept)

Sources
- EAGLE-I (Oak Ridge National Laboratory), customers out by county every 15 minutes, figshare 24237376, CC BY 4.0
- NOAA NCEI Storm Events Database, details files
- Open-Meteo historical weather API (ERA5 reanalysis), central Tucson
- EIA-861M monthly sales to ultimate customers (customer counts by class)
- LBNL-6941E (Sullivan et al., 2015), Table ES-1 interruption cost per event, 2013 dollars
"""
import csv
import gzip
import io
import subprocess
import sys
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
YEARS = range(2020, 2026)
UA = {"User-Agent": "portfolio-research-script"}
PIMA_FIPS = "04019"

EAGLEI_FILES = {2020: 42547894, 2021: 42547891, 2022: 42547897, 2023: 44574907, 2024: 53581661, 2025: 62164877}


def outages():
    """Stream each national EAGLE-I year and keep only Pima County rows (needs curl and awk, e.g. Git Bash)."""
    RAW.mkdir(parents=True, exist_ok=True)
    for y, fid in EAGLEI_FILES.items():
        out = RAW / f"eaglei_pima_{y}.csv"
        cmd = (f'curl -sL "https://ndownloader.figshare.com/files/{fid}" | '
               f"awk -F, 'NR==1 || $1==\"{PIMA_FIPS}\"' > \"{out.as_posix()}\"")
        subprocess.run(["bash", "-c", cmd], check=True)
        print(f"  EAGLE-I {y}: {sum(1 for _ in open(out)) - 1:,} Pima rows")


def weather():
    """Hourly observed weather for central Tucson, 2020-2025 (reanalysis, so it is consistent across years)."""
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude=32.22&longitude=-110.97"
           "&start_date=2020-01-01&end_date=2025-12-31"
           "&hourly=temperature_2m,dew_point_2m,precipitation,wind_speed_10m,wind_gusts_10m"
           "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=America%2FPhoenix")
    h = requests.get(url, headers=UA, timeout=180).json()["hourly"]
    df = pd.DataFrame({"local_time": h["time"], "temp_f": h["temperature_2m"], "dewpoint_f": h["dew_point_2m"],
                       "precip_in": h["precipitation"], "wind_mph": h["wind_speed_10m"],
                       "gust_mph": h["wind_gusts_10m"]})
    df.to_csv(DATA / "tucson_weather_hourly.csv", index=False)
    print(f"  weather: {len(df):,} hours")


def storm_reports():
    """NOAA Storm Events rows for Pima County (county-coded events plus Pima/Tucson forecast zones)."""
    idx = requests.get("https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/", headers=UA, timeout=60).text
    keep = []
    for y in YEARS:
        name = next(s.split('"')[0] for s in idx.split('href="')[1:]
                    if s.startswith(f"StormEvents_details-ftp_v1.0_d{y}_"))
        raw = requests.get("https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/" + name,
                           headers=UA, timeout=180).content
        df = pd.read_csv(io.BytesIO(gzip.decompress(raw)), dtype=str, low_memory=False)
        az = df[df.STATE == "ARIZONA"]
        county = (az.CZ_TYPE == "C") & (az.CZ_FIPS.astype(int) == 19)
        zone = (az.CZ_TYPE == "Z") & az.CZ_NAME.str.contains("PIMA|TUCSON", case=False, na=False)
        keep.append(az[county | zone])
        print(f"  NOAA {y}: {int((county | zone).sum())} Pima events")
    cols = ["EVENT_ID", "EPISODE_ID", "EVENT_TYPE", "CZ_TYPE", "CZ_NAME", "BEGIN_DATE_TIME", "END_DATE_TIME",
            "CZ_TIMEZONE", "MAGNITUDE", "MAGNITUDE_TYPE", "DAMAGE_PROPERTY", "INJURIES_DIRECT", "DEATHS_DIRECT",
            "BEGIN_LAT", "BEGIN_LON", "EVENT_NARRATIVE"]
    pd.concat(keep)[cols].to_csv(DATA / "noaa_storm_events_pima.csv", index=False)


def customer_mix():
    """TEP customers by class from EIA-861M (2025 monthly average): weights the per-event outage costs."""
    url = "https://www.eia.gov/electricity/data/eia861m/archive/xls/sales_ult_cust_2025.xlsx"
    df = pd.read_excel(io.BytesIO(requests.get(url, headers=UA, timeout=120).content), header=2)
    df = df.iloc[:, :16]
    df.columns = ["year", "month", "utility_number", "utility", "state", "ownership", "status",
                  "res_rev", "res_mwh", "res_cust", "com_rev", "com_mwh", "com_cust", "ind_rev", "ind_mwh", "ind_cust"]
    tep = df[df.utility.astype(str).str.contains("Tucson Electric", case=False)]
    tep[["year", "month", "utility", "res_cust", "com_cust", "ind_cust", "res_mwh", "com_mwh", "ind_mwh"]].to_csv(DATA / "tep_customers_2025.csv",
                                                                                 index=False)
    print(f"  EIA-861M: {len(tep)} TEP months")


def outage_costs():
    """LBNL-6941E Table ES-1, cost per interruption event, U.S. 2013 dollars (Sullivan, Schellenberg, Blundell 2015)."""
    rows = [
        ("Residential", 3.9, 4.5, 5.1, 9.5, 17.2, 32.4),
        ("Small C&I", 412, 520, 647, 1880, 4690, 9055),
        ("Medium and Large C&I", 12952, 15241, 17804, 39458, 84083, 165482),
    ]
    with open(DATA / "lbnl_cost_per_event_2013usd.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_class", "momentary", "min_30", "hr_1", "hr_4", "hr_8", "hr_16"])
        w.writerows(rows)
    print("  LBNL cost table written")
    # Table ES-2: the same costs by season and time of day. Report definitions: morning 6 AM-12 PM,
    # afternoon 12-5 PM, evening 5-10 PM, night 10 PM-6 AM; summer is 33% of hours (June-September).
    timing = [
        ("Medium and Large C&I", "summer", "all", 16172, 18861, 21850, 46546, 96252, 186983),
        ("Medium and Large C&I", "non-summer", "all", 11342, 13431, 15781, 35915, 77998, 154731),
        ("Small C&I", "summer", "morning", 461, 569, 692, 1798, 4073, 7409),
        ("Small C&I", "summer", "afternoon", 527, 645, 780, 1954, 4313, 7737),
        ("Small C&I", "summer", "evening/night", 272, 349, 440, 1357, 3518, 6916),
        ("Small C&I", "non-summer", "morning", 549, 687, 848, 2350, 5592, 10452),
        ("Small C&I", "non-summer", "afternoon", 640, 794, 972, 2590, 5980, 10992),
        ("Small C&I", "non-summer", "evening/night", 298, 388, 497, 1656, 4577, 9367),
        ("Residential", "summer", "morning/night", 6.8, 7.5, 8.4, 14.3, 24.0, 42.4),
        ("Residential", "summer", "afternoon", 4.3, 4.9, 5.5, 9.8, 17.1, 31.1),
        ("Residential", "summer", "evening", 3.5, 4.0, 4.6, 9.2, 17.5, 34.1),
        ("Residential", "non-summer", "morning/night", 3.9, 4.5, 5.1, 9.8, 17.8, 33.5),
        ("Residential", "non-summer", "afternoon", 2.3, 2.7, 3.1, 6.2, 12.1, 23.7),
        ("Residential", "non-summer", "evening", 1.5, 1.8, 2.2, 5.0, 10.8, 23.6),
    ]
    with open(DATA / "lbnl_cost_by_timing_2013usd.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_class", "season", "time_of_day", "momentary", "min_30", "hr_1", "hr_4", "hr_8", "hr_16"])
        w.writerows(timing)
    print("  LBNL timing table written")


def cpi():
    """BLS CPI-U (CUUR0000SA0) annual averages, to move the 2013-dollar costs to 2025 dollars."""
    rows = []
    for y in (2013, 2025):
        r = requests.post("https://api.bls.gov/publicAPI/v1/timeseries/data/",
                          json={"seriesid": ["CUUR0000SA0"], "startyear": str(y), "endyear": str(y)},
                          headers=UA, timeout=60).json()
        vals = [float(d["value"]) for d in r["Results"]["series"][0]["data"]
                if d["year"] == str(y) and d["period"] != "M13" and d["value"] != "-"]
        rows.append((y, round(sum(vals) / len(vals), 3), len(vals)))
    with open(DATA / "cpi_u_annual.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "cpi_u_annual_avg", "months"])
        w.writerows(rows)
    print(f"  CPI-U: {rows}")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    if "--outages" in sys.argv:
        outages()
    weather()
    storm_reports()
    customer_mix()
    outage_costs()
    cpi()
