#!/usr/bin/env python3
"""Assemble results/raw/b*.txt into one runs file, validating against the question set."""
import json, re, sys
from pathlib import Path

root = Path(__file__).parent
qs = {q["id"]: q for q in json.load(open(root / "questions.json"))["questions"]}
runs, problems = [], []
seen = set()

for f in sorted((root / "results" / "raw").glob("b*.txt")):
    batch_ids = [m.group(1) for m in
                 re.finditer(r"^\d+\.\s*\[([^\]]+)\]", (root / "prompts" / "full" / f.name).read_text(), re.M)]
    lines = [l for l in f.read_text().splitlines() if l.strip()]
    parsed = []
    for line in lines:
        m = re.match(r"\s*\[([^\]]+)\]\s*(.+)", line)
        if m:
            parsed.append((m.group(1).strip(), m.group(2).strip()))
    if len(parsed) != len(batch_ids):
        problems.append(f"{f.name}: {len(parsed)} answers vs {len(batch_ids)} questions")
    for i, (rid, ans) in enumerate(parsed):
        # trust position over the id the model echoed back
        true_id = batch_ids[i] if i < len(batch_ids) else rid
        if rid != true_id:
            problems.append(f"{f.name} line {i+1}: id '{rid}' != expected '{true_id}' (using position)")
        if true_id not in qs:
            problems.append(f"{f.name} line {i+1}: unknown id {true_id}")
            continue
        if true_id in seen:
            problems.append(f"{f.name} line {i+1}: duplicate {true_id}")
            continue
        seen.add(true_id)
        runs.append({"id": true_id, "answer": ans})

out = root / "results" / "runs_opus5_full.json"
json.dump(runs, open(out, "w"), indent=1, ensure_ascii=False)
print(f"assembled {len(runs)} answers -> {out.name}")
print(f"question set: {len(qs)}   covered: {len(seen)}   missing: {len(set(qs)-seen)}")
if problems:
    print(f"\n{len(problems)} problems:")
    for p in problems[:25]:
        print("  ", p)
