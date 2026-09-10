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

## Result — five models, 467 questions, no tools

| Model | Answered | Right *when it answered* | Right *of all 467* | Right source, wrong number |
|---|---:|---:|---:|---:|
| Gemini 3.1 Pro | 77 | **65.2%** | 6.4% | 35.3% |
| Grok 4.6 | 144 | 62.1% | 8.8% | 31.6% |
| GPT-5.5 | 326 | 58.2% | **31.9%** | 41.0% |
| Claude Opus 5 | 430 | 45.7% | 30.8% | 54.1% |
| Gemini 3.6 Flash | 404 | 41.9% | 28.3% | 58.8% |

Those middle columns rank in opposite orders. **The more a model answers, the
less each answer is worth** — the last column sorts with talkativeness.

One vendor, two tiers, no cross-vendor argument: **Gemini Pro answers 77
questions at 65.2%; Gemini Flash answers 404 at 41.9%** — and the fast tier, the
one that actually gets deployed behind a production pipeline, is wrong about the
number more often than not even when it names the right publisher.

## …and connecting GreenCalculus fixes it

90 questions, paired, same model with and without two keyless lookup tools:

| | Without tools | With GreenCalculus |
|---|---|---|
| Claude Opus 5 — within 10% | 37.1% | **98.7%** |
| Claude Opus 5 — off by >50% | 25.8% | **1.3%** |
| GPT-5.5 — within 10% | 50.0% | **100.0%** |
| GPT-5.5 — off by >50% | 19.6% | **0.0%** |

About **+61 points** for both, at 1.0–1.6 tool calls per question. The model is
not handed the answer — it searches, picks the factor and reads the value, so
this measures the integration, not a rigged prompt.

Full write-up, caveats, and the log of the scorer's own six bugs:
**[FINDINGS.md](./FINDINGS.md)**.

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
