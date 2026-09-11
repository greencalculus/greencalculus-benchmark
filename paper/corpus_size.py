#!/usr/bin/env python3
"""Recompute the corpus-size correlation reported in the paper and in guide 9327.

The published figure was once wrong and could not be reproduced, because the
specification lived in a session rather than in the repository. It lives here now.

  python3 paper/corpus_size.py                 # the pre-registered specification
  python3 paper/corpus_size.py --sensitivity   # all 48 pool x threshold variants

Corpus sizes come from sources.tsv beside this file: canonical (deduplicated) row
counts per source_id. Releases 2026.188 and 2026.189 added and removed no rows, so
these equal the counts at the benchmark's pinned data version 2026.187.
"""
import argparse, collections, itertools, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The pre-registered specification.
POOL = ("claude-opus-5", "gpt-5.5", "gemini-3.6-flash")
THRESHOLD = 9          # minimum scored answers for a publisher to enter
METRIC = "within_10pct"


def scoreable(a):
    """The canonical definition, from score.py: an answer is scoreable exactly
    when a relative error could be computed for it. Do not re-derive this from
    the answered/declined/unscoreable flags -- that combination is close but not
    identical, and the difference moves the coefficient."""
    return a["rel_error"] is not None


def load():
    """Answers, questions and corpus sizes. The dataset comes through
    verify/dataset.py so this works on a clean checkout, where hf/data/ is
    absent because it is generated rather than committed."""
    sys.path.insert(0, os.path.join(ROOT, "verify"))
    from dataset import load as load_config

    answers = load_config("answers")
    questions = {q["id"]: q for q in load_config("questions")}
    sizes = {}
    for line in open(os.path.join(HERE, "sources.tsv")):
        if "\t" not in line:
            continue
        source_id, rows = line.rstrip("\n").split("\t")
        sizes[source_id] = int(rows)
    return answers, questions, sizes


def accuracy_by_publisher(answers, questions, pool):
    agg = collections.defaultdict(lambda: [0, 0])
    for a in answers:
        if a["model"] not in pool or not scoreable(a):
            continue
        source_id = questions[a["question_id"]]["source_id"]
        agg[source_id][1] += 1
        if a[METRIC]:
            agg[source_id][0] += 1
    return agg


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def two_sided_p(r, n):
    """p for Pearson r via the t distribution, regularised incomplete beta."""
    df = n - 2
    t = abs(r) * math.sqrt(df / (1 - r * r))
    x = df / (df + t * t)
    a, b = df / 2.0, 0.5

    def betacf(a, b, x):
        c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        h = d
        for m in range(1, 400):
            m2 = 2 * m
            aa = m * (b - m) * x / ((a - 1.0 + m2) * (a + m2))
            d = 1.0 / (1.0 + aa * d); c = 1.0 + aa / c; h *= d * c
            aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + 1.0 + m2))
            d = 1.0 / (1.0 + aa * d); c = 1.0 + aa / c
            step = d * c; h *= step
            if abs(step - 1.0) < 3e-16:
                break
        return h

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    if x < (a + 1) / (a + b + 2):
        return math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a * betacf(a, b, x)
    return 1.0 - math.exp(math.log(1 - x) * b + math.log(x) * a - lbeta) / b * betacf(b, a, 1 - x)


def points(agg, sizes, threshold):
    return [(sizes[s], hit / total) for s, (hit, total) in agg.items()
            if total >= threshold and s in sizes]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensitivity", action="store_true",
                    help="sweep model pool and threshold, scoring rule held fixed")
    args = ap.parse_args()
    answers, questions, sizes = load()

    agg = accuracy_by_publisher(answers, questions, POOL)
    pts = sorted(points(agg, sizes, THRESHOLD))
    r = pearson([p[0] for p in pts], [p[1] for p in pts])
    p = two_sided_p(r, len(pts))

    print(f"pre-registered specification: {len(POOL)} models, >= {THRESHOLD} scored answers")
    print(f"  n = {len(pts)}   r = {r:+.4f}   p = {p:.4f}")
    print(f"  reported as r = {r:+.2f}, p = {p:.2f}\n")
    print("  rows   accuracy   n    publisher")
    for size, acc in pts:
        source_id = next(s for s, (h, t) in agg.items()
                         if s in sizes and sizes[s] == size and t >= THRESHOLD and abs(h / t - acc) < 1e-12)
        print(f"  {size:>5}   {acc * 100:>6.1f}%   {agg[source_id][1]:<4} {source_id}")

    if not args.sensitivity:
        return

    models = ["claude-opus-5", "gpt-5.5", "grok-4.6",
              "gemini-3.1-pro-preview", "gemini-3.6-flash"]
    rows, significant = [], 0
    for k in (3, 4, 5):
        for pool in itertools.combinations(models, k):
            a2 = accuracy_by_publisher(answers, questions, set(pool))
            for threshold in (1, 5, 9):
                pts2 = points(a2, sizes, threshold)
                if len(pts2) < 5:
                    continue
                r2 = pearson([q[0] for q in pts2], [q[1] for q in pts2])
                p2 = two_sided_p(r2, len(pts2))
                rows.append((r2, p2, threshold))
                significant += p2 < 0.05
    rs = [x[0] for x in rows]
    print(f"\nsensitivity: {len(rows)} specifications, scoring rule held fixed")
    print(f"  r from {min(rs):+.3f} to {max(rs):+.3f}; all negative: {all(x < 0 for x in rs)}")
    print(f"  reaching p < .05: {significant}")
    for threshold in (1, 5, 9):
        sub = [x for x in rows if x[2] == threshold]
        print(f"    threshold >= {threshold}: {sum(1 for x in sub if x[1] < 0.05)} of {len(sub)} significant")


if __name__ == "__main__":
    main()
