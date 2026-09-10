# Pilot run — Claude Opus 5, unaided, 45 questions

Run 2026-09-10 against data version 2026.187. Three fresh contexts, 15 questions
each, **0 tool uses** — no lookups, pure recall. One question per section, seeded.

## Headline, after hand-adjudication

| | |
|---|---|
| Gave a number | 44 / 45 |
| **Within 10% of the sourced value** | **~21 / 45 (47%)** |
| Named a source | 35 / 45 (78%) |
| Named the *right* source, when it named one | 29 / 35 (83%) |

**A confident, correctly-attributed citation accompanies a wrong number about
half the time.** That is the finding. The model is not usually refusing and it is
not usually citing garbage — it cites the right publisher and states the wrong
number, which is the combination most likely to survive review.

## The exemplar

> **R-290 (propane), per kg leaked**
> Opus 5: *"3 kgCO2e per kg leaked — GWP100 = 3 under IPCC AR5. This is the
> value DEFRA publishes."*
> Truth: **0.02**, IPCC AR6 WGI Ch 7 Table 7.SM.7.

150x too high, attributed to a publisher that does not publish it, with no hedge.
AR6 revised short-lived hydrocarbon GWPs down by two orders of magnitude and the
model is still answering from the older figure.

Others in the same shape: France grid 0.055 vs 0.035 (cited ADEME); supermini BEV
0.045 vs 0.02771 (cited DEFRA); crude steel ingot 2.1 vs 8.21 (cited the CBAM
defaults); TFT-FPD SF6 0.4 vs 4 (10x, cited IPCC).

## The automated scorer is NOT yet fit to publish

`score.py` reported 35.6% within-10%. Hand-adjudication puts it near 47%. The gap
is entirely scorer defects, not model performance:

- **No unit normalisation.** Hydrogen SMR: model said 63 kgCO2/GJ, truth 0.0172
  tonne C/GJ — 17.2 kg C x 44/12 = 63.07, i.e. *exactly right*, scored as a
  366,179% error. CHP: 80% vs 0.8 fraction, identical, scored 9,900% wrong.
  Same for PLA landfilled (0.02 t/short ton vs 20 kg/short ton).
- **Naive first-number extraction.** Swedish carbon tax: the model gave SEK 1,470
  *and* USD 130-140; truth is 144.62 USD/tCO2e, so the model was within 10% — the
  scorer took the SEK figure. CSRD: extracted "2464" from "Directive (EU)
  2022/2464" when the model's actual answer, FY2026, was correct.
- **Quantity mismatch is not detected.** UK residential gas: the model answered
  kWh per dwelling, the corpus holds kWh per m2. Neither is wrong; they are
  different questions.

**Before publishing any number from this benchmark, `score.py` needs unit
reconciliation and unit-aware extraction.** Publishing 35.6% would be publishing
a wrong figure about someone else's model.

## Also: it audits our own corpus

The R-290 check ran both ways. The model's disagreement sent us to the source,
and the corpus was right — AR6, cell-referenced. A disagreement is a prompt to
check, and sometimes the corpus will be the one that moves.
