"""Check that every number in a document traces to results.json.

    python check_numbers.py                      # MEMO.md
    python check_numbers.py deck/grid_script.md deck/tucson_grid.pptx   # any .md or .pptx (slide text, not notes)

Each number in the prose and tables (image paths and code removed) must match a headline value in results.json, read
directly, as a percent (x100) or in millions (/1e6), at the precision the document prints. Hourly and monthly arrays
(by_hour, by_month, profiles, bootstrap draws) are excluded, so a wrong number can't pass by matching some
unrelated hour. Numbers that are definitions, not results (calendar years, temperature bands, the 10% scenario size,
the 5,000-customer threshold, window lengths) are listed in FIXED. Anything left over is printed, and the exit code
is 1.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
SKIP_KEYS = {"by_hour", "by_month", "jul_aug_by_hour", "jul_aug_profile_year", "hourly", "daily", "rolling_by_day"}
# Definitions, labels and source names, not findings.
FIXED = {*range(1989, 2027), 80, 82, 90, 100, 105, 110, 10, 5000, 3, 4, 15, 0, 1, 0.5, 9, 12, 30, 6, 5, 7, 2,
         930, 861, 8, 11, 20, 2000, 1000, 95,
         34}  # 34: the number of utility surveys Berkeley Lab pooled (a citation, not a result)


def flat(x, path=""):
    """Yield (path, value) for every headline number."""
    if path.rsplit("/", 1)[-1] in SKIP_KEYS:
        return
    if isinstance(x, dict):
        for k, v in x.items():
            yield from flat(v, f"{path}/{k}")
    elif isinstance(x, list):
        if len(x) > 40:          # long arrays are series, not headline values
            return
        for v in x:
            yield from flat(v, path)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield path, float(x)
    elif isinstance(x, str):
        for m in re.findall(r"-?\d+(?:\.\d+)?", x):
            yield path, float(m)


SOURCES = {"TEP": R["peak"]["TEP"], "APS growth": R["peak"]["APS"]["growth"], "SRP growth": R["peak"]["SRP"]["growth"],
           "arizona": R["peak"]["arizona"], "outages": R["outages"], "act4": R["act4"]}
VALUES = [(p, v) for s in SOURCES.values() for p, v in flat(s) if v == v and abs(v) != float("inf")]


def matches(n: float, decimals: int, unit: str, approx: bool = False) -> bool:
    """unit: '%' (a percent: the value itself or a share x100), '$M' (dollars in millions), '$' (plain dollars),
    'MW' (only fields whose name says mw), or '' (anything else: the value itself)."""
    if n in FIXED:
        return True
    for p, v in VALUES:
        if unit == "MW" and "mw" not in p.lower():   # megawatt figures come from megawatt fields
            continue
        scaled = {"%": (v, v * 100, -v, -v * 100), "$M": (v / 1e6,), "$": (v, v / 1e6), "M": (v / 1e6,)}.get(unit, (v, -v))
        if any(round(x, decimals) == n or (approx and n and abs(x - n) / n <= 0.02) for x in scaled):
            return True
    return False


def read(path: Path) -> str:
    if path.suffix.lower() != ".pptx":
        return path.read_text(encoding="utf-8")
    from pptx import Presentation
    out = []
    for i, s in enumerate(Presentation(str(path)).slides, 1):
        out.append(f"== slide {i}")
        for sh in s.shapes:
            if sh.has_text_frame:
                out.append(sh.text_frame.text)
            if sh.has_table:
                out += [" | ".join(c.text for c in r.cells) for r in sh.table.rows]
    return "\n".join(out)


def check(path: Path) -> list:
    text = read(path)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # images
    text = re.sub(r"`[^`]*`", "", text)                       # code and file names
    text = re.sub(r"\]\([^)]*\)", "]", text)                  # markdown link targets (URLs)
    text = re.sub(r"NREL/TP-\S+|LBNL-\S+|\(\d:\d\d\)", "", text)   # report numbers, talk-track timings
    text = re.sub(r"(?m)^(## Slide|== slide) \d+", "", text)          # slide headers and markers
    text = re.sub(r"figshare \d+|Scientific Data \d+, \d+", "", text)   # citation identifiers
    bad = []
    for m in re.finditer(r"(?<![\w.:])-?(\$?)(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?=M\b|[^\w:]|$)", text):
        raw = m.group(2).replace(",", "")
        n = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        after = text[m.end():m.end() + 10]
        unit = ("%" if after.startswith("%") else
                "$M" if m.group(1) and re.match(r"\s*(million|M\b)", after) else
                "MW" if re.match(r"\s*(MW\b|megawatts?)", after) else
                "M" if re.match(r"\s*million", after) else
                "$" if m.group(1) else "")
        approx = bool(re.search(r"(about|almost|roughly|nearly)\s+$", text[max(0, m.start() - 12):m.start()]))
        if not matches(n, decimals, unit, approx):
            bad.append((text[:m.start()].count("\n") + 1, m.group(0)))
    return bad


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or [HERE / "MEMO.md"]
    total = 0
    for f in files:
        bad = check(f)
        total += len(bad)
        for line, tok in bad:
            print(f"{f.name} line {line}: {tok} not found in results.json")
        print(f"{f.name}: {'OK' if not bad else 'REVIEW'}, {len(bad)} unmatched")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
