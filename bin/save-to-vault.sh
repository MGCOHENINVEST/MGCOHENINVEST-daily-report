#!/usr/bin/env bash
# save-to-vault.sh — write a Claude chat summary note into the LOCAL Obsidian vault.
#
# SECURITY / DESIGN: the vault is a LOCAL-ONLY git repo with NO remote, by design.
# It holds sensitive notes and must never sit as plaintext on a hosted remote
# (GitHub etc.). This script therefore performs NO git operations and NO network
# push — it only writes a file into the vault's _chats/ folder. Off-site
# persistence is handled externally by the vault's launchd auto-commit and the
# daily encrypted-bundle backup. Do not add push/clone logic here.
#
# Usage:
#   echo "$SUMMARY" | bin/save-to-vault.sh \
#       --area INV --sub Deal --topic "Convolo Group" --entity "Convolo Group" \
#       --created 2026-07-01 --last-active 2026-07-10 --version 2 --source cowork
#
# Flags are passed straight through to bin/vault-note.py; this script supplies
# --out (the vault _chats folder). The summary body comes from stdin or
# --summary-file; omit it to write a fillable skeleton.
#
# Destination: set VAULT_CHATS_DIR to override; defaults to the iCloud Obsidian path.
set -euo pipefail

VAULT_CHATS_DIR="${VAULT_CHATS_DIR:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/MC_Obsidian/_chats}"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
note_gen="$here/vault-note.py"

if [[ ! -f "$note_gen" ]]; then
  echo "save-to-vault: cannot find vault-note.py at $note_gen" >&2
  exit 1
fi

if [[ ! -d "$VAULT_CHATS_DIR" ]]; then
  echo "save-to-vault: vault _chats folder not found:" >&2
  echo "  $VAULT_CHATS_DIR" >&2
  echo "Set VAULT_CHATS_DIR to your vault's _chats path, or create the folder first." >&2
  exit 1
fi

# Pass all caller args through; force --out to the local vault folder (ours wins
# as the last --out if the caller also passed one). No git, no network.
python3 "$note_gen" "$@" --out "$VAULT_CHATS_DIR"
