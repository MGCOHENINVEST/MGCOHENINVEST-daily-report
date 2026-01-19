#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACMR || true)
[ ${#STAGED[@]} -eq 0 ] && exit 0

# If freeze_index.md is staged, regenerate it and re-stage so commits never
# capture a stale freeze index.
need_freeze_refresh=0
for f in "${STAGED[@]}"; do
  if [[ "$f" == "freeze_index.md" ]]; then
    need_freeze_refresh=1
    break
  fi
done

if [[ "$need_freeze_refresh" -eq 1 ]]; then
  if [[ -x "scripts/update_freeze_index.sh" ]]; then
    scripts/update_freeze_index.sh >/dev/null
    git add freeze_index.md
  else
    echo "ERROR: freeze_index.md staged but scripts/update_freeze_index.sh missing or not executable" >&2
    exit 1
  fi
fi

# Block commits of secrets + runtime/output dirs (these must never be tracked)
DENY_PREFIXES=(
  "venv/" "out/" "logs/" "tmp/" "archive/" "backups/" "releases/"
  "_snap/" "_snapshots/" "config/" "assets/" "in/"
)
DENY_EXACT=( ".env" "config.env" ".mail.env" ".env_data" ".env_email" ".env_ids" )

declare -A bad=()

# Recompute staged list in case we re-staged freeze_index.md above
mapfile -t STAGED < <(git diff --cached --name-only --diff-filter=ACMR || true)
[ ${#STAGED[@]} -eq 0 ] && exit 0

for f in "${STAGED[@]}"; do
  for x in "${DENY_EXACT[@]}"; do
    [[ "$f" == "$x" ]] && bad["$f"]=1
  done

  [[ "$f" == .env.* ]] && bad["$f"]=1
  [[ "$f" == backup_* ]] && bad["$f"]=1

  for p in "${DENY_PREFIXES[@]}"; do
    [[ "$f" == "$p"* ]] && bad["$f"]=1
  done
done

if [ ${#bad[@]} -gt 0 ]; then
  echo "ERROR: refusing to commit local/runtime/secrets paths:" >&2
  for k in "${!bad[@]}"; do echo "  - $k" >&2; done
  echo "Fix: unstage them (git restore --staged <path>) or keep them out of git." >&2
  exit 1
fi

exit 0
