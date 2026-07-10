#!/usr/bin/env python3
"""SessionStart hook: name Cowork / Claude Code sessions per the chat naming protocol.

Emits a title of the form:  YYYY-MM-DD · AREA · Topic
See docs/CHAT_NAMING_PROTOCOL.md.

Reads the SessionStart hook payload from stdin and prints the sessionTitle
JSON to stdout. Never fails the session: any error results in no title change.
"""
import datetime
import json
import os
import re
import subprocess
import sys

SEP = " · "  # space + middle dot + space
DEFAULT_AREA = "SYS"


def project_dir(payload):
    return os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()


def area_code(root):
    env = os.environ.get("CLAUDE_CHAT_AREA", "").strip()
    if env:
        return env.upper()
    try:
        with open(os.path.join(root, ".claude", "chat-area"), encoding="utf-8") as fh:
            val = fh.read().strip()
            if val:
                return val.upper()
    except OSError:
        pass
    return DEFAULT_AREA


def topic(root):
    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=root, stderr=subprocess.DEVNULL
        ).decode().strip()

    try:
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
    except Exception:
        branch = ""

    if not branch or branch in ("HEAD", "main", "master"):
        return os.path.basename(os.path.abspath(root))

    # Strip an owner prefix like "claude/" or "feature/".
    branch = re.sub(r"^[A-Za-z0-9._-]+/", "", branch)
    # Strip a trailing random suffix that contains a digit (e.g. "-m29bcd").
    branch = re.sub(r"-(?=[a-z0-9]*\d)[a-z0-9]{5,8}$", "", branch)
    return branch.replace("-", " ").replace("_", " ").strip()


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # sessionTitle only applies on startup/resume; skip other sources cleanly.
    if payload.get("source") not in (None, "startup", "resume"):
        return

    root = project_dir(payload)
    date = datetime.date.today().isoformat()
    area = area_code(root)
    top = topic(root)

    title = f"{date}{SEP}{area}{SEP}{top}" if top else f"{date}{SEP}{area}"
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "sessionTitle": title,
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never break a session over a naming hook.
        sys.exit(0)
