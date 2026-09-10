# Claude Opus 5, unaided — 467 questions

Run 2026-09-10 against GreenCalculus data version 2026.187. Sixteen fresh
contexts, ~30 questions each, one tool call apiece (reading their own question
file) and no lookups. Questions cover 45 sections and 75 publishers.

## Result

| | |
|---|---|
| Gave a number | 456 / 467 (97.6%) |
| Declined outright | 8 (1.7%) |
| Hedged but still gave a number | 94 (20%) |
| **Within 10% of the sourced value** | **46.3%** (of 339 scoreable) |
| Within 50% | 79.1% |
| Off by more than 50%, stated as fact | 20.9% |
| Named a source | 75.2% |
| Named the *right* source, when it named one | 90.0% |
| **Named the right source AND got the number wrong** | **55.1%** |

112 questions were **unscoreable** — the model's unit and the source's unit
could not be reconciled (mostly a local-currency answer against a USD/tCO2e
truth). Those are excluded from the accuracy denominator rather than counted
wrong. See "Is the scorer trustworthy?" below.

## The finding

The model almost never refuses, and it almost always attributes correctly.
It names the right publisher 90% of the time — **and more than half of those
correctly-attributed answers carry a wrong number.**

That is the dangerous combination. A refusal is safe: the reader goes and looks
it up. A wrong number with no source is usually caught: the reader has nothing
to cite. A wrong number under the right publisher's name is the one that gets
pasted into a disclosure, because it looks exactly like diligence.

## It knows the famous numbers and invents the rest

Accuracy by section, where at least 8 questions were scoreable:

| | Section | Within 10% |
|---|---|---|
| Best | fuels | 92% (11/12) |
| | fuel_properties | 91% (10/11) |
| | mobile_combustion | 83% (10/12) |
| | district_heating | 80% (8/10) |
| Worst | cbam | 18% (2/11) |
| | ev_charging | 17% (2/12) |
| | ngfs_scenarios | 9% (1/11) |
| | food_pcf | 8% (1/12) |

Diesel per gallon and the calorific value of LPG are in every textbook, and the
model gets them right. Anything jurisdiction-specific, recently published, or
buried in an annex — a CBAM country default, an NGFS scenario cell, an
AGRIBALYSE product line — it fabricates with the same confident tone.

## Exemplars — right source, badly wrong number

| Factor | Model said | Truth | Cited |
|---|---|---|---|
| UK bio-methanol per litre | 0.665 | 0.00669 | DEFRA |
| Cattle manure CH4, anaerobic digestion, cool | 110 | 2.4 | IPCC |
| CBAM indirect, Namibia | 0.6 | 0.044 | CBAM |
| GCP europe-north2 gCO2e/kWh | 35 | 3 | Google |
| EPA WARM, PLA landfilled | 200 | 20 | EPA |
| DEFRA closed-loop PP recycling | 21.3 | 4.65 | DEFRA |

And from the 45-question pilot, the cleanest single case:

> **R-290 (propane), per kg leaked.** Opus 5: *"3 kgCO2e per kg leaked — GWP100
> = 3 under IPCC AR5. This is the value DEFRA publishes."*
> Truth: **0.02**, IPCC AR6 WGI Ch 7 Table 7.SM.7.

150x too high, attributed to a publisher that does not publish it, no hedge.
AR6 revised short-lived hydrocarbon GWPs down by two orders of magnitude; the
model is still answering from the older figure.

## Is the scorer trustworthy?

This is the part most benchmarks skip, so: the scorer was wrong first, and we
caught it.

The initial version compared numbers rather than quantities and reported 35.6%
on the pilot. It scored a *correct* hydrogen answer (63 kgCO2/GJ against a truth
of 0.0172 tonne C/GJ — the same number, x44/12) as a 366,179% error, and 80% vs
0.8 as 9,900% wrong. Hand-adjudicating all 45 pilot answers gave ~47%.
[`units.py`](./units.py) now reconciles mass/energy/volume/length scales,
percent against fraction, and the carbon-species conversion in both directions.

Two independent checks that the current number is real:

- **Against hand adjudication.** Automated 45.9% vs hand-read ~47% on the same
  45 answers.
- **Against scorer coverage.** Closing successive gaps moved unscoreable from
  137 to 126 to 112 — and the headline moved only 46.7% to 46.6% to 46.3%.
  If the unscoreable pile had been hiding a bias, converting a quarter of it
  would have shifted the result. It didn't.

Remaining unscoreable is dominated by currency (a SEK answer against a USD
truth) and by prose units like "calendar year" and "boolean". Those stay
excluded rather than guessed.

## Reproduce

```bash
python3 build_questions.py                                   # regenerate questions.json
python3 assemble.py                                          # results/raw/*.txt -> runs file
python3 score.py results/runs_opus5_full.json questions.json  # score
```

Raw model output is in [`results/raw/`](./results/raw), one file per batch,
verbatim. The prompt is in [`prompts/`](./prompts).

## Caveats

- One model, one run, no temperature sweep. Treat as a floor-setting
  measurement, not a leaderboard.
- Questions are generated from a corpus that only includes republishable
  factors, so the answer key can ship. That biases toward well-documented
  public sources — if anything, it makes the task *easier* than reality.
- 30 questions share a context window per batch, so answers are not fully
  independent of each other.
- 6 duplicate keys came out of the generator and were deduplicated at assembly
  (473 rows, 467 unique).
