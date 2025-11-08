#!/usr/bin/env python3
"""
Fetch Wall Street Journal RSS with a real UA, multiple fallbacks, and graceful errors.
Writes a compact JSON list to /opt/daily-report/out/data/news_wsj.json
"""

import json, sys, time, urllib.request, urllib.error, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

OUT = "/opt/daily-report/out/data/news_wsj.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari Daily-Report/1.0"

# WSJ has several public feeds; some return 403 without a UA.
# Include a few diverse ones to reduce the chance of empty results.
FEEDS = [
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.a.dj.com/rss/RSSBusiness.xml",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "https://feeds.a.dj.com/rss/RSSUSBusiness.xml",
]

def get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml,*/*"})
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
        pub   = item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date")
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
                "source": "WSJ",
            })
    return items

def main():
    all_items = []
    seen = set()

    for url in FEEDS:
        try:
            xml = get(url)
            items = parse_rss(xml)
            for it in items:
                key = (it["title"].strip().lower(), it["url"])
                if key in seen:
                    continue
                seen.add(key)
                all_items.append(it)
        except urllib.error.HTTPError as e:
            print(f"[WARN] WSJ fetch failed: {url}: HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"[WARN] WSJ fetch failed: {url}: {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] WSJ parse error: {url}: {e}", file=sys.stderr)

        time.sleep(0.2)

    # Sort by time, newest first, cap
    def sort_key(x):
        return (x["time"] is not None, x["time"] or "")
    all_items.sort(key=sort_key, reverse=True)
    all_items = all_items[:60]

    try:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(all_items)} WSJ items to {OUT}")
    except PermissionError:
        print(f"[ERROR] Permission denied writing {OUT}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
