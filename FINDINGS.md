# How wrong are LLMs about emission factors?

467 questions from the GreenCalculus corpus (data version 2026.187), covering 45
sections and 75 publishers. Five models, identical questions, identical wording,
batches of 30, **no tools and no lookups**. Run 2026-09-10.

## Two rankings, in opposite orders

**When it answers, is it right?**

| Model | Scoreable | Within 10% | Within 50% | Off by >50% |
|---|---:|---:|---:|---:|
| Gemini 3.1 Pro | 49 | **67.3%** | 83.7% | 16.3% |
| Grok 4.6 | 84 | 66.7% | 88.1% | 11.9% |
| GPT-5.5 | 257 | 58.0% | 85.2% | 14.8% |
| Claude Opus 5 | 342 | 45.9% | 78.7% | 21.3% |
| Gemini 3.6 Flash | 306 | 43.5% | 78.4% | 21.6% |

**Of all 467 asked, how many did it get right?**

| Model | Answered | Refused | Correct | Correct of all 467 |
|---|---:|---:|---:|---:|
| Claude Opus 5 | 456 | 11 | 157 | **33.6%** |
| GPT-5.5 | 341 | 126 | 149 | 31.9% |
| Gemini 3.6 Flash | 436 | 31 | 133 | 28.5% |
| Grok 4.6 | 150 | 317 | 56 | 12.0% |
| Gemini 3.1 Pro | 85 | **382** | 33 | 7.1% |

Quote either table alone and you have misled someone. The best model by one
measure is the worst by the other.

## The finding: the more a model talks, the less each statement is worth

Sort by how often a model answers, and the danger metric sorts with it almost
perfectly:

| Model | Answered | **Right source, wrong number** |
|---|---:|---:|
| Gemini 3.1 Pro | 85 | 30.6% |
| Grok 4.6 | 150 | 29.8% |
| GPT-5.5 | 341 | 41.0% |
| Claude Opus 5 | 456 | 55.2% |
| Gemini 3.6 Flash | 436 | 58.2% |

This is not a story about which vendor is smartest. It is about **calibration** —
whether a model knows where its knowledge ends. Gemini 3.1 Pro refused 382 of 467
questions and was right two-thirds of the time when it spoke. Claude Opus 5
refused 11 and was right 46% of the time.

For carbon accounting that trade is not neutral. A refusal costs you a lookup.
A confident wrong number costs you a misstated disclosure.

## The controlled comparison

The clearest evidence needs no cross-vendor argument, because it is one vendor
and one knowledge base at two tiers:

| Google model | Answered | Within 10% | Right source, wrong number |
|---|---:|---:|---:|
| Gemini 3.1 **Pro** | 85 / 467 | 67.3% | 30.6% |
| Gemini 3.6 **Flash** | 436 / 467 | 43.5% | 58.2% |

Same company, same training corpus. The fast tier answers five times as many
questions and is right on far fewer of them, and when it cites the correct
publisher it is wrong about the number more often than not.

**This matters because the fast tier is the one that gets deployed.** Nobody puts
a slow reasoning model behind a bulk emissions pipeline. The model most likely to
be sitting in a production carbon feature is the one that fabricates most.

## The dangerous combination

| Model | Named a source | Named the *right* source |
|---|---:|---:|
| GPT-5.5 | 56.3% | 93.5% |
| Gemini 3.6 Flash | 76.9% | 91.9% |
| Claude Opus 5 | 75.2% | 90.0% |
| Gemini 3.1 Pro | 13.5% | 85.7% |
| Grok 4.6 | 22.1% | 82.5% |

Every model attributes *well* — around 90% name the publisher the number really
comes from. And for the talkative ones, the majority of those correctly-attributed
answers still carry a wrong number.

That is the failure mode worth naming. A wrong figure with no source gets caught,
because nobody can cite it. A wrong figure under the right publisher's name looks
exactly like diligence, and goes into the report.

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

Diesel per gallon is in every textbook. A CBAM country default, an NGFS scenario
cell, an AGRIBALYSE product line — jurisdiction-specific or recently published —
is fabricated in the same confident tone.

## One clean case

> **R-290 (propane), per kg leaked.** Claude Opus 5: *"3 kgCO2e per kg leaked —
> GWP100 = 3 under IPCC AR5. This is the value DEFRA publishes."*
> Truth: **0.02**, IPCC AR6 WGI Ch 7 Table 7.SM.7.

150x too high, credited to a publisher that does not publish it, no hedge. AR6
revised short-lived hydrocarbon GWPs down by two orders of magnitude.

## Is the scorer trustworthy?

It was wrong four times, and each is recorded because on a benchmark the
corrections matter more than the headline.

1. **It compared numbers, not quantities.** The first version reported 35.6% and
   scored a *correct* answer of 63 kgCO2/GJ against a truth of 0.0172 tonne C/GJ
   (the same number, x44/12) as a 366,179% error. [`units.py`](./units.py) now
   reconciles mass/energy/volume/length, percent-vs-fraction and C<->CO2 both ways.
2. **It penalised a model for typography.** Grok writes `head-1 yr-1` and `N2O`
   with Unicode superscripts and subscripts; these were being stripped, so its
   units failed to parse.
3. **It discarded a whole batch on formatting.** Gemini numbered one batch
   `1. [id]` instead of `[id]` and the parser silently skipped all 30 answers.
4. **An empty response is not a refusal.** Reasoning models spend output tokens
   on internal reasoning before any visible text; too small a token budget returns
   HTTP 200 with *nothing* in it, which is indistinguishable from a refusal.
   Since this study turns on refusal rates, that would have inverted a model's
   result. All budgets raised to 32,000 tokens, and every refusal reported here
   was verified to be words ("I don't know this factor"), not an empty reply.

Two independent checks that the headline is real:

- **Against hand adjudication.** Automated 45.9% vs a hand read of ~47% on the
  same 45 pilot answers.
- **Against scorer coverage.** Closing successive gaps moved unscoreable from 137
  to 112 while the headline moved 46.7% -> 46.3%. If the unscoreable pile had
  hidden a bias, converting a quarter of it would have shifted the result.

Unreconcilable units are reported **UNSCOREABLE** and leave the denominator,
never counted wrong — mostly currency (a SEK answer against a USD truth) and
prose units like "calendar year".

## Caveats, stated plainly

- One run per model, no temperature sweep, no repeats. A floor-setting
  measurement, not a leaderboard.
- Gemini 3.1 Pro and Grok 4.6 answered so few questions that their accuracy rests
  on 49 and 84 scoreable answers respectively. Treat those percentages as
  indicative; the refusal counts are the solid part.
- 30 questions share a context window, so answers within a batch are not fully
  independent.
- Questions come only from factors we may republish, so the answer key can ship.
  That favours well-documented public sources — if anything it makes the task
  easier than reality.
- Model versions and run date are stated because these numbers will move.

## Reproduce

```bash
python3 build_questions.py            # regenerate questions.json
python3 run_model.py --model gpt-5.5  # ask a model (needs that provider's key)
python3 compare.py                    # score every run in results/
```

Every model's raw output is committed verbatim under [`results/`](./results),
one file per batch. The prompt is in [`prompts/`](./prompts).
