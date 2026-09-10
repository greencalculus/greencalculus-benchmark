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
from units import reconcile

RANGE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(?:[-–—]|\bto\b)\s*(\d[\d,]*(?:\.\d+)?)\s*([^,;.()]{0,45})")
SINGLE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?:\s*[eE]\s*([+-]?\d+))?\s*([^,;.()]{0,45})")

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


def candidates(text):
    """[(value, trailing_unit_text)] — ranges collapse to their midpoint."""
    out, seen = [], set()
    for m in RANGE.finditer(text or ""):
        lo, hi = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
        out.append(((lo + hi) / 2.0, m.group(3)))
        seen.update(range(m.start(), m.end()))
    for m in SINGLE.finditer(text or ""):
        if m.start() in seen:
            continue
        whole, exp, unit = m.group(1).replace(",", ""), m.group(2), m.group(3)
        if "." not in whole and not exp and re.fullmatch(r"(19|20)\d{2}", whole):
            continue  # a bare year is not a value
        v = float(whole) * (10 ** int(exp) if exp else 1)
        out.append((v, unit))
    return out


def best_value(answer, truth_unit):
    """The first candidate whose unit reconciles with the truth's unit."""
    for v, unit in candidates(answer):
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
