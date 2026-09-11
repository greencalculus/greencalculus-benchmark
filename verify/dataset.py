#!/usr/bin/env python3
"""One way to read the benchmark dataset, used by every figure script.

hf/data/ is gitignored -- generated, not source -- so a clean checkout has none
of it, and `hf/build.py` cannot fill the gap on CI: it refuses to run without
the private held-out set, because its job is to guarantee an upload carries no
held-out question. That guard protects the most valuable thing in the repo and
must not be relaxed to make a test pass.

So this falls back to calling the same builders in memory. Nothing is written,
only the public results are read, and the scored columns still come from
`score.score_one` -- never a second implementation of the scorer.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "hf", "data")

_MEMO = {}


def load(config):
    """The published dataset if it is on disk, otherwise the same rows built in
    memory from committed results.

    hf/data/ is gitignored, so a clean checkout has none of it. `hf/build.py`
    cannot fill the gap on CI either, and deliberately: it refuses to run
    without the private held-out set, because its job is to guarantee an upload
    carries no held-out question. That guard protects the most valuable thing in
    the repo and must not be relaxed to make a test pass.

    So the figures fall back to calling the same builders directly. Nothing is
    written, only the public results are read, and the scored columns still come
    from `score.score_one` — never a second implementation of the scorer."""
    path = os.path.join(DATA, config, "train.jsonl")
    if os.path.exists(path):
        with open(path) as fh:
            return [json.loads(line) for line in fh]

    if config in _MEMO:
        return _MEMO[config]
    sys.path.insert(0, os.path.join(ROOT, "hf"))
    import build as hf_build

    q = json.loads(open(os.path.join(ROOT, "questions.json"), encoding="utf-8").read())
    uniq = hf_build.question_order()          # ordered, as the runners batched them
    qmap = {x["id"]: x for x in uniq}
    builders = {
        "questions": lambda: hf_build.build_questions(uniq, q["canary"]),
        "answers": lambda: hf_build.build_answers(qmap, uniq),
        "paired": lambda: hf_build.build_paired(qmap, uniq),
        "recommendations": hf_build.build_recommendations,
        "direct_probe": hf_build.build_direct_probe,
    }
    if config not in builders:
        raise SystemExit(f"no in-memory builder for config {config!r}")
    _MEMO[config] = builders[config]()
    return _MEMO[config]


