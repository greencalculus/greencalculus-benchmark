#!/usr/bin/env python3
"""Issue #23: a currency written immediately before the number must reach reconcile.

  python3 verify/test_currency_prefix.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import score
import units


def _unit_for(text, value):
    hits = [(v, u) for v, u in score.candidates(text) if v == value]
    assert hits, f"no candidate {value} in {score.candidates(text)!r} from {text!r}"
    return hits[0][1]


def test_usd_prefix_reaches_reconcile():
    text = "Best estimate: about USD 5 /tCO2e."
    cands = score.candidates(text)
    assert cands, text
    unit = _unit_for(text, 5.0)
    assert "usd" in unit.lower(), unit
    got, note = units.reconcile(5, unit, "USD/tCO2e")
    assert got == 5.0 and note is None, (got, note)
    assert units.reconcile(5, "/tCO2e", "USD/tCO2e")[0] is None


def test_other_usd_spellings():
    for text in ("about US$ 5 /tCO2e.", "about $5 /tCO2e."):
        unit = _unit_for(text, 5.0)
        got, _ = units.reconcile(5, unit, "USD/tCO2e")
        assert got == 5.0, (text, unit, got)


def test_foreign_only_is_unscoreable():
    cases = (
        "About NT$300 per tCO2e.",
        "About NOK 1,000 per tCO2e in 2025.",
        "About EUR 65 /tCO2e.",
        "About SEK 1,450 per tCO2.",
    )
    for text in cases:
        unit = score.candidates(text)[0][1]
        # Currency is carried so "$" cannot steal "NT$", but there is no FX rate.
        got, _, _ = score.best_value(text, "USD/tCO2e")
        assert got is None, (text, unit, got)


def test_mixed_sentence_scores_the_usd_figure():
    text = (
        "About EUR 65–75 per tCO2e in 2024–2025, i.e. roughly USD 76 /tCO2e."
    )
    got, unit, _ = score.best_value(text, "USD/tCO2e")
    assert got == 76.0, (got, unit)
    assert "usd" in unit.lower(), unit


def test_euro_symbol_against_eur_truth():
    text = "Approximately €4.5 per tCO2e average EUA price in 2013."
    unit = _unit_for(text, 4.5)
    got, _ = units.reconcile(4.5, unit, "EUR/tCO2e")
    assert got == 4.5, (unit, got)


def test_nt_dollar_is_not_usd():
    text = "About NT$300 per tCO2e."
    unit = _unit_for(text, 300.0)
    assert "nt$" in unit.lower(), unit
    assert units.reconcile(300, unit, "USD/tCO2e")[0] is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all currency-prefix tests passed")
