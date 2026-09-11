# The claims gate

One rule:

> **A number does not go into published prose unless a committed script prints it.**

## Why this exists

On 10 September 2026 the guide *Where AI Is Reliable on Emission Factors*
published the corpus-size correlation as **r = −0.12**, described as
"essentially no relationship". It was wrong — the value is −0.28 — and, worse,
it was *unfalsifiable*: the specification behind it (which models, which answers
count, which threshold) lived in a working session and was never written down.
Nobody could check it, including us.

The correction then hit the same fault a second time. The first attempt
published −0.27, because "scoreable" was reconstructed from the data's flags
instead of read from `score.py`. The reconstruction is close but not identical,
and the gap moves the second decimal. This gate caught that within the hour.

The lesson is not "be more careful". It is that a figure whose recipe is not in
the repository cannot be checked by anyone, so it will eventually be wrong and
nobody will notice.

## The two scripts

| Script | What it does |
|---|---|
| `figures.py` | Recomputes every published figure from `hf/data/`, `results/` and `paper/sources.tsv`. `--check-fresh` re-runs the scorers and fails if a committed output has drifted from the script that made it. |
| `check_claims.py` | Extracts every numeric claim from the four study pages, the preprint, the dataset card and `FINDINGS.md`, and fails if any of them is neither reproduced by `figures.py` nor justified in `allowlist.json`. |

```sh
python3 verify/figures.py                 # all figures
python3 verify/figures.py --check-fresh   # committed outputs are not stale
python3 verify/check_claims.py            # includes the live pages over HTTP
python3 verify/check_claims.py --offline  # local files only
```

## Before publishing any number, anywhere

1. Make the script that produces it, or add it to `figures.py`.
2. Run `python3 verify/check_claims.py`. It must pass.
3. Only then write the sentence.

If a figure genuinely cannot be derived — a hand adjudication, a figure quoted
from someone else's pricing page, a historical value from an earlier scorer
version — it goes in `allowlist.json` **with a written reason**. "It is correct"
is not a reason. Every allowlist entry is a surface we cannot verify
automatically, which is a debt rather than a resolution.

## Known debt

- **The licence audit is not reproducible from this repository.** Its 137-source
  review lives in the `gc-sources` store, so the gate cannot check any of its
  numbers. They are trusted, not verified. Closing this is the next piece of work.
- **`FINDINGS.md` spans several scorer versions.** Its historical figures are
  allowlisted individually and marked as historical.

## For the search-enabled runs

The re-runs on 14 September and 6 October produce new figures. They follow the
same rule: the scorer output gets committed, `figures.py` gains the new family,
and no number from either run appears in a post, a guide or a thread until
`check_claims.py` passes with the new page in its surface list.
