"""CSV parsing helpers (no Django imports so they are easy to test)."""
import csv
import re
from datetime import date

PROVINCE_CODES = {
    "alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB",
    "newfoundland and labrador": "NL", "nova scotia": "NS", "northwest territories": "NT",
    "nunavut": "NU", "ontario": "ON", "prince edward island": "PE", "quebec": "QC", "québec": "QC",
    "saskatchewan": "SK", "yukon": "YT",
}
CODES = set(PROVINCE_CODES.values())
ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")

# column header in the university CSV -> (Deadline.kind, label used in titles)
DEADLINE_COLUMNS = [
    ("Early Application / Early Consideration Deadline", "early", "Early / recommended"),
    ("Regular Application Deadline", "regular", "Regular"),
    ("Supplementary Application Deadline", "supp", "Supplementary"),
    ("Scholarship Deadline", "scholarship", "Scholarship"),
]


def province_code(value):
    v = (value or "").strip()
    return v.upper() if v.upper() in CODES else PROVINCE_CODES.get(v.lower())


def extract_dates(cell):
    """Split a free-text cell on ';' and return (date, label) for each part holding an ISO date."""
    out = []
    for seg in (cell or "").split(";"):
        m = ISO.search(seg)
        if not m:
            continue
        try:
            d = date(*map(int, m.groups()))
        except ValueError:
            continue
        label = ISO.sub("", seg, count=1)
        label = re.sub(r"\b(by|on)\s+(?=for\b)", "", label)
        label = label.strip(" :-–—,")
        if re.match(r"e\.g\.", label, flags=re.I):
            label = "example date " + re.sub(r"^e\.g\.\s*", "", label, flags=re.I)
        label = re.sub(r"^for\s+", "", label, flags=re.I)
        label = re.sub(r"\s+", " ", label).strip(" :-–—,")
        label = re.sub(r"^\((.*)\)$", r"\1", label)
        out.append((d, label))
    return out


def university_rows(path):
    """Yield one dict per university with its info and any dated deadlines."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            status = (r.get("Deadline Verification Status") or "").strip()
            deadlines = []
            for col, kind, kind_label in DEADLINE_COLUMNS:
                for d, label in extract_dates(r.get(col)):
                    deadlines.append({"kind": kind, "due": d,
                                      "title": f"{kind_label}: {label}" if label else f"{kind_label} deadline"})
            yield {
                "name": r["University"].strip(),
                "province": province_code(r.get("Province/Territory")),
                "city": (r.get("City/Campus") or "").strip(),
                "url": (r.get("Official Admissions / Deadline URL") or "").strip(),
                "status": status,
                "notes": (r.get("Notes / Verification") or "").strip(),
                "verified": status.lower().startswith("partially verified"),
                "deadlines": deadlines,
            }


def school_rows(path):
    """Yield (name, city, province_code, board) for each school; province_code is None if unknown."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            g = lambda *keys: next((r[k].strip() for k in keys if r.get(k)), "")
            yield (g("School Name", "name"), g("City", "city"),
                   province_code(g("Province", "province")), g("School Board", "board"))
