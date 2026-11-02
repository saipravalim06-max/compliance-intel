"""
core/normalize.py — turn threshold text into (value, unit, bound).

    "₹50 crore in any financial year" -> 500_000_000 INR
    "Up to ₹15" + unit hint "lakh"      -> 1_500_000 INR, bound=UPPER
    "10 years from incorporation"       -> 10 YEARS
    "thirty (30) calendar day"          -> 30 DAYS
    "25% of INR 100 Crore fund"         -> 25 PERCENT   (primary figure only)

Only the FIRST quantity is returned as the primary threshold; later ones (e.g.
"max ₹25,000/trademark") are returned in `secondary`. Returns None when no
number is present — the caller must leave the field blank, never guess.
"""
import re
from typing import Optional

from core.taxonomy import Unit

_SCALE = {"crore": 1e7, "crores": 1e7, "cr": 1e7, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
          "million": 1e6, "thousand": 1e3}
_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
          "forty-five": 45, "sixty": 60, "ninety": 90}
_UPPER = re.compile(r"\b(up to|upto|max(?:imum)?|not (?:exceed|more than)|at most|within|no more than|<=)\b")
_LOWER = re.compile(r"\b(min(?:imum)?|at least|no less than|not less than|not fewer than|>=)\b")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def _unit_after(t: str, end: int) -> Optional[Unit]:
    tail = t[end:end + 30]
    if re.match(r"\s*(%|percent|per cent)", tail):
        return Unit.PERCENT
    if re.match(r"\s*(business|working)\s+days?", tail):
        return Unit.BUSINESS_DAYS
    if re.match(r"\s*(calendar\s+)?days?\b", tail):
        return Unit.DAYS
    if re.match(r"\s*-?\s*months?\b", tail):
        return Unit.MONTHS
    if re.match(r"\s*-?\s*years?\b", tail):
        return Unit.YEARS
    if re.match(r"\s*employees?\b", tail):
        return Unit.EMPLOYEES
    return None


def normalize_threshold(text, unit_hint: Optional[str] = None) -> Optional[dict]:
    if text is None or str(text).strip() == "" or str(text).lower() == "nan":
        return None
    t = str(text).lower().replace("₹", " inr ")
    t = re.sub(r"\brs\b\.?", " inr ", t)
    # "thirty (30)" -> keep the digits; bare number words -> digits
    t = re.sub(r"\b([a-z-]+)\s*\((\d+)\)", r"\2", t)
    for w, n in sorted(_WORDS.items(), key=lambda kv: -len(kv[0])):
        t = re.sub(rf"\b{w}\b", str(n), t)

    matches = list(re.finditer(_NUM, t))
    if not matches:
        return None
    hint = (unit_hint or "").strip().lower()

    def one(m):
        value = _to_float(m.group(1))
        end = m.end()
        scale_word = re.match(r"\s*(crores?|cr|lakhs?|lacs?|million|thousand)\b", t[end:])
        unit = _unit_after(t, end)
        currency = "inr" in t[max(0, m.start() - 8):m.start()] or scale_word is not None
        if scale_word:
            value *= _SCALE[scale_word.group(1)]
            unit = Unit.INR
        elif currency:
            unit = Unit.INR
        # the workbook's unit column may carry the scale ("lakh") while the text only has "₹15"
        if scale_word is None and unit == Unit.INR and hint in ("lakh", "lakhs", "crore", "crores"):
            value *= 1e5 if hint.startswith("lakh") else 1e7
        if unit is None and hint:
            if hint in ("lakh", "lakhs"):
                value *= 1e5
                unit = Unit.INR
            elif hint in ("crore", "crores"):
                value *= 1e7
                unit = Unit.INR
            else:
                unit = {"inr": Unit.INR, "%": Unit.PERCENT, "percent": Unit.PERCENT, "years": Unit.YEARS,
                        "months": Unit.MONTHS, "days": Unit.DAYS, "employees": Unit.EMPLOYEES,
                        "interns": Unit.COUNT}.get(hint)
        if unit is None:
            unit = Unit.COUNT  # bare quantity: "200 startups", "3 certifications"
        return value, unit

    v, u = one(matches[0])
    before = t[:matches[0].start()]
    bound = "UPPER" if _UPPER.search(before) or _UPPER.search(t) else ("LOWER" if _LOWER.search(t) else None)
    secondary = []
    for m in matches[1:]:
        sv, su = one(m)
        secondary.append({"value": sv, "unit": su.value if su else None})
    return {"value": v, "unit": u.value if u else None, "bound": bound, "secondary": secondary}


if __name__ == "__main__":
    for s, h in [("₹50 crore in any financial year", None), ("Up to ₹15", "lakh"),
                 ("10 years from incorporation", None), ("a minimum thirty (30) calendar day written notice", None),
                 ("25% of INR 100 Crore fund", None), ("50%; max ₹25,000/trademark", None),
                 ("Registered", None)]:
        print(f"{s!r:60} -> {normalize_threshold(s, h)}")
