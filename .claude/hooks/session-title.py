#!/usr/bin/env python3
"""SessionStart hook: name Cowork / Claude Code sessions per the chat naming protocol.

Emits a title of the form:  YYYY-MM-DD · AREA [· Sub] · Topic [· ↻YYYY-MM-DD]

The leading date is when the session was first created; the trailing "↻" date is
the most recent interaction. The two are equal on the first day (the ↻ suffix is
omitted then) and diverge once the session is resumed on a later day. The optional
"Sub" token is a sub-area (see docs/CHAT_NAMING_PROTOCOL.md) and is included only
when configured.

Reads the SessionStart hook payload from stdin and prints the sessionTitle JSON
to stdout. Never fails the session: any error results in no title change.
"""
import datetime
import json
import os
import re
import subprocess
import sys

SEP = " · "  # space + middle dot + space
LAST_ACTIVE_MARK = "↻"  # precedes the most-recent-interaction date
DEFAULT_AREA = "SYS"


def project_dir(payload):
    return os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()


def _read_config(root, env_name, file_name):
    val = os.environ.get(env_name, "").strip()
    if val:
        return val
    try:
        with open(os.path.join(root, ".claude", file_name), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def area_code(root):
    return (_read_config(root, "CLAUDE_CHAT_AREA", "chat-area") or DEFAULT_AREA).upper()


def sub_code(root):
    # Sub-areas are title-case tokens (e.g. "Deal", "Bugfix"); keep case as given.
    return _read_config(root, "CLAUDE_CHAT_SUB", "chat-sub")


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


def state_dir():
    """User-level state dir so one globally-installed hook works across all repos
    without writing into (or requiring a .gitignore in) each project."""
    override = os.environ.get("CLAUDE_SESSION_TITLE_STATE", "").strip()
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".claude", "session-titles")


def created_date(root, payload, today):
    """Return the session's original creation date, persisting it per session_id.

    On the first run for a session we record today's date; on resume we read it
    back so the leading date stays fixed while the ↻ date advances.
    """
    sid = payload.get("session_id")
    if not sid:
        return today
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(sid))
    sdir = state_dir()
    state_file = os.path.join(sdir, f"{safe}.created")
    if payload.get("source") == "resume":
        try:
            with open(state_file, encoding="utf-8") as fh:
                val = fh.read().strip()
                if val:
                    return val
        except OSError:
            pass
    # startup (or resume with no state): record and use today.
    try:
        os.makedirs(sdir, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as fh:
            fh.write(today)
    except OSError:
        pass
    return today


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # sessionTitle only applies on startup/resume; skip other sources cleanly.
    if payload.get("source") not in (None, "startup", "resume"):
        return

    root = project_dir(payload)
    today = datetime.date.today().isoformat()
    area = area_code(root)
    sub = sub_code(root)
    top = topic(root)
    created = created_date(root, payload, today)

    parts = [created, area]
    if sub:
        parts.append(sub)
    if top:
        parts.append(top)
    title = SEP.join(parts)
    if today != created:
        title += f"{SEP}{LAST_ACTIVE_MARK}{today}"

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
