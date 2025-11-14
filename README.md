# daily-report
Code, templates, schemas, and validators. Heavy freeze bundles live in object storage; see `data/FREEZE_INDEX.json`.
- For the canonical data layout, see `docs/DATA_SCHEMA_2025-11-14.md`.
- Email: templates/email/base_email.html.j2, scripts/render_email_smoke.sh
- Stock schema: stock.schema.json, src/validators/stock_validator.py
- CI: .github/workflows/ci.yml
- housekeeping: CI/branch protection hardening
