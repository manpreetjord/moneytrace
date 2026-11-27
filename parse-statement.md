# Statement Parsing Layer — Claude API

## Purpose
Takes raw extracted text from an HDFC savings or HDFC/CRED credit card statement PDF
and returns structured transactions matching the Supabase schema — categorized,
merchant-normalized, and flagged for habit spending.

## System Prompt (use as the `system` param, or first message, in the API call)

```
You are a financial statement parser. You will be given raw text extracted from a bank
or credit card statement PDF. Extract every transaction line and return ONLY a JSON array,
no preamble, no markdown fences, no commentary.

Each transaction object must have exactly these fields:
{
  "txn_date": "YYYY-MM-DD",
  "direction": "debit" | "credit",
  "amount": number,
  "merchant_raw": "string exactly as it appears in the statement",
  "merchant_normalized": "cleaned readable merchant name, e.g. 'merchant@ybl' -> 'Swiggy' if identifiable, else best guess, else same as merchant_raw",
  "category": one of [
    "Groceries", "Food & Dining", "Transport", "Rent/Housing", "Utilities",
    "Subscriptions", "Health & Fitness", "Shopping", "Entertainment", "Travel",
    "Investments", "EMI/Loans", "Lending & Borrowing", "Habit Spending", "Miscellaneous"
  ],
  "habit_subtype": "Late Night Orders" | "Impulse Buys" | "Vices" | null,
  "counterparty": "string, only for Lending & Borrowing category, else null",
  "confidence": "high" | "medium" | "low"
}

Rules:
- Salary credits, refunds, and reversals are direction "credit" — do NOT categorize salary
  as an expense category; use category "Miscellaneous" and flag confidence "low" so the
  app layer can route it to the income table instead.
- UPI transactions to food delivery apps (Swiggy, Zomato, etc.) placed after 11 PM local
  time should be categorized as "Habit Spending" with habit_subtype "Late Night Orders".
- Transfers to Groww, Zerodha, Binance, or any recognizable investment platform ->
  category "Investments", habit_subtype null.
- Transfers to individuals (person names, not merchants) with no clear goods/service ->
  category "Lending & Borrowing"; set counterparty to the person/UPI ID.
- Credit card bill payments FROM the savings account -> category "Miscellaneous",
  confidence "low", and add note "credit_card_bill_payment" so the app layer can exclude
  it from expense totals (the itemized card statement already covers the real spend).
- If a merchant cannot be identified at all, still return the row with
  merchant_normalized equal to merchant_raw and confidence "low" — never drop a row.
- Every row in the source text must produce exactly one output object. Do not summarize
  or merge rows.

Return ONLY the JSON array.
```

## Example API Call

```javascript
const response = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "claude-sonnet-4-6",
    max_tokens: 4000,
    messages: [
      {
        role: "user",
        content: `${SYSTEM_PROMPT}\n\nSTATEMENT TEXT:\n${rawStatementText}`
      }
    ]
  })
});

const data = await response.json();
const text = data.content.find(b => b.type === "text")?.text ?? "";
const cleaned = text.replace(/```json|```/g, "").trim();
const transactions = JSON.parse(cleaned);
```

## Notes on wiring into Pipedream
1. Pipedream step 1: trigger on new email (HDFC statement / e-statement) or manual file
   upload via Telegram bot.
2. Pipedream step 2: extract text from the PDF attachment (use a PDF-text-extraction step
   or a Pipedream code step with `pdf-parse`).
3. Pipedream step 3: call the Claude API with the prompt above.
4. Pipedream step 4: for each returned object —
   - if category is a real expense category -> insert into `transactions`
   - if flagged `credit_card_bill_payment` -> skip (already covered by card statement)
   - if flagged as likely income (confidence low + credit direction + large round amount)
     -> insert into `income` table instead, with source guessed as "Salary" or ask for
     manual confirmation via Telegram bot reply
5. Telegram bot: send a daily/weekly digest — "12 new transactions parsed, 2 flagged low
   confidence, tap to review" — this is your manual QA loop before trusting the data.

## Testing before scaling
Run this against ONE month's statement first. Manually check:
- Are all rows captured (row count matches statement row count)?
- Are merchant names normalized sensibly?
- Is Habit Spending only capturing what you actually intended (not over-flagging)?
Only after a clean test month should this run against the full historical backfill.
