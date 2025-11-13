#!/usr/bin/env bash
set -euo pipefail

exec /usr/bin/flock -n /tmp/daily-email.lock /bin/bash -s <<'EOF'
set -euo pipefail

ROOT=/opt/daily-report
cd "$ROOT"

if [ -f "$ROOT/.env" ]; then
  set +u
  . "$ROOT/.env"
  set -u
fi

echo "[daily-email] starting build at $(date --iso-8601=seconds)"
"$ROOT/bin/build-email.sh"

echo "[daily-email] normalising yield JSON"
"$ROOT/bin/fix-yield-json.py"

if [ -x "$ROOT/bin/send-email.sh" ]; then
  "$ROOT/bin/send-email.sh"
else
  echo "[send] skip: no send-email.sh"
fi

echo "[daily-email] done"
EOF
