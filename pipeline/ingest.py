"""Parse every raw statement in data/raw/ into one normalised ledger.

    python3 pipeline/ingest.py          -> writes data/ledger.json + prints a dedup report

Sources (file name prefix decides the parser):
    hdfc_*.xls        HDFC XX3937 account statement (base layer, always kept)
    phonepe_*.csv     PhonePe export (CSV, has UTR)
    phonepe_*.pdf     PhonePe export (PDF, has UTR)
    gpay_*.pdf        Google Pay statement (has UPI transaction ID)
    supermoney_*.pdf  super.money history (no reference number)

Dedup, in order:
 1. UPI app rows whose 12-digit UPI ref appears in an HDFC narration are the same
    payment as that bank row: they only enrich it (payee name), never add money.
 2. Same UPI ref seen in two app exports (e.g. the two PhonePe exports) is kept once.
 3. super.money has no ref: an XX3937 row inside HDFC coverage is assumed to be in
    the bank already; an XX2953 row is dropped if another app already has the same
    (date, amount) on XX2953.
 4. Wallet / gift-card instrument rows are dropped: wallet top-ups already left
    the bank as their own debit.
Every kept row gets an id; nothing is categorised here (see rules.py).
"""
import json, re, subprocess, sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "ledger.json"


def pdftext(path):
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout


def money(s):
    return float(str(s).replace("₹", "").replace("INR", "").replace(",", "").strip())


# ---------- parsers: each returns a list of dicts ----------

def parse_hdfc(path):
    x = pd.read_excel(path, header=None)
    hi = x.index[x.iloc[:, 0].astype(str).str.strip() == "Date"][0]
    t = x.iloc[hi + 1:, :7].copy()
    t.columns = ["date", "narration", "bankref", "valuedt", "w", "d", "bal"]
    t = t[t.date.astype(str).str.match(r"^\d\d/\d\d/\d\d$")]
    rows = []
    for _, r in t.iterrows():
        nar = str(r.narration).strip()
        w, d = (0 if pd.isna(r.w) else float(r.w)), (0 if pd.isna(r.d) else float(r.d))
        m = re.match(r"^UPI-(.+?)-", nar)
        ref = re.search(r"-(\d{12})-", nar)
        rows.append(dict(
            date=datetime.strptime(r.date, "%d/%m/%y").strftime("%Y-%m-%d"),
            amount=w or d, dir="out" if w else "in", account="HDFC-3937", source="hdfc",
            ref=ref.group(1) if ref else str(r.bankref).strip(), payee=(m.group(1).strip() if m else ""),
            narration=nar, balance=float(r.bal), file=path.name))
    return rows


def _acct(s):
    s = str(s)
    if "2953" in s: return "SBI-2953"
    if "3937" in s: return "HDFC-3937"
    return "WALLET"


def parse_phonepe_csv(path):
    lines = path.read_text().splitlines()
    hi = next(i for i, l in enumerate(lines) if l.startswith("Date,"))
    t = pd.read_csv(path, skiprows=hi, dtype=str).fillna("")
    t = t[t.Date.str.match(r"^\d{4}-\d\d-\d\d$") & (t.Amount.str.strip() != "")]
    rows = []
    for _, r in t.iterrows():
        det = r["Transaction Details"].strip()
        rows.append(dict(date=r.Date.strip(), amount=money(r.Amount), dir="out" if r["Transaction Type"].strip() == "Debit" else "in",
                         account=_acct(r["Credit/debit instrument"]), source="phonepe", ref=str(r.UTR).strip(),
                         payee=re.sub(r"^(Paid to|Received from)\s+", "", det), narration=det, file=path.name))
    return rows


def parse_phonepe_pdf(path):
    txt = pdftext(path)
    blocks = re.split(r"\n(?=[A-Z][a-z]{2} \d\d, \d{4}\s)", txt)
    rows = []
    for b in blocks:
        m = re.match(r"([A-Z][a-z]{2} \d\d, \d{4})\s+(.+?)\s{2,}(Debit|Credit)\s+(?:INR\s*([\d,\.]+))?", b)
        if not m: continue
        amt = m.group(4) or re.search(r"INR\s*\n?.*?([\d,]+\.\d\d)", b[m.end() - 30:], re.S).group(1)
        utr = re.search(r"UTR No\s*:\s*(\d+)", b)
        acc = re.search(r"(?:Debited from|Credited to)\s+(XX\d{4}|Gift Card|Wallet)", b)
        det = m.group(2).strip()
        rows.append(dict(date=datetime.strptime(m.group(1), "%b %d, %Y").strftime("%Y-%m-%d"), amount=money(amt),
                         dir="out" if m.group(3) == "Debit" else "in", account=_acct(acc.group(1) if acc else ""),
                         source="phonepe", ref=utr.group(1) if utr else "", payee=re.sub(r"^(Paid to|Received from)\s+", "", det),
                         narration=det, file=path.name))
    return rows


def parse_gpay(path):
    txt = pdftext(path)
    rows = []
    for m in re.finditer(r"(\d\d \w{3}, \d{4})\s+(Paid to|Received from|Self transfer to)\s+(.+?)\s{2,}₹([\d,\.]+)\s*\n.*?UPI Transaction ID:\s*(\d+)\s*\n\s*(?:Paid by|Paid to|Received in)\s+(.+?)\n", txt):
        rows.append(dict(date=datetime.strptime(m.group(1), "%d %b, %Y").strftime("%Y-%m-%d"), amount=money(m.group(4)),
                         dir="in" if m.group(2) == "Received from" else "out", account=_acct(m.group(6)), source="gpay",
                         ref=m.group(5), payee=m.group(3).strip(), narration=f"{m.group(2)} {m.group(3).strip()}", file=path.name))
    return rows


def parse_supermoney(path):
    txt = pdftext(path)
    rows = []
    for m in re.finditer(r"^\s*(.+?)\s{2,}(SBI 2953|HDFC 3937)\s+(-?[\d,]+\.\d\d)\s+(\d{1,2} \w+ \d{4})\s+(SUCCESS)", txt, re.M):
        a = money(m.group(3))
        rows.append(dict(date=datetime.strptime(m.group(4), "%d %B %Y").strftime("%Y-%m-%d"), amount=abs(a),
                         dir="out" if a < 0 else "in", account=_acct(m.group(2)), source="supermoney", ref="",
                         payee=m.group(1).strip(), narration=m.group(1).strip(), file=path.name))
    return rows


PARSERS = [("hdfc_", ".xls", parse_hdfc), ("phonepe_", ".csv", parse_phonepe_csv), ("phonepe_", ".pdf", parse_phonepe_pdf),
           ("gpay_", ".pdf", parse_gpay), ("supermoney_", ".pdf", parse_supermoney)]


def main():
    raw = {}
    coverage = []  # HDFC statement periods
    for f in sorted(RAW.iterdir()):
        for pre, ext, fn in PARSERS:
            if f.name.startswith(pre) and f.suffix == ext:
                raw.setdefault(fn.__name__, []).extend(r := fn(f))
                print(f"  {f.name}: {len(r)} rows")
                if pre == "hdfc_":
                    coverage.append((min(x["date"] for x in r), max(x["date"] for x in r)))
    bank = raw.get("parse_hdfc", [])
    # HDFC files can overlap at their boundary day: drop exact repeats
    seen, b2 = set(), []
    for r in bank:
        k = (r["date"], r["ref"], r["amount"], r["dir"], r["narration"])
        if k not in seen: seen.add(k); b2.append(r)
    bank = b2
    bank_refs = {r["ref"]: r for r in bank if re.fullmatch(r"\d{12}", r["ref"])}
    covered = lambda d: any(a <= d <= b for a, b in coverage)

    stats = {}
    def stat(k): stats[k] = stats.get(k, 0) + 1
    kept_apps, app_refs, sbi_keys = [], set(), set()
    for name in ["parse_phonepe_csv", "parse_phonepe_pdf", "parse_gpay", "parse_supermoney"]:
        for r in raw.get(name, []):
            if r["account"] == "WALLET": stat("wallet/gift card dropped"); continue
            if r["ref"] and r["ref"] in bank_refs:
                b = bank_refs[r["ref"]]
                b.setdefault("app_payee", r["payee"]); b.setdefault("app_source", r["source"])
                stat("matched to HDFC row by UPI ref"); continue
            if r["ref"] and r["ref"] in app_refs: stat("duplicate across app exports (same ref)"); continue
            if r["account"] == "HDFC-3937" and covered(r["date"]):
                stat("XX3937 inside HDFC coverage, no ref match (assumed in bank)"); continue
            if r["account"] == "HDFC-3937":
                stat("XX3937 outside HDFC coverage (kept, partial month)")
            if r["source"] == "supermoney" and (r["date"], r["amount"], r["dir"]) in sbi_keys:
                stat("super.money duplicate of another app (date, amount)"); continue
            if r["ref"]: app_refs.add(r["ref"])
            if r["account"] == "SBI-2953" and r["source"] != "supermoney": sbi_keys.add((r["date"], r["amount"], r["dir"]))
            kept_apps.append(r); stat(f"kept {r['source']} {r['account']}")
    ledger = sorted(bank + kept_apps, key=lambda r: (r["date"], r["source"]))
    for i, r in enumerate(ledger):
        r["id"] = f"{r['source'][:2]}{i:05d}"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(dict(hdfc_coverage=sorted(coverage), rows=ledger), indent=0))
    print(f"\nHDFC rows {len(bank)} | app rows kept {len(kept_apps)} | ledger {len(ledger)} -> {OUT.relative_to(ROOT)}")
    for k, v in sorted(stats.items()): print(f"  {v:5d}  {k}")


if __name__ == "__main__":
    main()
