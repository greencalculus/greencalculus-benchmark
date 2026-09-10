#!/usr/bin/env python3
"""Compare a model with GreenCalculus tools against the same model without them,
on exactly the same questions. Paired, so nothing hinges on sampling."""
import json
from pathlib import Path
from compare import question_order, load_run
from score import score_one

ROOT = Path(__file__).parent


def main():
    uniq = question_order()
    qmap = {q["id"]: q for q in uniq}

    no_tools = {}
    for d in sorted(ROOT.glob("results/raw_*")):
        no_tools[d.name.replace("raw_", "")] = load_run(d, uniq)
    legacy = ROOT / "results" / "runs_opus5_full.json"
    if legacy.exists():
        no_tools["claude-opus-5"] = {r["id"]: r["answer"] for r in json.load(open(legacy))}

    rows = []
    for f in sorted(ROOT.glob("results/tools_*.jsonl")):
        model = f.name[len("tools_"):-len(".jsonl")]
        with_tools = {}
        calls = []
        for line in f.open():
            if not line.strip():
                continue
            r = json.loads(line)
            with_tools[r["id"]] = r["answer"]
            calls.append(r.get("tool_calls", 0))
        base = no_tools.get(model, {})
        ids = [i for i in with_tools if i in base and i in qmap]
        if not ids:
            continue

        def tally(src):
            sc = [score_one(qmap[i], src[i]) for i in ids]
            scoreable = [s for s in sc if s["rel_error"] is not None]
            n = len(scoreable) or 1
            return {
                "answered": sum(1 for s in sc if s["answered"]),
                "scoreable": len(scoreable),
                "within10": round(100 * sum(1 for s in scoreable if s["within_10pct"]) / n, 1),
                "correct_of_all": round(100 * sum(1 for s in sc if s["within_10pct"]) / len(ids), 1),
                "wrong50": round(100 * sum(1 for s in scoreable if not s["within_50pct"]) / n, 1),
            }

        a, b = tally(base), tally(with_tools)
        rows.append((model, len(ids), sum(calls) / len(calls), a, b))

    print(f"{'model':18} {'paired':>7} {'tool/q':>7} | {'WITHOUT TOOLS':>26} | {'WITH GREENCALCULUS':>26}")
    print(f"{'':18} {'':>7} {'':>7} | {'answered':>9}{'≤10%':>8}{'>50% off':>9} | {'answered':>9}{'≤10%':>8}{'>50% off':>9}")
    print("-" * 96)
    for m, n, tc, a, b in rows:
        print(f"{m:18} {n:>7} {tc:>7.1f} | {a['answered']:>9}{a['within10']:>7.1f}%{a['wrong50']:>8.1f}% "
              f"| {b['answered']:>9}{b['within10']:>7.1f}%{b['wrong50']:>8.1f}%")
    print()
    for m, n, tc, a, b in rows:
        print(f"  {m}: correct on {a['correct_of_all']}% of {n} questions without tools "
              f"-> {b['correct_of_all']}% with GreenCalculus "
              f"({'+' if b['correct_of_all']>=a['correct_of_all'] else ''}{round(b['correct_of_all']-a['correct_of_all'],1)} pts)")
    json.dump([{"model": m, "paired_n": n, "avg_tool_calls": round(tc, 2),
                "without": a, "with": b} for m, n, tc, a, b in rows],
              open(ROOT / "results" / "paired.json", "w"), indent=1)


if __name__ == "__main__":
    main()
