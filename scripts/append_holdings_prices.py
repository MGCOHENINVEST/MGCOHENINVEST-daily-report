#!/usr/bin/env python3
import csv, json, glob, os, sys
from datetime import datetime, timezone

ROOT = "/opt/daily-report"
HTML = f"{ROOT}/out/email/email_body.html"
J    = f"{ROOT}/out/data/market_eodhd.json"

def load_quotes_nested(path):
    lut={}
    try:
        j=json.load(open(path, encoding="utf-8"))
        for bucket in ("equities","indices","fx"):
            for r in j.get(bucket,[]) or []:
                q=r.get("quote") or {}
                code = (q.get("code") or r.get("ticker") or r.get("symbol") or "").strip()
                last = q.get("close"); chp = q.get("change_p")
                if code: lut[code] = {"last": last, "change_p": chp}
    except Exception as e:
        print(f"[WARN] could not read {path}: {e}", file=sys.stderr)
    return lut

def load_holdings(root):
    rows=[]
    for f in sorted(glob.glob(os.path.join(root,"config/holdings_*.csv"))):
        tag = os.path.splitext(os.path.basename(f))[0].split("_",1)[-1]
        try:
            with open(f, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    sym=(r.get("symbol") or r.get("ticker") or "").strip()
                    name=(r.get("name") or "").strip()
                    if sym:
                        rows.append({"tag":tag,"symbol":sym,"name":name})
        except Exception as e:
            print(f"[WARN] read {f}: {e}", file=sys.stderr)
    return rows

def make_table(holdings, quotes):
    if not holdings: 
        return "<!-- no holdings_* files -->"
    # Group by tag (e.g., L / DE / SW)
    groups={}
    for h in holdings:
        groups.setdefault(h["tag"], []).append(h)
    parts=[]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts.append('<div class="section"><div class="section__title">Holdings (live)</div>')
    parts.append(f'<p class="meta">Quotes via EODHD – {ts}</p>')
    for tag, items in groups.items():
        parts.append(f'<h4 style="margin:.5rem 0">{tag}</h4>')
        parts.append('<table class="table"><thead><tr>'
                     '<th>Symbol</th><th>Name</th>'
                     '<th class="td-right">Last</th><th class="td-right">1D&nbsp;Δ%</th>'
                     '</tr></thead><tbody>')
        for it in items[:50]:  # cap to keep email small
            q = quotes.get(it["symbol"]) or {}
            last = q.get("last"); chp = q.get("change_p")
            last_s = f"{last:.2f}" if isinstance(last,(int,float)) else "—"
            chp_s  = (f'{chp:+.2f}%' if isinstance(chp,(int,float)) else "—")
            parts.append(f'<tr><td>{it["symbol"]}</td>'
                         f'<td>{(it["name"] or "")}</td>'
                         f'<td class="td-right">{last_s}</td>'
                         f'<td class="td-right">{chp_s}</td></tr>')
        parts.append('</tbody></table>')
    parts.append('</div>')
    return "\n".join(parts)

def main():
    quotes = load_quotes_nested(J)
    holds  = load_holdings(ROOT)
    block  = make_table(holds, quotes)
    if not os.path.exists(HTML):
        print(f"[ERROR] missing {HTML}", file=sys.stderr); sys.exit(1)
    html = open(HTML,encoding="utf-8").read()
    # Insert before </body>
    if "</body>" in html:
        html = html.replace("</body>", block + "\n</body>")
    else:
        html += "\n" + block + "\n"
    open(HTML,"w",encoding="utf-8").write(html)
    print("[INFO] appended holdings section")

if __name__ == "__main__":
    main()
