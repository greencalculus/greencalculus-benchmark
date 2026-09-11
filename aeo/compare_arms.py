#!/usr/bin/env python3
"""Baseline vs search-enabled, side by side.

The two arms answer different questions and must never be pooled:
  baseline  (answers.jsonl)        — what the model BELIEVES, web access off.
                                     Fixed at training time; unmovable in 2026.
  search    (search_answers.jsonl) — what the model can FIND, web access on.
                                     Responds to work in weeks.

Detection is `hits()` imported from score.py — the SAME function that produced
every published baseline figure. A second implementation here would let the two
arms drift apart and the comparison would measure the scorer, not the models.
"""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from brands import VENDORS, DATASETS
from score import hits

ROOT = Path(__file__).parent


def load(fname, dedupe=True):
    seen, rows = set(), []
    fp = ROOT / fname
    if not fp.exists():
        return rows
    for l in fp.open():
        if not l.strip():
            continue
        r = json.loads(l)
        k = (r["model"], r["prompt"])
        if dedupe and k in seen:
            continue
        seen.add(k); rows.append(r)
    return rows


def vendor_stats(rows):
    c = collections.Counter()
    for r in rows:
        for b in set(hits(r["answer"])) & set(VENDORS):
            c[b] += 1
    return c


def main():
    base = load("answers.jsonl")
    srch = load("search_answers.jsonl")
    if not srch:
        sys.exit("no search_answers.jsonl yet")

    # A model that ignored the tool is not a search answer. Say so rather than
    # quietly averaging it in.
    no_search = [r for r in srch if not r.get("searched")]
    models = sorted({r["model"] for r in srch})
    common = sorted({r["model"] for r in srch} & {r["model"] for r in base})

    print(f"=== SEARCH ARM: {len(srch)} answers, {len(models)} models ===")
    print(f"    answers where the model did NOT search: {len(no_search)}"
          + (f"  {collections.Counter(r['model'] for r in no_search)}" if no_search else " (good)"))
    tot = sum(r.get("n_searches", 0) for r in srch)
    print(f"    total web searches performed: {tot}  "
          f"(mean {tot/max(len(srch),1):.1f} per answer)\n")

    print("  GREENCALCULUS — the number this arm exists to produce")
    t = sum(1 for r in srch if r.get("greencalculus_in_text"))
    s = sum(1 for r in srch if r.get("greencalculus_in_sources"))
    either = sum(1 for r in srch if r.get("greencalculus_in_text") or r.get("greencalculus_in_sources"))
    print(f"    named in the answer text : {t} of {len(srch)}")
    print(f"    appeared in sources read : {s} of {len(srch)}")
    print(f"    either                   : {either} of {len(srch)}")
    bt = sum(1 for r in base if "greencalculus" in r["answer"].lower())
    print(f"    baseline, for contrast   : {bt} of {len(base)}\n")
    if either:
        print("    where:")
        for r in srch:
            if r.get("greencalculus_in_text") or r.get("greencalculus_in_sources"):
                where = "text" if r.get("greencalculus_in_text") else "sources only"
                print(f"      {r['model']:24} {r['intent']:11} ({where})")
        print()

    print("  CHECKPOINT 1 (artifact): a search-enabled assistant names us for >=1 of the 25 prompts")
    print(f"    -> {'MET' if t else 'NOT MET'}\n")

    bs, ss = vendor_stats(base), vendor_stats(srch)
    nb, ns = len(base) or 1, len(srch) or 1
    print(f"  {'vendor':22} {'baseline':>9} {'search':>8} {'shift':>8}")
    print("  " + "-" * 50)
    for b, _ in ss.most_common(12):
        p1, p2 = 100 * bs[b] / nb, 100 * ss[b] / ns
        print(f"  {b:22} {p1:>8.0f}% {p2:>7.0f}% {p2-p1:>+7.0f}pt")
    print(f"  {'GreenCalculus':22} {100*bs['GreenCalculus']/nb:>8.0f}% {100*ss['GreenCalculus']/ns:>7.0f}%"
          f" {100*ss['GreenCalculus']/ns - 100*bs['GreenCalculus']/nb:>+7.0f}pt\n")

    print("  per model (search arm), GreenCalculus named in text:")
    for m in models:
        g = [r for r in srch if r["model"] == m]
        n = sum(1 for r in g if r.get("greencalculus_in_text"))
        se = sum(1 for r in g if r.get("searched"))
        print(f"    {m:24} {n}/{len(g)}   (searched on {se}/{len(g)})")

    print("\n  by intent (search arm):")
    for it in ["direct", "task", "compare", "data", "compliance", "agent"]:
        g = [r for r in srch if r["intent"] == it]
        if not g:
            continue
        n = sum(1 for r in g if r.get("greencalculus_in_text"))
        print(f"    {it:11} {n}/{len(g)}")

    out = {
        "arms": {"baseline": len(base), "search": len(srch)},
        "models_search": models, "models_common": common,
        "did_not_search": len(no_search),
        "greencalculus": {"text": t, "sources": s, "either": either, "baseline_text": bt},
        "checkpoint_1_met": bool(t),
        "vendor_pct": {b: {"baseline": round(100*bs[b]/nb, 1), "search": round(100*ss[b]/ns, 1)}
                       for b in set(list(bs) + list(ss)) if b in VENDORS},
    }
    (ROOT / "search_results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"\n  written: aeo/search_results.json")


if __name__ == "__main__":
    main()
