#!/usr/bin/env python3
import json, csv, sys, os, html

tpl_path = sys.argv[1] if len(sys.argv) > 1 else "daily_report_full.html"
out_path = sys.argv[2] if len(sys.argv) > 2 else "daily_report_rendered.html"

def read_json(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def read_csv_rows(p):
    try:
        with open(p, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

macro        = read_json("macro.json") or {}
news_general = read_json("news_general.json") or {}
news_finance = read_json("news_finance.json") or {}
watchlist    = read_csv_rows("prices.csv")
dividends    = read_csv_rows("dividends.csv")

def find_list(blob):
    # Normalize to a list of items from many possible shapes
    if isinstance(blob, list):
        return blob
    if not isinstance(blob, dict):
        return []
    for path in (
        ("articles",),
        ("items",),
        ("news",),
        ("data","articles"),
        ("payload","items"),
        ("results",),
    ):
        cur = blob
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, list):
            return cur
    return []

def li_news(blob):
    items = find_list(blob)
    lis = []
    for it in items:
        if not isinstance(it, dict): 
            continue
        title = it.get("title") or it.get("headline") or it.get("name") or it.get("summary") or ""
        url   = it.get("url")   or it.get("link")     or it.get("href")    or "#"
        if not title:
            continue
        lis.append(f'<li><a href="{html.escape(str(url))}">{html.escape(str(title))}</a></li>')
    return "<li>No items</li>" if not lis else "".join(lis)

def table_rows(rows, keys, empty_cols=3):
    if not rows:
        return f"<tr><td colspan='{empty_cols}'>No data</td></tr>"
    out=[]
    for r in rows:
        tds = [f"<td>{html.escape(str(r.get(k,'')))}</td>" for k in keys]
        out.append("<tr>"+"".join(tds)+"</tr>")
    return "".join(out)

# Column guesses
wl_keys = ("Ticker","Name","Price")
if watchlist and not all(k in watchlist[0] for k in wl_keys):
    wl_keys = tuple(list(watchlist[0].keys())[:3])

div_keys = ("Ticker","Ex-Date","Pay Date","Amount")
if dividends and not all(k in dividends[0] for k in div_keys):
    div_keys = tuple(list(dividends[0].keys())[:4])

# Map your actual macro keys → template placeholders
UK_CPI = macro.get("UK_CPI") or macro.get("uk_cpi_yoy") or ""
US_CPI = macro.get("US_CPI") or macro.get("us_cpi_yoy") or ""
WTI    = macro.get("WTI")    or macro.get("wti")        or ""

RECO   = macro.get("RECOMMENDATION") or macro.get("recommendation") or macro.get("note") or ""
QUOTE  = macro.get("QUOTE")          or (macro.get("quote") or {}).get("text")   or macro.get("quote_text")  or ""
QATTR  = macro.get("QUOTE_ATTR")     or (macro.get("quote") or {}).get("author") or macro.get("quote_author") or ""

repl = {
    "{{UK_CPI}}":         str(UK_CPI),
    "{{US_CPI}}":         str(US_CPI),
    "{{WTI}}":            str(WTI),
    "{{NEWS_GENERAL}}":   li_news(news_general),
    "{{NEWS_FINANCE}}":   li_news(news_finance),
    "{{WATCHLIST_ROWS}}": table_rows(watchlist, wl_keys),
    "{{DIVIDEND_ROWS}}":  table_rows(dividends, div_keys),
    "{{RECOMMENDATION}}": html.escape(str(RECO)),
    "{{QUOTE}}":          html.escape(str(QUOTE)),
    "{{QUOTE_ATTR}}":     html.escape(str(QATTR)),
}

html_src = open(tpl_path, encoding="utf-8").read()
for k, v in repl.items():
    html_src = html_src.replace(k, v)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html_src)

if "{{" in html_src and "}}" in html_src:
    import re, sys
    missing = sorted(set(re.findall(r"\{\{[^}]+\}\}", html_src)))
    sys.stderr.write("Unfilled placeholders remain: " + ", ".join(missing[:10]) + "\n")
    sys.exit(2)

print(f"Wrote {out_path}")
