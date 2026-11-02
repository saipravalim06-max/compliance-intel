"""
core/quantities.py — find the numbers that matter in a clause or policy line.

For each quantity we return: value, unit, bound direction and the "kind" of
thing being measured (notice period, liability cap, warranty period...).
Two numbers are only comparable when their kind AND dimension match, which is
what stops "7 days to cure a breach" from being compared with "30 days notice".

    find_quantities("terminate upon seven (7) days' written notice")
      -> [Quantity(value=7, unit=DAYS, bound=None, kind='TERMINATION_NOTICE')]
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from core.taxonomy import Unit

# ---------------------------------------------------------------- number words
_ONES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_WORD = "|".join(sorted(list(_ONES) + list(_TENS) + ["hundred"], key=len, reverse=True))
_NUMWORDS = re.compile(rf"\b((?:{_WORD})(?:[\s-]+(?:and\s+)?(?:{_WORD}))*)\b")


def _words_to_int(chunk: str) -> Optional[int]:
    total, current, seen = 0, 0, False
    for w in re.split(r"[\s-]+", chunk):
        if w == "and":
            continue
        if w in _ONES:
            current += _ONES[w]; seen = True
        elif w in _TENS:
            current += _TENS[w]; seen = True
        elif w == "hundred":
            current = max(current, 1) * 100; seen = True
        else:
            return None
    return total + current if seen else None


def preprocess(text: str) -> str:
    """Lower-case; 'thirty (30)' -> '30'; 'forty-five' -> '45'; currency symbols -> words."""
    t = text.lower().replace("’", "'")
    t = re.sub(rf"\b(?:{_WORD})(?:[\s-]+(?:and\s+)?(?:{_WORD}|half))*\s*(?:percent|per cent)\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)", r"\1%", t)
    t = re.sub(rf"\b(?:{_WORD})(?:[\s-]+(?:and\s+)?(?:{_WORD}))*\s*\(\s*(\d[\d,]*(?:\.\d+)?)\s*\)", r"\1", t)  # 'thirty (30)' -> '30'
    t = _NUMWORDS.sub(lambda m: str(_words_to_int(m.group(1))) if _words_to_int(m.group(1)) is not None else m.group(0), t)
    t = t.replace("₹", " inr ").replace("us$", " usd ").replace("$", " usd ")
    t = re.sub(r"\brs\b\.?", " inr ", t)
    return re.sub(r"[ \t]+", " ", t)


# ------------------------------------------------------------------ patterns
_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_MONEY_AFTER = re.compile(rf"\b(inr|usd|eur|gbp)\s*{_NUM}(?:\s*(crores?|lakhs?|million|billion|thousand|k)\b)?")
_MONEY_BEFORE = re.compile(rf"{_NUM}\s*(?:(crores?|lakhs?|million|billion|thousand)\s*)?(inr|usd|dollars?|rupees|eur|gbp)\b")
_PERCENT = re.compile(rf"{_NUM}\s*(?:%|percent|per cent)")
_FEES_MONTHS = re.compile(rf"{_NUM}\s*(?:\(\d+\)\s*)?months?\s*(?:'s)?\s*(?:of|worth of)\s*(?:the\s+)?(?:total\s+|annual\s+)?(?:fees|charges|payments|amounts)")
_FEES_IN_MONTHS = re.compile(rf"(?:fees|charges|payments|amounts)[^.;]{{0,80}}?(?:in|during|over)\s+(?:the\s+)?{_NUM}\s*months?\s+(?:immediately\s+)?(?:preceding|prior|before)")
_FEES_PRECEDING = re.compile(rf"(?:fees|charges|payments|amounts)[^.;]{{0,80}}?(?:preceding|previous|prior|last)\s+{_NUM}\s*months?")
_DURATION = re.compile(rf"{_NUM}\s*-?\s*(?:consecutive\s+|calendar\s+|full\s+)?(business\s+|working\s+)?(hours?|days?|weeks?|months?|years?)\b")
_PER = re.compile(r"[\s)]*(?:per|each|every|a|/)\s*(month|year|annum|occurrence|incident|claim)\b|[\s)]*(annually|yearly|monthly|per annum)\b")

_SCALE = {"crore": 1e7, "crores": 1e7, "lakh": 1e5, "lakhs": 1e5, "million": 1e6, "billion": 1e9, "thousand": 1e3, "k": 1e3}

_LOWER = re.compile(r"(at least|no less than|not less than|no fewer than|not fewer than|a minimum of|minimum|not below|no shorter than|not shorter than|min\.)")
_UPPER = re.compile(r"(no more than|not more than|at most|maximum|a maximum of|not exceed|not to exceed|up to|upto|within|"
                    r"no later than|not later than|not longer than|no longer than|capped at|limited to|exceeding|exceeds|in excess of|"
                    r"more than|longer than|greater than|not be greater than)")
_LESS = re.compile(r"(?<!no )(?<!not )(?<!at )(less than|fewer than|shorter than)")
_NOT_CAPPED_BELOW = re.compile(r"not\s+(?:be\s+)?(?:capped|limited)\s+(?:to\s+|at\s+)?(?:below|under|less than)")
_AT_LEAST_ONCE_EVERY = re.compile(r"at least once\s+(?:every|per|in each|in any|within each)")


@dataclass
class Quantity:
    value: float
    unit: Unit
    bound: Optional[str] = None      # 'UPPER' (ceiling) | 'LOWER' (floor) | None
    per: Optional[str] = None        # 'month' | 'year' | 'occurrence' | 'incident' | 'claim' | None
    kind: Optional[str] = None
    raw: str = ""
    inferred: bool = False           # e.g. "terminate immediately" -> 0 days
    pos: int = -1                    # offset in the preprocessed text (for local-context checks)
    end: int = -1


def _per(tail: str) -> Optional[str]:
    m = _PER.match(tail)
    if not m:
        return None
    w = (m.group(1) or m.group(2) or "").replace("annum", "year").replace("annually", "year") \
        .replace("yearly", "year").replace("monthly", "month")
    return w or None


def _bound(window: str, prohibition: bool) -> Optional[str]:
    if _NOT_CAPPED_BELOW.search(window):
        return "LOWER"
    if _AT_LEAST_ONCE_EVERY.search(window):
        return "UPPER"          # "at least once every 90 days" = interval must be <= 90
    last, pos = None, -1
    for rx, tag in ((_LOWER, "LOWER"), (_UPPER, "UPPER"), (_LESS, "LESS")):
        for m in rx.finditer(window):
            if m.start() >= pos:
                pos, last = m.start(), tag
    if last == "LESS":
        return "LOWER" if prohibition else "UPPER"
    return last


_ASIDE = re.compile(r"\((?:e\.g\.|i\.e\.|for example|for instance|see|per|such as)[^)]*\)", re.IGNORECASE)


def prep(text: str) -> str:
    """Preprocessing used by BOTH find_quantities and detect_kind (same string, same offsets)."""
    return preprocess(_ASIDE.sub(" ", text))


def find_quantities(text: str, prohibition: bool = False) -> List[Quantity]:
    # parenthetical examples ("(e.g., critical vendors require 60 days per POL-01)") are not requirements
    t = prep(text)
    found = []   # (start, end, Quantity)

    def window(start):
        return t[max(0, start - 70):start]

    for m in _FEES_MONTHS.finditer(t):
        found.append((m.start(), m.end(), Quantity(float(m.group(1).replace(",", "")), Unit.MONTHS_OF_FEES,
                                                   _bound(window(m.start()), prohibition), raw=m.group(0))))
    for m in list(_FEES_PRECEDING.finditer(t)) + list(_FEES_IN_MONTHS.finditer(t)):
        found.append((m.start(), m.end(), Quantity(float(m.group(1).replace(",", "")), Unit.MONTHS_OF_FEES,
                                                   _bound(window(m.start()), prohibition), raw=m.group(0))))
    for rx, cur_i, scale_i, val_i in ((_MONEY_AFTER, 1, 3, 2), (_MONEY_BEFORE, 3, 2, 1)):
        for m in rx.finditer(t):
            val = float(m.group(val_i).replace(",", ""))
            sc = m.group(scale_i)
            if sc:
                val *= _SCALE[sc]
            cur = m.group(cur_i)
            unit = Unit.USD if cur in ("usd", "dollar", "dollars", "eur", "gbp") else Unit.INR
            found.append((m.start(), m.end(), Quantity(val, unit, _bound(window(m.start()), prohibition),
                                                       per=_per(t[m.end():m.end() + 30]), raw=m.group(0))))
    for m in _PERCENT.finditer(t):
        found.append((m.start(), m.end(), Quantity(float(m.group(1).replace(",", "")), Unit.PERCENT,
                                                   _bound(window(m.start()), prohibition),
                                                   per=_per(t[m.end():m.end() + 30]), raw=m.group(0))))
    for m in _DURATION.finditer(t):
        # skip "12 months" already consumed as "months of fees"
        if any(s <= m.start() < e for s, e, q in found if q.unit == Unit.MONTHS_OF_FEES):
            continue
        unit_word = m.group(3).rstrip("s")
        biz = bool(m.group(2))
        unit = {"hour": Unit.HOURS, "day": Unit.BUSINESS_DAYS if biz else Unit.DAYS, "week": Unit.WEEKS,
                "month": Unit.MONTHS, "year": Unit.YEARS}[unit_word]
        found.append((m.start(), m.end(), Quantity(float(m.group(1).replace(",", "")), unit,
                                                   _bound(window(m.start()), prohibition), raw=m.group(0))))
    # drop overlaps (keep the earliest/longest), then order by position
    found.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out, last_end = [], -1
    for s, e, q in found:
        if s >= last_end:
            q.pos, q.end = s, e
            out.append(q)
            last_end = e
    return out


# ----------------------------------------------------------- unit conversion
_TO_HOURS = {Unit.HOURS: 1, Unit.DAYS: 24, Unit.WEEKS: 168, Unit.MONTHS: 730, Unit.YEARS: 8760}
_TIME = set(_TO_HOURS) | {Unit.BUSINESS_DAYS}


def compare_values(c_val: float, c_unit: Unit, p_val: float, p_unit: Unit):
    """Return (c_in_policy_unit, status): status is 'EXACT', 'APPROX' (business<->calendar days) or
    'INCOMPARABLE'. Money in different currencies is incomparable."""
    if c_unit == p_unit:
        return c_val, "EXACT"
    if c_unit in _TO_HOURS and p_unit in _TO_HOURS:
        return c_val * _TO_HOURS[c_unit] / _TO_HOURS[p_unit], "EXACT"
    if {c_unit, p_unit} & {Unit.BUSINESS_DAYS} and (c_unit in _TIME and p_unit in _TIME):
        # 1 business day ~ 1.4 calendar days
        c_cal = c_val * 1.4 if c_unit == Unit.BUSINESS_DAYS else c_val * _TO_HOURS[c_unit] / 24
        p_cal = p_val * 1.4 if p_unit == Unit.BUSINESS_DAYS else p_val * _TO_HOURS[p_unit] / 24
        return (c_cal / p_cal) * p_val, "APPROX"
    return None, "INCOMPARABLE"


# --------------------------------------------------------------- kind detection
_NOTICE_KINDS = {"TERMINATION_NOTICE", "RENEWAL_NOTICE", "AUDIT_NOTICE", "FM_NOTICE",
                 "CHANGE_OF_CONTROL_NOTICE", "BREACH_NOTIFICATION"}


_LEAD_AFTER = re.compile(r"\b(?:prior|before|in advance|ahead of|preceding)\b")
_NOTICE_DIRECT = re.compile(r"^\s*(?:'s)?\s*(?:(?:prior|advance|written|formal)\s+)*(?:notice|notification|notif\w*)\b")
_TERM_AFTER = re.compile(r"^\s*-?\s*(?:terms?|periods?|renewals?|extensions?)\b")
_LEAD_REQUIRED = {"RENEWAL_NOTICE", "AUDIT_NOTICE"}
_NO_YEARS = {"AUDIT_NOTICE", "FM_NOTICE", "BREACH_NOTIFICATION", "CHANGE_OF_CONTROL_NOTICE", "INSURANCE_NOTICE"}


def detect_kind(text: str, q: Quantity) -> Optional[str]:
    kind = _detect_kind(text, q)
    if kind in _NOTICE_KINDS and q.pos >= 0 and not q.inferred:
        t = prep(text)
        after_full = t[q.end:]
        after = re.split(r"[,;]| unless | provided | except ", t[q.pos: q.pos + 100])[0]   # stay inside the same clause
        local = t[max(0, q.pos - 90): q.pos] + " " + after
        # "five-year term" / "one (1) year periods" are lengths of a term, not notice periods
        if _TERM_AFTER.match(after_full):
            return "RENEWAL_TERM" if "renew" in t else None
        if kind in _NO_YEARS and q.unit == Unit.YEARS:
            return None
        if not any(w in local for w in ("notice", "notif", "inform", "give", "provide", "report", "deliver", "advance", "prior")):
            return "RENEWAL_TERM" if "renew" in t else None
        if kind in _LEAD_REQUIRED:
            # must read as lead time ("90 days prior to ...") or as the notice itself ("a 6 month notice")
            lead = _LEAD_AFTER.search(after_full[:60]) or _NOTICE_DIRECT.match(after_full)
            if not lead:
                return None
    return kind


def _detect_kind(text: str, q: Quantity) -> Optional[str]:
    t = prep(text)
    has = lambda *ws: any(w in t for w in ws)  # noqa: E731
    u = q.unit
    if u == Unit.MONTHS_OF_FEES:
        return "LIABILITY_CAP"
    if u in (Unit.USD, Unit.INR):
        if has("insur"):
            # which cover is this amount for? look at the words next to the amount, not the whole sentence
            local = t[max(0, q.pos - 130): q.pos + 70] if q.pos >= 0 else t
            lhas = lambda *ws: any(w in local for w in ws)  # noqa: E731
            if lhas("cyber"):
                return "INSURANCE_CYBER"
            if lhas("professional", "errors and omissions", "e&o", "malpractice", "indemnity insurance"):
                return "INSURANCE_PROFESSIONAL"
            if lhas("general liability", "commercial general", "cgl", "bodily injury", "property damage", "each occurrence", "per occurrence"):
                return "INSURANCE_GENERAL"
            return "INSURANCE_OTHER"      # employer's liability, workers' compensation, auto, umbrella ... not comparable
        if has("liabilit") and has("cap", "exceed", "limit"):
            return "LIABILITY_CAP_AMOUNT"
        return None
    if u == Unit.PERCENT:
        if has("late", "interest", "penalt", "overdue"):
            return "LATE_FEE_RATE"
        if has("advance", "deposit", "upfront", "up-front", "prepay"):
            return "ADVANCE_PAYMENT"
        if has("escalat", "increase", "price", "fee", "rate", "renew"):
            return "PRICE_INCREASE"
        return None
    if u in _TIME:
        if has("backup"):
            return "BACKUP_PURGE"
        if has("vulnerab") and has("remed", "patch", "fix", "resolv"):
            return "VULN_REMEDIATION"
        if has("environmental") and has("incident", "notice", "report", "notif"):
            return "ENV_INCIDENT_REPORT"
        if has("force majeure") and has("terminat") and has("consecutive", "continue", "persist"):
            return "FM_TERMINATION_RIGHT"
        if has("force majeure") and has("notice", "notif", "inform"):
            return "FM_NOTICE"
        # Classify a duration by the nearest relevant cue, not by
        # unrelated wording elsewhere in the same contract clause.
        if q.pos >= 0 and not q.inferred:
            before = t[max(0, q.pos - 100):q.pos]
            after = t[q.end:min(len(t), q.end + 120)]

            def nearest_cue(pattern, left, right):
                matches = list(re.finditer(pattern, left + " " + right))
                if not matches:
                    return None
                split = len(left) + 1
                return min(
                    abs(m.start() - split)
                    for m in matches
                )

            cure_distance = nearest_cue(r"\bcure\w*\b", before, after)
            notice_distance = nearest_cue(
                r"\b(?:notice|notif\w*|prior|advance)\b", before, after
            )

            if cure_distance is not None and (notice_distance is None or cure_distance < notice_distance):
                return "CURE_PERIOD"
        elif has("cure"):
            return "CURE_PERIOD"
        if has("renew") and (has("term", "period", "duration", "successive") or _TERM_AFTER.match(t[q.end:])):
            if q.pos >= 0 and not q.inferred:
                before = t[max(0, q.pos - 80):q.pos]
                after = t[q.end:min(len(t), q.end + 80)]
                local = before + " " + after
                if re.search(r"\b(?:term|terms|successive|longer than|period|periods)\b", local) and not re.search(r"\b(?:notice|notif\w*|prior|advance)\b", after[:40]):
                    return "RENEWAL_TERM"
            elif has("term", "longer than") and not has("notice", "notif"):
                return "RENEWAL_TERM"
        if has("renew") and has("notice", "notif", "non-renewal", "nonrenewal"):
            return "RENEWAL_NOTICE"
        if has("change of control", "merger", "acquisition") and has("notice", "notif", "inform") and not has("terminat"):
            return "CHANGE_OF_CONTROL_NOTICE"
        if has("insur") and has("notice", "notif", "cancel"):
            return "INSURANCE_NOTICE"
        if has("audit") and has("notice", "notif"):
            return "AUDIT_NOTICE"
        if has("breach", "incident", "unauthorized disclosure", "unauthorised disclosure", "security event"):
            # Only classify this duration as breach notification when the
            # nearby wording links it to reporting or notifying the incident.
            if q.pos >= 0 and not q.inferred:
                before = t[max(0, q.pos - 100):q.pos]
                after = t[q.end:min(len(t), q.end + 100)]
                local = before + " " + after

                if re.search(
                    r"\b(?:notify|notifies|notified|notification|notifications|"
                    r"report|reports|reported|inform|informs|informed|"
                    r"discover|discovered|awareness)\b",
                    local,
                ):
                    return "BREACH_NOTIFICATION"
            elif has("notif", "report", "inform", "notice", "discover"):
                return "BREACH_NOTIFICATION"
        if has("non-compete", "noncompete", "not compete", "shall not compete", "compete with", "competing", "competitive"):
            return "NON_COMPETE_DURATION"
        if has("solicit"):
            return "NON_SOLICIT_DURATION"
        if has("exclusiv"):
            return "EXCLUSIVITY_DURATION"
        if has("warrant"):
            return "WARRANTY_PERIOD"
        if has("delet", "destr", "purg", "return", "erase", "dispos") and not has("retain ", "surviv"):
            return "DATA_DELETION"
        if has("confidential") and has("surviv", "after", "following", "thereafter", "expir", "terminat"):
            return "CONFIDENTIALITY_SURVIVAL"
        if has("retain", "retention", "kept", "keep", "records") and u in (Unit.YEARS, Unit.MONTHS):
            return "RECORD_RETENTION"
        if has("negotiat", "good-faith", "good faith", "amicabl"):
            return "NEGOTIATION_PERIOD"
        if has("review", "assessment", "penetration") and has("every", "once", "annual", "each"):
            return "REVIEW_INTERVAL"
        if has("pay", "invoice", "net ", "payment"):
            return "PAYMENT_TERM"
        if has("insur"):
            return "INSURANCE_NOTICE"
        if has("terminat", "cancel", "notice"):
            return "TERMINATION_NOTICE"
    return None


# kind -> default direction of the *policy's* limit when its wording gives none
KIND_DEFAULT_BOUND = {
    "TERMINATION_NOTICE": "LOWER", "CURE_PERIOD": "LOWER", "PAYMENT_TERM": "LOWER", "WARRANTY_PERIOD": "LOWER",
    "CONFIDENTIALITY_SURVIVAL": "LOWER", "RECORD_RETENTION": "LOWER", "NEGOTIATION_PERIOD": "LOWER",
    "LIABILITY_CAP": "LOWER", "LIABILITY_CAP_AMOUNT": "LOWER",
    "INSURANCE_GENERAL": "LOWER", "INSURANCE_CYBER": "LOWER", "INSURANCE_PROFESSIONAL": "LOWER",
    "NON_COMPETE_DURATION": "UPPER", "NON_SOLICIT_DURATION": "UPPER", "EXCLUSIVITY_DURATION": "UPPER",
    "RENEWAL_TERM": "UPPER",
    "LATE_FEE_RATE": "UPPER", "PRICE_INCREASE": "UPPER", "ADVANCE_PAYMENT": "UPPER",
    "RENEWAL_NOTICE": "UPPER", "AUDIT_NOTICE": "UPPER", "BREACH_NOTIFICATION": "UPPER",
    "DATA_DELETION": "UPPER", "BACKUP_PURGE": "UPPER", "VULN_REMEDIATION": "UPPER", "ENV_INCIDENT_REPORT": "UPPER",
    "FM_NOTICE": "UPPER", "FM_TERMINATION_RIGHT": "UPPER", "CHANGE_OF_CONTROL_NOTICE": "UPPER", "REVIEW_INTERVAL": "UPPER",
}

if __name__ == "__main__":
    for s in ["Either party may terminate upon seven (7) days' prior written notice.",
              "must not permit unilateral termination by a counterparty with less than fifteen (15) days notice",
              "total liability should not be capped below an amount equal to twelve (12) months of fees",
              "Overdue amounts shall bear interest at 1.5% per month.",
              "Vendors shall maintain cyber liability insurance of USD 2,000,000 per incident."]:
        qs = find_quantities(s, prohibition=("must not" in s))
        print([(q.value, q.unit.value, q.bound, q.per, detect_kind(s, q)) for q in qs])
