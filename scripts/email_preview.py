#!/usr/bin/env python3
import csv, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
csv_path = ROOT / "out/universe/merged.csv"
out_path = ROOT / "out/email/preview.html"
out_path.parent.mkdir(parents=True, exist_ok=True)

# Load merged universe
rows = []
with csv_path.open(newline="", encoding="utf-8") as f:
    rdr = csv.DictReader(f)
    rows = list(rdr)

# Build columns (ticker first, keep whatever exists)
cols = ["ticker"]
for r in rows:
    for k in r.keys():
        if k not in cols:
            cols.append(k)

def esc(x): 
    return html.escape("" if x is None else str(x))

head = (
    "<!doctype html><meta charset='utf-8'>"
    "<style>"
    "table{border-collapse:collapse;width:100%}"
    "th,td{border:1px solid #ddd;padding:6px}"
    "th{background:#f6f6f6;text-align:left}"
    "td.num{text-align:right}"
    "</style><body><h2>Universe Preview</h2>"
)
tb = ["<table><thead><tr>"] + [f"<th>{esc(c)}</th>" for c in cols] + ["</tr></thead><tbody>"]

for r in rows:
    tb.append("<tr>")
    for c in cols:
        v = r.get(c, "")
        cls = " class='num'" if c.lower() in {"last","last_base","weight","change","change_pct"} else ""
        tb.append(f"<td{cls}>{esc(v)}</td>")
    tb.append("</tr>")

tb.append("</tbody></table>")
(Path(out_path)).write_text(head + "".join(tb) + "</body>", encoding="utf-8")
print(out_path)
