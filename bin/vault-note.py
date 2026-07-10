#!/usr/bin/env python3
"""Generate an Obsidian vault note for a Claude chat / Cowork session.

Produces a Markdown summary note whose filename and YAML frontmatter follow the
chat naming protocol (see docs/CHAT_NAMING_PROTOCOL.md). The summary body is
supplied by the caller (a file, stdin, or left as a skeleton to fill in).

Title / filename shape:
  YYYY-MM-DD · AREA [· Sub] · Topic [· vN]        (filename, ↻ date excluded)
  YYYY-MM-DD · AREA [· Sub] · Topic [· vN] [· ↻YYYY-MM-DD]   (title, in frontmatter)

Examples
--------
# Write a note into the vault's Chats folder, summary piped in:
  echo "$SUMMARY" | bin/vault-note.py \
      --area INV --sub Deal --topic "Convolo Group" --entity "Convolo Group" \
      --created 2026-07-01 --last-active 2026-07-10 --version 2 --source cowork \
      --out /path/to/Vault/Chats

# Print to stdout with a skeleton body:
  bin/vault-note.py --area SYS --sub Vault --topic "Vault flatten" --created 2026-07-10
"""
import argparse
import datetime
import os
import re
import sys

SEP = " · "             # space + middle dot + space
LAST_ACTIVE_MARK = "↻"  # ↻


def today():
    return datetime.date.today().isoformat()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def core_title(area, sub, topic, version):
    """AREA [· Sub] · Topic [· vN] — the stable part, without dates."""
    parts = [area]
    if sub:
        parts.append(sub)
    parts.append(topic)
    if version:
        parts.append(f"v{version}")
    return SEP.join(parts)


def full_title(created, area, sub, topic, version, last_active):
    """Display title incl. leading created date and trailing ↻ last-active date."""
    title = f"{created}{SEP}{core_title(area, sub, topic, version)}"
    if last_active and last_active != created:
        title += f"{SEP}{LAST_ACTIVE_MARK}{last_active}"
    return title


def safe_filename(created, area, sub, topic, version):
    """Filename base minus filesystem-hostile chars.

    Keeps the middle-dot separators (valid on macOS/Windows/Obsidian) and the ↻
    date is intentionally excluded so the note updates in place as last_active
    advances. Strips: / \\ : * ? " < > |
    """
    name = f"{created}{SEP}{core_title(area, sub, topic, version)}"
    name = re.sub(r'[\\/:*?"<>|]', "-", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name + ".md"


def read_summary(args):
    if args.summary_file:
        with open(args.summary_file, encoding="utf-8") as fh:
            return fh.read().strip()
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped
    return ""


SKELETON = """## Summary

_One-paragraph overview of what this chat was about._

## Key points

-

## Decisions

-

## Follow-ups

- [ ]

## Links

-
"""


def render(args):
    created = args.created or today()
    last_active = args.last_active or today()
    version = args.version
    title = full_title(created, args.area, args.sub, args.topic, version, last_active)

    tags = ["chat", args.area]
    if args.sub:
        tags.append(slug(args.sub))
    if args.entity:
        tags.append(slug(args.entity))
    if args.source:
        tags.append(args.source)

    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f"created: {created}")
    lines.append(f"last_active: {last_active}")
    lines.append(f"area: {args.area}")
    if args.sub:
        lines.append(f'subarea: "{args.sub}"')
    lines.append(f'topic: "{args.topic}"')
    if args.entity:
        lines.append(f'entity: "{args.entity}"')
    if version:
        lines.append(f"version: {version}")
    if args.source:
        lines.append(f"source: {args.source}")
    lines.append("tags: [" + ", ".join(tags) + "]")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    body = read_summary(args)
    lines.append(body if body else SKELETON)
    lines.append("")
    return created, "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", required=True, help="Area code, e.g. INV, SYS, LTX")
    ap.add_argument("--sub", help="Optional sub-area token, e.g. Deal, Bugfix, Vault")
    ap.add_argument("--topic", required=True, help="Short topic description")
    ap.add_argument("--entity", help="Optional entity this concerns (company, project, person) for cross-area retrieval")
    ap.add_argument("--created", help="Creation date YYYY-MM-DD (default: today)")
    ap.add_argument("--last-active", dest="last_active", help="Most-recent-interaction date YYYY-MM-DD (default: today)")
    ap.add_argument("--version", type=int, help="Version number for iterations of the same topic")
    ap.add_argument("--source", choices=["cowork", "claude.ai"], help="Where the chat happened")
    ap.add_argument("--summary-file", help="File containing the summary body (else stdin, else skeleton)")
    ap.add_argument("--out", help="Directory to write the note into (default: print to stdout)")
    args = ap.parse_args()

    args.area = args.area.upper()
    created, content = render(args)

    if not args.out:
        sys.stdout.write(content)
        return

    os.makedirs(args.out, exist_ok=True)
    fname = safe_filename(created, args.area, args.sub, args.topic, args.version)
    path = os.path.join(args.out, fname)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(path)


if __name__ == "__main__":
    main()
