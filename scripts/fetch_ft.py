#!/usr/bin/env python3
"""
Fetch FT RSS with a real UA, multiple fallbacks, and graceful errors.
Writes a compact JSON list to /opt/daily-report/out/data/news_ft.json
"""

import json, sys, time, urllib.request, urllib.error, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

OUT = "/opt/daily-report/out/data/news_ft.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari Daily-Report/1.0"

# A mix of general + markets + companies feeds.
# Some FT paths 404 intermittently; we keep several and log warnings as needed.
FEEDS = [
    "https://www.ft.com/rss/home/uk",              # UK homepage
    "https://www.ft.com/companies?format=rss",     # Companies (alt format param)
    "https://www.ft.com/world?format=rss",         # World
    "https://www.ft.com/markets?format=rss",       # Markets (404 sometimes; harmless)
    "https://www.ft.com/technology?format=rss",    # Tech
    "https://www.ft.com/opinion?format=rss",       # Opinion
]

def get(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

def parse_rss(xml_bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    items = []
    for item in root.findall(".//channel/item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        pub   = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
        )
        cat   = item.findtext("category") or ""
        ts = None
        if pub:
            try:
                ts = parsedate_to_datetime(pub).isoformat()
            except Exception:
                ts = None
        if title and link:
            items.append({
                "title": title,
                "url": link,
                "time": ts,
                "topic": (cat or ""),
                "source": "FT",
            })
    return items

def main():
    all_items, seen = [], set()

    for url in FEEDS:
        try:
            xml = get(url)
            for it in parse_rss(xml):
                key = (it["title"].strip().lower(), it["url"])
                if key in seen:
                    continue
                seen.add(key)
                all_items.append(it)
        except urllib.error.HTTPError as e:
            print(f"[WARN] FT fetch failed: {url}: HTTP {e.code}: {e.reason}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"[WARN] FT fetch failed: {url}: {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] FT parse error: {url}: {e}", file=sys.stderr)
        time.sleep(0.2)

    # Newest first, cap to a sensible size
    def sort_key(x):
        return (x["time"] is not None, x["time"] or "")
    all_items.sort(key=sort_key, reverse=True)
    all_items = all_items[:80]

    try:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(all_items)} FT items to {OUT}")
    except PermissionError:
        print(f"[ERROR] Permission denied writing {OUT}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
