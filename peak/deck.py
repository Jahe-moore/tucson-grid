"""Companion PowerPoint for the Arizona grid episode, drawn from results.json and data/grid.duckdb.

    python analysis.py && python deck.py

Writes ..\\YouTube\\02_Arizona_Grid\\Arizona_Grid.pptx. Consulting standard: action titles, Georgia titles, Arial body,
navy plus one steel accent, section tracker, source line on every data slide, native (editable) charts, speaker notes
taken from deck_script.md. Series colors are the reference palette's light-mode steps (TEP blue, APS orange, SRP aqua).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
EP = HERE.parent / "YouTube" / "02_Arizona_Grid"
OUT = EP / "Arizona_Grid.pptx"
R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
con = duckdb.connect(str(HERE / "data" / "grid.duckdb"), read_only=True)
NAMES = ["TEP", "APS", "SRP"]

NAVY, STEEL = "1B2A41", "4F7CAC"
INK, INK2, MUTED, RULE, BAR_MUTED = "1F1F1F", "404040", "6E6E6E", "C9CED6", "B4B7BC"
SER = {"TEP": "2A78D6", "APS": "EB6834", "SRP": "1BAF7A"}
TITLE_FONT, BODY_FONT = "Georgia", "Arial"
SECTIONS = ["Approach", "Data quality", "Heat", "Growth", "Forecasts", "Evening ramp", "Recommendation"]
SRC = "Source: EIA-930 hourly balancing-area data, EIA-861, Open-Meteo. Analysis: Jake Moore."
L, W = 0.6, 12.13  # content left edge and width, inches

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
NOTES = {}


def rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h)


# ---------- deck_script.md -> speaker notes ----------
def deck_script() -> dict[int, str]:
    body = (EP / "deck_script.md").read_text(encoding="utf-8").split("\n---\n")[1]
    out = {}
    for blk in re.split(r"\n(?=## Slide )", body):
        m = re.match(r"## Slide (\d+)[^\n]*\n", blk)
        if m:
            out[int(m.group(1))] = "\n\n".join(" ".join(p.split()) for p in blk[m.end():].strip().split("\n\n"))
    return out


NOTES = deck_script()


# ---------- text helpers ----------
def text(s, x, y, w, h, runs, size=17, color=INK, font=BODY_FONT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None, space_after=0):
    """runs: str, or list of paragraphs; each paragraph a str or list of (text, {opts})."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = [runs] if isinstance(runs, str) else runs
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        for t, o in ([(p, {})] if isinstance(p, str) else p):
            r = para.add_run()
            r.text = t
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = rgb(o.get("color", color))
    return tb


def rule(s, x1, y1, x2, y2, color=RULE, width=0.75):
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    ln.line.color.rgb = rgb(color)
    ln.line.width = Pt(width)
    return ln


def frame(section: str | None, title: str, source: str | None = SRC, page=True):
    s = prs.slides.add_slide(BLANK)
    if section:
        runs = []
        for i, sec in enumerate(SECTIONS):
            on = sec == section
            runs.append((sec, {"bold": on, "color": NAVY if on else "9A9EA5"}))
            if i < len(SECTIONS) - 1:
                runs.append(("     ", {}))
        text(s, L, 0.32, W, 0.3, [runs], size=11, name="Section tracker")
        rule(s, L, 0.68, L + W, 0.68)
    text(s, L, 0.85, W, 1.05, title, size=26, color=NAVY, font=TITLE_FONT, bold=True, name="Title",
         anchor=MSO_ANCHOR.TOP)
    if source:
        text(s, L, 7.0, 10.5, 0.25, source, size=11, color=MUTED, name="Source")
    if page:
        text(s, 12.23, 7.0, 0.5, 0.25, str(len(prs.slides)), size=11, color=MUTED, align=PP_ALIGN.RIGHT,
             name="Page number")
    return s


def dark_slide(title: str, sub: str, byline: str):
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = rgb(NAVY)
    text(s, 0.9, 2.3, 11.5, 1.6, title, size=42, color="FFFFFF", font=TITLE_FONT, bold=True, name="Title",
         anchor=MSO_ANCHOR.BOTTOM)
    rule(s, 0.9, 4.15, 4.4, 4.15, color=STEEL, width=1.5)
    text(s, 0.9, 4.4, 11.5, 0.9, sub, size=20, color="D5DEEA", name="Subtitle")
    text(s, 0.9, 6.4, 11.5, 0.4, byline, size=14, color="A9B6C8", name="Byline")
    return s


# ---------- chart helpers ----------
def style_chart(ch, legend=False, size=14):
    ch.font.name = BODY_FONT
    ch.font.size = Pt(size)
    ch.font.color.rgb = rgb(INK2)
    ch.has_title = False
    ch.has_legend = legend
    if legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(size)
    try:
        va = ch.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb("E3E5E8")
        va.major_gridlines.format.line.width = Pt(0.75)
        va.format.line.fill.background()
        va.tick_labels.font.size = Pt(size)
        va.tick_labels.font.color.rgb = rgb(MUTED)
        ca = ch.category_axis
        ca.format.line.color.rgb = rgb(RULE)
        ca.tick_labels.font.size = Pt(size)
        ca.tick_labels.font.color.rgb = rgb(MUTED)
        ca.has_major_gridlines = False
    except Exception:
        pass


def axis_title(axis, t, size=13):
    axis.has_title = True
    tf = axis.axis_title.text_frame
    tf.text = t
    r = tf.paragraphs[0].runs[0]
    r.font.size = Pt(size)
    r.font.bold = False
    r.font.color.rgb = rgb(MUTED)
    r.font.name = BODY_FONT


def label_skip(ch, n: int):
    cat = ch._chartSpace.find(".//" + qn("c:catAx"))
    if cat is None:
        return
    el = etree.SubElement(cat, qn("c:tickLblSkip"))
    el.set("val", str(n))
    nm = cat.find(qn("c:noMultiLvlLbl"))
    if nm is not None:
        nm.addprevious(el)
    mk = etree.Element(qn("c:tickMarkSkip"))
    mk.set("val", str(n))
    el.addnext(mk)


def line_series(ch, colors, widths=None, dash=None):
    for i, ser in enumerate(ch.plots[0].series):
        ser.smooth = False
        ser.marker.style = XL_MARKER_STYLE.NONE
        ser.format.line.color.rgb = rgb(colors[i])
        ser.format.line.width = Pt((widths or [2.25] * 9)[i])
        if dash and dash[i]:
            ser.format.line.dash_style = dash[i]


def end_label(ser, idx: int, t: str, size=14):
    dl = ser.points[idx].data_label
    dl.has_text_frame = True
    dl.text_frame.text = t
    r = dl.text_frame.paragraphs[0].runs[0]
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = rgb(INK)
    dl.position = XL_LABEL_POSITION.RIGHT


def add_chart(s, kind, data, x, y, w, h, name):
    gf = s.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), data)
    gf.name = name
    return gf.chart


def bar_colors(ch, colors):
    ser = ch.plots[0].series[0]
    for i, c in enumerate(colors):
        p = ser.points[i]
        p.format.fill.solid()
        p.format.fill.fore_color.rgb = rgb(c)
    for dpt in ser._element.findall(qn("c:dPt")):  # keep negative bars filled
        inv = etree.Element(qn("c:invertIfNegative"))
        inv.set("val", "0")
        dpt.find(qn("c:idx")).addnext(inv)


def value_labels(ch, fmt, pos=XL_LABEL_POSITION.OUTSIDE_END, size=16):
    pl = ch.plots[0]
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.number_format = fmt
    dl.number_format_is_linked = False
    dl.position = pos
    dl.font.size = Pt(size)
    dl.font.bold = True
    dl.font.color.rgb = rgb(INK)


def side_notes(s, x, y, w, items, size=17, gap=0.22):
    """Commentary column: list of (headline, detail) with thin rules between, no cards."""
    cy = y
    for i, (head, det) in enumerate(items):
        lines = max(1, round(len(det) / (w * 9.0) + 0.49)) if det else 0
        h = 0.36 + lines * 0.3
        paras = [[(head, {"bold": True, "color": NAVY})]]
        if det:
            paras.append([(det, {"size": size - 2, "color": INK2})])
        text(s, x, cy, w, h, paras, size=size, space_after=3, name=f"Note {i + 1}")
        cy += h + gap
        if i < len(items) - 1:
            rule(s, x, cy - gap / 2, x + w, cy - gap / 2)
    return cy


HOUR_LABELS = ["12a", "1a", "2a", "3a", "4a", "5a", "6a", "7a", "8a", "9a", "10a", "11a",
               "12p", "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p", "10p", "11p"]

# =====================================================================================================
# 1 Title
s = dark_slide("Arizona's Grid on the Hottest Afternoon",
               "How TEP, APS and SRP handle heat, growth and the evening solar ramp, from public data only",
               "Jake Moore  ·  University of Arizona, MIS  ·  November 2026")

# 2 Short answer (SCRA)
s = frame(None, "Arizona's three big grids react to heat the same way, but their growth, forecasts and evenings "
          "are drifting apart", source=SRC)
rows = [("Situation", "TEP, APS and SRP each publish a day-ahead load forecast, and Arizona's yearly peak lands on "
         "the hottest summer afternoons."),
        ("Complication", "Load is growing at very different rates, solar is reshaping the evening, and every forecast "
         "series has a reporting break that distorts a simple score."),
        ("Resolution", "All three add about 2% of peak per °F above 80-84°F and peak at 5-6 PM. Forecasts miss by "
         "3-4% an hour, and TEP's hot-day peak runs 1.5-2% low."),
        ("Action", "Run a daily hot-day check that flags any day-ahead peak more than 2% below what the temperature "
         "slope predicts.")]
y0, rh = 2.2, 1.12
for i, (lab, body) in enumerate(rows):
    y = y0 + i * rh
    text(s, L, y, 2.3, rh - 0.2, lab, size=19, color=NAVY if lab != "Action" else STEEL, font=TITLE_FONT, bold=True,
         name=f"SCRA label {i + 1}")
    text(s, L + 2.5, y, W - 2.5, rh - 0.2, body, size=18, name=f"SCRA text {i + 1}")
    if i < len(rows) - 1:
        rule(s, L, y + rh - 0.14, L + W, y + rh - 0.14)

# 3 The data
s = frame("Approach", "Five years of public hourly data cover all three grids, with no utility access needed")
srcs = [("EIA-930 hourly grid data", "For every balancing area, every hour: actual load, the day-ahead forecast, "
         "generation by fuel, and flows in and out."),
        ("EIA-861 annual filings", "Each utility's retail sales by customer class, customer counts and outage "
         "minutes; used to check what the hourly data is counting."),
        ("Open-Meteo weather", "Hourly temperature for central Tucson and Phoenix Sky Harbor, plus what the weather "
         "models predicted the day before.")]
side_notes(s, L, 2.15, 7.4, srcs, size=18, gap=0.3)
rule(s, 8.55, 2.2, 8.55, 6.6)
n_rows = con.execute("SELECT count(*) FROM hourly").fetchone()[0]
stats = [(f"{round(n_rows, -3):,}", "hourly rows, one per area per hour"),
         ("Jan 2022 - Nov 2026", "almost five years"),
         ("3 balancing areas", "TEP in Tucson; APS and SRP in Phoenix")]
for i, (big, small) in enumerate(stats):
    y = 2.15 + i * 1.5
    text(s, 8.9, y, 3.8, 0.7, big, size=30 if i == 0 else 24, color=NAVY, font=TITLE_FONT, bold=True,
         name=f"Stat {i + 1}", anchor=MSO_ANCHOR.BOTTOM)
    text(s, 8.9, y + 0.75, 3.8, 0.5, small, size=15, color=MUTED, name=f"Stat {i + 1} label")

# 4 The system (chevrons)
s = frame("Approach", "A five-step pipeline turns public files into one memo per grid, and reruns any week",
          source="Code: pull.py, analysis.py (DuckDB), visuals.py, deck.py.")
steps = [("Pull", "Stream each 45 MB EIA file and keep only the three Arizona areas; add weather and filings"),
         ("Store", "One DuckDB table, one row per area per hour, joined to its weather"),
         ("Check", "Duplicates, gaps, copied forecasts, and reporting breaks found by their shape"),
         ("Model", "Heat response, growth with weather removed, forecast scoring, evening ramp"),
         ("Decide", "One memo per area and a side-by-side, every number traced to a query")]
cw, ov = 2.49, 0.15
for i, (head, body) in enumerate(steps):
    x = L + i * (cw - ov + 0.06)
    shp = s.shapes.add_shape(MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON, Inches(x), Inches(2.35),
                             Inches(cw), Inches(0.85))
    shp.name = f"Step {i + 1}"
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(STEEL if head == "Check" else NAVY)
    shp.line.fill.background()
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.text = head
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size = Pt(20)
    p.runs[0].font.bold = True
    p.runs[0].font.name = BODY_FONT
    p.runs[0].font.color.rgb = rgb("FFFFFF")
    text(s, x + 0.12, 3.5, cw - 0.45, 2.4, body, size=17, color=INK2, name=f"Step {i + 1} detail")
rule(s, L, 6.05, L + W, 6.05)
text(s, L, 6.2, W, 0.6, [[("The check step matters most: ", {"bold": True, "color": STEEL}),
                          ("the first forecast scores were wrong in a convincing way, because the reporting itself "
                           "had changed.", {})]], size=17, name="Callout")

# 5 Reporting breaks
s = frame("Data quality", "Every forecast series has a reporting break, so each is scored only on its "
          "like-for-like months")
win = R["meta"]["forecast_windows"]
for i, u in enumerate(NAMES):
    m = R[u]["breaks"]["monthly"]
    months = m["month"]
    lo, hi = win[u]
    inside = [lo[:7] <= mo <= hi[:7] for mo in months]
    cd = CategoryChartData()
    cd.categories = [mo[:4] if mo.endswith("-01") else "" for mo in months]
    scored = [v if ok else None for v, ok in zip(m["bias_pct"], inside)]
    left = [v if (not ok or (j + 1 < len(inside) and not inside[j + 1]) or (j > 0 and not inside[j - 1])) else None
            for j, (v, ok) in enumerate(zip(m["bias_pct"], inside))]
    cd.add_series("Left out", left)
    cd.add_series("Scored", scored)
    y = 2.0 + i * 1.55
    ch = add_chart(s, XL_CHART_TYPE.LINE, cd, L + 1.0, y, 8.1, 1.5, f"{u} monthly bias chart")
    style_chart(ch, size=12)
    line_series(ch, [BAR_MUTED, SER[u]], [2.0, 2.5])
    ch.value_axis.tick_labels.number_format = '0"%"'
    ch.value_axis.tick_labels.number_format_is_linked = False
    ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    label_skip(ch, 1)
    if i < 2:
        ch.category_axis.tick_labels.font.color.rgb = rgb("FFFFFF")
    text(s, L, y + 0.55, 0.9, 0.4, u, size=18, bold=True, name=f"{u} label")
side_notes(s, 9.95, 2.1, 2.78, [
    ("TEP: Aug 2023", "Forecast ran ~13% above load, then dropped to zero the month in-area gas output doubled."),
    ("APS: Feb 2025", "Reported load stepped above the forecast overnight; scored through Jan 2025."),
    ("SRP: Mar 2026", "Forecast sits a flat 500-700 MW above load every hour; later months left out.")],
    size=16, gap=0.2)
text(s, L + 1.0, 6.72, 8.1, 0.25, "Monthly average of (day-ahead forecast - actual load) / actual load. "
     "Gray months are left out of scoring.", size=12, color=MUTED, name="Chart note")

# 6 APS gap shape
s = frame("Data quality", "Since Feb 2025, APS's reported load has run 450-700 MW above its forecast overnight, "
          "with no public cause")
rows6 = con.execute("""SELECT CASE WHEN day < DATE '2025-02-01' THEN 'before' ELSE 'after' END AS p, hour,
                       avg(demand_raw - forecast) AS gap FROM hourly WHERE utility='APS'
                       AND day >= DATE '2024-02-01' GROUP BY 1, 2 ORDER BY 1, 2""").df()
cd = CategoryChartData()
cd.categories = HOUR_LABELS
cd.add_series("Feb 2024 - Jan 2025", [round(v) for v in rows6[rows6.p == "before"].gap])
cd.add_series("Feb 2025 on", [round(v) for v in rows6[rows6.p == "after"].gap])
ch = add_chart(s, XL_CHART_TYPE.LINE, cd, L, 2.0, 7.9, 4.75, "APS gap by hour chart")
style_chart(ch, legend=True)
line_series(ch, [BAR_MUTED, SER["APS"]], [2.25, 3.5])
ch.value_axis.tick_labels.number_format = '#,##0'
ch.value_axis.tick_labels.number_format_is_linked = False
ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
axis_title(ch.value_axis, "Actual load minus forecast (MW)")
label_skip(ch, 3)
side_notes(s, 8.95, 2.1, 3.78, [
    ("A night-time block", "The new gap is 450-700 MW overnight and appeared within one month; a forecast "
     "miss would follow the afternoon heat instead."),
    ("Sales did not jump", "APS's own retail sales rose only 1.5% in 2025, so the block is not APS customers "
     "alone."),
    ("Kept separate", "APS is scored through January 2025; later months are reported on their own.")], size=17)

# 7 Heat scatter
s = frame("Heat", "Above about 82°F, every extra degree adds 61 MW to TEP's daily peak and about 140 MW to each "
          "Phoenix grid")
for i, u in enumerate(NAMES):
    d = con.execute(f"""SELECT max(temp_f) AS t, max(demand) AS p FROM hourly WHERE utility='{u}'
                        {"AND day >= DATE '2023-08-01'" if u == "TEP" else ""}
                        {"AND day <= DATE '2026-02-28'" if u == "SRP" else ""} GROUP BY day""").df().dropna()
    xd = XyChartData()
    ser = xd.add_series(u)
    for t, p in zip(d.t, d.p):
        ser.add_data_point(round(float(t), 1), round(float(p) / 1000, 3))
    x = L + i * 4.1
    h = R[u]["heat"]
    text(s, x, 2.0, 3.9, 0.7, [[(u, {"bold": True, "size": 20})],
                               [(f"+{h['mw_per_f_above']:.0f} MW per °F above {h['breakpoint_f']:.0f}°F",
                                 {"size": 16, "color": INK2})]], name=f"{u} heading")
    ch = add_chart(s, XL_CHART_TYPE.XY_SCATTER, xd, x - 0.1, 2.75, 3.95, 4.0, f"{u} heat scatter")
    style_chart(ch, size=12)
    sr = ch.plots[0].series[0]
    sr.format.line.fill.background()
    sr.marker.style = XL_MARKER_STYLE.CIRCLE
    sr.marker.size = 3
    sr.marker.format.fill.solid()
    sr.marker.format.fill.fore_color.rgb = rgb(SER[u])
    sr.marker.format.line.fill.background()
    ch.category_axis.minimum_scale = 30
    ch.category_axis.maximum_scale = 120
    ch.category_axis.major_unit = 30
    ch.value_axis.tick_labels.number_format = '0.0'
    ch.value_axis.tick_labels.number_format_is_linked = False
    axis_title(ch.category_axis, "Daily high (°F)", size=12)
    if i == 0:
        axis_title(ch.value_axis, "Daily peak (thousand MW)", size=12)
text(s, L, 6.78, W, 0.2, "Each dot is one day. TEP from Aug 2023 and SRP through Feb 2026, after each area's "
     "reporting break.", size=11, color=MUTED, name="Chart note")

# 8 Heat scaled
s = frame("Heat", "Scaled to their size, all three grids add about 2% of their hot-day peak for every degree")
cd = CategoryChartData()
cd.categories = NAMES
cd.add_series("% of hot-day peak per °F", [R[u]["heat"]["pct_of_mean_summer_peak_per_f"] for u in NAMES])
ch = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, cd, L, 2.0, 6.9, 4.75, "Heat per degree chart")
style_chart(ch)
bar_colors(ch, [SER[u] for u in NAMES])
ch.plots[0].gap_width = 120
value_labels(ch, '0.0"%"', size=18)
axis_title(ch.value_axis, "Added peak per °F, % of hot-day peak")
ch.value_axis.minimum_scale = 0
ch.value_axis.maximum_scale = 2.6
ch.value_axis.tick_labels.number_format = '0.0"%"'
ch.value_axis.tick_labels.number_format_is_linked = False
ch.category_axis.tick_labels.font.size = Pt(16)
ch.category_axis.tick_labels.font.bold = True
side_notes(s, 8.0, 2.1, 4.73, [
    ("110°F vs 100°F: about 20% more peak", "Ten degrees at roughly 2% each, on the same grid."),
    ("In megawatts", f"TEP {R['TEP']['heat']['mw_per_f_above']:.0f}, APS {R['APS']['heat']['mw_per_f_above']:.0f}, "
     f"SRP {R['SRP']['heat']['mw_per_f_above']:.0f} MW per °F above each grid's breakpoint."),
    ("Hot nights matter most at SRP", "Each degree of summer overnight low adds 28 MW at SRP, 12 at TEP and 10 at "
     "APS, on top of daytime heat.")], size=17)

# 9 Peak together
s = frame("Heat", "All three peak in the same 5-6 PM hour, so a statewide heat wave tightens every grid at once")
hp = con.execute("""SELECT utility, hour, avg(demand) AS load FROM hourly WHERE month(day) IN (7, 8)
                    AND year(day) = 2025 GROUP BY 1, 2 ORDER BY 1, 2""").df()
cd = CategoryChartData()
cd.categories = HOUR_LABELS
for u in NAMES:
    g = hp[hp.utility == u]
    cd.add_series(u, [round(v, 1) for v in (g.load / g.load.max() * 100)])
ch = add_chart(s, XL_CHART_TYPE.LINE, cd, L, 2.0, 7.9, 4.75, "Average summer day chart")
style_chart(ch, legend=True)
line_series(ch, [SER[u] for u in NAMES], [2.75] * 3)
ch.value_axis.minimum_scale = 50
ch.value_axis.maximum_scale = 100
ch.value_axis.major_unit = 10
ch.value_axis.tick_labels.number_format = '0"%"'
ch.value_axis.tick_labels.number_format_is_linked = False
axis_title(ch.value_axis, "% of the grid's own peak hour")
label_skip(ch, 3)
corr = R["arizona"]["summer_daily_peak_corr"]
side_notes(s, 8.95, 2.1, 3.78, [
    ("Same hour", "July-August 2025: all three average their peak in the 5-6 PM hour."),
    ("Same days", f"Summer daily peaks correlate {min(corr.values()):.2f}-{max(corr.values()):.2f}; all three "
     f"share {R['arizona']['shared_top20_all_three']} of their 20 highest-load days."),
    ("Question it raises", "If every grid peaks together, how much import is available when the others need it "
     "too?")], size=17)
text(s, L, 6.78, 7.9, 0.2, "July-August 2025 average day, each grid scaled to its own peak hour.", size=11,
     color=MUTED, name="Chart note")

# 10 Growth
s = frame("Growth", "With weather removed, the APS area's load grew 10.8% since 2024, while TEP and SRP grew under 3%")
years = [2022, 2023, 2024, 2025, 2026]
cd = CategoryChartData()
cd.categories = ["2022", "2023", "2024", "2025", "2026*"]
for u in NAMES:
    g = {int(k): v for k, v in R[u]["growth"]["weather_adjusted_mean_load_mw"].items()}
    cd.add_series(u, [round(g[y] / g[2022] * 100, 1) if y in g else None for y in years])
ch = add_chart(s, XL_CHART_TYPE.LINE_MARKERS, cd, L, 2.0, 7.9, 4.75, "Weather-adjusted growth chart")
style_chart(ch, legend=True)
line_series(ch, [SER[u] for u in NAMES], [2.75] * 3)
for i, u in enumerate(NAMES):
    sr = ch.plots[0].series[i]
    sr.marker.style = XL_MARKER_STYLE.CIRCLE
    sr.marker.size = 9
    sr.marker.format.fill.solid()
    sr.marker.format.fill.fore_color.rgb = rgb(SER[u])
    sr.marker.format.line.color.rgb = rgb("FFFFFF")
ch.value_axis.minimum_scale = 95
ch.value_axis.maximum_scale = 125
ch.value_axis.major_unit = 5
axis_title(ch.value_axis, "Average load, weather removed (2022 = 100)")
on = R["arizona"]["jul_aug_2025_overnight_min_pct_of_peak"]
side_notes(s, 8.95, 2.1, 3.78, [
    ("Since 2024", "APS area +10.8% (to Nov 2026), SRP +2.6% (2025), TEP +1.7% (to Nov 2026)."),
    ("Load that runs all night", f"The APS area's overnight low sits at {on['APS']:.1f}% of its peak hour, vs "
     f"{on['TEP']:.1f}% at TEP and {on['SRP']:.1f}% at SRP."),
    ("2025 outran retail sales", "The area added about 337 MW of average load while APS's retail sales rose 1.5%.")],
    size=17)
text(s, L, 6.78, 7.9, 0.2, "* 2026 through Nov 2. SRP stops at 2025: its reported load changed coverage in "
     "March 2026.", size=11, color=MUTED, name="Chart note")

# 11 Forecast skill
a = R["arizona"]["forecast_peer_window"]
s = frame("Forecasts", "TEP and SRP forecasts miss by about 3% an hour and are statistically tied; APS trails by "
          "about a point")
cd = CategoryChartData()
cd.categories = NAMES
cd.add_series("MAPE", [a[u]["mape_pct"] for u in NAMES])
ch = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, cd, L, 2.0, 6.4, 4.75, "Forecast skill chart")
style_chart(ch)
bar_colors(ch, [SER[u] for u in NAMES])
ch.plots[0].gap_width = 120
value_labels(ch, '0.00"%"', size=18)
ch.value_axis.minimum_scale = 0
ch.value_axis.maximum_scale = 5
ch.value_axis.major_unit = 1
ch.value_axis.tick_labels.number_format = '0"%"'
ch.value_axis.tick_labels.number_format_is_linked = False
axis_title(ch.value_axis, "Average hourly miss (MAPE)")
ch.category_axis.tick_labels.font.size = Pt(16)
ch.category_axis.tick_labels.font.bold = True
# interval table, thin rules only
tx, ty = 7.5, 2.15
text(s, tx, ty, 5.2, 0.4, "95% ranges, 14-day blocks resampled", size=16, bold=True, color=NAVY, name="Range head")
rows11 = [(u, f"{a[u]['mape_pct']:.2f}%", f"{a[u]['ci95'][0]:.2f} to {a[u]['ci95'][1]:.2f}") for u in NAMES]
rows11 += [(k, f"{a[k]['mean_pct_points']:+.2f} pts", f"{a[k]['ci95'][0]:+.2f} to {a[k]['ci95'][1]:+.2f}")
           for k in ("TEP minus SRP", "TEP minus APS", "SRP minus APS")]
for i, (k, v, ci) in enumerate(rows11):
    y = ty + 0.55 + i * 0.5
    text(s, tx, y, 2.3, 0.4, k, size=16, name=f"Range row {i + 1} name")
    text(s, tx + 2.3, y, 1.3, 0.4, v, size=16, bold=True, align=PP_ALIGN.RIGHT, name=f"Range row {i + 1} value")
    text(s, tx + 3.75, y, 1.45, 0.4, ci, size=16, color=INK2, align=PP_ALIGN.RIGHT, name=f"Range row {i + 1} ci")
    rule(s, tx, y + 0.44, tx + 5.2, y + 0.44, width=0.75 if i != 2 else 1.25, color=RULE if i != 2 else MUTED)
text(s, tx, ty + 3.7, 5.2, 0.9, "TEP minus SRP crosses zero: no detectable difference. Both differences "
     "against APS stay below zero.", size=16, color=INK2, name="Range note")
text(s, L, 6.78, 6.4, 0.2, "Aug 2023 to Jan 2025, the window where all three report consistently.", size=11,
     color=MUTED, name="Chart note")

# 12 TEP hot days
b = R["TEP"]["forecast"]["daily_peak_by_temp"]
ws = R["TEP"]["forecast"]["weather_surprise_summer"]
s = frame("Forecasts", "TEP's day-ahead peak runs 1.5-2% low on 90-105°F days, even when the weather forecast was "
          "right")
cd = CategoryChartData()
cd.categories = [f"{x['band']}°F" for x in b]
cd.add_series("Peak forecast minus actual", [x["mean_err_pct"] for x in b])
ch = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, cd, L, 2.0, 7.9, 4.75, "TEP hot-day error chart")
style_chart(ch)
bar_colors(ch, [SER["TEP"] if x["band"] in ("90-100", "100-105") else BAR_MUTED for x in b])
ch.plots[0].gap_width = 80
ch.plots[0].series[0].invert_if_negative = False
value_labels(ch, '+0.0"%";-0.0"%"', size=16)
ch.value_axis.minimum_scale = -5
ch.value_axis.maximum_scale = 1
ch.value_axis.tick_labels.number_format = '0"%"'
ch.value_axis.tick_labels.number_format_is_linked = False
ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
ch.category_axis.tick_labels.font.size = Pt(14)
axis_title(ch.value_axis, "Day-ahead peak minus actual peak (%)")
side_notes(s, 8.95, 2.1, 3.78, [
    ("Hot days only", "Below 90°F the peak forecast is unbiased; 90-105°F days run 1.65-1.78% low."),
    ("Not the weather call", f"On {ws['within 3F']['days']} summer days when the temperature forecast was within "
     f"3°F, the peak still ran {abs(ws['within 3F']['mean_err_pct']):.2f}% low."),
    ("110°F+ is thin", "That band is 10 days, so its -4.1% is suggestive only.")], size=17)
text(s, L, 6.78, 7.9, 0.2, "TEP, Aug 2023 to Nov 2026, by daily high. Days per band: " + ", ".join(str(x["days"]) for x in b) + ".", size=11, color=MUTED, name="Chart note")

# 13 Evening ramp
s = frame("Evening ramp", "Solar now covers 42% of the APS area's midday load, and its evening climb doubled to "
          "2,104 MW")
hr = R["APS"]["net_load"]["jul_aug_by_hour"]
cd = CategoryChartData()
cd.categories = HOUR_LABELS
cd.add_series("Load", [round(v / 1000, 2) for v in hr["load"]])
cd.add_series("Load minus utility solar and wind", [round(v / 1000, 2) for v in hr["net"]])
ch = add_chart(s, XL_CHART_TYPE.LINE, cd, L, 2.35, 6.6, 4.4, "APS average day chart")
style_chart(ch, legend=True)
from pptx.enum.dml import MSO_LINE_DASH_STYLE  # noqa: E402
line_series(ch, [SER["APS"], NAVY], [3.0, 2.5], [None, MSO_LINE_DASH_STYLE.DASH])
ch.value_axis.tick_labels.number_format = '0.0'
ch.value_axis.tick_labels.number_format_is_linked = False
axis_title(ch.value_axis, "Thousand MW")
label_skip(ch, 3)
text(s, L, 2.0, 6.6, 0.35, "APS area, July-August 2026 average day", size=16, bold=True, color=NAVY,
     name="Left chart head")
rows13 = R["APS"]["net_load"]["by_year"]
cd = CategoryChartData()
cd.categories = [str(r["year"]) for r in rows13]
cd.add_series("Evening 3-hour climb (MW)", [round(r["mean_daily_max_3h_ramp_mw"]) for r in rows13])
ch = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, cd, 7.55, 2.35, 5.18, 4.4, "APS ramp by year chart")
style_chart(ch)
bar_colors(ch, [SER["APS"] if r["year"] == rows13[-1]["year"] else BAR_MUTED for r in rows13])
ch.plots[0].gap_width = 70
value_labels(ch, '#,##0', size=15)
ch.value_axis.minimum_scale = 0
ch.value_axis.maximum_scale = 2500
ch.value_axis.tick_labels.number_format = '#,##0'
ch.value_axis.tick_labels.number_format_is_linked = False
text(s, 7.55, 2.0, 5.18, 0.35, "Average daily biggest 3-hour climb, MW", size=16, bold=True, color=NAVY,
     name="Right chart head")
text(s, L, 6.78, W, 0.2, "Rooftop solar is already netted out of load, so the true climb is larger. "
     "TEP's 2026 climb: 644 MW; SRP's 2025: 1,002 MW.", size=11, color=MUTED, name="Chart note")

# 14 Side by side (table)
s = frame("Recommendation", "Same heat and the same peak hour, but very different growth and evenings")
tab = [("", "TEP", "APS", "SRP"),
       ("Added peak per °F above the breakpoint", *[f"{R[u]['heat']['mw_per_f_above']:.0f} MW" for u in NAMES]),
       ("Average peak hour, July-August 2025", "5-6 PM", "5-6 PM", "5-6 PM"),
       ("Growth since 2024, weather removed", "+1.7%", "+10.8%", "+2.6%"),
       ("Forecast miss, Aug 2023-Jan 2025", *[f"{a[u]['mape_pct']:.1f}%" for u in NAMES]),
       ("Evening 3-hour climb, latest year", "644 MW", "2,104 MW", "1,002 MW"),
       ("Outage minutes per customer, 2025", "41.8", "73.1", "49.9")]
cx = [L, L + 6.0, L + 8.05, L + 10.1]
cwid = [5.8, 2.0, 2.0, 2.0]
for i, row in enumerate(tab):
    y = 2.05 + i * 0.66
    for j, v in enumerate(row):
        head = i == 0
        text(s, cx[j], y, cwid[j], 0.5, v, size=19 if head else 18, bold=head or j > 0,
             color=NAVY if head else (INK if j else INK2), align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT,
             name=f"Table r{i} c{j}", anchor=MSO_ANCHOR.MIDDLE)
    rule(s, L, y + 0.58, L + W, y + 0.58, color=MUTED if i == 0 else RULE, width=1.25 if i == 0 else 0.75)
text(s, L, 6.72, W, 0.25, "Growth: TEP and APS through Nov 2026, SRP through 2025. Outage minutes exclude major "
     "events (EIA-861).", size=12, color=MUTED, name="Table note")

# 15 Recommendation
s = frame("Recommendation", "A daily hot-day check would flag any day-ahead peak more than 2% below what the "
          "temperature slope predicts", source="Method: the fitted heat slope per area (TEP 61 MW per °F above "
          "82°F) applied to the day-ahead temperature forecast.")
steps = [("Morning", "Pull the day-ahead load forecast and tomorrow's forecast high"),
         ("Estimate", "Predict the peak from the fitted temperature slope for that grid"),
         ("Compare", "Day-ahead peak vs the slope estimate, as a percent"),
         ("Flag", "More than 2% low on a 90°F+ day goes to the planner")]
cw = 3.08
for i, (head, body) in enumerate(steps):
    x = L + i * (cw - 0.12 + 0.05)
    shp = s.shapes.add_shape(MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON, Inches(x), Inches(2.2),
                             Inches(cw), Inches(0.8))
    shp.name = f"Check step {i + 1}"
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(STEEL if head == "Flag" else NAVY)
    shp.line.fill.background()
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.text = head
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size = Pt(20)
    p.runs[0].font.bold = True
    p.runs[0].font.name = BODY_FONT
    p.runs[0].font.color.rgb = rgb("FFFFFF")
    text(s, x + 0.15, 3.2, cw - 0.55, 1.3, body, size=17, color=INK2, name=f"Check step {i + 1} detail")
rule(s, L, 4.6, L + W, 4.6)
why = [("Why 2%", "TEP's hot-day peak already averages 1.65-1.78% low, about one degree's worth of load at 2% "
        "per °F."),
       ("Why it pays", "A low forecast means buying power at the hottest, most expensive hour of the day."),
       ("What it needs", "Only the public inputs and the slope this project already fits. Nothing new to collect.")]
for i, (h_, d_) in enumerate(why):
    x = L + i * 4.1
    text(s, x, 4.8, 3.8, 1.9, [[(h_, {"bold": True, "color": NAVY, "size": 18})], [(d_, {"color": INK2})]],
         size=17, space_after=4, name=f"Why {i + 1}")
    if i:
        rule(s, x - 0.2, 4.85, x - 0.2, 6.6)

# 16 Questions
s = frame("Recommendation", "Three open questions are worth answering before using these series for planning",
          source=SRC)
qs = [("The February 2025 divergence", "A steady 450-700 MW overnight gap between APS's forecast and its reported "
       "area load needs an explanation before either series is used for planning."),
      ("Shared peaks", "If all three peak in the same hour on the same days, how much of each grid's peak-hour import "
       "is available when the others need it too?"),
      ("The evening ramp", "The APS area's evening climb is about a quarter of its peak, and TEP's grew 21% in 2026. "
       "Storage at the peak hour: about 1,000 MW in the APS area, 270 MW at TEP, 200 MW at SRP.")]
for i, (h_, d_) in enumerate(qs):
    y = 2.15 + i * 1.5
    text(s, L, y, 0.8, 0.9, str(i + 1), size=36, color=STEEL, font=TITLE_FONT, bold=True, name=f"Q{i + 1} number")
    text(s, L + 0.9, y + 0.05, W - 0.9, 1.3, [[(h_, {"bold": True, "color": NAVY, "size": 19})], [(d_, {})]],
         size=17, space_after=4, name=f"Q{i + 1}")
    if i < len(qs) - 1:
        rule(s, L, y + 1.38, L + W, y + 1.38)

# 17 Close
s = dark_slide("Built entirely from public data", "Rerun it for any week, or point it at your own grid.",
               "Jake Moore  ·  @JakeMooreEdu")

# 18-20 Appendix
s = frame(None, "Appendix A: method and data notes", source=SRC)
items = [
    ("Coverage", "Balancing-area data covers more than each utility's retail customers: own retail sales are 62% of "
     "TEP's 2025 area energy, 88% of APS's and 94.5% of SRP's. Comparisons use each area in its own terms."),
    ("Scoring windows", "TEP from Aug 2023, APS through Jan 2025, SRP through Feb 2026. Common window: Aug 2023 to "
     "Jan 2025."),
    ("Weather", "Central Tucson for TEP; Phoenix Sky Harbor for APS and SRP. APS also serves Yuma and northern "
     "Arizona."),
    ("Uncertainty", "Ranges resample 14-day blocks of days because forecast misses persist; heat-wave ranges "
     "resample events (5-9 per area), so treat those as suggestive."),
    ("Reproduce", "python pull.py && python analysis.py && python deck.py")]
side_notes(s, L, 2.0, W, items, size=17, gap=0.14)

full = [("Customers, 2025", "0.46 million", "1.43 million", "1.19 million"),
        ("Breakpoint where load turns steep", "82°F", "84°F", "80.5°F"),
        ("Added peak per °F above it (MW / % of hot-day peak)", "61 / 2.2%", "139 / 2.0%", "137 / 2.0%"),
        ("Added peak per °F of overnight low, summer", "12 MW", "10 MW", "28 MW"),
        ("Weather-adjusted load, 2024 to latest", "+1.7%", "+10.8%", "+2.6%"),
        ("Weather-adjusted load, 2022 to 2025", "+5.0%", "+16.0%", "+8.8%"),
        ("Retail sales 2022-2025", "+1.4%", "+12.0%", "+10.1%"),
        ("Overnight low as % of peak hour, Jul-Aug 2025", "59.5%", "66.5%", "58.6%"),
        ("Forecast MAPE, Aug 2023-Jan 2025", "3.02%", "3.98%", "2.93%"),
        ("Forecast MAPE, own like-for-like window", "2.87%", "3.82%", "3.16%"),
        ("Midday solar share of load, latest summer", "31%", "42%", "21%"),
        ("Average daily 3-hour net-load ramp, latest year", "644 MW", "2,104 MW", "1,002 MW"),
        ("Battery output in the top 100 load hours", "267 MW", "1,030 MW", "205 MW"),
        ("Outage minutes per customer, no major events, 2025", "41.8", "73.1", "49.9")]
for part, (title, chunk) in enumerate((("Appendix B: full comparison, demand and heat", full[:7]),
                                       ("Appendix C: full comparison, forecasts, solar and reliability", full[7:]))):
    s = frame(None, title, source=SRC)
    for i, row in enumerate([("", "TEP", "APS", "SRP")] + chunk):
        y = 2.0 + i * 0.6
        for j, v in enumerate(row):
            head = i == 0
            text(s, cx[j], y, cwid[j], 0.45, v, size=17, bold=head or j > 0,
                 color=NAVY if head else (INK if j else INK2), align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT,
                 name=f"Table r{i} c{j}", anchor=MSO_ANCHOR.MIDDLE)
        rule(s, L, y + 0.53, L + W, y + 0.53, color=MUTED if i == 0 else RULE, width=1.25 if i == 0 else 0.75)

for i, sl in enumerate(prs.slides, 1):
    sl.notes_slide.notes_text_frame.text = NOTES.get(i, "")
EP.mkdir(parents=True, exist_ok=True)
assert len(NOTES) == len(prs.slides), f"deck_script.md covers {len(NOTES)} of {len(prs.slides)} slides"
prs.save(OUT)
print("wrote", len(prs.slides), "slides to", OUT)
