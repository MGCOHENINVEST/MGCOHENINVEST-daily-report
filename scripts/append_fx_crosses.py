#!/usr/bin/env python3
import json, pathlib, sys, html
RAW = pathlib.Path("/opt/daily-report/out/email/email_body.html")
DATA = pathlib.Path("/opt/daily-report/out/data/fx_cross.json")

def main():
    if not RAW.exists() or not DATA.exists():
        print("[append_fx_crosses] skip (missing body or data)")
        return
    dj = json.loads(DATA.read_text())
    rows = dj.get("cross") or []
    if not rows:
        print("[append_fx_crosses] no rows")
        return
    parts = ['<h2>FX Crosses</h2>',
             "<table border='1' cellpadding='4' cellspacing='0'>",
             "<tr><th>Cross</th><th>Last</th><th>Chg 1D</th></tr>"]
    for r in rows:
        parts.append(f"<tr><td>{html.escape(r['pair'])}</td><td>{r['last']}</td><td>{r['chg1d']}</td></tr>")
    parts.append("</table>")
    body = RAW.read_text()
    body += "\n" + "\n".join(parts) + "\n"
    RAW.write_text(body)
    print("[append_fx_crosses] appended to body")
if __name__ == "__main__":
    main()
