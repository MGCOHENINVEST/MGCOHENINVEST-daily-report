#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys
from pathlib import Path
from hashlib import blake2b

SRC = Path("/opt/daily-report/out/email/email_body.html")
DST = SRC  # in-place overwrite

# 1) Load
text = SRC.read_text(encoding="utf-8", errors="ignore")

# 2) Normalize stupid characters (hello CP1252)
# EUR", EUR~, stray smart quotes, etc.
replacements = {
    "EUR\"": "", "EUR~": "", "IEUR": "I", "–": "-", "—": "-",
    "\u00a0": " ", "\r": ""
}
for k,v in replacements.items():
    text = text.replace(k, v)

# 3) Tokenize into blocks by big headings we expect to be unique
# Add anything you never want duplicated.
headings = [
    r"^Kairos\s*Daily Report.*?$",
    r"^Trend is the markets memory; mean reversion is its gravity\.$",
    r"^Generated at .*? UTC$",
    r"^FX Pairs$", r"^FX Cross Rates$", r"^FX Crosses$",
    r"^Yield Curves$", r"^Commodity News$", r"^Commodities$",
    r"^Financial$", r"^Nuclear/Uranium$", r"^AT1\b",
    r"^World & Policy Headlines$", r"^Financial Headlines$",
    r"^Commodity Headlines$",
    r"^Holdings L$", r"^Holdings DE$", r"^Holdings SW$", r"^Holdings TEST$",
]
# Build a splitter that marks headings
splitter = re.compile(r"(?m)^(?:" + "|".join(headings) + r")\s*$")

# Walk through, keep first seen block for each heading, drop repeats.
out_lines = []
seen = set()
h = blake2b

lines = text.split("\n")
i = 0
current_heading = None
buffer = []

def flush():
    if not buffer: 
        return
    block = "\n".join(buffer)
    # Hash block to catch exact duplicates even when heading repeats with same content
    key = str((current_heading, h(block.encode("utf-8")).hexdigest()))
    # If we've already seen an identical block under this heading, drop it
    if key not in seen:
        out_lines.extend(buffer)
        seen.add(key)

# Iterate lines
while i < len(lines):
    line = lines[i]
    if splitter.match(line):
        # flush previous block
        flush()
        buffer = [line]
        current_heading = line.strip()
    else:
        if not buffer:
            buffer = [line]
            current_heading = None
        else:
            buffer.append(line)
    i += 1
flush()

clean = "\n".join(out_lines)

# 4) Secondary de-dupe: collapse exact multi-block repeats (paranoid mode)
# If same 30+ line chunk repeats back-to-back, keep one.
chunks = re.split(r"(\n{2,})", clean)
acc, cache = [], set()
for c in chunks:
    if len(c.splitlines()) >= 30:
        digest = h(c.encode("utf-8")).hexdigest()
        if digest in cache:
            continue
        cache.add(digest)
    acc.append(c)
clean = "".join(acc)

# 5) Tidy excessive blank lines
clean = re.sub(r"\n{3,}", "\n\n", clean).strip() + "\n"

DST.write_text(clean, encoding="utf-8")
print("cleanup_body.py: wrote cleaned body ->", DST)
