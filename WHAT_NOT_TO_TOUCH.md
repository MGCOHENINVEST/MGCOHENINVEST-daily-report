# What Not To Touch (Kairos / Daily-Report)

This system stays reliable because it has boundaries. Don’t get creative with the boundaries.

## Hard boundaries

### Secrets never go into git
Do not commit:
- `.env`, `.env.*`, `.env_email`, `.env_data`, `.env_ids`, `.mail.env`, `config.env`
If you need templates, create `.env.example` with fake values only.

### Runtime/output directories are not source
Do not commit or hand-edit generated/runtime directories:
- `out/` (generated artefacts)
- `logs/` (runtime logs)
- `venv/` (python environment)
- `tmp/`, `archive/`, `backups/`, `releases/`, `_snap/`, `_snapshots/`, `config/`
- `assets/`, `in/` (treat as local/runtime unless explicitly promoted)

## Source of truth hierarchy
1) Pipeline outputs (canonical registries / `*.scored.json`) decide what exists.
2) Renderer decides presentation/state only (no hidden selection logic in HTML).
3) Delivery (mailer/systemd) sends what renderer produced.

## Renderer contract (keep stable)
- Selection is upstream-only via `selected_for_display` (or equivalent).
- Warnings are informational, not selection logic.
- Theme isolation: one theme does not mutate another theme’s data.
- Card contract: 10 core + 5 next per theme (don’t break layouts casually).

## Change discipline
Before “improvements”:
- Make a freeze tarball + SHA + handoff note.
- Keep edits tight, reversible, and documented for future readers.
