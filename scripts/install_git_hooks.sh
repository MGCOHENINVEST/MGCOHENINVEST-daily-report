#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

HOOKS_DIR="$ROOT/.git/hooks"
install -d -m 755 "$HOOKS_DIR"

# Install a tiny delegating hook so the repo version of the guardrails is always used.
cat > "$HOOKS_DIR/pre-commit" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
exec "$ROOT/scripts/guardrails_check_paths.sh"
EOF

chmod 755 "$HOOKS_DIR/pre-commit"

echo "Installed pre-commit hook -> .git/hooks/pre-commit"
echo "Hook delegates to: scripts/guardrails_check_paths.sh"
