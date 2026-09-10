# How wrong are LLMs about emission factors?

467 questions drawn from the GreenCalculus corpus (data version 2026.187),
covering 45 sections and 75 publishers. Every model was asked the same questions
in the same wording, in batches of 30, with no tools and no lookups. Run
2026-09-10.

## Two numbers, and you need both

**When it answers, is it right?**

| Model | Scoreable | Within 10% | Within 50% | Off by >50% |
|---|---:|---:|---:|---:|
| Grok 4.6 | 84 | **66.7%** | 88.1% | 11.9% |
| Claude Opus 5 | 342 | 45.9% | 78.7% | 21.3% |
| Gemini 3.6 Flash | 306 | 43.5% | 78.4% | 21.6% |

**Of all 467 asked, how many did it actually get right?**

| Model | Answered | Refused | Correct | Correct of all 467 |
|---|---:|---:|---:|---:|
| Claude Opus 5 | 456 | 11 | 157 | **33.6%** |
| Gemini 3.6 Flash | 436 | 31 | 133 | 28.5% |
| Grok 4.6 | 150 | **317** | 56 | 12.0% |

The tables rank in opposite orders, and that is the finding. Quote either alone
and you have misled someone.

## The real story is calibration, not accuracy

**Grok 4.6 refused 317 of 467 questions** — more than two in three, usually with
a flat "I don't know this factor." When it did answer it was right two-thirds of
the time, the best rate here by a wide margin. It is not the most knowledgeable
model in this test. It is the most *honest about the edge of its knowledge*.

**Claude Opus 5 refused 11 times out of 467.** It answers essentially everything,
which is why it gets the most questions right in absolute terms — and also why it
produces by far the most confidently wrong numbers.

For carbon accounting that trade is not neutral. A refusal costs you a lookup. A
confident wrong number costs you a misstated disclosure.

## The dangerous combination

| Model | Named a source | Named the *right* source | **Right source, wrong number** |
|---|---:|---:|---:|
| Gemini 3.6 Flash | 76.9% | 91.9% | **58.2%** |
| Claude Opus 5 | 75.2% | 90.0% | **55.2%** |
| Grok 4.6 | 22.1% | 82.5% | **29.8%** |

All three attribute well — around 90% of the time they name the publisher the
number really comes from. And for the two talkative models, **the majority of
those correctly-attributed answers still carry a wrong number.**

That is the failure mode worth naming. A wrong figure with no source gets caught,
because nobody can cite it. A wrong figure under the right publisher's name looks
exactly like diligence, and goes into the report.

Grok's much lower rate is mostly a consequence of refusing: it cites rarely
because it answers rarely.

## It knows the famous numbers and invents the rest

Claude Opus 5 by section, where at least 8 questions were scoreable:

| | Section | Within 10% |
|---|---|---:|
| Best | fuels | 92% |
| | fuel_properties | 91% |
| | mobile_combustion | 83% |
| Worst | cbam | 18% |
| | ev_charging | 17% |
| | ngfs_scenarios | 9% |
| | food_pcf | 8% |

Diesel per gallon is in every textbook and it gets it right. A CBAM country
default, an NGFS scenario cell, an AGRIBALYSE product line — jurisdiction-specific
or recently published — it fabricates in the same tone.

## One clean case

> **R-290 (propane), per kg leaked.** Claude Opus 5: *"3 kgCO2e per kg leaked —
> GWP100 = 3 under IPCC AR5. This is the value DEFRA publishes."*
> Truth: **0.02**, IPCC AR6 WGI Ch 7 Table 7.SM.7.

150x too high, credited to a publisher that does not publish it, no hedge. AR6
revised short-lived hydrocarbon GWPs down by two orders of magnitude.

## Is the scorer trustworthy?

It was wrong first, twice, and both are documented because the correction matters
more than the headline.

- **It compared numbers, not quantities.** The first version reported 35.6% and
  scored a *correct* answer of 63 kgCO2/GJ against a truth of 0.0172 tonne C/GJ
  (the same number, x44/12) as a 366,179% error. [`units.py`](./units.py) now
  reconciles mass/energy/volume/length, percent-vs-fraction, and the C<->CO2
  conversion both ways.
- **It penalised a model for its typography.** Grok writes `head-1 yr-1` and
  `N2O` with Unicode superscripts and subscripts; those were being stripped, so
  its units failed to parse. Normalised now — caught before any number was
  published.
- **It threw away a whole batch on formatting.** Gemini numbered one batch
  `1. [id]` instead of `[id]` and the parser skipped all 30. Fixed; all three
  models now parse at 467/467.

Two independent checks that the headline is real:

- **Against hand adjudication.** Automated 45.9% vs a hand read of ~47% on the
  same 45 pilot answers.
- **Against scorer coverage.** Closing successive gaps moved unscoreable from 137
  to 112 while the headline moved 46.7% -> 46.3%. If the unscoreable pile had
  hidden a bias, converting a quarter of it would have shifted the result.

Unreconcilable units are reported **UNSCOREABLE** and leave the denominator —
never counted as wrong. What remains is mostly currency (a SEK answer against a
USD truth) and prose units like "calendar year".

## Caveats, stated plainly

- **Gemini 3.6 Flash is not Google's frontier model.** It is the fast tier, run
  because the Pro models are not available on a free key. Do not read it as
  "Gemini scores X" — it is a different weight class from Opus 5 and Grok 4.6.
- **GPT is absent** — the account had no credits at run time.
- One run per model, no temperature sweep, no repeats. A floor-setting
  measurement, not a leaderboard.
- 30 questions share a context window, so answers within a batch are not fully
  independent.
- Questions come only from factors we may republish, so the answer key can ship.
  That favours well-documented public sources — if anything it makes the task
  easier than reality.

## Reproduce

```bash
python3 build_questions.py                 # regenerate questions.json
python3 run_model.py --model grok-4.6      # ask a model (needs that provider's key)
python3 compare.py                         # score every run in results/
```

Every model's raw output is committed verbatim under
[`results/`](./results), one file per batch. The prompt is in
[`prompts/`](./prompts).
