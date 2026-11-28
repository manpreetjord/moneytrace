"""Category rules. First match wins. Edit this file to recategorise; never edit numbers in index.html.

Each rule: (category, field, regex)
  field "payee"     -> matched against the payee name only (HDFC "UPI-<payee>-" segment, or the app's
                       "Paid to <payee>"), upper-cased with spaces collapsed. Use this by default:
                       matching the whole narration caught handles like "RXAIRTEL"/"PAID VIA CRED" and
                       misfiled hundreds of rows in the old hand-built version.
  field "narration" -> whole narration, for non-UPI lines (NEFT, FD, ACH, POS) and autopay handles.

Only add a merchant/person after the user has confirmed who they are (house rule: never guess).
Anything unmatched lands in "unreviewed" (counted as Living) and shows up in data/review.csv.

Bucket of each category (what the Overview counts it as) is in BUCKET below.
"""
import re

RULES = [
    # ---- money in ----
    ("salary",        "narration", r"^NEFT CR-.*TATA CONSULTANCY"),
    ("fd_redeem",     "narration", r"^IB FD PREMAT"),
    ("mf_redeem",     "narration", r"MOTILAL OSWAL MUTUAL FUND|ANGEL ONE LTD DSCNB"),
    ("dividend",      "narration", r"^ACH C-"),

    # ---- own money moving between own accounts ----
    ("self_transfer", "payee",     r"^MANPREET ?SINGH$|^9969178114|MANPREETJORD|^X+2953$"),

    # ---- savings ----
    ("fd",            "narration", r"^FD THROUGH MOBILE"),
    ("invest_btc",    "payee",     r"^TUSHAR AGARWAL|^KHEBADE SAURABH NAND|^RAHULRAHUL1PTYES"),
    ("invest_market", "payee",     r"GROWW|ICCL|^ANGEL ONE|^MUTUAL FUNDS"),

    # ---- family (confirmed, excluded from lending) ----
    ("family",        "payee",     r"JASBIR ?KAUR|^GURKIRPAL SINGH|^ADITI YADAV|^GURPREET ?KAUR"),  # Gurpreet Kaur = sister

    # ---- lending (confirmed people) and poker ----
    ("lending",       "payee",     r"^GAURAV CHAHAL|^NITIN SHIVANKIT|^SUNNY ?BOSE|^(MR )?SAURABH SINGH|^SAMRENDRA SINGH|"
                                   r"^SUMIT GAUR|^SUMIT BENIWAL|^SHUBHAM KUMAR PANDEY"),
    ("poker",         "payee",     r"^RAHUL YADAV"),

    # ---- habit (café / paan / wine / liquor), all confirmed ----
    ("habit",         "payee",     r"^BREW BROS|^NITIN SHIVNATH WANGE|^SHANI$|^SURAJ SAROJ|^SUDESH PAN|^GAURI SHANKAR|"
                                   r"BANARAS(I)? PA+N|^HERO PAN|PAN SHOP|PAAN|^SURAJ SHARAD SHINDE|^CHAI ?SUTTA|STYLISH TEA BAR|"
                                   r"WINE|LIQUOR|BEER|^SHREE SATVA TRADITIO|SPORTS BAR|^NINE AVENUE|^PINKY THAKURDAS JAGWANI|^JAHANGIR ?ALI|^POONAM|"
                                   r"^KALPANA MANOJ MEHTA|^SHIVANAND HOSPITALIT"),  # last two: paan shops (user)

    # ---- card bills (card spend itself is not itemised: no full card statements) ----
    ("card_bill",     "payee",     r"^CRED CLUB$|^CRED$|^SBI CARDS"),
    ("card_bill",     "narration", r"GPAY-CREDITCARD@"),

    # ---- bills ----
    ("bill_phone",    "payee",     r"^(BHARTI )?AIRTEL"),
    ("bill_power",    "narration", r"BBPSBP@YBL|SV2512112238344230219611|^BILL PAID - ELECTRICITY"),
    ("bill_gas",      "payee",     r"GAS AGENCY|^RUDRA GAS"),
    ("bill_carwash",  "payee",     r"CAR WASH"),
    ("bill_carwash",  "narration", r"-CAR WASH"),

    # ---- subscriptions ----
    ("subscription",  "payee",     r"^NETFLIX|^APPLE MEDIA|^JEEVANSATHI"),
    ("subscription",  "narration", r"PLAYSTORE|GOOGLE PLAY|CLAUDE\.AI|ANTHROPIC"),

    # ---- living, by type ----
    ("quick_commerce","payee",     r"BLINKIT|ZEPTO|GROFERS|INSTAMART"),
    ("groceries",     "payee",     r"SUPER ?MA(RKET|LL)?\b|^SHREE GANESH SUPER|^VIGHNAHARTA SUPER|KIRANA|^GREEN MART|^VEGGIES|DMART|^PUBLIC BAZAAR"),
    ("food",          "payee",     r"SWIGGY|ZOMATO|^ETERNAL LIMITED"),
    ("shopping",      "payee",     r"AMAZON|FLIPKART|MYNTRA|^CROMA|^TRENT|^ASICS|^AXIS$|^LENSKART|^DECATHLON"),
    ("shopping",      "narration", r"^(CRV )?POS .*(AMAZON|MYNTRA)|^IMPS-.*MYNTRA"),
    ("travel",        "payee",     r"MAKE ?MY ?TRIP|^MMT|IRCTC|CONFIRM ?TICKET|^REDBUS|^INDIGO|^IXIGO"),
    # forex bought for travel: payee VPA is EbixCash World Money (forex dealer)
    ("travel",        "narration", r"EBIXCASHWORLDMONEY"),
    ("transport",     "payee",     r"PETROLEUM|^ARUN KATHWATE|^UBER|^RAPIDO|^OLA\b"),
    ("car",           "payee",     r"^CAR TECH CARE"),
    ("car",           "narration", r"-CAR BUMPER REPAIR"),
    ("health",        "payee",     r"HOSPITAL$|HOSPITAL |HOSPITALOPD|MEDICO|PHARMA|CLINIC|^ASK PATH|CHEMIST"),
    ("groceries",     "payee",     r"VEGETABLE"),
    ("insurance",     "payee",     r"^DIGIT$|POLICYBAZAAR|^PAID - INSURANCE"),
    ("education",     "payee",     r"^NAMASTEDEV"),
    ("bill_other",    "narration", r"GOOGLEBBPSUTILITY@"),
    # HDFC debit card, international: Australian Dept of Home Affairs online = visa application charge
    ("visa_fee",      "narration", r"^POS \S+ HOME AFFAIRS ONL"),
    ("cash",          "narration", r"^(ATW|NWD|EAW)-"),
    ("fx_fees",       "narration", r"^\.DC INTL POS TXN MARKUP|^RFX "),
    # PhonePe wallet top-ups: what the wallet bought is not itemised anywhere
    ("wallet_topup",  "narration", r"PHONEPEWALLETTOPUP|\*+OPUP@YBL"),
    ("wallet_topup",  "payee",     r"^WALLET TOP-UP"),
]

BUCKET = {
    "salary": "income", "fd_redeem": "ignore_in", "mf_redeem": "ignore_in", "dividend": "ignore_in",
    "self_transfer": "self", "fd": "fd", "invest_btc": "invest", "invest_market": "invest",
    "family": "family", "lending": "lending", "poker": "living", "habit": "habit",
    "card_bill": "living", "bill_phone": "living", "bill_power": "living", "bill_gas": "living",
    "bill_carwash": "living", "subscription": "living", "quick_commerce": "living", "groceries": "living",
    "food": "living", "shopping": "living", "car": "living", "insurance": "living", "education": "living",
    "bill_other": "living", "cash": "living", "visa_fee": "living", "fx_fees": "living", "wallet_topup": "living", "travel": "living", "transport": "living", "health": "living",
    "unreviewed": "living",
}

_COMPILED = [(c, f, re.compile(rx, re.I)) for c, f, rx in RULES]


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


def categorise(row):
    """Return (category, how) for one ledger row."""
    fields = {"payee": [norm(row.get("payee")), norm(row.get("app_payee"))], "narration": [norm(row.get("narration"))]}
    for cat, field, rx in _COMPILED:
        if any(v and rx.search(v) for v in fields[field]):
            return cat, "rule"
    return "unreviewed", "none"
