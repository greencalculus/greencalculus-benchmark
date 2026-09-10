#!/usr/bin/env python3
"""Score every model run in results/ and print the comparison.

Each results/raw_<model>/ directory is one model's answers; batch files map to
questions by position, exactly as assemble.py does for the Claude run, so no
model gets a different parsing path.
"""
import json, re, sys
from pathlib import Path
from score import score_one, summarise

ROOT = Path(__file__).parent
BATCH = 30


def question_order():
    qs = json.load(open(ROOT / "questions.json"))["questions"]
    seen, uniq = set(), []
    for q in qs:
        if q["id"] not in seen:
            seen.add(q["id"]); uniq.append(q)
    return uniq


def load_run(d, uniq):
    """Map answers to questions by batch position — never by the id the model echoed."""
    by_id = {}
    for f in sorted(d.glob("b*.txt")):
        n = int(re.search(r"b(\d+)", f.name).group(1))
        expected = uniq[(n - 1) * BATCH:n * BATCH]
        blocks = re.findall(r"^\s*(?:\d+[.)]\s*)?\[([^\]]+)\]\s*(.+?)\s*$", f.read_text(encoding="utf-8"), re.M)
        for i, (_echoed, ans) in enumerate(blocks):
            if i < len(expected):
                by_id.setdefault(expected[i]["id"], ans)
    return by_id


def main():
    uniq = question_order()
    qmap = {q["id"]: q for q in uniq}
    runs = {}

    for d in sorted(ROOT.glob("results/raw_*")):
        runs[d.name.replace("raw_", "")] = load_run(d, uniq)
    legacy = ROOT / "results" / "runs_opus5_full.json"
    if legacy.exists():
        runs["claude-opus-5"] = {r["id"]: r["answer"] for r in json.load(open(legacy))}

    if not runs:
        sys.exit("no runs found")

    out = {}
    for model, answers in sorted(runs.items()):
        scored = [score_one(qmap[i], a) for i, a in answers.items() if i in qmap]
        out[model] = {"summary": summarise(scored), "n_answers": len(answers)}

    hdr = f"{'model':26} {'asked':>6} {'scored':>7} {'≤10%':>7} {'≤50%':>7} {'>50% off':>9} {'cited':>7} {'src ok':>7} {'RIGHT SRC/WRONG №':>18}"
    print(hdr); print("-" * len(hdr))
    for m, r in sorted(out.items(), key=lambda kv: -(kv[1]["summary"].get("within_10pct") or 0)):
        s = r["summary"]
        print(f"{m:26} {s['n']:>6} {s['scoreable']:>7} {s['within_10pct']:>6.1f}% "
              f"{s['within_50pct']:>6.1f}% {s['confidently_wrong']:>8.1f}% "
              f"{s['cited_a_source']:>6.1f}% {(s['citation_correct_of_cited'] or 0):>6.1f}% "
              f"{s['right_source_wrong_number']:>17.1f}%")
    json.dump(out, open(ROOT / "results" / "comparison.json", "w"), indent=1)
    print(f"\nwritten: results/comparison.json")


if __name__ == "__main__":
    main()
