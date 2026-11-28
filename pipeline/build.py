"""Ledger -> categorised rows -> Overview/Monthly data -> injected into index.html.

    python3 pipeline/ingest.py && python3 pipeline/build.py

Inputs (all gitignored, under data/):
    ledger.json     from ingest.py
    overrides.json  {"<date>|<amount>|<dir>|<narration>": "<category>"} for rows the user confirmed
                    by hand that no rule covers. Beats rules.
Outputs:
    index.html      the `var D=[...]` line between /*GEN:D*/ markers is replaced
    data/review.csv unreviewed outgoing payments grouped by payee, biggest first (the Review queue)

Definitions (match the notes on the Overview page):
    income  = salary credits only
    living  = every outgoing payment that isn't habit/FD/invest/family/lending/self-transfer,
              from HDFC AND the SBI side (PhonePe/GPay/super.money on XX2953)
    remaining = income - living - habit - fd - invest - family - lending
    saved   = remaining + fd + invest
A month is included only if an HDFC statement covers the whole month; otherwise it is a gap.
"""
import csv, json, re, sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import BUCKET, categorise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HTML = ROOT / "index.html"


def key(r):
    return f"{r['date']}|{r['amount']:.2f}|{r['dir']}|{r['narration']}"


def month_end(m):
    y, mo = int(m[:4]), int(m[5:])
    nxt = date(y + (mo == 12), mo % 12 + 1, 1)
    return (nxt - timedelta(days=1)).isoformat()


def main():
    led = json.loads((DATA / "ledger.json").read_text())
    rows, coverage = led["rows"], led["hdfc_coverage"]
    ov_path = DATA / "overrides.json"
    overrides = json.loads(ov_path.read_text()) if ov_path.exists() else {}

    used = 0
    for r in rows:
        if key(r) in overrides:
            r["cat"], r["how"] = overrides[key(r)], "override"; used += 1
        else:
            r["cat"], r["how"] = categorise(r)
        if r["cat"] not in BUCKET:
            sys.exit(f"unknown category {r['cat']!r} for {key(r)}")

    # a reversal (REV-UPI) undoes the original payment: give it the original's category
    by_ref = {re.search(r"-(\d{12})-", r["narration"]).group(1): r for r in rows
              if r["source"] == "hdfc" and r["dir"] == "out" and re.search(r"-(\d{12})-", r["narration"])}
    for r in rows:
        m = re.search(r"-(\d{12})-", r["narration"])
        if r["narration"].startswith("REV-") and m and m.group(1) in by_ref:
            r["cat"], r["how"], r["reversal"] = by_ref[m.group(1)]["cat"], "reversal", True

    months = sorted({r["date"][:7] for r in rows if r["source"] == "hdfc"})
    covered = lambda m: any(a <= f"{m}-01" and b >= month_end(m) for a, b in coverage)
    app_span = defaultdict(lambda: [None, None])
    for r in rows:
        if r["account"] == "SBI-2953":
            s = app_span[r["file"]]
            s[0] = min(s[0] or r["date"], r["date"]); s[1] = max(s[1] or r["date"], r["date"])
    sbi_seen = lambda m: "full" if any(a <= f"{m}-01" and b >= month_end(m) for a, b in app_span.values()) else \
        ("partial" if any(a <= month_end(m) and b >= f"{m}-01" for a, b in app_span.values()) else "none")

    agg = defaultdict(lambda: defaultdict(float))
    liquid = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        m, b, a = r["date"][:7], BUCKET[r["cat"]], r["amount"]
        if r["source"] == "hdfc":
            liquid[m] = r.get("balance")
        if r["dir"] == "in":
            if b == "income": agg[m]["income"] += a
            elif r.get("reversal"): agg[m][b] -= a; agg[m]["c:" + r["cat"]] -= a
            continue
        agg[m][b] += a
        agg[m]["c:" + r["cat"]] += a
        if r["account"] == "SBI-2953" and b == "living": agg[m]["sbi_living"] += a

    D = []
    for m in months:
        if not covered(m):
            D.append(dict(m=m, gap=True)); continue
        g = agg[m]
        row = dict(m=m, income=g["income"], spent=g["living"], wasted=g["habit"], fd=g["fd"], other=g["invest"],
                   fam=g["family"], lend=g["lending"], liquid=liquid.get(m), qc=g["c:quick_commerce"],
                   sub=g["c:subscription"], ph=g["c:bill_phone"], el=g["c:bill_power"], gs=g["c:bill_gas"],
                   cw=g["c:bill_carwash"], card=g["c:card_bill"], poker=g["c:poker"], unrev=g["c:unreviewed"],
                   sbi=g["sbi_living"], sbiv=sbi_seen(m))
        row["bill"] = row["ph"] + row["el"] + row["gs"] + row["cw"]
        row["saved"] = row["income"] - row["spent"] - row["wasted"] - row["fd"] - row["other"] - row["fam"] - row["lend"]
        D.append({k: (round(v) if isinstance(v, float) else v) for k, v in row.items()})

    # review queue
    rev = defaultdict(lambda: [0, 0.0, "", ""])
    for r in rows:
        if r["cat"] == "unreviewed" and r["dir"] == "out":
            p = (r.get("app_payee") or r["payee"] or r["narration"][:40]).strip()
            v = rev[p]; v[0] += 1; v[1] += r["amount"]; v[2] = v[2] or r["date"]; v[3] = r["date"]
    with open(DATA / "review.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["payee", "count", "total", "first", "last"])
        for p, (n, t, a, b) in sorted(rev.items(), key=lambda kv: -kv[1][1]):
            w.writerow([p, n, round(t, 2), a, b])

    html = HTML.read_text()
    new = "/*GEN:D*/var D=" + json.dumps(D, separators=(",", ":")) + ";/*END:D*/"
    if "/*GEN:D*/" in html:
        html = re.sub(r"/\*GEN:D\*/.*?/\*END:D\*/", lambda _: new, html, count=1, flags=re.S)
    else:
        html, n = re.subn(r"var D=\[.*?\];", lambda _: new, html, count=1, flags=re.S)
        assert n == 1, "could not find the D array in index.html"
    HTML.write_text(html)

    tot = defaultdict(float)
    for d in D:
        for k, v in d.items():
            if isinstance(v, (int, float)) and k != "liquid": tot[k] += v
    print(f"rows {len(rows)} | overrides used {used} | months {len(D)} ({sum(1 for d in D if d.get('gap'))} gap)")
    print("totals:", {k: round(v) for k, v in tot.items()})
    print(f"review queue: {len(rev)} payees, ₹{sum(v[1] for v in rev.values()):,.0f} -> data/review.csv")


if __name__ == "__main__":
    main()
