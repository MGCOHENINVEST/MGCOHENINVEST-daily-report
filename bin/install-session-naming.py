#!/usr/bin/env python3
"""Install the session-title hook globally so EVERY repo names Cowork/Claude Code
sessions per the chat naming protocol (see docs/CHAT_NAMING_PROTOCOL.md).

It copies .claude/hooks/session-title.py to ~/.claude/hooks/ and merges a
SessionStart hook entry into ~/.claude/settings.json. Idempotent and safe:
existing settings are backed up and the hook entry is de-duplicated.

Per-repo behaviour is unchanged: the global hook still reads each project's
.claude/chat-area / .claude/chat-sub (or the CLAUDE_CHAT_AREA / CLAUDE_CHAT_SUB
env vars), falling back to area "SYS" when a repo sets nothing.

Usage:
  bin/install-session-naming.py            # install
  bin/install-session-naming.py --print    # show what it would do, change nothing
  bin/install-session-naming.py --uninstall
"""
import argparse
import datetime
import json
import os
import shutil
import sys

HOOK_NAME = "session-title.py"
GLOBAL_CMD = 'python3 "$HOME/.claude/hooks/session-title.py"'
MATCHER = "startup|resume"


def paths():
    here = os.path.dirname(os.path.abspath(__file__))
    src_hook = os.path.join(here, os.pardir, ".claude", "hooks", HOOK_NAME)
    claude = os.path.join(os.path.expanduser("~"), ".claude")
    return {
        "src_hook": os.path.normpath(src_hook),
        "dest_hook": os.path.join(claude, "hooks", HOOK_NAME),
        "settings": os.path.join(claude, "settings.json"),
    }


def load_settings(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def our_entry(session_start):
    for entry in session_start:
        for h in entry.get("hooks", []):
            if h.get("command") == GLOBAL_CMD:
                return entry
    return None


def add_hook(settings):
    hooks = settings.setdefault("hooks", {})
    session_start = hooks.setdefault("SessionStart", [])
    if our_entry(session_start):
        return False  # already present
    session_start.append(
        {
            "matcher": MATCHER,
            "hooks": [{"type": "command", "command": GLOBAL_CMD}],
        }
    )
    return True


def remove_hook(settings):
    session_start = settings.get("hooks", {}).get("SessionStart", [])
    kept = [
        e
        for e in session_start
        if not any(h.get("command") == GLOBAL_CMD for h in e.get("hooks", []))
    ]
    changed = len(kept) != len(session_start)
    if changed:
        settings["hooks"]["SessionStart"] = kept
    return changed


def backup(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = f"{path}.bak-{stamp}"
    shutil.copy2(path, dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", dest="dry", action="store_true", help="show planned actions, change nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove the global hook entry (leaves the copied script)")
    args = ap.parse_args()

    p = paths()

    if args.uninstall:
        settings = load_settings(p["settings"])
        if remove_hook(settings):
            if args.dry:
                print(f"[dry-run] would remove SessionStart entry from {p['settings']}")
            else:
                backup(p["settings"])
                with open(p["settings"], "w", encoding="utf-8") as fh:
                    json.dump(settings, fh, indent=2)
                    fh.write("\n")
                print(f"Removed hook entry from {p['settings']}")
        else:
            print("Nothing to remove.")
        return

    if not os.path.exists(p["src_hook"]):
        sys.exit(f"Cannot find source hook at {p['src_hook']}")

    settings = load_settings(p["settings"])
    would_add = our_entry(settings.get("hooks", {}).get("SessionStart", [])) is None

    if args.dry:
        print("[dry-run] planned actions:")
        print(f"  copy {p['src_hook']}")
        print(f"    -> {p['dest_hook']}")
        if os.path.exists(p["settings"]):
            print(f"  back up {p['settings']}")
        print(f"  {'add' if would_add else 'keep (already present)'} SessionStart hook: {GLOBAL_CMD}")
        return

    # Copy the hook.
    os.makedirs(os.path.dirname(p["dest_hook"]), exist_ok=True)
    shutil.copy2(p["src_hook"], p["dest_hook"])
    os.chmod(p["dest_hook"], 0o755)
    print(f"Installed hook -> {p['dest_hook']}")

    # Merge settings.
    if os.path.exists(p["settings"]):
        b = backup(p["settings"])
        print(f"Backed up settings -> {b}")
    added = add_hook(settings)
    os.makedirs(os.path.dirname(p["settings"]), exist_ok=True)
    with open(p["settings"], "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)
        fh.write("\n")
    print(f"{'Added' if added else 'Kept existing'} SessionStart hook in {p['settings']}")
    print("\nDone. New sessions in any repo will be named "
          "'YYYY-MM-DD · AREA · Topic'. Set a repo's area with .claude/chat-area.")


if __name__ == "__main__":
    main()
