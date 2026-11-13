"""Build the Tucson Grid deck: the demand side, the storm side, and where the money goes.

    python deck/build_grid_deck.py          # 27 slides, notes from deck/grid_script.md
    python deck/build_grid_deck.py --mini   # 13 slides (10 minutes), notes from deck/grid_mini_script.md

It runs the outage deck's own setup and helpers from outages/deck/build_deck.py (template, fonts, colors) and re-runs
the storm slides from that file block by block, unchanged, so they stay identical to the outage deck. build_deck.py
itself is not modified, and `python outages/deck/build_deck.py` still builds the 34-slide outage deck.
Numbers: results.json (python combine.py) for the demand side and Act 4; outages/deck/numbers.json for the storm side.
"""
import json
import re
import sys
from pathlib import Path

GRID = Path(__file__).resolve().parent.parent
SRC = GRID / "outages" / "deck" / "build_deck.py"
MINI_FLAG = "--mini" in sys.argv

# ---- run the outage deck's setup (template, helpers) without its --mini switch ----
pre, deck_part = SRC.read_text(encoding="utf-8").split("# ---------- the deck ----------")
argv, sys.argv = sys.argv, [str(SRC)]
ns = {"__file__": str(SRC), "__name__": "outage_deck"}
exec(compile(pre, str(SRC), "exec"), ns)
sys.argv = argv
globals().update({k: v for k, v in ns.items() if not k.startswith("__")})

R = json.loads((GRID / "results.json").read_text(encoding="utf-8"))
TEP, A4 = R["peak"]["TEP"], R["act4"]
OUT_FILE = GRID / "deck" / ("tucson_grid_10min.pptx" if MINI_FLAG else "tucson_grid.pptx")
GRID_KEEP = [1, 2, 3, 7, 8, 12, 14, 15, 18, 20, 23, 24, 25]

# ---- speaker notes, keyed by full-deck slide number ----
script = (GRID / "deck" / ("grid_mini_script.md" if MINI_FLAG else "grid_script.md")).read_text(encoding="utf-8")
GRID_NOTES = {}
for m in re.finditer(r"^## Slide (\d+)[^\n]*\n(.*?)(?=^## Slide |\Z)", script, re.S | re.M):
    n = int(m.group(1))
    GRID_NOTES[GRID_KEEP[n - 1] if MINI_FLAG else n] = re.sub(r"\n{3,}", "\n\n", m.group(2).strip())
ns["NOTES"].clear()
ns["NOTES"].update(GRID_NOTES)

# ---- the outage deck's slide blocks, by their own numbers ----
head, *rest = re.split(r"^(# \d+ [^\n]*)$", deck_part, flags=re.M)
exec(compile(head, str(SRC), "exec"), ns)          # cm, cut, sc, N lookups the blocks use
globals().update({k: v for k, v in ns.items() if not k.startswith("__")})
BLOCKS = {int(rest[i].split()[1]): rest[i + 1] for i in range(0, len(rest) - 1, 2)}
BLOCKS = {k: v.split("\nif MINI:")[0] for k, v in BLOCKS.items()}   # the last block carries the save step


def outage_slide(n: int, mini_title: bool = False) -> None:
    ns["MINI"] = mini_title
    exec(compile(BLOCKS[n], f"{SRC.name} block {n}", "exec"), ns)


def picture(slide, path, x, y, w=None, h=None):
    from PIL import Image
    iw, ih = Image.open(path).size
    if w and not h:
        h = w * ih / iw
    if h and not w:
        w = h * iw / ih
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))


def m(x, d=1):
    return f"${x / 1e6:.{d}f}M"


def clock(hour: float) -> str:
    """17.139 -> '5:08 PM' (the memos' rounding of decimal hours)."""
    h, mins = int(hour), round((hour - int(hour)) * 60)
    return f"{h - 12 if h > 12 else h}:{mins:02d} {'PM' if h >= 12 else 'AM'}"


ramp = {r["year"]: r for r in TEP["net_load"]["by_year"]}
bands = {b["band"]: b for b in TEP["forecast"]["daily_peak_by_temp"]}
growth = {u: R["peak"][u]["growth"]["mean_load_change_2024_latest_pct"] for u in ("TEP", "APS", "SRP")}
S, RP, HF, BT = A4["storms"], A4["ramp"], A4["hot_day_forecast"], A4["battery"]
TEPCH = GRID / "peak" / "charts" / "tep"
ORANGE = RGBColor(0xD9, 0x59, 0x26)

# 1 Title
title_slide("c04.jpg", "Jake Moore, University of Arizona", "What Summer Costs Tucson's Grid",
            "Heat, Storms and Where the Money Goes, From Public Data", focus=(0.5, 0.35))

# 2 Research question
s = new_slide("Title Only")
s.shapes.title._element.getparent().remove(s.shapes.title._element)
picture_fill(s, IMG / "c12.jpg", 0, 0, 5.1, 7.5, focus=(0.55, 0.5))
for el in RQ_LINE:
    append(s, el)
text(s, 6.15, 1.45, 5.0, 0.75, "RESEARCH QUESTION:", size=36, bold=True, border=INK, align=PP_ALIGN.CENTER,
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 5.6, 2.55, 7.1, 2.35, "What does summer cost Tucson's electric grid, from the heat on one side and storms on "
     "the other, and where would money do the most good?", size=27, border=INK, anchor=MSO_ANCHOR.MIDDLE, margin=0.14)
text(s, 5.6, 5.25, 7.1, 0.9, [[("Two studies, one answer: ", {"bold": True}), ("peak demand in Python and SQL, storm "
     "outages in R, combined in one results file.", {})]], size=18, color=GREY)
finish(s)

# 3 Two sides of summer
s = content("Two Sides of Summer")
sides = [("HEAT PUSHES DEMAND UP", ORANGE, [
            f"Every °F above {TEP['heat']['breakpoint_f']:.0f}°F adds about {TEP['heat']['mw_per_f_above']:.0f} MW to the peak",
            f"The forecast runs about {HF['shortfall_mw_90_105f']} MW short on 90-105°F days",
            f"As solar grows, the evening climb grew {RP['growth_mean_mw']:.0f} MW in one year"]),
         ("STORMS KNOCK CUSTOMERS OUT", PLUM, [
            f"Outages cost Pima County about {m(S['customer_cost_per_year'])} a year",
            f"July holds {pct(N['jul'])} of all outage time",
            f"Night outages last {N['night_len']:.0f}% longer than daytime ones"])]
for i, (h, col, items) in enumerate(sides):
    x = 0.88 + i * 5.9
    shape(s, MSO_SHAPE.RECTANGLE, x, 2.25, 5.65, 0.7, fill=col, text_=h, size=19, bold=True)
    shape(s, MSO_SHAPE.RECTANGLE, x, 2.95, 5.65, 3.2, fill=WHITE, line=col)
    bullets(s, x + 0.15, 3.15, 5.35, 2.9, items, size=18, gap=8)
source(s, "Demand: Tucson Electric Power's grid area. Outages: Pima County. 2020-2026, all public data.")
finish(s)

# 4 The data
s = content("The Data – Six Public Sources")
cards = [("GRID", "EIA-930", "Hourly demand, day-ahead forecast and generation by fuel"),
         ("SALES", "EIA-861", "Yearly sales, customers and outage minutes"),
         ("WEATHER", "Open-Meteo", "Hourly temperature, dew point, rain and wind"),
         ("OUTAGES", "EAGLE-I, Oak Ridge", "Customers out in Pima County every 15 minutes"),
         ("OUTAGE COST", "Berkeley Lab", "What an outage costs homes and businesses"),
         ("BATTERIES", "NREL", "2024 cost of a 4-hour utility battery")]
for i, (h, src, what) in enumerate(cards):
    x, y = 0.88 + (i % 3) * 3.9, 2.2 + (i // 3) * 2.05
    shape(s, MSO_SHAPE.RECTANGLE, x, y, 3.7, 0.5, fill=PLUM, text_=h, size=15, bold=True)
    shape(s, MSO_SHAPE.RECTANGLE, x, y + 0.5, 3.7, 1.4, fill=WHITE, line=PLUM)
    text(s, x + 0.08, y + 0.56, 3.55, 0.4, src, size=15, bold=True, color=PLUM)
    text(s, x + 0.08, y + 0.95, 3.55, 0.9, what, size=15)
source(s, "All free and public. Arizona time (UTC-7, no daylight saving) throughout.")
finish(s)

# 5 How it's built
s = content("How I Built It")
steps = [("1  PULL", "pull.py runs both\npullers, pinned dates"),
         ("2  DEMAND", "Python + DuckDB\nheat, forecast, ramp"),
         ("3  OUTAGES", "R Markdown\ncost and 4 models"),
         ("4  COMBINE", "combine.py\none results.json"),
         ("5  CHECK", "check_numbers.py\nmemo, script, slides")]
for i, (h, b) in enumerate(steps):
    x = 0.88 + i * 2.3
    shape(s, MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON, x, 2.3, 2.33, 0.75, fill=PLUM, text_=h, size=16, bold=True)
    text(s, x + 0.1, 3.15, 2.2, 1.0, b, size=15, color=INK)
text(s, 0.88, 4.45, 11.6, 1.55, [[("Every number traces to the data. ", {"bold": True}),
     ("A checker reads the memo, the talk track and the text of these slides, pulls out every number and confirms "
      "each one is in results.json. A deliberately wrong number fails it.", {})]], size=18, border=INK, margin=0.16, anchor=MSO_ANCHOR.MIDDLE)
finish(s)

# 6 Divider
divider("c10.jpg", "Heat: The Demand Side", "What drives the peak, and how well it's predicted", focus=(0.5, 0.5))

# 7 Heat drives the peak
s = content("Heat Drives the Peak")
picture(s, TEPCH / "2_peak_vs_temperature.png", 0.75, 2.0, w=7.4)
h = TEP["heat"]
bullets(s, 8.4, 2.25, 4.1, 4.2, [
    [(f"Above {h['breakpoint_f']:.0f}°F, air conditioning takes over", {"bold": True})],
    (f"+{h['mw_per_f_above']:.0f} MW for every °F, {h['pct_of_mean_summer_peak_per_f']}% of a hot-day peak", 1),
    (f"Temperature explains {pct(h['fit_r2'])} of the day-to-day swings", 1),
    [(f"{pct(h['summer_peak_hour_share']['17:00'])} of summer days peak 5-6 PM", {"bold": True})],
    [("A hot night adds about a quarter as much as a hot afternoon", {})],
], size=17)
finish(s)

# 8 The forecast on hot days
s = content("The Forecast Runs Short on Hot Days")
picture(s, TEPCH / "3_peak_error_by_temperature.png", 0.75, 2.0, w=7.4)
bullets(s, 8.4, 2.25, 4.1, 4.3, [
    [("Day-ahead forecast: ", {"bold": True}), (f"{TEP['forecast']['mape_pct']}% average hourly miss", {})],
    [("Mild days: on target", {"bold": True})],
    [(f"90-105°F: {abs(HF['mean_err_pct_90_105f']):.1f}% low, about {HF['shortfall_mw_90_105f']} MW", {"bold": True, "color": RED})],
    [(f"110°F+: {abs(HF['err_pct_110f']):.1f}% low, about {HF['shortfall_mw_110f']} MW", {"bold": True, "color": RED})],
    ("Even when the weather forecast was right", 1),
], size=17)
finish(s)

# 9 Demand is barely growing
s = content("Demand Is Barely Growing")
wa = TEP["growth"]["weather_adjusted_mean_load_mw"]
rows = [["Weather-adjusted", "2024", "2025", "2026"],
        ["Average demand (MW)", f"{wa['2024']:,}", f"{wa['2025']:,}", f"{wa['2026']:,}"]]
table(s, 0.88, 2.2, 6.2, 1.1, rows, [2.6, 1.2, 1.2, 1.2], body_fills=[SLATE], size=16)
text(s, 0.88, 3.45, 6.2, 0.35, "Weather-adjusted: what each year would use under the same weather", size=12,
     font=SERIF, color=GREY, margin=0)
for i, (u, col) in enumerate([("APS", ORANGE), ("SRP", GREEN), ("TEP", NAVY)]):
    y = 2.3 + i * 1.15
    shape(s, MSO_SHAPE.RECTANGLE, 7.6, y, 4.85 * growth[u] / max(growth.values()), 0.75, fill=col)
    text(s, 7.6, y + 0.78, 4.9, 0.3, f"{u}  +{growth[u]}% since 2024", size=15, bold=True, margin=0)
text(s, 0.88, 4.2, 6.2, 1.9, [[("Growth isn't Tucson's problem. ", {"bold": True}),
     ("The Phoenix utilities are growing several times faster. In Tucson, the pressure comes from when power is "
      "needed, which is the next section.", {})]], size=17, border=INK, margin=0.14)
source(s, "Weather-adjusted average demand. APS and TEP through Nov 2026, SRP through 2025.")
finish(s)

# 10 Divider
divider("c09.jpg", "Solar and the Evening Ramp", "Why the hard hour is moving later", focus=(0.5, 0.55))

# 11 What the evening ramp is
s = content("What the Evening Ramp Is")
picture(s, GRID / "peak" / "charts" / "explainer_evening_ramp.png", 0.88, 1.95, w=8.1)
bullets(s, 9.25, 2.2, 3.25, 4.3, [
    [("Net load", {"bold": True}), (": demand minus solar and wind", {})],
    "What gas, coal, batteries and imports must supply",
    [("Evening ramp", {"bold": True}), (": its fast climb as solar fades", {})],
], size=17, gap=8)
source(s, "Illustrative shapes, not measured data.")
finish(s)

# 12 TEP's ramp
s = content("Tucson's Evening Ramp Grew in One Year")
picture(s, TEPCH / "4_net_load_profile.png", 0.75, 2.0, w=7.0)
rows = [["", "2024", "2025", "2026"],
        ["Solar share, midday", *(pct(ramp[y]["midday_solar_share"]) for y in (2024, 2025, 2026))],
        ["Avg 3-hour climb (MW)", *(f"{ramp[y]['mean_daily_max_3h_ramp_mw']:.0f}" for y in (2024, 2025, 2026))],
        ["Net-load peak", *(clock(ramp[y]["summer_net_peak_hour"]) for y in (2024, 2025, 2026))]]
table(s, 8.0, 2.2, 4.5, 1.9, rows, [1.95, 0.85, 0.85, 0.85], body_fills=[SLATE, LT], size=13)
bullets(s, 8.0, 4.35, 4.5, 2.0, [
    [(f"+{RP['growth_mean_mw']:.0f} MW in one year", {"bold": True, "color": RED}),
     (f" (+{RP['growth_p95_mw']:.0f} on the hardest days)", {})],
    f"Battery output at peak: {RP['battery_at_peak_2026_mw']:.0f} MW in 2026",
], size=16)
finish(s)

# 13 Divider
divider("c05.jpg", "Storms: The Outage Side", "What outages cost, and what makes a bad night", focus=(0.5, 0.45))

# 14-21 Storm slides, unchanged from the outage deck
outage_slide(9)     # 14 the worst night
outage_slide(10)    # 15 monsoon season
outage_slide(11)    # 16 humidity
outage_slide(14)    # 17 pricing an outage
outage_slide(15)    # 18 the price tag
outage_slide(20)    # 19 slower restoration at night
prs.slides[-1].shapes.title.text_frame.text = "Slower Restoration at Night"
outage_slide(25, mini_title=True)   # 20 flagging a big night by 3 PM
prs.slides[-1].shapes.title.text_frame.text = "Flagging a Big Night by 3 PM"
outage_slide(26)    # 21 does the flag hold up

# 22 Divider
divider("c13.jpg", "Where the Money Goes", "Two problems, measured two ways", focus=(0.5, 0.5))

# 23 Act 4 chart
s = content("Where the Money Goes")
picture(s, GRID / "charts" / "act4_where_the_money_goes.png", 1.27, 1.95, w=10.8)
source(s, "Left: dollars a year (2025 $); benefits exclude what each fix would cost. Right: megawatts. "
          "Not one ranking: the units differ.")
finish(s)

# 24 The comparison, with the battery yardstick
s = content("Putting the Two Sides Side by Side")
rows = [["Summer problem", "How big", "One fix, per year (2025 $)"],
        ["Storm outages", f"{m(S['customer_cost_per_year'])} a year to customers",
         f"10% fewer hit: {m(S['benefit_10pct_fewer_interrupted'])}. 10% faster: {m(S['benefit_10pct_faster'])}. "
         f"Night at day pace: {m(S['benefit_night_at_day_pace'])}"],
        ["Evening ramp", f"+{RP['growth_mean_mw']:.0f} MW in one year",
         f"Batteries for that growth: about {m(RP['yardstick_growth_mean_per_year'])}"],
        ["Hot-day forecast", f"{HF['shortfall_mw_90_105f']} MW short, 90-105°F",
         "A modeling fix, no build. No public price"]]
table(s, 0.88, 2.15, 11.6, 2.4, rows, [2.3, 3.4, 5.9], body_fills=[SLATE, LT], size=15)
text(s, 0.88, 4.8, 11.6, 0.95, [[("Battery yardstick: ", {"bold": True}),
     (f"NREL's 2024 cost for a 4-hour battery, ${BT['usd_per_kw_2025']:,} per kW in 2025 dollars, spread over a "
      f"{BT['life_years']}-year life plus 2.5% a year upkeep: about ${BT['usd_per_kw_year_2025']:.0f} per kW each year. "
      "No financing cost, so it's a floor.", {})]], size=16, border=INK, margin=0.14)
finish(s)

# 25 What this means
s = content("What This Means")
bullets(s, 0.88, 2.2, 11.6, 4.3, [
    [("Storm outages are the biggest dollar figure. ", {"bold": True, "color": PLUM}),
     (f"At {m(S['customer_cost_per_year'])} a year, each improvement priced here is worth "
      f"{m(S['benefit_10pct_faster'])} to {m(S['benefit_night_at_day_pace'])} a year, before its own cost.", {})],
    [("The evening is the grid's new pressure. ", {"bold": True, "color": ORANGE}),
     (f"One year of solar growth added a ramp worth about {m(RP['yardstick_growth_mean_per_year'])} a year in batteries.", {})],
    [("The forecast gap is a modeling problem. ", {"bold": True}),
     (f"{HF['shortfall_mw_90_105f']} MW short on hot days is fixed in the model, not by building anything.", {})],
    [("Both land on summer evenings. ", {"bold": True}),
     ("Storms build from mid-afternoon; the net-load peak now comes after 6 PM.", {})],
], size=19, gap=10)
finish(s)

# 26 Limitations and conclusion
s = content("Limitations and What I Learned")
bullets(s, 0.88, 2.2, 6.1, 4.2, [
    [("Two areas: ", {"bold": True}), ("demand is TEP's grid area, outages are Pima County", {})],
    [("Benefits only: ", {"bold": True}), ("what each fix would cost TEP isn't public", {})],
    [("Battery yardstick is a floor: ", {"bold": True}), ("no financing, one tool among several", {})],
    [("Associations, not causes", {"bold": True})],
    [("Public forecast, not TEP's planning model", {"bold": True})],
], size=17, gap=6)
text(s, 7.3, 2.2, 5.2, 2.75, [[("What I learned", {"bold": True})],
     [("The hard part was putting two different measurements on one page without pretending they're the same. "
       "Outage costs are dollars to customers, the ramp is megawatts, so I showed both and gave the megawatts a "
       "sourced yardstick instead of forcing one ranking.", {})]], size=17, border=PLUM, margin=0.16)
finish(s)

# 27 References
s = content("References")
bullets(s, 0.88, 2.15, 11.6, 4.4, [
    "U.S. EIA. Form EIA-930 hourly balancing authority data; Forms EIA-861 and EIA-861M.",
    "ORNL. EAGLE-I yearly outage files 2020-2025, figshare 24237376. Brelsford et al. (2024), Scientific Data 11, 271.",
    "NOAA NCEI. Storm Events Database. Open-Meteo. Historical Weather (ERA5) and Previous Runs APIs.",
    "Sullivan, Schellenberg & Blundell (2015). LBNL-6941E, Tables ES-1 and ES-2.",
    "Cole, Ramasamy & Turan (2025). Cost Projections for Utility-Scale Battery Storage: 2025 Update. NREL/TP-6A40-93281.",
    "NREL (2024). Annual Technology Baseline: Utility-Scale Battery Storage.",
    "U.S. BLS. CPI-U, series CUUR0000SA0.",
    "Photos: Wikimedia Commons, mostly A Guy Named Nyal (CC BY-SA 2.0); credits in outages/deck/img/credits.json.",
], size=14, font=SERIF, gap=5)
finish(s)

sldIdLst = prs.slides._sldIdLst
assert len(sldIdLst) == 27, len(sldIdLst)
if MINI_FLAG:
    for i, sldId in reversed(list(enumerate(list(sldIdLst), start=1))):
        if i not in GRID_KEEP:
            prs.part.drop_rel(sldId.rId)
            sldIdLst.remove(sldId)
prs.save(str(OUT_FILE))
print(f"wrote {OUT_FILE.name} with {len(sldIdLst)} slides; notes on "
      f"{sum(1 for sl in prs.slides if sl.has_notes_slide and sl.notes_slide.notes_text_frame.text.strip())}")
