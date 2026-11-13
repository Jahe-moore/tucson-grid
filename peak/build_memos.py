"""Render the four peak-demand memos into one page: peak_demand_memos.html.

Run after analysis.py whenever a memo changes:  python build_memos.py
"""
import re
from pathlib import Path

import markdown

HERE = Path(__file__).parent
MEMOS = [("tep", "MEMO.md"), ("arizona", "MEMO_ARIZONA.md"), ("aps", "MEMO_APS.md"), ("srp", "MEMO_SRP.md")]
LINKS = {name: f"#{key}" for key, name in MEMOS}

CSS = """
:root { --navy:#1B2A41; --steel:#5B7FA6; --text:#1F2933; --muted:#5F6B7A; --line:#D4D8DF; --band:#F3F5F8; }
* { box-sizing:border-box; }
body { margin:0; background:#fff; color:var(--text); font:15px/1.6 'Libre Baskerville', Georgia, serif; }
.wrap { max-width:1100px; margin:0 auto; padding:1.5rem 1rem 3rem; }
nav { position:sticky; top:0; z-index:1; background:var(--navy); }
nav .wrap { display:flex; flex-wrap:wrap; gap:.4rem 1.2rem; padding:.7rem 1rem; }
nav a { color:#fff; text-decoration:none; font:700 .8rem 'League Spartan', sans-serif; letter-spacing:.08em; text-transform:uppercase; }
nav a:hover { text-decoration:underline; }
section { padding-top:1rem; border-top:3px solid var(--navy); margin-top:2.5rem; scroll-margin-top:3rem; }
section:first-of-type { border-top:0; margin-top:0; }
h1, h2, h3 { font-family:'League Spartan', sans-serif; color:var(--navy); line-height:1.2; }
h1 { font-size:1.7rem; margin:.4rem 0 .6rem; }
h2 { font-size:1.2rem; margin:1.8rem 0 .5rem; }
table { border-collapse:collapse; width:100%; margin:.6rem 0 1rem; font-size:.85rem; }
th, td { border-bottom:1px solid var(--line); padding:.4rem .55rem; text-align:left; vertical-align:top; }
th { background:var(--band); font:700 .72rem 'League Spartan', sans-serif; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
img { max-width:100%; height:auto; border:1px solid var(--line); margin:.5rem 0; }
code { font-size:.85em; background:var(--band); padding:0 .25rem; }
.table-scroll { overflow-x:auto; }
"""


def render(key: str, name: str) -> str:
    html = markdown.markdown((HERE / name).read_text(encoding="utf-8"), extensions=["tables"])
    for md, anchor in LINKS.items():
        html = html.replace(f'href="{md}"', f'href="{anchor}"')
    html = re.sub(r"<table>", '<div class="table-scroll"><table>', html).replace("</table>", "</table></div>")
    return f'<section id="{key}">{html}</section>'


def explainer() -> None:
    """Illustrative evening-ramp diagram (stylized shapes, not measured data) -> charts/explainer_evening_ramp.png."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    h = np.linspace(0, 24, 241)
    demand = 60 + 28 * np.exp(-((h - 17.5) / 4.2) ** 2) + 6 * np.exp(-((h - 8) / 2.5) ** 2)
    solar = np.where((h > 6.5) & (h < 19.5), 38 * np.sin(np.pi * (h - 6.5) / 13).clip(0) ** 1.4, 0)
    net = demand - solar
    f, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    ax.fill_between(h, net, demand, color="#F2B33D", alpha=0.35, lw=0, label="Supplied by solar")
    ax.plot(h, demand, color="#1B2A41", lw=2.5, label="Total demand")
    ax.plot(h, net, color="#D95926", lw=2.5, label="Remaining demand (net load)")
    ramp = (h >= 14.5) & (h <= 18.5)
    ax.plot(h[ramp], net[ramp], color="#D95926", lw=6, solid_capstyle="round")
    k = np.searchsorted(h, 16.5)
    ax.annotate("Evening ramp: other sources\nmust climb fast as solar fades", xy=(16.6, net[k]), xytext=(18.4, 30),
                color="#D95926", fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color="#D95926", lw=1.2))
    ax.set_xticks([0, 6, 12, 18, 24], ["12 AM", "6 AM", "12 PM", "6 PM", "12 AM"])
    ax.set_yticks([])
    ax.set_ylabel("Electricity demand")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 100)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.set_title("Why the evening matters", loc="left", fontsize=14, fontweight="bold", color="#1B2A41")
    f.text(0.99, 0.01, "Illustrative example, not measured utility data", ha="right", fontsize=8, color="#5F6B7A")
    f.tight_layout()
    f.savefig(HERE / "charts" / "explainer_evening_ramp.png", facecolor="white")
    plt.close(f)


def main() -> None:
    explainer()
    nav = "".join(f'<a href="#{k}">{label}</a>' for k, label in
                  [("tep", "Tucson Electric Power"), ("arizona", "Arizona comparison"), ("aps", "APS"), ("srp", "SRP")])
    body = "".join(render(k, n) for k, n in MEMOS)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Peak demand memos</title>
<link href="https://fonts.googleapis.com/css2?family=League+Spartan:wght@400;700&family=Libre+Baskerville:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><nav><div class="wrap">{nav}</div></nav><main class="wrap">{body}</main></body></html>
"""
    (HERE / "peak_demand_memos.html").write_text(page, encoding="utf-8")
    print("wrote peak_demand_memos.html")


if __name__ == "__main__":
    main()
