#!/usr/bin/env python3
"""Score a model's unaided answers against the sourced ground truth.

STATUS: this scorer UNDERSTATES accuracy and must not produce a published
figure yet. It has no unit reconciliation (a correct answer in kg C/GJ scored
against a truth in tonne C/GJ reads as a 366,179% error) and its number
extraction takes the first plausible number, which picks SEK out of an answer
that also gave USD. See FINDINGS-pilot.md. Fixing both is the next task.


Four things are measured, and the fourth is the one that matters:

  answered          did it give a number at all, or decline
  value_within_10   the number is within 10% of the sourced value
  cited             it named a publisher or document
  citation_correct  the source it named is the source the number actually
                    comes from — a model that cites DEFRA for an EPA figure
                    is more dangerous than one that cites nothing
"""
import json, re, unicodedata

NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?:\s*[eE]\s*([+-]?\d+))?")

# publisher -> the strings a model plausibly uses for it
ALIASES = {
    "DEFRA": ["defra", "desnz", "beis", "uk government", "department for energy security"],
    "EPA": ["epa", "environmental protection agency", "egrid"],
    "IPCC": ["ipcc", "intergovernmental panel"],
    "EMBER": ["ember"],
    "ADEME": ["ademe", "base carbone", "agribalyse"],
    "EUROSTAT": ["eurostat"],
    "ECCC": ["eccc", "environment and climate change canada"],
    "DCCEEW": ["dcceew", "nga factors", "australian national greenhouse"],
    "WORLD_BANK": ["world bank"],
    "STATCAN": ["statistics canada", "statcan"],
    "OEKOBAUDAT": ["ökobaudat", "okobaudat", "oekobaudat"],
    "GLEC": ["glec", "smart freight"],
    "NETL": ["netl", "national energy technology"],
    "CBAM": ["cbam", "carbon border"],
    "USEEIO": ["useeio"],
}
DECLINE = ["i don't have", "i do not have", "cannot provide", "can't provide", "unable to",
           "no reliable", "i'd recommend checking", "consult the", "varies", "i don't know"]


def norm(s):
    return unicodedata.normalize("NFKD", (s or "")).lower()


def extract_number(text):
    """First plausible factor-like number in the text."""
    for m in NUM.finditer(text or ""):
        whole, frac, exp = m.group(1).replace(",", ""), m.group(2), m.group(3)
        # skip bare years
        if not frac and not exp and re.fullmatch(r"(19|20)\d{2}", whole):
            continue
        v = float(whole + ("." + frac if frac else ""))
        if exp:
            v *= 10 ** int(exp)
        return v
    return None


def source_family(source_id):
    sid = (source_id or "").upper()
    for fam in ALIASES:
        if sid.startswith(fam):
            return fam
    return sid.split("_")[0] or None


def cited_families(text):
    t = norm(text)
    return {fam for fam, words in ALIASES.items() if any(w in t for w in words)}


def score_one(q, answer):
    truth = q["truth"]
    t = norm(answer)
    declined = any(d in t for d in DECLINE) and extract_number(answer) is None
    got = extract_number(answer)
    within = None
    if got is not None and truth["value"]:
        within = abs(got - truth["value"]) / abs(truth["value"])
    # Citations only count on an answer that actually gave a number. A refusal
    # that name-drops a publisher ("consult the DEFRA tables") is not a citation,
    # and counting it inflates the citation-accuracy figure.
    fams = cited_families(answer) if got is not None else set()
    want = source_family(truth["source_id"])
    return {
        "id": q["id"],
        "section": q["section"],
        "answered": got is not None,
        "declined": declined,
        "got": got,
        "expected": truth["value"],
        "rel_error": within,
        "within_10pct": bool(within is not None and within <= 0.10),
        "within_50pct": bool(within is not None and within <= 0.50),
        "cited": bool(fams),
        "cited_families": sorted(fams),
        "expected_family": want,
        "citation_correct": bool(want and want in fams),
        "citation_wrong": bool(fams and want and want not in fams),
    }


def summarise(scored):
    n = len(scored)
    if not n:
        return {}
    answered = [s for s in scored if s["answered"]]
    cited = [s for s in scored if s["cited"]]
    pct = lambda k: round(100 * k / n, 1)
    return {
        "n": n,
        "answered_pct": pct(len(answered)),
        "declined_pct": pct(sum(1 for s in scored if s["declined"])),
        "within_10pct_of_all": pct(sum(1 for s in scored if s["within_10pct"])),
        "within_10pct_of_answered": round(100 * sum(1 for s in answered if s["within_10pct"]) / len(answered), 1) if answered else None,
        "within_50pct_of_answered": round(100 * sum(1 for s in answered if s["within_50pct"]) / len(answered), 1) if answered else None,
        "cited_a_source_pct": pct(len(cited)),
        "citation_correct_of_cited": round(100 * sum(1 for s in cited if s["citation_correct"]) / len(cited), 1) if cited else None,
        "confidently_wrong_pct": pct(sum(1 for s in scored if s["answered"] and not s["within_50pct"])),
    }


if __name__ == "__main__":
    import sys
    runs = json.load(open(sys.argv[1]))
    qs = {q["id"]: q for q in json.load(open(sys.argv[2]))["questions"]}
    scored = [score_one(qs[r["id"]], r["answer"]) for r in runs if r["id"] in qs]
    print(json.dumps({"summary": summarise(scored), "detail": scored}, indent=1))
