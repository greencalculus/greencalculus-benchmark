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

## Result — Claude Opus 5, 467 questions, unaided

**46.3% within 10%** of the sourced value. It named a source 75% of the time and
named the *right* one 90% of those — **but 55% of the correctly-attributed
answers carried a wrong number.** It is best on textbook fuel factors (92%) and
worst on anything jurisdiction-specific or recent (food PCF 8%, NGFS 9%).

Full write-up, exemplars, and the evidence that the scorer itself is sound:
**[FINDINGS.md](./FINDINGS.md)**. Earlier 45-question pilot:
[FINDINGS-pilot.md](./FINDINGS-pilot.md).

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
