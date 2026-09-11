#!/usr/bin/env python3
"""Flatten this repo into HuggingFace dataset configs.

Two rules drive the design.

1. The scored columns come from `score.score_one`, the SAME function that
   produces the numbers in the guides and the Zenodo record. If the scorer is
   fixed, this dataset moves with it. Re-implementing the scoring here would
   let the published figures and the dataset drift apart silently, which is the
   one failure this repo exists to argue against.

2. Nothing here may touch the held-out split. `assert_no_holdout()` aborts the
   build if a held-out id reaches any row. The CI guard protects git; it does
   not protect an upload, and an upload is exactly how this would leak.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# aeo/ has its own score.py. Import the ROOT scorer first and never put aeo/ on
# sys.path globally, or `from score import score_one` silently resolves to the
# AEO module and this build scores nothing.
from score import score_one                      # noqa: E402
from compare import question_order, load_run      # noqa: E402

OUT = Path(__file__).parent / "data"


def holdout_ids():
    """Read the private set if it is present, so the guard can be exact.
    If it is absent (a fresh clone), fall back to the manifest's count so the
    build still refuses to run blind."""
    p = ROOT / "holdout.json"
    if p.exists():
        return {q["id"] for q in json.loads(p.read_text(encoding="utf-8"))["questions"]}
    man = json.loads((ROOT / "holdout-manifest.json").read_text(encoding="utf-8"))
    print(f"  ! holdout.json absent — cannot verify exactly. Manifest says n={man['n']}.")
    print("    Clone greencalculus/benchmark-holdout beside this repo and re-run.")
    sys.exit("refusing to build without the held-out set available to check against")


def assert_no_holdout(rows, field, banned):
    hit = sorted({r[field] for r in rows if r.get(field) in banned})
    if hit:
        sys.exit(f"HELD-OUT LEAK: {len(hit)} held-out ids in output, e.g. {hit[:3]}")


def write(name, rows):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    with (d / "train.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {name:16} {len(rows):>5} rows")
    return len(rows)


def build_questions(qs, canary):
    return [{
        "id": q["id"], "section": q["section"], "question": q["question"],
        "truth_value": q["truth"]["value"], "truth_unit": q["truth"]["unit"],
        "truth_gas": q["truth"].get("gas"), "truth_basis": q["truth"].get("basis"),
        "country_iso3": q["truth"].get("country_iso3"),
        "publisher": q["truth"].get("publisher"),
        "source_name": q["truth"].get("source_name"),
        "source_id": q["truth"].get("source_id"),
        "cell_ref": q["truth"].get("cell_ref"),
        "proof_url": q["truth"].get("proof_url"),
        # Carried on every row on purpose: a scraper that takes only the parquet
        # still takes the canary with it. See CANARY.md.
        "canary": canary,
    } for q in qs]


def build_answers(qmap, uniq):
    runs = {}
    for d in sorted(ROOT.glob("results/raw_*")):
        runs[d.name.replace("raw_", "")] = load_run(d, uniq)
    legacy = ROOT / "results" / "runs_opus5_full.json"
    if legacy.exists():
        runs["claude-opus-5"] = {r["id"]: r["answer"] for r in json.load(open(legacy))}
    rows = []
    for model, answers in sorted(runs.items()):
        for qid, text in answers.items():
            if qid not in qmap:
                continue
            s = score_one(qmap[qid], text)
            rows.append({
                "model": model, "question_id": qid, "section": s["section"],
                "answer": text,
                "answered": s["answered"], "declined": s["declined"],
                "unscoreable_units": s["unscoreable"],
                "extracted_value": s["got"], "truth_value": s["expected"],
                "truth_unit": s["truth_unit"], "unit_used": s["unit_used"],
                "rel_error": s["rel_error"],
                "within_10pct": s["within_10pct"], "within_50pct": s["within_50pct"],
                "cited_a_source": s["cited"], "cited_families": s["cited_families"],
                "expected_family": s["expected_family"],
                "citation_correct": s["citation_correct"],
                "right_source_wrong_number": bool(
                    s["citation_correct"] and s["rel_error"] is not None
                    and not s["within_10pct"]),
            })
    return rows


def build_recommendations():
    import importlib.util, re
    spec = importlib.util.spec_from_file_location("aeo_brands", ROOT / "aeo" / "brands.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    BRANDS, VENDORS, DATASETS = m.BRANDS, m.VENDORS, m.DATASETS
    seen, rows = set(), []
    for line in (ROOT / "aeo" / "answers.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        k = (r["model"], r["prompt"])
        if k in seen:
            continue                       # runners append; the study de-dups on (model, prompt)
        seen.add(k)
        low = r["answer"].lower()
        named = [b for b in VENDORS if any(re.search(p, low) for p in BRANDS[b])]
        first, pos = None, 10 ** 9
        for b in VENDORS:
            for p in BRANDS[b]:
                m = re.search(p, low)
                if m and m.start() < pos:
                    pos, first = m.start(), b
        rows.append({
            "model": r["model"], "intent": r["intent"], "prompt": r["prompt"],
            "answer": r["answer"],
            "vendors_named": sorted(named), "n_vendors_named": len(named),
            "first_vendor_named": first,
            "datasets_cited": sorted(d.lstrip("_") for d in DATASETS
                                     if any(re.search(p, low) for p in BRANDS[d])),
            "names_greencalculus": "GreenCalculus" in named,
        })
    return rows


# Hand labels. score.py cannot decide these — "did the model invent a company"
# is a reading, not a regex. Recorded explicitly so the judgement is auditable
# rather than buried in a heuristic. The raw text is in the row; disagree freely.
PROBE_OUTCOME = {
    ("claude-opus-5", "known", 0): "declined",
    ("claude-opus-5", "known", 1): "declined",
    ("claude-opus-5", "compare", 0): "declined",
    ("gemini-3.1-pro-preview", "known", 0): "declined",
    ("gemini-3.1-pro-preview", "known", 1): "declined",
    ("gemini-3.1-pro-preview", "compare", 0): "fabricated",
    ("gemini-3.6-flash", "known", 0): "declined",
    ("gemini-3.6-flash", "known", 1): "fabricated",
    ("gemini-3.6-flash", "compare", 0): "fabricated",
    ("grok-4.6", "known", 0): "declined",
    ("grok-4.6", "known", 1): "declined",
    ("grok-4.6", "compare", 0): "declined",
}


def build_direct_probe():
    rows, n = [], {}
    for line in (ROOT / "aeo" / "direct_probe.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        k = (r["model"], r["kind"])
        i = n.get(k, 0); n[k] = i + 1
        rows.append({
            "model": r["model"], "probe_kind": r["kind"], "prompt": r["prompt"],
            "answer": r["answer"],
            "outcome": PROBE_OUTCOME.get((r["model"], r["kind"], i), "unlabelled"),
            "presupposes_answer": r["kind"] == "compare",
        })
    return rows


def build_paired(qmap, uniq):
    """The with/without-tools arm, per answer.

    results/paired.json holds only summaries. The per-answer data is in
    results/tools_<model>.jsonl (the WITH-tools side); the WITHOUT side is the
    same model's unaided answer to the same question, already in build_answers.
    Pairing them here is what makes the RAG effect inspectable rather than a
    claim, so both sides are emitted with a shared question_id.
    """
    rows = []
    for f in sorted((ROOT / "results").glob("tools_*.jsonl")):
        model = f.name[len("tools_"):-len(".jsonl")]
        unaided = {}
        d = ROOT / "results" / f"raw_{model}"
        if d.exists():
            unaided = load_run(d, uniq)
        legacy = ROOT / "results" / "runs_opus5_full.json"
        if not unaided and model == "claude-opus-5" and legacy.exists():
            unaided = {r["id"]: r["answer"] for r in json.load(open(legacy))}

        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            qid = r["id"]
            if qid not in qmap:
                continue
            w = score_one(qmap[qid], r["answer"])
            rows.append({
                "model": model, "condition": "with_tools", "question_id": qid,
                "section": w["section"], "answer": r["answer"],
                "tool_calls": r.get("tool_calls"),
                "extracted_value": w["got"], "truth_value": w["expected"],
                "truth_unit": w["truth_unit"], "rel_error": w["rel_error"],
                "within_10pct": w["within_10pct"],
            })
            if qid in unaided:
                o = score_one(qmap[qid], unaided[qid])
                rows.append({
                    "model": model, "condition": "without_tools", "question_id": qid,
                    "section": o["section"], "answer": unaided[qid],
                    "tool_calls": 0,
                    "extracted_value": o["got"], "truth_value": o["expected"],
                    "truth_unit": o["truth_unit"], "rel_error": o["rel_error"],
                    "within_10pct": o["within_10pct"],
                })
    return rows


def main():
    q = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
    canary, banned = q["canary"], holdout_ids()
    uniq = question_order(); qmap = {x["id"]: x for x in uniq}
    print(f"building ({len(banned)} held-out ids excluded)")

    qr = build_questions(uniq, canary);      assert_no_holdout(qr, "id", banned)
    ar = build_answers(qmap, uniq);          assert_no_holdout(ar, "question_id", banned)
    pr = build_paired(qmap, uniq);                     assert_no_holdout(pr, "question_id", banned)
    rr = build_recommendations()
    dr = build_direct_probe()

    OUT.mkdir(parents=True, exist_ok=True)
    total = sum(write(n, r) for n, r in
                [("questions", qr), ("answers", ar), ("paired", pr),
                 ("recommendations", rr), ("direct_probe", dr)] if r)
    print(f"  {'total':16} {total:>5} rows")
    print("  held-out leak check: PASSED")


if __name__ == "__main__":
    main()
