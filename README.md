# Emission-factor accuracy benchmark

How wrong are language models when you ask them for an emission factor with no
tools — and, worse, how often do they name the wrong source for a number?

**473 questions, 45 sections, 75 publishers**, generated deterministically
(seed 20260910) from data version 2026.187. Only factors we may republish are
used, so the answer key ships with the benchmark.

Questions are phrased the way a practitioner asks, not as canonical keys:

> What is the greenhouse-gas emission factor for UK grid electricity —
> location-based, per kWh?

## What is measured

| Metric | Why it matters |
|---|---|
| `answered` / `declined` | does it give a number at all |
| `within_10pct` | is the number right |
| `cited` | did it name a publisher |
| `citation_correct` | **is the source it named the source the number comes from** |
| `confidently_wrong` | gave a number, off by >50%, no hedge |

The fourth row is the story. A model that cites DEFRA for an EPA figure is more
dangerous than one that cites nothing, because the citation is what makes a
reader stop checking.

## Pilot result

Claude Opus 5, unaided, 45 questions, 0 tool uses: **47.2% within 10%** of the
sourced value (of 36 scoreable; 8 had units too ambiguous to reconcile and are
excluded rather than counted wrong). 84% named a source and 90% of those named
the right one — but **when it named the right source, the number was still wrong
51.7% of the time.** See [FINDINGS-pilot.md](./FINDINGS-pilot.md).

## Status

- `build_questions.py` — generates `questions.json`. **Run and verified.**
- `score.py` — scoring and summary. **Verified against 8 synthetic answers**
  covering exact, close-but-wrong-source, confidently wrong, refusal, and a
  bare year (which must not be read as a value).
- **Pilot run** against Claude Opus 5 (45 of 473 questions) — see above.
- **Not yet run against other vendors.** GPT/Gemini need API keys and spend money.
- **`score.py` now does unit reconciliation** ([`units.py`](./units.py)) and
  unit-aware, range-aware extraction. Validated against independent hand
  adjudication of the pilot: automated 47.2% vs hand-read ~47%.

A known scoring bias was found and fixed during development: a refusal that
name-drops a publisher ("consult the DEFRA tables") was counting as a correct
citation. Citations now only count on answers that actually gave a number.

## Run

```bash
python3 build_questions.py                   # regenerate the set
python3 score.py runs.json questions.json    # score a model's answers
```

`runs.json` is `[{"id": "<factor key>", "answer": "<the model's raw reply>"}]` —
so any model or harness can produce it.
