"""Render MEMO.md to tucson_grid_memo.html and print it to tucson_grid_memo.pdf with headless Chrome.

    python build_memo.py      # after combine.py; check_numbers.py should pass first
"""
import os
import subprocess
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CSS = (HERE / "peak" / "build_memos.py").read_text(encoding="utf-8").split('CSS = """')[1].split('"""')[0]
PRINT = "@media print { nav { display:none; } img { max-height:9cm; } h2 { break-after:avoid; } table, img { break-inside:avoid; } }"


def main() -> None:
    body = markdown.markdown((HERE / "MEMO.md").read_text(encoding="utf-8"), extensions=["tables"])
    body = body.replace("<table>", '<div class="table-scroll"><table>').replace("</table>", "</table></div>")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>What summer costs Tucson's grid</title>
<link href="https://fonts.googleapis.com/css2?family=League+Spartan:wght@400;700&family=Libre+Baskerville:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}{PRINT}</style></head>
<body><main class="wrap"><section>{body}</section></main></body></html>
"""
    html = HERE / "tucson_grid_memo.html"
    html.write_text(page, encoding="utf-8")
    chrome = next(p for p in (Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
                              Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
                              Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe")
                  if p.exists())
    pdf = HERE / "tucson_grid_memo.pdf"
    subprocess.run([str(chrome), "--headless=new", "--disable-gpu", f"--user-data-dir={tempfile.gettempdir()}/grid_memo_chrome",
                    "--no-pdf-header-footer", "--virtual-time-budget=15000", f"--print-to-pdf={pdf}", html.as_uri()],
                   check=True, timeout=120)
    print(f"wrote {html.name} and {pdf.name}")


if __name__ == "__main__":
    main()
