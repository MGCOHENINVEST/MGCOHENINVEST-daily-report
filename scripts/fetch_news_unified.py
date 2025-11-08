#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re, html
from pathlib import Path

OUT = Path("/opt/daily-report/out/data/news.json")

def fix_text(s: str | None) -> str:
    if not s:
        return ""
    s = str(s)
    # normalize curly quotes/dashes and common cp1252 goo
    s = (s.replace("\u2018", "'").replace("\u2019", "'")
           .replace("\u201C", '"').replace("\u201D", '"')
           .replace("\u2013", "-").replace("\u2014", "-")
           .replace("\u2026", "..."))
    # nuke common “EUR"” artifacts from bad source encodings
    s = re.sub(r"\bEUR[\"~]\b", "", s)
    s = html.unescape(s)
    return s.strip()

def fetch_headlines() -> list[dict]:
    # Your existing fetch logic lives here; this is a stub to keep file runnable.
    # Replace with your real aggregator and map through fix_text()
    sample = [
        {"title": "Financial markets flail in the face of tariffs", "source": "FT"},
        {"title": "Gold surges past $4,000 an ounce", "source": "Bloomberg"}
    ]
    for row in sample:
        row["title"]  = fix_text(row.get("title"))
        row["source"] = fix_text(row.get("source"))
    return sample

def main():
    data = {"items": fetch_headlines()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()

