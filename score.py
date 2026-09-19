#!/usr/bin/env python3
"""Score a model's unaided answers against the sourced ground truth.

Four things are measured, and the fourth is the one that matters:

  answered          did it give a number at all, or decline
  value_within_10   the number is within 10% of the sourced value, AFTER unit
                    reconciliation (see units.py)
  cited             it named a publisher or document
  citation_correct  the source it named is the source the number actually comes
                    from — a model that cites DEFRA for an EPA figure is more
                    dangerous than one that cites nothing

Three outcomes per question, not two: correct, wrong, or UNSCOREABLE. A pair of
units this scorer cannot reconcile is excluded from the accuracy denominator and
reported separately, never counted as a wrong answer.
"""
import json, re, unicodedata
from units import CURRENCY, reconcile

# Tokens recognised immediately before a number. CURRENCY already has
# usd/us$/$/eur/gbp/sek; € and £ are listed there in spirit but stripped by
# _clean, so they are canonicalised to EUR/GBP before they reach reconcile.
# Extra ISO/local codes are recognised so "NT$" is not stolen by "$" and so a
# foreign-only figure stays attached to its own code — never given an FX rate.
_EXTRA_CURRENCY = ("€", "£", "nt$", "nok", "aud", "huf", "zar", "jpy", "twd", "mxn")
_SYMBOL_CANON = {"€": "EUR", "£": "GBP"}
_CURRENCY_FAMILY = {
    "usd": "usd", "us$": "usd", "$": "usd",
    "eur": "eur", "€": "eur",
    "gbp": "gbp", "£": "gbp",
    "sek": "sek", "nok": "nok",
    "nt$": "twd", "twd": "twd",
    "aud": "aud", "huf": "huf", "zar": "zar", "jpy": "jpy", "mxn": "mxn",
}


def _currency_token_alts():
    toks = sorted(set(CURRENCY) | set(_EXTRA_CURRENCY), key=len, reverse=True)
    parts = []
    for tok in toks:
        esc = re.escape(tok)
        parts.append(rf"(?<![\w]){esc}(?![\w])" if tok.isalpha() else esc)
    return parts


_CUR_ALTS = _currency_token_alts()
_CUR_BEFORE = re.compile(r"(?:" + "|".join(_CUR_ALTS) + r")\s*$", re.I)
_CUR_LEADING = re.compile(r"^(?:" + "|".join(_CUR_ALTS) + r")", re.I)


def _leading_currency_family(unit):
    """Numerator currency family, or None if the unit does not start with one."""
    if not unit:
        return None
    m = _CUR_LEADING.match(unit.lstrip())
    if not m:
        return None
    return _CURRENCY_FAMILY.get(m.group(0).rstrip().lower())


def _trailing_takes_currency(unit):
    """True when the captured tail is a unit (``/tCO2e``, ``per tCO2e``), not a scale word."""
    raw = (unit or "").lstrip().lower()
    return (not raw) or raw.startswith("/") or raw.startswith("per")


def _with_currency_prefix(text, start, unit):
    """Carry a currency written immediately before the number into `unit`."""
    m = _CUR_BEFORE.search(text[:start])
    if not m or not _trailing_takes_currency(unit):
        return unit, None
    cur = _SYMBOL_CANON.get(m.group(0).strip(), m.group(0).strip())
    fam = _CURRENCY_FAMILY.get(m.group(0).strip().lower())
    unit = unit or ""
    if not unit:
        return cur, fam
    return f"{cur} {unit.lstrip()}", fam

# The unit is whatever immediately follows the number, but it must stop at the
# first separator — an em-dash, comma or bracket usually introduces the source
# ("0.0277 kg CO2e per passenger.km — ADEME Base Carbone 2026 (element 43255)"),
# and swallowing that made a perfectly good unit unparseable.
_UNIT = r"([^,;()\[\]]{0,45}?)(?=\s*(?:[—–]|--|\.\s|,|;|\(|\[|$))"
RANGE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(?:[-–—]|\bto\b)\s*(\d[\d,]*(?:\.\d+)?)\s*" + _UNIT)
SINGLE = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?:\s*[eE]\s*([+-]?\d+))?\s*" + _UNIT)

ALIASES = {
    "DEFRA": ["defra", "desnz", "beis", "uk government", "department for energy security"],
    "EPA": ["epa", "environmental protection agency", "egrid", "warm"],
    "IPCC": ["ipcc", "intergovernmental panel"],
    "EMBER": ["ember"],
    "ADEME": ["ademe", "base carbone", "agribalyse", "base empreinte"],
    "EUROSTAT": ["eurostat"],
    "ECCC": ["eccc", "environment and climate change canada", "canada nir"],
    "DCCEEW": ["dcceew", "nga factors", "national greenhouse accounts"],
    "WORLD": ["world bank"],
    "STATCAN": ["statistics canada", "statcan"],
    "OEKOBAUDAT": ["ökobaudat", "okobaudat", "oekobaudat"],
    "GLEC": ["glec", "smart freight"],
    "NETL": ["netl"],
    "CBAM": ["cbam", "carbon border"],
    "USEEIO": ["useeio"],
    "GCP": ["google cloud", "google"],
    "NGFS": ["ngfs"],
    "CSRD": ["csrd", "esrs"],
    "CA": ["sb-253", "sb253", "sb-261", "california"],
    "GHGP": ["ghg protocol", "greenhouse gas protocol"],
    "NEED": ["need", "national energy efficiency data"],
    "SCARBOROUGH": ["scarborough"],
    "AU": ["australian government"],
}
DECLINE = ["i don't have", "i do not have", "cannot provide", "can't provide", "unable to",
           "no reliable", "i don't know", "i do not know", "don't reliably recall",
           "cannot recall", "can't recall", "would not stand behind", "i don't recall",
           "do not reliably know"]


def norm(s):
    return unicodedata.normalize("NFKD", (s or "")).lower()


def _iter_candidates(text):
    """Yield (value, unit, prefix_family_or_None). Ranges collapse to midpoint."""
    text = text or ""
    seen = set()
    for m in RANGE.finditer(text):
        lo, hi = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
        unit, pref_fam = _with_currency_prefix(text, m.start(), m.group(3))
        yield (lo + hi) / 2.0, unit, pref_fam
        seen.update(range(m.start(), m.end()))
    for m in SINGLE.finditer(text):
        if m.start() in seen:
            continue
        whole, exp, unit = m.group(1).replace(",", ""), m.group(2), m.group(3)
        if "." not in whole and not exp and re.fullmatch(r"(19|20)\d{2}", whole):
            continue  # a bare year is not a value
        v = float(whole) * (10 ** int(exp) if exp else 1)
        unit, pref_fam = _with_currency_prefix(text, m.start(), unit)
        yield v, unit, pref_fam


def candidates(text):
    """[(value, unit_text)] — ranges collapse to their midpoint.

    The unit is the text that trails the number, plus a currency token written
    immediately before it. Models write ``USD 5 /tCO2e``; without the prefix
    the extractor only sees ``/tCO2e``, which never reaches reconcile as
    ``USD/tCO2e``.
    """
    return [(v, unit) for v, unit, _ in _iter_candidates(text)]


def best_value(answer, truth_unit):
    """The first candidate whose unit reconciles with the truth's unit.

    A currency we lifted from immediately before the number is not FX-converted
    into a different currency. ``EUR 65 /tCO2e`` against ``USD/tCO2e`` stays
    unscoreable; if the same sentence also states a USD figure, that is scored.
    Trailing currencies already in the unit text (``85 EUR per tonne``) keep
    their existing reconcile behaviour.
    """
    want = _leading_currency_family(truth_unit)
    for v, unit, pref_fam in _iter_candidates(answer):
        if want and pref_fam and pref_fam != want:
            continue
        conv, note = reconcile(v, unit, truth_unit)
        if conv is not None:
            return conv, unit, note
    return None, None, None


def source_family(source_id):
    sid = (source_id or "").upper()
    for fam in ALIASES:
        if sid.startswith(fam):
            return fam
    return sid.split("_")[0] or None


def cited_families(text):
    t = norm(text)
    return {f for f, words in ALIASES.items() if any(w in t for w in words)}


def score_one(q, answer):
    truth = q["truth"]
    t = norm(answer)
    raw = candidates(answer)
    hedged = any(d in t for d in DECLINE)
    declined = hedged and not raw
    got, used_unit, note = best_value(answer, truth["unit"])
    unscoreable = bool(raw) and got is None

    rel = None
    if got is not None and truth["value"]:
        rel = abs(got - truth["value"]) / abs(truth["value"])

    fams = cited_families(answer) if raw else set()
    want = source_family(truth["source_id"])
    return {
        "id": q["id"], "section": q["section"],
        "answered": bool(raw), "declined": declined, "hedged": hedged,
        "unscoreable": unscoreable, "unit_used": used_unit, "unit_note": note,
        "got": got, "expected": truth["value"], "truth_unit": truth["unit"],
        "rel_error": rel,
        "within_10pct": bool(rel is not None and rel <= 0.10),
        "within_50pct": bool(rel is not None and rel <= 0.50),
        "cited": bool(fams), "cited_families": sorted(fams),
        "expected_family": want,
        "citation_correct": bool(want and want in fams),
        "citation_wrong": bool(fams and want and want not in fams),
    }


def summarise(scored):
    n = len(scored)
    if not n:
        return {}
    scoreable = [s for s in scored if s["rel_error"] is not None]
    cited = [s for s in scored if s["cited"]]
    d = len(scoreable) or 1
    return {
        "n": n,
        "answered": sum(1 for s in scored if s["answered"]),
        "declined": sum(1 for s in scored if s["declined"]),
        "hedged_but_answered": sum(1 for s in scored if s["hedged"] and s["answered"]),
        "unscoreable_units": sum(1 for s in scored if s["unscoreable"]),
        "scoreable": len(scoreable),
        "within_10pct": round(100 * sum(1 for s in scoreable if s["within_10pct"]) / d, 1),
        "within_50pct": round(100 * sum(1 for s in scoreable if s["within_50pct"]) / d, 1),
        "confidently_wrong": round(100 * sum(1 for s in scoreable if not s["within_50pct"]) / d, 1),
        "cited_a_source": round(100 * len(cited) / n, 1),
        "citation_correct_of_cited": round(100 * sum(1 for s in cited if s["citation_correct"]) / len(cited), 1) if cited else None,
        "right_source_wrong_number": round(
            100 * sum(1 for s in scoreable if s["citation_correct"] and not s["within_10pct"]) /
            (sum(1 for s in scoreable if s["citation_correct"]) or 1), 1),
    }


if __name__ == "__main__":
    import sys
    runs = json.load(open(sys.argv[1]))
    qs = {q["id"]: q for q in json.load(open(sys.argv[2]))["questions"]}
    scored = [score_one(qs[r["id"]], r["answer"]) for r in runs if r["id"] in qs]
    print(json.dumps({"summary": summarise(scored), "detail": scored}, indent=1))
