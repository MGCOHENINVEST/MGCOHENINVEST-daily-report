#!/usr/bin/env python3
import json, time, re
from pathlib import Path

ROOT = Path("/opt/daily-report")
OUT = ROOT / "out" / "email" / "email_body.html"
DATA = ROOT / "out" / "data"

def read_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def html_escape(s):
    return (s.replace("&","&amp;")
             .replace("<","&lt;")
             .replace(">","&gt;"))

def render_fx():
    fx = read_json(DATA / "fx_pairs.json")
    if not fx or not fx.get("pairs"):
        return "<h2>FX Pairs</h2><p><small>No FX data available.</small></p>"
    rows = []
    rows.append("<h2>FX Pairs</h2>")
    rows.append("<table border='1' cellpadding='4' cellspacing='0'>"
                "<tr><th>Pair</th><th>Last</th><th>Chg 1D</th></tr>")
    for r in fx["pairs"]:
        pair = html_escape(str(r.get("pair","")))
        last = r.get("last","")
        chg  = r.get("chg_1d","")
        rows.append(f"<tr><td>{pair}</td><td>{last}</td><td>{chg}</td></tr>")
    rows.append("</table>")
    return "".join(rows)

def render_yields():
    us = read_json(DATA / "yield_US.json")
    uk = read_json(DATA / "yield_UK.json")
    out = ["<h2>Yield Curves</h2>"]
    def tbl(name, block):
        if not block or not isinstance(block.get("today"), dict):
            out.append(f"<p><small>{name} yields unavailable.</small></p>")
            return
        def mkrows(key):
            d = block.get(key) or {}
            return "".join(f"<tr><td>{tenor}</td><td>{d.get(tenor)}</td></tr>" for tenor in d.keys())
        # today / w1 / m1 on separate tables to avoid width issues
        for key in ("today","w1","m1"):
            if block.get(key):
                out.append(f"<br/><table border='1' cellpadding='4' cellspacing='0'>"
                           f"<thead><tr><th>{name} {key}</th><th>Yield</th></tr></thead>"
                           f"<tbody>{mkrows(key)}</tbody></table>")
            else:
                out.append(f"<p><small>{name} {key} unavailable.</small></p>")
    tbl("US", us); tbl("UK", uk)
    return "".join(out)

def render_holdings():
    mkt = read_json(DATA / "market_eodhd.json") or {}
    eq = mkt.get("equities") or []
    if not eq:
        return ""
    # group by suffix: .DE / .LSE / .SW / .US / other
    buckets = {}
    for row in eq:
        sym = str(row.get("symbol","")).strip()
        name = str(row.get("name") or sym)
        m = re.search(r"\.([A-Z]+)$", sym)
        suf = (m.group(1) if m else "OTHER")
        buckets.setdefault(suf, []).append((sym, name))
    order = ["DE","LSE","SW","US","OTHER"]
    html = []
    for key in order:
        rows = buckets.get(key)
        if not rows: 
            continue
        html.append(f"<h3>Holdings {html_escape(key)}</h3>")
        html.append("<table border='1' cellpadding='4' cellspacing='0'><tr><th>Symbol</th><th>Name</th></tr>")
        for sym, name in rows:
            html.append(f"<tr><td>{html_escape(sym)}</td><td>{html_escape(name)}</td></tr>")
        html.append("</table>")
    return "".join(html)

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    parts.append("<h1>Kairos<br/>Daily Report</h1>")
    parts.append("<p><em>Trend is the markets memory; mean reversion is its gravity.</em></p>")
    parts.append(f"<p><small>Generated at {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())} UTC</small></p>")
    parts.append(render_fx())
    parts.append(render_yields())
    parts.append(render_holdings())
    html = "".join(parts)
    with OUT.open("w", encoding="utf-8") as f:
        f.write(html)
    print(f"build_email_body.py: wrote {OUT}")

if __name__ == "__main__":
    main()
