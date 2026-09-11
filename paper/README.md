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
| Corpus-size correlation | recomputed against live canonical row counts |
| Category and publisher accuracy | `hf/data/answers/` pooled over 3 models |

**One correction this surfaced.** The published guide states the corpus-size
correlation as *r* = −0.12. It does not reproduce: under every specification
tried (3 or 5 models, ≥1/≥5/≥9 scored answers, canonical row counts) the
coefficient falls between **−0.25 and −0.34**. The guide's worked examples *do*
reproduce exactly (3 rows → 55.6%, 1,424 rows → 50.7%), so the error is in the
coefficient alone. The paper reports −0.28 with its range and notes that at
*n* = 24 nothing here reaches significance — which is why the conclusion (size
does not explain the spread) is unchanged. **The guide should be corrected.**
