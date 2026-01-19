#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FREEZE_DIR="/opt/daily-report-freeze"
OUT="$ROOT/freeze_index.md"

{
  echo "# Freeze index"
  echo ""
  echo "Auto-generated from \`$FREEZE_DIR\`."
  echo "Run: \`scripts/update_freeze_index.sh\`"
  echo ""
  echo "| File | SHA256 | Modified (UTC) |"
  echo "|---|---|---|"
  shopt -s nullglob
  for f in "$FREEZE_DIR"/*.tgz; do
    base="$(basename "$f")"
    sha_file="${f}.sha256"
    if [ -f "$sha_file" ]; then
      sha="$(awk '{print $1}' "$sha_file")"
    else
      sha="$(sha256sum "$f" | awk '{print $1}')"
    fi
    mtime="$(date -u -r "$f" '+%Y-%m-%d %H:%M:%S UTC')"
    echo "| \`$base\` | \`$sha\` | $mtime |"
  done
} > "$OUT"

echo "Wrote $OUT"
