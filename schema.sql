-- ============================================================
-- Personal Finance Tracker — Supabase Schema (Phase 1)
-- Sources covered: HDFC savings statement + HDFC/CRED credit card statement
-- ============================================================

-- ---------- ACCOUNTS ----------
-- Every money source/sink: bank account, credit card, investment platform
create table accounts (
  id uuid primary key default gen_random_uuid(),
  name text not null,                -- e.g. 'HDFC Savings', 'HDFC Credit Card', 'Binance', 'Groww'
  account_type text not null check (account_type in ('bank', 'credit_card', 'investment', 'wallet', 'cash')),
  created_at timestamptz default now()
);

-- ---------- CATEGORIES ----------
create table categories (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  nature text not null check (nature in ('need', 'want', 'investment', 'habit', 'transfer')),
  is_habit_flagged boolean default false,   -- true for the "where am I leaking money" bucket
  sort_order int default 0
);

insert into categories (name, nature, is_habit_flagged, sort_order) values
  ('Groceries', 'need', false, 1),
  ('Food & Dining', 'want', false, 2),
  ('Transport', 'need', false, 3),
  ('Rent/Housing', 'need', false, 4),
  ('Utilities', 'need', false, 5),
  ('Subscriptions', 'want', false, 6),
  ('Health & Fitness', 'need', false, 7),
  ('Shopping', 'want', false, 8),
  ('Entertainment', 'want', false, 9),
  ('Travel', 'want', false, 10),
  ('Investments', 'investment', false, 11),
  ('EMI/Loans', 'need', false, 12),
  ('Lending & Borrowing', 'transfer', false, 13),
  ('Habit Spending', 'habit', true, 14),
  ('Miscellaneous', 'want', false, 15);

-- ---------- HABIT SUBTYPES ----------
-- Only meaningful when category = 'Habit Spending'. Keeps the bucket diagnostic, not a dumping ground.
create table habit_subtypes (
  id uuid primary key default gen_random_uuid(),
  name text not null unique      -- e.g. 'Late Night Orders', 'Impulse Buys', 'Vices'
);

-- ---------- INCOME ----------
create table income (
  id uuid primary key default gen_random_uuid(),
  account_id uuid references accounts(id),
  source text not null,           -- 'Salary - TCS', 'Binance Trading Gain', 'Groww Dividend', etc.
  amount numeric(12,2) not null,
  currency text default 'INR',
  received_on date not null,
  is_recurring boolean default false,
  notes text,
  created_at timestamptz default now()
);

-- ---------- TRANSACTIONS (all expenses / transfers) ----------
create table transactions (
  id uuid primary key default gen_random_uuid(),
  account_id uuid references accounts(id) not null,
  category_id uuid references categories(id) not null,
  habit_subtype_id uuid references habit_subtypes(id),   -- nullable, only for Habit Spending
  direction text not null check (direction in ('debit', 'credit')),
  amount numeric(12,2) not null,
  txn_date date not null,
  merchant_raw text,              -- exactly as it appears in the statement (e.g. 'merchant@ybl')
  merchant_normalized text,       -- Claude-normalized readable name (e.g. 'Swiggy')
  counterparty text,              -- for Lending & Borrowing: who the money went to/came from
  is_settled boolean,             -- for Lending & Borrowing: has it been repaid
  source_document text,           -- which statement file this came from, for traceability
  notes text,
  created_at timestamptz default now()
);

create index idx_transactions_date on transactions(txn_date);
create index idx_transactions_category on transactions(category_id);

-- ============================================================
-- RECONCILIATION VIEW — the core insight engine
-- Monthly: income, expenses by category, investments, savings rate
-- ============================================================
create view monthly_reconciliation as
select
  date_trunc('month', coalesce(i.received_on, t.txn_date)) as month,
  coalesce(sum(i.amount) filter (where i.id is not null), 0) as total_income,
  coalesce(sum(t.amount) filter (where t.direction = 'debit' and c.nature != 'investment'), 0) as total_expense,
  coalesce(sum(t.amount) filter (where c.nature = 'investment'), 0) as total_invested,
  coalesce(sum(t.amount) filter (where c.is_habit_flagged), 0) as total_habit_spend
from income i
full outer join transactions t on date_trunc('month', t.txn_date) = date_trunc('month', i.received_on)
left join categories c on c.id = t.category_id
group by 1
order by 1;

-- Savings rate is computed in the app layer as:
-- (total_income - total_expense - total_invested) / nullif(total_income, 0)
