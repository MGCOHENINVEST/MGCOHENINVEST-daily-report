#!/usr/bin/env python3
"""Generate an Obsidian vault note for a Claude chat / Cowork session.

Produces a Markdown summary note whose filename and YAML frontmatter follow the
chat naming protocol (see docs/CHAT_NAMING_PROTOCOL.md). The summary body is
supplied by the caller (a file, stdin, or left as a skeleton to fill in).

Examples
--------
# Write a note into the vault's Chats folder, summary piped in:
  echo "$SUMMARY" | bin/vault-note.py \
      --area INV --topic "Convolo Group" --created 2026-07-01 \
      --last-active 2026-07-10 --version 2 --source cowork \
      --out /path/to/Vault/Chats

# Print to stdout with a skeleton body:
  bin/vault-note.py --area SYS --topic "Vault flatten" --created 2026-07-10
"""
import argparse
import datetime
import os
import re
import sys

SEP = " · "          # space + middle dot + space
LAST_ACTIVE_MARK = "↻"  # ↻


def today():
    return datetime.date.today().isoformat()


def build_title(area, topic, version):
    title = f"{area}{SEP}{topic}"
    if version:
        title += f"{SEP}v{version}"
    return title


def full_title(created, area, topic, version, last_active):
    """Display title incl. leading created date and trailing ↻ last-active date."""
    title = f"{created}{SEP}{build_title(area, topic, version)}"
    if last_active and last_active != created:
        title += f"{SEP}{LAST_ACTIVE_MARK}{last_active}"
    return title


def safe_filename(created, area, topic, version):
    """Filename base: 'YYYY-MM-DD · AREA · Topic [· vN]' minus filesystem-hostile chars.

    Keeps the middle-dot separators (valid on macOS/Windows/Obsidian) but strips
    characters that break sync clients: / \\ : * ? " < > |
    """
    name = f"{created}{SEP}{build_title(area, topic, version)}"
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
    title = full_title(created, args.area, args.topic, version, last_active)
    tags = ["chat", args.area]
    if args.source:
        tags.append(args.source)

    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f"created: {created}")
    lines.append(f"last_active: {last_active}")
    lines.append(f"area: {args.area}")
    lines.append(f'topic: "{args.topic}"')
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
    ap.add_argument("--topic", required=True, help="Short topic description")
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
    fname = safe_filename(created, args.area, args.topic, args.version)
    path = os.path.join(args.out, fname)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(path)


if __name__ == "__main__":
    main()
