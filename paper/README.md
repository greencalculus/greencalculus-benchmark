# Paper — *Right Source, Wrong Number*

A 4-page workshop paper on the emission-factor accuracy benchmark, written for
two destinations:

- **arXiv** (`cs.CL`, cross-list `cs.LG`) — needs an endorsement; see below.
- **Climate Change AI** workshops (Papers track, 4 pages, dataset submissions
  explicitly welcome). The NeurIPS 2026 deadline was 29 Aug 2026 and has passed;
  the next is the ICLR 2027 workshop.

## Compiling

There is no LaTeX on the build machine. `main.tex` is deliberately
**self-contained** — `article` class, no external `.sty` — so it compiles
unmodified on Overleaf or arXiv:

1. Open [overleaf.com](https://www.overleaf.com), New Project → Upload Project → `main.tex`
2. Compile. It should land at 4 pages.

For a CCAI submission, swap `\documentclass` for their template and delete the
`geometry`/`titlespacing` block.

## arXiv endorsement

First-time `cs.*` submitters need an endorsement from an established arXiv
author, and **since 21 January 2026 an institutional email address no longer
grants it automatically**. The Climate Change AI community platform is the
obvious place to ask — everyone there publishes in exactly these categories.

## Every figure is reproducible

No number in the paper is quoted from a previous write-up. Each was recomputed
from the published data on 11 September 2026:

| Claim | Source |
|---|---|
| Accuracy, citation rates, right-source-wrong-number | `compare.py` over `results/` |
| Paired arm (37.1→98.7, 50.0→100.0) | `results/paired.json` + `hf/data/paired/` |
| Corpus-size correlation | `paper/corpus_size.py` over `hf/data/` + `paper/sources.tsv` |
| Category and publisher accuracy | `hf/data/answers/` pooled over 3 models |

**One correction this surfaced, now shipped.** The guide published the
corpus-size correlation as *r* = −0.12 and called it "essentially no
relationship". Neither half held. Under the pre-registered specification the
coefficient is **−0.274** (*n* = 24, *p* = 0.195), which is a weak relationship
rather than an absent one, so the sentence had to change with the number: it now
states the coefficient, the *n* and the non-significance instead of
characterising the strength. The guide was corrected on 2026-09-11, with a
changelog entry and the specification pinned in its engineering record.

The root cause was that the specification lived in a session rather than in the
repository, so nobody could check it. `corpus_size.py` and `sources.tsv` beside
this file fix that — `python3 paper/corpus_size.py` prints the coefficient, the
*p* value and all 24 publishers, and `--sensitivity` runs the 48-specification
sweep the paper cites. Run it before quoting the number anywhere.

Two things the recomputation caught beyond the coefficient:

- The draft's robustness claim was wrong. It said the coefficient "ranges from
  −0.25 to −0.34" and that none of those reaches *p* < .05. The actual sweep
  gives −0.11 to −0.42, and **16 of 48 specifications do reach *p* < .05** —
  14 of them at the loosest threshold, where a publisher with one scored answer
  enters at 0% or 100%. The paper now claims a stable sign and an unstable
  significance, which is what the data supports.
- Neither corpus-size basis reproduces −0.28: canonical deduplicated rows give
  −0.274, raw listing rows −0.249. The paper and the guide both now carry −0.27.

The guide's worked examples were correct throughout and all four reproduce
exactly under the pinned specification — 3 rows 55.6%, 19 rows 96.3%, 1,424 rows
50.7%, 2,451 rows 17.4% — which is how the fault was localised to the
coefficient alone.
