#!/usr/bin/env python3
import csv, glob, json, os, sys
from html import escape

ROOT = "/opt/daily-report"
MARKET = f"{ROOT}/out/data/market_eodhd.json"
IN_HTML = f"{ROOT}/out/email/email_body.html"
OUT_HTML = f"{ROOT}/out/email/email_body.html"  # append into base; wrap afterwards

def safe_float(x):
    if x is None: return None
    try:
        return float(x)
    except Exception:
        s = str(x).strip().upper()
        if s in ("", "NA", "N/A", "NULL", "NONE", "-", "—"):
            return None
        try:
            return float(s)
        except Exception:
            return None

def fmt_num(x, fmt=",.2f"):
    v = safe_float(x)
    return "" if v is None else format(v, fmt)

def sign_class(x):
    v = safe_float(x)
    if v is None: return ""
    return "pos" if v > 0 else ("neg" if v < 0 else "")

def load_quotes():
    lut = {}
    try:
        j = json.load(open(MARKET, encoding="utf-8"))
        for bucket in ("equities", "indices", "fx"):
            for r in j.get(bucket, []):
                q = r.get("quote") or {}
                code = q.get("code") or r.get("symbol")
                last = q.get("close") if q.get("close") not in ("NA", "N/A") else None
                if code:
                    lut[code] = {
                        "last": last,
                        "change_p": q.get("change_p"),
                    }
    except Exception as e:
        print(f"[WARN] could not read {MARKET}: {e}", file=sys.stderr)
    return lut

def load_map():
    mp = {}
    p = f"{ROOT}/config/eodhd_map.valid.csv"
    if os.path.exists(p):
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sym = (row.get("symbol") or "").strip()
                es  = (row.get("symbol_eodhd") or "").strip()
                if sym and es: mp[sym] = es
    return mp

def load_holdings():
    groups = {}
    for f in glob.glob(f"{ROOT}/config/holdings_*.csv"):
        tag = os.path.basename(f).split("_",1)[1].split(".")[0].upper()
        rows = []
        with open(f, newline="", encoding="utf-8") as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                rows.append({
                    "symbol": (row.get("symbol") or row.get("ticker") or "").strip(),
                    "name": (row.get("name") or "").strip(),
                    "weight": (row.get("weight") or "").strip(),
                })
        groups[tag] = rows
    return groups

def render_table(title, rows):
    html = []
    html.append(f'<div class="section"><div class="section__title">{escape(title)}</div>')
    html.append('<table class="table"><thead><tr>')
    html.append('<th>Symbol</th><th>Name</th><th class="td-right">Price</th><th class="td-right">1D Δ%</th>')
    html.append('</tr></thead><tbody>')
    for r in rows:
        price = fmt_num(r.get("last"))
        chg = fmt_num(r.get("change_p"), ",.2f")
        cls = sign_class(r.get("change_p"))
        html.append(
            f"<tr><td>{escape(r.get('symbol',''))}</td>"
            f"<td>{escape(r.get('name',''))}</td>"
            f'<td class="td-right">{price}</td>'
            f'<td class="td-right {cls}">{chg}</td></tr>'
        )
    html.append('</tbody></table></div>')
    return "\n".join(html)

def main():
    quotes = load_quotes()
    mapping = load_map()
    groups = load_holdings()

    sections = []
    for tag, rows in sorted(groups.items()):
        out_rows = []
        for r in rows:
            sym = r["symbol"]
            code = mapping.get(sym) or sym
            q = quotes.get(code, {})
            out_rows.append({
                "symbol": sym,
                "name": r.get("name") or code,
                "last": q.get("last"),
                "change_p": q.get("change_p"),
            })
        sections.append(render_table(f"Holdings · {tag}", out_rows))

    if not sections:
        print("[INFO] No holdings files found; nothing to append.")
        return

    try:
        html = open(IN_HTML, encoding="utf-8").read()
    except Exception as e:
        print(f"[ERROR] cannot read {IN_HTML}: {e}", file=sys.stderr)
        sys.exit(1)

    block = "\n".join(sections) + "\n"
    needle = "<!-- holdings will be appended here by append_holdings.py -->"
    if needle in html:
        html = html.replace(needle, needle + "\n" + block)
    else:
        html = html.replace("</body>", block + "</body>")

    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Appended holdings sections into {OUT_HTML}")

if __name__ == "__main__":
    main()

