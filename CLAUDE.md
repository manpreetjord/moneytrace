# Money Trace — project context for Claude

Read this before touching anything. This file exists so a fresh Claude session
(CLI or otherwise) doesn't have to re-derive what's already been figured out.

## What this is
Manpreet's personal finance tracker. Not a generic budgeting app — the point is
to answer specific questions from real bank/UPI statements: where habit spend
(café/paan/wine/liquor) leaks money, who owes him what and vice versa, what's
actually invested, and a monthly good/bad "advisor" rating. Everything on the
dashboard is reconciled from real statements, not estimates. If a number can't
be traced to a statement line, it goes in the Review queue flagged as unconfirmed
— it does not get silently folded into a category.

## Current state
`index.html` is a single-file dashboard (no build step, no framework) — open it
directly in a browser. It's published two places:
1. A Claude artifact (ask the user if they still want that kept in sync, or if
   GitHub Pages has fully replaced it)
2. **GitHub Pages**, auto-deployed by `.github/workflows/deploy.yml` on every
   push to `master`. Live at https://manpreetjord.github.io/moneytrace/
   (private repo, so viewers need GitHub access to it).

The repo has no backend. `schema.sql` (Supabase/Postgres) and `parse-statement.md`
(a Claude API prompt for parsing statements) describe a planned pipeline that was
never built — all reconciliation so far has been done manually in-session,
one statement upload at a time, with the results hand-written into `index.html`.
Don't assume that pipeline exists; it doesn't yet.

## Current reconciled headline numbers (as of the last pass — verify before quoting)
- **Habit spending**: ₹99,765 over 18 months (Jun'25–Nov'26), ~₹5,542/month
- **Total invested**: ₹3,68,481 (FD ₹2,03,946, BTC ₹1,45,000, Groww ₹38,000,
  Angel One ₹11,732, Mutual Funds NCL +₹20,000, Motilal Oswal MF -₹50,197 net withdrawn)
- **Lending gap (excl. family)**: ₹1,35,404 across 8 people — see the Lending
  tab in `index.html` for the per-person table, it's the source of truth
- **Poker**: ₹12,912 net to Rahul Yadav — deliberately tracked separately from
  lending, it's gambling not a loan
- **Family support** (excluded from the "lending gap" on purpose): ₹2,30,000 to
  Jasbir Kaur, ₹61,975 to Aditi Yadav (a Dubai trip for her parents), ₹1.7L
  college fees to Gurkirpal Singh

Full detail, including the "Safe Report" (a rounded version with habit spend
and friends' names stripped out — built for showing to family) lives in the
Report tab's two-way toggle.

## Data sources discovered so far — and the dedup method
The user pays through **four different rails** that all eventually settle to
one of two accounts (HDFC XX3937, SBI XX2953): the HDFC bank statement itself,
a credit card, PhonePe, GPay, and **super.money** (found late — barely
overlaps PhonePe at all, so don't assume a new app's data is already covered).

Rule that's been load-bearing every time a new statement shows up:
1. The HDFC bank statement is the base layer — covers Jun'25 through whatever
   the most recent `.xls` upload reaches (Oct'26 as of now).
2. Any UPI app transaction tagged to **XX3937** inside that covered window is
   assumed to already be in the bank statement — don't re-add it.
3. Any UPI app transaction tagged to **XX2953** (the SBI side) is *not* in the
   bank statement at all — it's genuinely new money, always.
4. Before trusting that a new UPI export is "new," check it for date-range
   overlap against every UPI export already reconciled, by matching
   `(date, amount)` pairs. PhonePe and super.money, despite covering the same
   account and overlapping time window, turned out to have almost zero
   transaction-level overlap — they're complementary, not duplicates. Don't
   assume any app's export duplicates another's without checking.
5. Whatever month(s) the newest export reaches that the bank statement hasn't
   caught up to yet (currently: Nov 2026) is a **genuine gap** — note it as
   partial data, don't extrapolate a full month from it.

## Known people (so you don't have to re-ask)
- **Habit-spend merchants**: Brew Bros Cafe & Nitin = same person/cafe, SHANI =
  paan shop, Suraj Saroj/Banaras Paan Darbar/Hero Pan shop = paan shops,
  Jahangir Ali = juice shop, Poonam = food, Wine Metro & Bar / Nine Avenue
  Luxury Liquor / The Liquor Story / Vishal Wines / Lakshya Wines = liquor
- **Lending**: Gaurav Chahal, Nitin Shivankit, Sunny Bose, Saurabh Singh,
  Samrendra Singh Sisodia, Sumit Gaur, Sumit Beniwal, Shubham Kumar Pandey —
  see Lending tab for live balances. Rahul Yadav is poker, not lending.
- **Family (not loans, deliberately excluded from the lending gap)**:
  Jasbir Kaur, Gurkirpal Singh (college fees), Aditi Yadav (Dubai trip, parents)
- **Still unconfirmed** — don't categorize these without asking: Pravin Thorat
  (₹51,292), Bimla Chahar (₹11,255), Ashvani Kumar (₹10,000), and several
  super.money names flagged in the Review tab (Aman Deo, Niranjan Kumar, Sutar
  Petroleum, Pramod Ranba Nagargoje, Manish Kirana Store, Avinash Santosh
  Jadhav, MMT Passenger Railway). The original "Shubham ₹5,000" lending the
  user remembered is still unlocated — only small unrelated amounts found.

## House rules for continuing this
- **Never guess a merchant identity.** Every name/merchant mapping above came
  from the user confirming it conversationally. A new cryptic UPI handle goes
  to the Review queue, not into a category.
- **Real statements only.** Don't estimate or average to fill a gap month —
  say it's a gap.
- **One clean recompute beats another patch.** This dashboard drifted badly
  once from incremental one-line edits (numbers went out of sync with each
  other) and the user called it out hard. When new data changes several
  categories, recompute the whole affected area from source, don't hand-edit
  just the one number that was asked about.
- **Statement files never get committed.** `.gitignore` blocks `.xls/.xlsx/.csv/.pdf`
  and `uploads/`. Keep it that way — this is a private repo but still shouldn't
  carry raw bank data.
- **Design**: dark-first with a light theme + day/night toggle (persisted in
  localStorage), single CSS custom-property system in `index.html`'s `<style>`
  block (`--teal`/`--amber`/`--brick`/`--blue` as the semantic accent colors).
  Sidebar nav on desktop, collapses to a horizontal pill bar under 900px.
- **Deploys itself.** Push to `master` → GitHub Actions builds and deploys to
  Pages automatically. (Note: the Pages deploy step has been flaky once or
  twice with a transient "no artifact found" error from GitHub's side — if a
  run fails on `deploy-pages` right after a successful `upload-artifact`,
  just re-run it, don't assume the workflow itself is broken.)

## If continuing in Claude Code CLI specifically
You'll have direct filesystem access and can connect MCP servers / local apps
the way this hosted session couldn't. Good next steps the user has mentioned
but not yet pursued: wiring up the planned Supabase + Claude API parsing
pipeline (`parse-statement.md`) so statements don't have to be hand-processed
every time, and/or a Telegram bot for quick categorization on the go.
