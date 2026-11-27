# Money Trace — Personal Finance Tracker

A finance tracker built to answer one question: where is the money actually going,
and what's habit-driven waste vs. real spend.

## Contents
- `index.html` — the dashboard UI (10 screens: Dashboard, Transactions, Review queue,
  Categories, Lending, Income, Insights, Report, Upload, Settings)
- `schema.sql` — Supabase/Postgres schema (accounts, categories, income, transactions,
  habit_subtypes, monthly_reconciliation view)
- `parse-statement.md` — Claude API prompt + wiring notes for parsing bank/card
  statements into structured transactions

## Status
UI is built and currently populated with real parsed data from manual analysis
(HDFC bank statement, credit card, GPay, PhonePe). No live backend yet — Supabase
+ Pipedream + the Claude API parser described in `parse-statement.md` are designed
but not wired up.

## Stack (planned)
Next.js PWA + Supabase + Pipedream + Telegram bot + Claude API parsing layer

## Note
Statement files (.xls/.pdf/.csv) are gitignored — this repo holds the app and
pipeline code only, not financial source documents.
