# Emission-factor accuracy benchmark

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22692277.svg)](https://doi.org/10.5281/zenodo.22692277)
[![questions](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgreencalculus%2Fgreencalculus-benchmark%2Fmain%2Fquestions.json&query=%24.n&label=questions&color=04BF62)](./questions.json)
[![data version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgreencalculus%2Fgreencalculus-benchmark%2Fmain%2Fquestions.json&query=%24.data_version&label=ground%20truth&color=04BF62)](https://verify.greencalculus.com)
[![findings](https://img.shields.io/badge/write--up-FINDINGS.md-04BF62)](./FINDINGS.md)
[![licence](https://img.shields.io/badge/licence-MIT-blue)](./LICENSE)

How wrong are language models when you ask them for an emission factor with no
tools — and, worse, how often do they name the wrong source for a number?

**467 questions, 45 sections, 75 publishers**, generated deterministically
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

> **The write-up lives at [greencalculus.com/guides/ai-emission-factors-accuracy](https://greencalculus.com/guides/ai-emission-factors-accuracy/)** —
> the findings, the caveats and a live factor lookup you can try. This repo is the
> evidence behind it: the questions, the answer key, every model's raw output, the
> scoring code and the harness, so anyone can re-run it and check us.
>
> Licence terms for all 137 sources: [emission-factor-licences](https://greencalculus.com/guides/emission-factor-licences/).

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

## A second study: who AI recommends

[`aeo/`](./aeo) is a separate measurement in the same spirit. The benchmark above
asks whether AI gets emission *factors* right. The AEO arm asks whether AI knows
who *sells* them: 25 buying prompts across six intents, put to the same five
models with no tools and no web access, 125 answers, every vendor mention counted.

Climatiq leads at 69% reach and 43% first-named, then ecoinvent (68%) and
EXIOBASE (58%); 93% of answers name one of those three. Public datasets outrank
every vendor — DEFRA and the US EPA at 83% each. **GreenCalculus, who ran the
study, was named in 0 of 125 answers**, one of only two tracked vendors never
named at all.

It also contains a direct probe: asked about GreenCalculus with explicit
permission to decline, every model that answered declined. Asked instead to
compare us to Climatiq, two of four invented a company profile. Write-up:
<https://greencalculus.com/guides/ai-recommended-carbon-data-providers/>

## Status

Everything above has been run. Nothing here is a projection.

- **All five models, all 467 questions, unaided** — Claude Opus 5, GPT-5.5,
  Gemini 3.1 Pro, Gemini 3.6 Flash, Grok 4.6. Raw replies are in
  [`results/`](./results), one directory per model, so any number in this README
  can be re-scored from the answers that produced it.
- **The paired tool run** — 90 questions, two models, with and without the two
  keyless lookup tools ([`results/paired.json`](./results/paired.json)).
- `build_questions.py` — generates `questions.json`. Run and verified.
- `score.py` — scoring and summary. Verified against 8 synthetic answers
  covering exact, close-but-wrong-source, confidently wrong, refusal, and a
  bare year (which must not be read as a value). Does unit reconciliation
  ([`units.py`](./units.py)) and unit-aware, range-aware extraction; validated
  against independent hand adjudication of the pilot — automated 46.9% vs
  hand-read ~47%.

Two bugs found in our own harness, both fixed, both worth knowing about:

- A refusal that name-drops a publisher ("consult the DEFRA tables") was
  counting as a correct citation. Citations now only count on answers that
  actually gave a number.
- `questions.json` was published with 6 duplicate rows — the section listing
  the API serves can repeat a key, and the generator's dedup arrived one commit
  after the file. Scoring keys on the factor key, so the duplicates always
  collapsed and no published result changes; the file now says 467 like
  everything else. Six more, all in unit handling, are logged in
  [FINDINGS.md](./FINDINGS.md).

## Run

```bash
python3 build_questions.py                   # regenerate the set
python3 score.py runs.json questions.json    # score a model's answers
```

`runs.json` is `[{"id": "<factor key>", "answer": "<the model's raw reply>"}]` —
so any model or harness can produce it.

## Citing this benchmark

Archived on Zenodo. The **concept DOI** always resolves to the latest version;
cite the versioned DOI if you need the exact snapshot you ran against.

- Concept DOI (latest): [10.5281/zenodo.22692277](https://doi.org/10.5281/zenodo.22692277)
- Version 1.0.0 (10 Sep 2026): [10.5281/zenodo.22692278](https://doi.org/10.5281/zenodo.22692278)

> Say, J. (2026). *GreenCalculus Emission-Factor Accuracy Benchmark (with the AI
> vendor-recommendation study)* (Version 1.0.0) [Data set]. Zenodo.
> https://doi.org/10.5281/zenodo.22692278

Machine-readable metadata is in [`CITATION.cff`](./CITATION.cff).
