"""Build the storm-outage deck on Jake's ESOC 214 flight-delay deck (its ChronicleVTI theme, layouts and shapes).

Run from the project folder:  python deck/build_deck.py
Needs: deck/charts/*.png (Rscript deck/deck_charts.R), deck/numbers.json, deck/img/*.jpg + credits.json,
deck/deck_script.md (speaker notes, one '## Slide N' section per slide).
"""
import copy
import json
import re
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
TEMPLATE = Path.home() / "OneDrive - University of Arizona/2025-2026/2024-2025/Fall_2025/ESOC214/Final_Project/final_project_jakemoore.pptx"
OUT = HERE / "storm_outage_cost_jakemoore.pptx"
N = json.loads((HERE / "numbers.json").read_text())
CREDITS = json.loads((HERE / "img/credits.json").read_text())
CH = HERE / "charts"
IMG = HERE / "img"

PLUM = RGBColor(0x73, 0x4B, 0x67)
PLUM_LT = RGBColor(0xEF, 0xE7, 0xEC)
INK = RGBColor(0x1C, 0x1C, 0x1C)
GREY = RGBColor(0x59, 0x59, 0x59)
NAVY = RGBColor(0x1F, 0x38, 0x64)
SLATE = RGBColor(0x44, 0x54, 0x6A)
RED = RGBColor(0x8B, 0x00, 0x00)
GREEN = RGBColor(0x00, 0x64, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ARROW = RGBColor(0xC9, 0xC2, 0xC6)
COND = "Univers Condensed"
SERIF = "Calisto MT"


def money(x, d=1):
    return f"${x / 1e6:.{d}f}M"


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


# ---------- template ----------
prs = Presentation(str(TEMPLATE))
LAY = {l.name: l for l in prs.slide_layouts}


def grab(slide_no, *names):
    s = prs.slides[slide_no - 1]
    return [copy.deepcopy(sh._element) for n in names for sh in s.shapes if sh.name == n]


TITLE_DECOR = grab(1, "Rectangle 86", "Straight Connector 87", "Rectangle 88", "Straight Connector 89")
TITLE_TOPLINE = grab(1, "Subtitle 2")[1:]          # the second "Subtitle 2" is the top text box
TITLE_PH = grab(1, "Title 1", "Subtitle 2")[:2]
DIV_DECOR = grab(9, "Rectangle 2098", "Straight Connector 2100")
DIV_TITLE = grab(9, "Title 1")
RQ_LINE = grab(2, "Straight Connector 15")

# drop every original slide (their video, audio and pictures go with them)
sldIdLst = prs.slides._sldIdLst
for sldId in list(sldIdLst):
    prs.part.drop_rel(sldId.rId)
    sldIdLst.remove(sldId)

# Mini version: `python deck/build_deck.py --mini` keeps only the slides in MINI_KEEP (full-deck numbers, in order),
# takes notes from mini_script.md (its own 1..n numbering) and writes a separate file. The full deck is untouched.
MINI = "--mini" in __import__("sys").argv
MINI_KEEP = [1, 2, 4, 7, 9, 10, 14, 15, 18, 20, 25, 26, 28, 30, 33, 34]
if MINI:
    OUT = HERE / "storm_outage_cost_jakemoore_10min.pptx"
SCRIPT = (HERE / ("mini_script.md" if MINI else "deck_script.md")).read_text(encoding="utf-8")
NOTES = {}
for m in re.finditer(r"^## Slide (\d+)[^\n]*\n(.*?)(?=^## Slide |\Z)", SCRIPT, re.S | re.M):
    body = m.group(2).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    n = int(m.group(1))
    NOTES[MINI_KEEP[n - 1] if MINI else n] = body


# ---------- helpers ----------
def new_slide(layout):
    s = prs.slides.add_slide(LAY[layout])
    return s


def notes(slide):
    n = len(prs.slides._sldIdLst)
    if n in NOTES:
        slide.notes_slide.notes_text_frame.text = NOTES[n]


def put_back(slide, el):
    slide.shapes._spTree.insert(2, el)


def append(slide, el):
    slide.shapes._spTree.append(copy.deepcopy(el))


def picture_fill(slide, path, x, y, w, h, focus=(0.5, 0.5)):
    """Add a picture cropped to fill the box (like a picture placeholder), centred on focus."""
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    iw, ih = Image.open(path).size
    box, img = w / h, iw / ih
    if img > box:   # too wide: crop sides
        keep = box / img
        left = max(0, min(1 - keep, focus[0] - keep / 2))
        pic.crop_left, pic.crop_right = left, 1 - keep - left
    else:
        keep = img / box
        top = max(0, min(1 - keep, focus[1] - keep / 2))
        pic.crop_top, pic.crop_bottom = top, 1 - keep - top
    return pic


def chart(slide, name, x, y, w=None, h=None):
    path = CH / name
    iw, ih = Image.open(path).size
    if w and not h:
        h = w * ih / iw
    if h and not w:
        w = h * iw / ih
    return slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))


def text(slide, x, y, w, h, runs, size=16, font=COND, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, border=None, fill=None, margin=0.08, line_space=None):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, {bold, color, size, italic})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(margin))
    if border:
        tb.line.color.rgb = border
        tb.line.width = Pt(1)
    if fill:
        tb.fill.solid()
        tb.fill.fore_color.rgb = fill
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line_space:
            p.line_spacing = line_space
        parts = para if isinstance(para, list) else [(para, {})]
        for t, o in parts:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", color)
    return tb


def bullets(slide, x, y, w, h, items, size=17, font=COND, color=INK, gap=6):
    """items: list of str or (str, level) or (list-of-runs, level). Real bullets, like the theme's."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(0.04))
    for i, it in enumerate(items):
        content, lvl = (it, 0) if not isinstance(it, tuple) else it
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        pPr = p._p.get_or_add_pPr()
        indent = 0.26 + 0.3 * lvl
        pPr.set("marL", str(int(Inches(indent))))
        pPr.set("indent", str(int(-Inches(0.24))))
        bu = pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"})
        pPr.append(bu)
        pPr.append(pPr.makeelement(qn("a:buChar"), {"char": "•" if lvl == 0 else "–"}))
        parts = content if isinstance(content, list) else [(content, {})]
        for t, o in parts:
            r = p.add_run()
            r.text = t
            r.font.name = o.get("font", font)
            r.font.size = Pt(o.get("size", size - 2 * lvl))
            r.font.bold = o.get("bold", False)
            r.font.color.rgb = o.get("color", color)
    return tb


def title(slide, t, size=None):
    ph = slide.shapes.title
    ph.text_frame.text = t
    if size:
        for p in ph.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(size)
    return ph


def shape(slide, kind, x, y, w, h, fill=None, line=None, line_w=1.0, text_=None, size=14, color=WHITE, bold=False,
          font=COND, align=PP_ALIGN.CENTER):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_w)
    s.shadow.inherit = False
    if text_ is not None:
        tf = s.text_frame
        tf.word_wrap = True
        for side in ("left", "right", "top", "bottom"):
            setattr(tf, f"margin_{side}", Inches(0.06))
        paras = text_ if isinstance(text_, list) else [text_]
        for i, t in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size if i == 0 else size - 2)
            r.font.bold = bold if i == 0 else False
            r.font.name = font
            r.font.color.rgb = color
    return s


def line(slide, x1, y1, x2, y2, color=INK, width=1.0, arrow=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if arrow:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def table(slide, x, y, w, h, rows, col_w, header_fill=GREY, body_fills=None, size=13, font=SERIF, first_bold=True):
    t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h)).table
    for j, cw in enumerate(col_w):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = str(val)
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = header_fill
            else:
                c.fill.fore_color.rgb = (body_fills[(i - 1) % len(body_fills)] if body_fills else SLATE)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.name = font
                    r.font.color.rgb = WHITE
                    r.font.bold = (i == 0) or (first_bold and j == 0)
    return t


def source(slide, t):
    text(slide, 0.88, 6.36, 11.5, 0.3, t, size=10, font=SERIF, color=GREY, margin=0)


# ---------- slide builders ----------
def title_slide(photo, top_line, title_text, subtitle, focus=(0.5, 0.5)):
    s = new_slide("Title Slide")
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    for el in TITLE_PH:
        append(s, el)
    for el in TITLE_DECOR:
        append(s, el)
    for el in TITLE_TOPLINE:
        append(s, el)
    pic = picture_fill(s, IMG / photo, 0, 0, 13.333, 7.5, focus)
    put_back(s, pic._element)
    shp = {sh.name: sh for sh in s.shapes}
    phs = [sh for sh in s.shapes if sh.is_placeholder]
    phs[0].text_frame.text = title_text
    phs[0].width = Inches(9.6)
    for r in phs[0].text_frame.paragraphs[0].runs:
        r.font.color.rgb = WHITE
    phs[1].text_frame.text = subtitle
    phs[1].width = Inches(10.0)
    for r in phs[1].text_frame.paragraphs[0].runs:
        r.font.color.rgb = WHITE
    top = [sh for sh in s.shapes if not sh.is_placeholder and sh.has_text_frame and sh.name == "Subtitle 2"][0]
    top.text_frame.text = top_line
    for r in top.text_frame.paragraphs[0].runs:
        r.font.color.rgb = WHITE
    notes(s)
    return s


def divider(photo, words, kicker, focus=(0.5, 0.5)):
    s = new_slide("Title Only")
    s.shapes.title._element.getparent().remove(s.shapes.title._element)
    for el in DIV_DECOR:
        append(s, el)
    for el in DIV_TITLE:
        append(s, el)
    pic = picture_fill(s, IMG / photo, 0, 0, 13.333, 7.5, focus)
    put_back(s, pic._element)
    ph = [sh for sh in s.shapes if sh.is_placeholder][0]
    ph.text_frame.text = words
    for p in ph.text_frame.paragraphs:
        for r in p.runs:
            r.font.color.rgb = WHITE
    text(s, 0.88, 1.72, 6.2, 0.45, kicker, size=18, font=SERIF, color=WHITE, margin=0)
    notes(s)
    return s


def content(t, size=None):
    s = new_slide("Title Only")
    title(s, t, size)
    return s


def finish(s):
    notes(s)


# ---------- the deck ----------
cm = N["cm"]
cut = N["cut_table"]
cmp_ = {r["Model"]: r for r in N["comparison"]}
sc = N["scen"]
SN = N["sensitivity"]
M2 = {r["term"]: r for r in N["m2_table"]}
ROLL = {r["Test year"]: r for r in N["rolling"]}
SEL = {r["group"]: r for r in N["selection"]}
LT = RGBColor(0x59, 0x67, 0x81)

# 1 Title
title_slide("c04.jpg", "Jake Moore, Portfolio Project, Data Analysis in R",
            "What Do Monsoon Power Outages Cost Tucson?",
            "A Regression and Classification Approach Using 210,000 Outage Readings", focus=(0.5, 0.35))

# 2 Research question
s = new_slide("Title Only")
s.shapes.title._element.getparent().remove(s.shapes.title._element)
picture_fill(s, IMG / "c12.jpg", 0, 0, 5.1, 7.5, focus=(0.55, 0.5))
for el in RQ_LINE:
    append(s, el)
text(s, 6.15, 1.45, 5.0, 0.75, "RESEARCH QUESTION:", size=36, bold=True, border=INK, align=PP_ALIGN.CENTER,
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 5.6, 2.55, 7.1, 2.35, "What do power outages cost Pima County, what conditions go with a severe storm "
     "night, and can the worst nights be flagged by 3 PM?", size=28, border=INK, anchor=MSO_ANCHOR.MIDDLE, margin=0.14)
text(s, 5.6, 5.25, 7.1, 0.9, [[("Four models: ", {"bold": True}), ("multiple linear regression, linear regression, "
     "logistic regression and a decision tree, all in R.", {})]], size=18, color=GREY)
finish(s)

# 3 Introduction
s = content("Introduction – Why Power Outages?")
bullets(s, 0.88, 2.25, 7.0, 4.2, [
    [("Purpose / Motivation", {"bold": True})],
    ("Estimate what outages cost the homes and businesses of Pima County.", 1),
    ("Find the conditions that go with a severe storm night and with slow restoration.", 1),
    ("Test whether the worst nights can be flagged early enough to act on.", 1),
    [("Why Tucson?", {"bold": True})],
    ("Tucson Electric Power reported 168.7 outage minutes per customer in 2023.", 1),
    ("106.8 of those minutes came from major storm days.", 1),
    ("Hardening the grid costs money, so every budget has to show where it pays.", 1),
], size=19)
picture_fill(s, IMG / "c11.jpg", 8.25, 2.3, 4.2, 3.95, focus=(0.45, 0.5))
text(s, 8.25, 6.27, 4.2, 0.3, "Restoration is a crew on a pole, one circuit at a time", size=11, font=SERIF, color=GREY,
     margin=0, align=PP_ALIGN.RIGHT)
finish(s)

# 4 The data
s = content("The Data – Four Public Sources")
cards = [
    ("OUTAGES", "EAGLE-I, Oak Ridge National Lab", "Customers out in Pima County, every 15 minutes", f"{N['readings']:,} readings"),
    ("WEATHER", "Open-Meteo (ERA5)", "Hourly heat, dew point, gusts and rain, central Tucson", "52,608 hours"),
    ("STORM REPORTS", "NOAA Storm Events", "Thunderstorm wind, hail, lightning, flash floods", "618 reports"),
    ("COST", "Berkeley Lab + EIA", "Survey cost per outage, weighted by TEP's customers and sales", "LBNL-6941E, EIA-861M"),
]
for i, (h, src, what, n) in enumerate(cards):
    x = 0.88 + i * 2.95
    shape(s, MSO_SHAPE.RECTANGLE, x, 2.3, 2.75, 0.62, fill=PLUM, text_=h, size=17, bold=True)
    shape(s, MSO_SHAPE.RECTANGLE, x, 2.92, 2.75, 3.25, fill=WHITE, line=PLUM)
    text(s, x + 0.08, 3.02, 2.6, 0.75, src, size=15, bold=True, color=PLUM)
    text(s, x + 0.08, 3.75, 2.6, 1.5, what, size=16)
    text(s, x + 0.08, 5.45, 2.6, 0.6, n, size=16, bold=True, font=SERIF)
source(s, "2020-2025, all free and public. Joined by date and hour in Arizona time (UTC-7, no daylight saving).")
finish(s)

# 5 How I built it in R
s = content("How I Built It in R")
steps = [("1  PULL", "pull_data.py streams\n7 GB of national files,\nkeeps Pima County"),
         ("2  CLEAN", "tidyverse + lubridate\ntime zones, gaps,\nduplicates"),
         ("3  ENGINEER", "storm nights, events,\nweather by 3 PM"),
         ("4  MODEL", "lm, glm, rpart\nbroom, car, pROC, caret"),
         ("5  REPORT", "R Markdown paper,\nggplot2 charts")]
for i, (h, b) in enumerate(steps):
    x = 0.88 + i * 2.3
    shape(s, MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON, x, 2.3, 2.33, 0.75, fill=PLUM, text_=h, size=16, bold=True)
    text(s, x + 0.1, 3.15, 2.2, 1.0, b, size=15, color=INK)
code = ("# Outage times arrive in UTC; Arizona is UTC-7 all year\n"
        "outages_clean <- outages_raw %>%\n"
        "  mutate(time = with_tz(ymd_hms(run_start_time, tz = \"UTC\"),\n"
        "                        \"America/Phoenix\")) %>%\n"
        "  distinct(time, .keep_all = TRUE)")
text(s, 0.88, 4.35, 7.6, 1.65, code, size=14, font="Consolas", fill=RGBColor(0xF4, 0xF1, 0xF3), margin=0.16,
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 8.8, 4.35, 3.66, 1.65, [[("Every number on these slides ", {}), ("is computed by the code", {"bold": True}),
     (". Re-run the R Markdown file and everything rebuilds.", {})]], size=17, border=INK, margin=0.14,
     anchor=MSO_ANCHOR.MIDDLE)
finish(s)

# 6 Data cleaning
s = content("Data Cleaning")
rm_ = N["removed"]
bullets(s, 0.88, 2.25, 5.3, 4.1, [
    f"Removed {rm_['blank']:,} blank readings and {rm_['outside_2020_2025']} outside 2020-2025",
    "Converted UTC to Arizona time",
    ("Checked against NOAA: on July 14, 2024 outages crossed 1,000 at 5:45 PM, the minute NOAA logged thunderstorm wind", 1),
    "Filled missing intervals with zero (base case)",
    [("Flagged ", {}), (f"{N['uncertain_int']:,} uncertain intervals", {"bold": True}),
     (": a count of 500+ that drops straight to nothing", {})],
    (f"Filling them in instead adds {pct(N['gap_effect'])} to outage time", 1),
], size=18)
stair = ["Removed:\nBlank Readings", "Converted:\nUTC to Arizona", "Kept:\n2020-2025", "Filled:\nGaps = Zero",
         "Flagged:\nUncertain Gaps"]
for i, t_ in enumerate(stair):
    x, y = 6.55 + i * 1.18, 1.0 + i * 1.08
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, 1.6, 0.92, fill=PLUM, text_=t_, size=13)
    if i < len(stair) - 1:
        a = shape(s, MSO_SHAPE.BENT_ARROW, x + 0.3, y + 0.95, 0.85, 0.55, fill=ARROW)
        a.rotation = 90
finish(s)

# 7 Feature engineering
s = content("Feature Engineering – The Storm Night")
hours = ["NOON", "3 PM", "6 PM", "9 PM", "MIDNIGHT", "3 AM", "6 AM"]
x0, x1 = 0.88, 12.45
step = (x1 - x0) / (len(hours) - 1)
shape(s, MSO_SHAPE.RECTANGLE, x0, 2.55, step, 0.6, fill=RGBColor(0xC9, 0xC2, 0xC6), text_="WEATHER BY 3 PM", size=14,
      color=INK, bold=True)
shape(s, MSO_SHAPE.RECTANGLE, x0 + step, 2.55, x1 - x0 - step, 0.6, fill=PLUM, text_="STORM NIGHT: 3 PM TO 6 AM",
      size=16, bold=True)
for i, h in enumerate(hours):
    x = x0 + i * step
    line(s, x, 3.15, x, 3.35, INK, 1.25)
    text(s, x - 0.6, 3.38, 1.2, 0.35, h, size=13, align=PP_ALIGN.CENTER, margin=0)
defs = [("CUSTOMER-MINUTES", "One customer without power for one minute: the area under the outage curve."),
        ("BIG OUTAGE NIGHT", "5,000+ customers out at the same time, about 1.1% of Pima County."),
        ("OUTAGE EVENT", f"A run of 500+ out that peaks at 1,000+. {N['events']} events in six years."),
        ("RESTORATION TIME", "Hours from the peak until the county count falls to 10% of it.")]
for i, (h, b) in enumerate(defs):
    x = 0.88 + (i % 2) * 5.85
    y = 4.05 + (i // 2) * 1.2
    shape(s, MSO_SHAPE.RECTANGLE, x, y, 0.16, 1.0, fill=PLUM)
    text(s, x + 0.28, y - 0.02, 5.3, 1.05, [[(h, {"bold": True, "size": 16})], [(b, {"size": 16})]], size=16, margin=0.02)
source(s, "Storms build in the afternoon and run past midnight, so a calendar day would split one storm in two.")
finish(s)

# 8 Divider
divider("c03.jpg", "Exploring the Data", "Where, when and how big", focus=(0.6, 0.5))

# 9 The scope of the problem
s = content("The Scope of the Problem")
chart(s, "c02_worst_night.png", 0.75, 2.0, w=7.4)
bullets(s, 8.4, 2.25, 4.1, 4.2, [
    [("July 28, 2023", {"bold": True})],
    ("54,076 customers out at once", 1),
    ("About 12% of the county", 1),
    [("Customer-minutes", {"bold": True})],
    ("The red area under the curve", 1),
    (f"{N['top_night_cmin'] / 1e6:.1f} million inside the 3 PM-6 AM window", 1),
    [(f"The 8 worst nights hold {pct(N['top8'])} of all overnight outage time", {"bold": True})],
], size=18)
finish(s)

# 10 Monsoon season
s = content("Monsoon Season Matters")
chart(s, "c01_month.png", 0.75, 2.0, w=7.5)
bullets(s, 8.55, 2.3, 3.95, 4.0, [
    f"July: {pct(N['jul'])} of all recorded outage time",
    f"August: another {pct(N['aug'])}",
    [("June 15 to Sept 30 ", {"bold": True}), (f"is under a third of the year and holds {pct(N['mons_share'])}", {})],
    "The timing points at the storms, but doesn't prove every outage was storm-caused",
], size=18)
finish(s)

# 11 Humidity
s = content("The Humidity Signal")
chart(s, "c03_humidity.png", 0.88, 1.95, h=4.45)
bullets(s, 7.0, 2.3, 5.5, 3.0, [
    [("Median noon dew point:", {"bold": True})],
    (f"Big outage nights: {N['dew_big']:.0f}°F", 1),
    (f"Normal monsoon nights: {N['dew_norm']:.0f}°F", 1),
    "Dew point measures moisture in the air, the fuel for a monsoon thunderstorm",
    "It's measurable at noon, hours before the storm",
], size=18)
text(s, 7.0, 5.35, 5.45, 0.85, "This becomes Model 3: can a 3 PM reading flag the night?", size=17, bold=True,
     border=INK, anchor=MSO_ANCHOR.MIDDLE, margin=0.12)
finish(s)

# 12 Cross-check
s = content("Cross-Check Against TEP's Numbers")
rows = [["Year", "County data", "TEP filing"]] + [[str(r["Year"]), f"{r['EAGLE-I minutes per customer']:.1f}",
         f"{r['TEP reported (all events)']:.1f}"] for r in N["validation"]]
table(s, 0.88, 2.2, 5.2, 3.6, rows, [1.4, 1.9, 1.9], body_fills=[SLATE, LT], size=16)
text(s, 0.88, 5.95, 5.2, 0.35, "Outage minutes per customer, all events", size=12, font=SERIF, color=GREY, margin=0)
bullets(s, 6.6, 2.25, 5.85, 4.1, [
    "Same rise and fall, 2023 the worst in both",
    "County data runs higher in 5 of 6 years, likely because:",
    ("Pima County also includes Trico Electric Co-op", 1),
    ("15-minute snapshots, not each customer", 1),
    ("Utilities may exclude some events from filings", 1),
    "A check on direction, not proof the county data is exact",
], size=18)
finish(s)

# 13 Divider
divider("c05.jpg", "What Does an Outage Cost?", "A modeled estimate, and how sure it is", focus=(0.5, 0.45))

# 14 Pricing an outage
s = content("Pricing an Outage")
rows = [["Cost per outage (2013 $)", "1 hour", "4 hours", "16 hours"],
        ["Home", "$5.10", "$9.50", "$32.40"],
        ["Small business", "$647", "$1,880", "$9,055"],
        ["Medium or large business", "$17,804", "$39,458", "$165,482"]]
table(s, 0.88, 2.15, 6.6, 1.8, rows, [2.7, 1.2, 1.3, 1.4], body_fills=[SLATE, LT], size=15)
text(s, 0.88, 4.0, 6.6, 0.3, "Berkeley Lab, 34 utility surveys from 1989-2012 (LBNL-6941E, Table ES-1)",
     size=11, font=SERIF, color=GREY, margin=0)
flow = [("1  MIX", f"About {N['large_n']:.0f} large accounts, estimated from TEP's sales and LBNL's average sizes"),
        ("2  LENGTH", "Customer-minutes ÷ peak customers (a proxy)"),
        ("3  DOLLARS", f"2013 to 2025 prices: × {N['cpi']:.3f} (CPI)")]
for i, (h, b) in enumerate(flow):
    y = 4.45 + i * 0.66
    shape(s, MSO_SHAPE.PENTAGON, 0.88, y, 1.6, 0.55, fill=PLUM, text_=h, size=14, bold=True)
    text(s, 2.6, y + 0.02, 4.9, 0.52, b, size=15, anchor=MSO_ANCHOR.MIDDLE)
chart(s, "c05_cost_curve.png", 7.75, 2.1, w=4.75)
finish(s)

# 15 The price tag
s = content("The Price Tag – A Modeled Estimate")
text(s, 0.88, 2.1, 4.6, 1.0, money(N["avg_cost"]), size=60, bold=True, color=RED, margin=0)
text(s, 0.88, 3.1, 4.6, 0.5, "a year, all outages, 2020-2025 average", size=17, margin=0)
text(s, 0.88, 3.65, 4.6, 1.75, [[("One-at-a-time sensitivity range: ", {"bold": True}),
     (f"{money(N['sens_lo'], 0)} to {money(N['sens_hi'], 0)}", {"bold": True, "color": RED})],
     [(f"Monsoon season: about {money(N['mons_cost'])} of it. Businesses carry {pct(1 - N['home_share'])}.", {})]],
     size=16, border=INK, margin=0.14)
text(s, 0.88, 5.5, 4.6, 0.9, f"Shows which assumptions matter, not the odds. Stacked, the corners run "
     f"{money(N['combo_low'], 0)} to {money(N['combo_high'], 0)}.", size=13, color=GREY, margin=0)
chart(s, "c15_sensitivity.png", 5.6, 1.95, w=6.9)
finish(s)

# 16 Divider
divider("c02.jpg", "Models 1 & 2: Linear Regression", "Outage severity, and slower restoration", focus=(0.5, 0.5))

# 17 How MLR works
s = content("How Multiple Linear Regression Works")
text(s, 0.88, 2.15, 6.2, 1.05, [[("log(customer-minutes) = ", {"bold": True}),
     ("b0 + b1·gust + b2·rain + b3·dew point + b4·heat + error", {})]], size=17, border=INK, margin=0.14,
     anchor=MSO_ANCHOR.MIDDLE, font=SERIF)
bullets(s, 0.88, 3.45, 6.2, 3.0, [
    [("One line through many inputs at once", {"bold": True})],
    ("Each b is that input's association, holding the others fixed", 1),
    [("Why the log?", {"bold": True})],
    ("Most nights are near zero, a few are in the millions; each b reads as a % change", 1),
    [("Weather only, on purpose", {"bold": True})],
    ("Wind reports are often filed because a line went down, so they'd be circular", 1),
], size=17, gap=4)
chart(s, "c06_mlr_scatter.png", 7.4, 2.05, w=5.1)
finish(s)

# 18 Model 1 results
s = content("Model 1 – What Goes With Outage Severity")
chart(s, "c07_mlr_effects.png", 0.75, 2.0, w=7.4)
bullets(s, 8.45, 2.25, 4.05, 4.2, [
    "Standardized: each input moved by one typical amount (1 standard deviation)",
    "Heat and moisture look broadly comparable to wind and rain; the intervals are wide",
    [(f"R² = {N['m1_r2']:.2f}", {"bold": True}), (" on log customer-minutes: weak", {})],
    ("One weather point is a likely reason, not a proven one", 1),
    ("Associations, not causes", 1),
], size=17)
finish(s)

# 19 Diagnostics
s = content("Checking the Model – Diagnostics")
vif = N["vif"]
rows = [["Input", "VIF"], ["Peak gust", f"{vif['storm_gust']:.2f}"], ["Rain", f"{vif['storm_rain_tenths']:.2f}"],
        ["Noon dew point", f"{vif['noon_dew']:.2f}"], ["Daily high", f"{vif['day_high']:.2f}"]]
table(s, 0.88, 2.2, 3.4, 2.0, rows, [2.3, 1.1], body_fills=[SLATE, LT], size=16)
text(s, 0.88, 4.4, 5.6, 1.9, [[("Key Concept – Multicollinearity", {"bold": True})],
     [("VIF measures how much an input overlaps with the others. Under 5 means each coefficient can be read on "
       "its own. All four here are under 2.", {})]], size=16, border=INK, margin=0.14)
chart(s, "c08_residuals.png", 6.9, 2.0, w=5.6)
text(s, 6.9, 6.2, 5.6, 0.4, "The diagonal edge: nights near zero sit on a floor the line can't go below",
     size=12, font=SERIF, color=GREY, margin=0)
finish(s)

# 20 Model 2
s = content("Model 2 – Slower Restoration")
chart(s, "c09_restore_effects.png", 0.75, 2.0, w=7.3)
bullets(s, 8.35, 2.25, 4.15, 4.3, [
    [("Unit: ", {}), (f"{N['events_m2']} events", {"bold": True}), (" with measured restoration", {})],
    (f"Set aside: {N['events'] - N['events_m2']}, similar size, {SEL['Set aside']['Share of modeled cost']} of cost", 1),
    f"Median: {N['med_restore_hrs']:.1f} hour to reach 10% of the peak",
    [("Night peak: ", {}), (f"+{N['night_pct']:.0f}%", {"bold": True, "color": RED}), (f" ({N['night_ci']}%)", {})],
    (f"Clustered by storm date: {N['night_cl'][0]:.0f}% to {N['night_cl'][1]:.0f}%", 1),
    [("An association: ", {"bold": True}), ("access, damage and staffing are all possible reasons", {})],
], size=17)
finish(s)

# 21 Divider
divider("c08.jpg", "Model 3: Logistic Regression", "Can a big outage night be flagged by 3 PM?", focus=(0.5, 0.5))

# 22 How logistic works
s = content("How Logistic Regression Works")
chart(s, "c10_scurve.png", 0.75, 2.0, w=6.9)
bullets(s, 7.95, 2.2, 4.55, 4.3, [
    [("Predicts a probability", {"bold": True}), (" for yes/no: a big outage night or not", {})],
    [("Log-odds", {"bold": True}), (" are a straight line; the S-curve turns them into 0-100%", {})],
    [("Odds ratio", {"bold": True}), (" = e^b: how an input multiplies the odds", {})],
    [("Fixed in advance:", {"bold": True}), (" moisture and heat, the fuel for a thunderstorm", {})],
    (f"{N['already_out']} days removed: 5,000+ still out at 2:45 PM", 1),
], size=17, gap=5)
finish(s)

# 23 Train-test split by time
s = content("Train-Test Split by Time")
for i, y in enumerate([2020, 2021, 2022, 2023, 2024, 2025]):
    x = 0.88 + i * 1.93
    shape(s, MSO_SHAPE.RECTANGLE, x, 2.35, 1.85, 0.75, fill=(GREY if y <= 2023 else RED), text_=str(y), size=20, bold=True)
text(s, 0.88, 3.18, 7.6, 0.4, f"TRAIN: {N['train_n']} monsoon nights, {N['train_big']} big", size=16, bold=True,
     color=GREY, margin=0)
text(s, 8.6, 3.18, 3.85, 0.4, f"TEST: {N['test_n']} nights, {N['test_big']} big", size=16, bold=True, color=RED, margin=0)
text(s, 0.88, 3.85, 5.6, 2.4, [[("Why not a random 80/20 split?", {"bold": True})],
     [("A random split lets the model learn from July 14, 2024 and get tested on July 15. Splitting by time is how it "
       "would be used: built on the past, judged on the future.", {})]], size=17, border=INK, margin=0.14)
text(s, 6.85, 3.85, 5.6, 2.4, [[("Two inputs, chosen before testing", {"bold": True})],
     [(f"Noon dew point: odds × {N['or_dew']:.2f} per °F", {"bold": True})],
     [(f"Afternoon heat: odds × {N['or_high']:.2f} per °F", {"bold": True})],
     [(f"With only {N['train_big']} big nights, letting an algorithm pick inputs would chase noise. "
       f"All seven inputs scored {N['auc_full']:.2f}, no better.", {})]], size=16, border=INK, margin=0.14)
finish(s)

# 24 Confusion matrix
s = content("Logistic Regression – Confusion Matrix")
cmrows = [["", "Actual normal", "Actual big"], ["Flagged: no", f"True negatives\n{cm['tn']}", f"Missed\n{cm['fn']}"],
          ["Flagged: yes", f"False alarms\n{cm['fp']}", f"Caught\n{cm['tp']}"]]
t = table(s, 0.88, 2.2, 5.6, 2.6, cmrows, [1.6, 2.0, 2.0], header_fill=GREY, body_fills=[GREY], size=16)
for (i, j), col in {(1, 1): NAVY, (2, 2): NAVY, (1, 2): SLATE, (2, 1): SLATE}.items():
    t.cell(i, j).fill.fore_color.rgb = col
for i in range(3):
    t.rows[i].height = Inches(0.6 if i == 0 else 1.0)
    for j in range(3):
        c = t.cell(i, j); c.vertical_anchor = MSO_ANCHOR.MIDDLE
        for p in c.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER if j else PP_ALIGN.LEFT
            for r in p.runs:
                big = bool(i and j and r.text.strip().isdigit())
                r.font.size = Pt(28 if big else 16); r.font.bold = big or r.font.bold
text(s, 0.88, 4.9, 5.6, 0.35, "Test years 2024-2025, operating cutoff", size=12, font=SERIF, color=GREY, margin=0)
res = [["Metric", "Value", "Meaning"],
       ["Sensitivity", pct(N["sens"]), f"Caught {cm['tp']} of {cm['tp'] + cm['fn']} big nights"],
       ["Specificity", pct(N["spec"]), f"Left {cm['tn']} of {cm['tn'] + cm['fp']} quiet nights alone"],
       ["Precision", pct(N["prec"]), f"{cm['tp']} of {cm['tp'] + cm['fp']} flags were real"],
       ["Balanced accuracy", pct(N["bal"]), "Average of sensitivity and specificity"]]
table(s, 6.85, 2.2, 5.6, 2.3, res, [1.75, 0.85, 3.0], header_fill=GREY, body_fills=[SLATE, LT], size=14)
text(s, 6.85, 4.7, 5.6, 1.65, [[("Key Concept – Why not accuracy?", {"bold": True})],
     [(f"Only {pct(N['test_big'] / N['test_n'])} of nights were big. Always saying no is "
       f"{pct(1 - N['test_big'] / N['test_n'])} accurate and catches nothing.", {})]], size=16, border=INK, margin=0.12)
finish(s)

# 25 ROC and cutoff
s = content("Model 3 – Flagging a Big Night by 3 PM" if MINI else "ROC Curve and Choosing the Cutoff")
chart(s, "c11_roc.png", 0.75, 1.95, h=4.55)
crows = [["Cutoff", "Flagged", "Caught", "False alarms", "Precision"]] + [
    [r["Cutoff"].replace("Operating budget (top 20%)", "Top 20%").replace("Balanced (Youden)", "Balanced"),
     str(r["Test nights flagged"]), f"{r['Big nights caught']} of {N['test_big']}", str(r["False alarms"]), r["Precision"]]
    for r in cut]
table(s, 6.4, 2.2, 6.05, 1.35, crows, [1.3, 1.05, 1.1, 1.45, 1.15], body_fills=[SLATE, LT], size=14)
bullets(s, 6.4, 3.8, 6.05, 2.7, [
    [("Test AUC ", {}), (f"{N['auc_test']:.2f}", {"bold": True}), (f" vs. {N['auc_cal']:.2f} for the date alone", {})],
    (f"95% interval {N['auc_lo']:.2f}-{N['auc_hi']:.2f}, from only {N['test_big']} big nights", 1),
    [("Top 20% cutoff: ", {"bold": True}), (f"one evening in five, but {pct(1 - N['prec'])} of flags are false alarms", {})],
], size=17, gap=5)
finish(s)

# 26 Does it hold up (new)
s = content("Does the Flag Hold Up?")
chart(s, "c16_rolling.png", 0.75, 1.9, w=5.6)
chart(s, "c17_precision.png", 6.85, 1.9, w=5.6)
text(s, 0.88, 6.05, 11.6, 0.6, f"2022: {ROLL[2022]['AUC']:.2f}, no better than chance. 2023: {ROLL[2023]['AUC']:.2f}. 2024: {ROLL[2024]['AUC']:.2f}. "
          f"2025 had no big nights. The {N['auc_test']:.2f} is a best case: promising, but unstable.", size=14, bold=True, margin=0)
finish(s)

# 27 Divider
divider("c04.jpg", "Model 4: Decision Tree", "An interpretable alternative", focus=(0.5, 0.5))

# 28 Tree
s = content("Model 4 – A Decision Tree Rule Card" if MINI else "How a Decision Tree Works – The Rule Card")
chart(s, "c14_tree.png", 0.75, 1.95, w=7.0)
bullets(s, 8.0, 2.2, 4.5, 2.4, [
    [("Yes/no questions", {"bold": True}), (", each split making the groups purer (Gini)", {})],
    [("Pruned", {"bold": True}), (" by cross-validation, one whole season held out at a time", {})],
    [("Equal priors", {"bold": True}), (", so leaf percentages are weighted, not real odds", {})],
], size=16, gap=4)
text(s, 8.0, 4.75, 4.5, 1.65, [[("The rule card", {"bold": True})],
     [(f"Noon dew point {N['rule_dew']}°F+ and before {N['rule_date']}", {})],
     [("Flags ", {}), (pct(N["tree_flag"]), {"bold": True}), (f" of test nights vs. {pct(N['flag_share'])} for logistic. "
       f"Test AUC {cmp_['Rule-card tree (Model 4)']['Test AUC']:.2f} vs. {N['auc_test']:.2f}", {})]],
     size=16, border=INK, margin=0.12)
finish(s)

# 29 Overfitting
s = content("Overfitting – Memorizing Is Not Learning")
chart(s, "c12_overfit.png", 0.75, 2.0, w=7.4)
ut = cmp_["Unrestricted tree, no pruning"]
bullets(s, 8.45, 2.25, 4.05, 4.2, [
    [("Unpruned tree: ", {"bold": True}), (f"{N['free_leaves']} leaves on {N['train_big']} big training nights", {})],
    (f"Train AUC {ut['Train AUC']:.2f}, test {ut['Test AUC']:.2f}: it memorized 2020-2023", 1),
    [("Pruning by season: ", {"bold": True}), (f"{N['season_leaves']} leaves, the rule card", {})],
    [("Logistic ranks the nights; the tree trades accuracy for rules anyone can repeat", {"bold": True})],
], size=17)
finish(s)

# 30 Recommendations
s = content("Recommendations")
chart(s, "c13_scenarios.png", 0.75, 2.0, w=7.0)
bullets(s, 8.05, 2.2, 4.45, 4.3, [
    [("Look at prevention first", {"bold": True, "color": GREEN})],
    (f"10% fewer interrupted: {money(sc[0])} a year vs. {money(sc[1])} for 10% faster repairs", 1),
    [("Investigate the night difference", {"bold": True, "color": RED})],
    (f"Half of it is worth {money(sc[3])} a year, if it's fixable; priced on the {N['night_len']:.0f}% longer average outage", 1),
    [("Treat the 3 PM flag as promising, not proven", {"bold": True})],
    ("Promising, but not reliable enough yet to schedule crews around", 1),
], size=16, gap=4)
finish(s)

# 31 Limitations
s = content("Limitations")
bullets(s, 0.88, 2.2, 11.6, 4.3, [
    [("County, not utility: ", {"bold": True}), ("Pima County includes Trico Electric Co-op's customers.", {})],
    [("Missing readings: ", {"bold": True}), (f"a gap can be zero or a reporting outage; filling them adds {pct(N['gap_effect'])}.", {})],
    [("One weather point: ", {"bold": True}), (f"a likely reason Model 1's R² is only {N['m1_r2']:.2f}, though not the only one.", {})],
    [("Few big nights: ", {"bold": True}), (f"{N['train_big'] + N['test_big']} in six seasons, none in 2025.", {})],
    [("Associations, not causes: ", {"bold": True}), ("including the night restoration difference.", {})],
    [("Cost rests on assumptions: ", {"bold": True}), ("the business mix most of all; survey costs from 1989-2012.", {})],
    [("Reanalysis, not forecasts: ", {"bold": True}), ("ERA5 is rebuilt after the fact, so the 3 PM flag is a feasibility test.", {})],
], size=18, gap=6)
finish(s)

# 32 Future work
s = content("Future Work and Implications")
bullets(s, 0.88, 2.2, 7.0, 4.3, [
    [("Better cost inputs", {"bold": True})],
    ("Berkeley Lab's ICE Calculator 2.2 (Feb 2026) and TEP's real business mix", 1),
    [("Add forecasts", {"bold": True})],
    ("Archived HRRR forecasts (from 2018) and GFS (from March 2021) include storm energy", 1),
    [("Go below the county", {"bold": True})],
    ("Circuit and crew data would test the night difference directly", 1),
    [("What it gives a utility now", {"bold": True})],
    ("A mid-afternoon risk signal and a way to compare prevention with speed", 1),
], size=18, gap=3)
picture_fill(s, IMG / "c10.jpg", 8.25, 2.3, 4.2, 3.95, focus=(0.5, 0.5))
finish(s)

# 33 Conclusion
s = content("Conclusion")
bullets(s, 0.88, 2.2, 11.6, 1.8, [
    f"Outages cost Pima County an estimated {money(N['avg_cost'])} a year, about {money(N['mons_cost'])} of it in monsoon season. The business mix moves it most.",
    f"Heat, moisture, wind and rain go with severe nights; night outages restore about {N['night_pct']:.0f}% slower.",
    "A hot, humid afternoon is a promising but unstable signal, not yet reliable enough to act on alone.",
], size=18, gap=4)
text(s, 0.88, 4.25, 11.6, 2.1, [[("What I learned", {"bold": True})],
     [("The hardest part wasn't picking a model. It was deciding what a missing reading means, how to measure "
       "restoration from county totals, how many large businesses TEP serves, and whether two measures of outage length "
       "can stand in for each other. Those choices moved the results "
       "more than any algorithm did.", {})]], size=18, border=PLUM, margin=0.16)
finish(s)

# 34 References
s = content("References")
bullets(s, 0.88, 2.15, 6.7, 4.4, [
    "Brelsford et al. (2024). Recorded electricity outages by U.S. county 2014-2022. Scientific Data 11, 271.",
    "ORNL. EAGLE-I yearly outage files 2020-2025, figshare 24237376.",
    "NOAA NCEI. Storm Events Database, 2020-2025.",
    "Open-Meteo. Historical Weather (ERA5), Historical Forecast and Previous Runs APIs.",
    "U.S. EIA. Forms EIA-861M and EIA-861, Tucson Electric Power.",
    "Sullivan, Schellenberg & Blundell (2015). LBNL-6941E, Tables ES-1 and ES-2.",
    "Berkeley Lab & Resource Innovations (2026). ICE Calculator 2.0 Final Report (version 2.2). OSTI 3021993.",
    "U.S. BLS. CPI-U, series CUUR0000SA0.",
    "UCLA Statistical Consulting Group. Logit Regression. Google ML Crash Course: ROC and AUC.",
], size=13, font=SERIF, gap=4)
used = ["c04.jpg", "c12.jpg", "c11.jpg", "c03.jpg", "c05.jpg", "c02.jpg", "c08.jpg", "c10.jpg"]
seen = []
for f in used:
    c = f"{CREDITS[f]['author'].split(chr(10))[0][:34]}, {CREDITS[f]['license']}"
    if c not in seen:
        seen.append(c)
text(s, 7.95, 2.15, 4.5, 2.3, [[("Photos (Wikimedia Commons)", {"bold": True, "size": 14})]] +
     [[(c, {})] for c in seen] + [[("Tucson monsoon photos by A Guy Named Nyal", {"italic": True})]],
     size=12, font=SERIF, border=INK, margin=0.12)
finish(s)

if MINI:
    for i, sldId in reversed(list(enumerate(list(sldIdLst), start=1))):
        if i not in MINI_KEEP:
            prs.part.drop_rel(sldId.rId)
            sldIdLst.remove(sldId)
prs.save(str(OUT))
print(f"wrote {OUT} with {len(prs.slides._sldIdLst)} slides; notes on {sum(1 for sl in prs.slides if sl.has_notes_slide and sl.notes_slide.notes_text_frame.text.strip())}")
