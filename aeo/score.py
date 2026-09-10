#!/usr/bin/env python3
"""Score the AI recommendation study.

Three things are measured:
  presence    — was the brand named at all, in how many answers
  primacy     — when named, how early (first brand named is what a reader acts on)
  share       — mentions as a share of all vendor mentions
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from brands import BRANDS, VENDORS, DATASETS

ROOT = Path(__file__).parent

def hits(text):
    """-> {brand: first character offset}, so order of appearance is recoverable."""
    t = text.lower()
    out = {}
    for brand, pats in BRANDS.items():
        pos = min((m.start() for p in pats for m in re.finditer(p, t)), default=None)
        if pos is not None:
            out[brand] = pos
    return out

def main():
    # Two runners wrote two files and overlap on some models — dedupe on
    # (model, prompt), first write wins.
    seen, rows = set(), []
    for f in ("answers.jsonl", "answers2.jsonl"):
        fp = ROOT / f
        if not fp.exists():
            continue
        for l in fp.open():
            if not l.strip():
                continue
            r = json.loads(l)
            k = (r["model"], r["prompt"])
            if k in seen:
                continue
            seen.add(k)
            rows.append(r)
    if not rows:
        sys.exit("no answers")
    models = sorted({r["model"] for r in rows})
    n_ans = len(rows)

    present = collections.Counter()      # answers naming the brand
    first   = collections.Counter()      # answers where it is the FIRST vendor named
    mentions_by_model = collections.defaultdict(collections.Counter)
    by_intent = collections.defaultdict(collections.Counter)
    intent_totals = collections.Counter()
    gc_urls = 0

    for r in rows:
        h = hits(r["answer"])
        vend = {b: p for b, p in h.items() if b in VENDORS}
        for b in h:
            present[b] += 1
            mentions_by_model[r["model"]][b] += 1
            by_intent[r["intent"]][b] += 1
        intent_totals[r["intent"]] += 1
        if vend:
            first[min(vend, key=vend.get)] += 1
        if "greencalculus.com" in r["answer"].lower():
            gc_urls += 1

    tot_vendor_mentions = sum(present[b] for b in VENDORS) or 1
    print(f"=== {n_ans} answers · {len(models)} models · {len(set(r['prompt'] for r in rows))} prompts ===\n")
    print(f"  {'vendor':22} {'answers naming it':>18} {'% of answers':>13} {'named FIRST':>12} {'share of voice':>15}")
    print("  " + "-"*84)
    for b, c in present.most_common():
        if b not in VENDORS: continue
        print(f"  {b:22} {c:>18} {100*c/n_ans:>12.0f}% {first[b]:>12} {100*c/tot_vendor_mentions:>14.1f}%")

    print(f"\n  GreenCalculus named in {present['GreenCalculus']} of {n_ans} answers"
          f" ({100*present['GreenCalculus']/n_ans:.0f}%); greencalculus.com URL in {gc_urls}.")

    print("\n  Public datasets cited (not vendors):")
    for b, c in present.most_common():
        if b in DATASETS:
            print(f"    {b[1:]:20} {c:>4} answers ({100*c/n_ans:.0f}%)")

    print("\n  By model — top 3 vendors named:")
    for m in models:
        top = ", ".join(f"{b} {c}" for b, c in mentions_by_model[m].most_common() if b in VENDORS)
        gcc = mentions_by_model[m]["GreenCalculus"]
        print(f"    {m:24} GC={gcc:<3} | {top[:88]}")

    print("\n  By intent — is GreenCalculus named anywhere?")
    for it, tot in intent_totals.most_common():
        gcc = by_intent[it]["GreenCalculus"]
        lead = by_intent[it].most_common()
        lead = next((b for b, _ in lead if b in VENDORS), "—")
        print(f"    {it:12} {gcc}/{tot} answers   most-named there: {lead}")

    json.dump({"answers": n_ans, "present": dict(present), "first": dict(first),
               "gc_urls": gc_urls}, (ROOT / "results.json").open("w"), indent=1)

if __name__ == "__main__":
    main()
