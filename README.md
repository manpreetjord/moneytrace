# Money Trace — Personal Finance Tracker

A finance tracker built to answer one question: where is the money actually
going, and what's habit-driven waste vs. real spend vs. real investment.

**Viewing:** open `index.html` locally or use the private Claude artifact. The
GitHub Pages URL intentionally serves only a blank placeholder: Pages from a
personal account is public even for a private repo.

## Contents
- `index.html` — the full dashboard, single file, no build step. 11 screens:
  Dashboard, Monthly (per-month advisor ratings), Transactions, Review queue,
  Categories, Lending, Income, Insights, Report (Safe/Real Deal toggle),
  Upload, Settings. Light/dark theme toggle, responsive (sidebar on desktop,
  tab bar on mobile).
- `CLAUDE.md` — detailed project context for continuing this with Claude
  (data sources, dedup methodology, known people, current numbers, house
  rules). **Read this first** before making changes — it has everything that
  would otherwise need re-explaining.
- `pipeline/` — `ingest.py` (statements -> ledger, UPI-ref dedup), `rules.py` (categories),
  `build.py` (ledger -> Overview/Monthly data in `index.html` + review queue). Raw statements and the
  ledger live in `data/`, which is gitignored.
- `schema.sql` — a planned Supabase/Postgres schema (not yet wired up)
- `parse-statement.md` — a planned Claude API prompt for automated statement
  parsing (not yet wired up)
- `.github/workflows/deploy.yml` — publishes a blank placeholder to GitHub
  Pages (the dashboard itself is never published there)

## Status
Fully manual reconciliation pipeline: statements get uploaded in a Claude
session, parsed and cross-checked against every other source already on file
(to avoid double-counting across apps), and the dashboard gets hand-updated
with the result. No live backend — see `CLAUDE.md` for what's planned vs.
built.

Current data sources reconciled: HDFC bank statements (3), HDFC/CRED credit
card, PhonePe (full year), GPay, and super.money (full year) — all settling
to one of two linked accounts (HDFC XX3937, SBI XX2953).

## Note
Statement files (`.xls`/`.xlsx`/`.csv`/`.pdf`) and an `uploads/` folder are
gitignored — this repo holds the app and docs only, never raw bank data.
