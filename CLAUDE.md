# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this project is

"Kairos / Daily-Report" is a **daily (and weekly) financial email pipeline**. It
fetches market data (equities, bonds, FX, commodities, yield curves, macro,
news), assembles canonical JSON/CSV snapshots, renders an HTML email, and sends
it via Postmark. The report covers UK and US markets plus themed sections
(e.g. nuclear / alternative power — "WNAP").

The production system runs on a server under `/opt/daily-report` on a
systemd timer. **This git repo is the source of truth for code, templates,
schemas, and validators only** — not for runtime data or the large "freeze"
bundles (those live in S3; see `data/FREEZE_INDEX.json` and `freeze_index.md`).

## Read these first

- `README.md` — one-paragraph orientation.
- `WHAT_NOT_TO_TOUCH.md` — **hard boundaries. Read before making changes.**
- `docs/DATA_SCHEMA_2025-11-14.md` — canonical data schema (the contract for
  every JSON/CSV file the pipeline produces).
- `docs/RUNBOOK.md` — how to run/inspect the production daily email.
- `docs/FREEZE_2025-11-15.md` — example of a freeze/handoff note.

## Repository layout

```
.
├── src/                      # Newer, structured pipeline + Jinja2 email renderer
│   ├── email_renderer.py     # Jinja2 renderer (templates/email/base_email.html.j2)
│   ├── equity_overview.py, build_stock_from_universe.py, ...
│   └── validators/           # CI schema validators (stock, bond)
├── scripts/                  # The bulk of the pipeline: fetchers, builders, mergers, senders
├── bin/                      # Server-side runner shims (reference /opt/daily-report)
├── templates/
│   ├── email/base_email.html.j2   # Jinja2 email template (structured path)
│   └── wrapper.html
├── data/                     # Small canonical CSVs + FREEZE_INDEX.json
│   ├── stock.csv, bonds.csv  # Equity/bond master rows (validated in CI)
│   └── FREEZE_INDEX.json     # Pointer to S3 freeze bundles
├── docs/                     # Schema, runbook, freeze notes, examples/
├── aws/                      # VENDORED AWS CLI v2 — do NOT edit (see below)
├── freeze_*/                 # Snapshot dirs; freeze_index.md indexes S3 bundles
├── render_template.py        # LEGACY renderer (placeholder substitution)
├── send_report.py            # SMTP/Postmark sender
├── run_daily_report.sh       # LEGACY end-to-end driver
├── freeze.sh, scripts/make_freeze.sh   # Create + upload freeze tarballs to S3
└── .github/workflows/ci.yml  # CI: validators + email smoke render
```

### `aws/` is vendored — ignore it

`aws/` is a checked-in build of the AWS CLI v2 (~15k files). It is **not project
code**. Never edit it, and when searching/exploring the codebase, exclude it
(`git ls-files | grep -v '^aws/'`) to avoid drowning in vendored files.

## The two rendering paths (important)

There are **two distinct email-rendering paths** in this repo. Know which one
you are touching.

1. **Legacy / placeholder path**
   - `run_daily_report.sh` → `render_template.py <template> <out>` → `send_report.py`
   - Template is plain HTML with `{{PLACEHOLDER}}` tokens
     (`daily_report_full.html`); `render_template.py` does string substitution
     from `macro.json`, `news_*.json`, `prices.csv`, `dividends.csv`.
   - Refuses to send if any `{{...}}` placeholder remains unfilled (exit 2).

2. **Structured / Jinja2 path** (newer, exercised by CI)
   - `src/email_renderer.py --template-dir templates/email --data <payload.json>
     --snapshot ... --freeze ... --out ...`
   - Uses real Jinja2 (`templates/email/base_email.html.j2`) with autoescaping.
   - `scripts/render_email_smoke.sh` drives this as the CI smoke test.

The **production server path** (`bin/run-daily-email.sh`,
`bin/run-daily-email.core.sh`) orchestrates many `scripts/*` steps and references
`/opt/daily-report/...`, including some scripts that live only on the server
(e.g. `bin/build-email.sh`, `bin/send-email.sh`). Those paths won't resolve in a
fresh checkout — treat these shims as documentation of the server flow, not
something you can run locally as-is.

## The data pipeline (`scripts/`)

Scripts follow consistent name prefixes:

- `fetch_*` — pull raw data from vendors (EODHD, FT, WSJ, BBC, AT1 sources).
- `build_*` — compute a canonical section (commodities, curves UK/US, macro
  UK/US, universe, weekly nuclear/alt-power).
- `merge_*` — merge regional/thematic additions into the universe.
- `at1_*` — AT1 (bank contingent-convertible bond) fetch/price/filter/CSV steps.
- `fx_*` — FX pairs and cross-rate building.
- `append_*` / `emit_*` / `wrap_*` / `cleanup_*` — compose and post-process the
  email body HTML.
- `send_email_*`, `postmark_send.py` — delivery.
- `assemble_daily.py` — collect the day's section JSONs into `daily.json`.
- `refresh_all.py` — local orchestrator (`--quick`, `--clean`, `--json`,
  `--save-html`, `--tail`), writes to `out/daily/<date>/`.
- `health_check.py` — post-run assertions (required files exist & non-empty,
  minimum universe/commodity/curve counts).

Many server steps are defensive: `[ -x script ] && run || true` so a missing or
failing optional step doesn't abort the whole run.

## Data conventions (from `docs/DATA_SCHEMA_2025-11-14.md`)

- Every canonical JSON includes: `schema_version`, `as_of_date`,
  `as_of_time_utc`, `data_vintage` (`T-1_close` | `T_intraday` | `T_close`),
  `generated_at_utc`.
- `null` = unavailable/unknown; `0` = real zero. **No magic sentinels** like `-999`.
- Multi-source numeric fields carry paired `*_source` and `*_as_of` fields
  (e.g. `pe_forward`, `pe_forward_source`, `pe_forward_as_of`).
- Runs are **stateless**: each day pulls what it needs and writes a
  self-contained snapshot under `out/data/` (or `out/daily/<date>/`).
- Canonical CSV inputs: `data/stock.csv` (equity master:
  `ticker,exchange,isin,name,country,sector,currency`), `data/bonds.csv`
  (`ticker,isin,issuer,coupon,maturity,price,ytm,running_yield,currency`).
  Sample/test versions live in `docs/examples/`.

## Development workflow

### Branching & commits
- Develop on the assigned feature branch; never push to `main` without
  permission. `main` is protected and requires green CI + CODEOWNERS review
  (`@MGCOHENINVEST` owns everything; see `.github/CODEOWNERS`).
- Do not open a PR unless explicitly asked.
- PRs should follow `.github/pull_request_template.md` (CI green, docs updated,
  email smoke render passes, no large artifacts added).

### Git hooks (run these locally)
- Install: `scripts/install_git_hooks.sh` — sets `.git/hooks/pre-commit` to
  delegate to `scripts/guardrails_check_paths.sh`.
- The guardrail hook **blocks committing** secrets and runtime/output dirs, and
  auto-regenerates `freeze_index.md` (via `scripts/update_freeze_index.sh`) when
  it's staged.
- `.githooks/pre-commit` additionally bans committing archive files
  (`.zip/.7z/.tar/.gz/.bz2`).

### CI (`.github/workflows/ci.yml`)
On PRs and pushes to `main`:
1. `python src/validators/stock_validator.py` — validates `data/stock.csv`
   (required columns, no `(ticker, isin)` dupes). Skips gracefully if absent.
2. `python src/validators/bond_validator.py` — validates `data/bonds.csv`
   (required fields, numeric sanity). Skips gracefully if absent.
3. `./scripts/render_email_smoke.sh` — renders the Jinja2 email to
   `out/daily_smoke_test.html` and asserts it's non-empty.

Reproduce CI locally:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # Jinja2>=3.1.3 (Python 3.10 in CI)
python src/validators/stock_validator.py
python src/validators/bond_validator.py
./scripts/render_email_smoke.sh
```

## Hard boundaries — do NOT cross (see `WHAT_NOT_TO_TOUCH.md`)

- **Never commit secrets**: `.env`, `.env.*`, `.env_email`, `.env_data`,
  `.env_ids`, `.mail.env`, `config.env`. Use `.env.example` with fake values.
- **Never commit runtime/output dirs** (they are gitignored and hook-blocked):
  `out/`, `logs/`, `venv/`, `tmp/`, `archive/`, `backups/`, `releases/`,
  `_snap/`, `_snapshots/`, `config/`, `assets/`, `in/`.
- **Never commit large archives** (`.zip`, `.tgz`, `.tar.gz`). Freeze bundles go
  to S3 (`s3://daily-report-freezes-michael/daily-report/...`) and are tracked
  by SHA-256 in `freeze_index.md` / `data/FREEZE_INDEX.json`.
- **Source-of-truth hierarchy**: pipeline outputs decide *what exists*; the
  renderer decides *presentation only* (no hidden selection logic in HTML);
  delivery just sends what the renderer produced.
- **Renderer contract**: selection is upstream-only via `selected_for_display`;
  warnings are informational, not selection logic; themes don't mutate each
  other's data; card layout is 10 core + 5 next per theme.

## Freeze / release discipline

Before significant changes, create a **freeze**: a tarball + SHA-256 + handoff
note. Use `scripts/make_freeze.sh` (server-side, tars `/opt/daily-report`) or
`freeze.sh <id>` (zips + uploads to S3 + verifies). Then add the entry to
`freeze_index.md` (the pre-commit hook regenerates it on stage). Keep edits
tight, reversible, and documented for the next reader.

## Conventions to match

- Python: standard library first; Jinja2 is the only hard dependency. Scripts
  are small, single-purpose, and `argparse`-driven where they take inputs.
- Read helpers are defensive (try/except → empty dict/list) so a missing input
  degrades gracefully rather than crashing the run.
- Bash: `set -Eeuo pipefail`; optional steps guarded with
  `[ -x ... ] && ... || true`.
- Prefer atomic writes (write temp then `mv`) for files the mailer reads.
