#!/usr/bin/env python3
"""
predict/scripts/screen_universe.py - Unbiased Multi-Ticker Thematic Screener

Evaluates any custom or discovered list of Indian equity tickers against the
institutional multi-archetype framework:
- Zero portfolio anchoring (evaluates any ticker objectively).
- Automatically categorizes candidates into Tier 1 (Quality Compounders),
  Tier 2 (Emerging Pure-Plays / High Optionality), and Disqualified / Rejects.
- Computes deterministic forward multiples, cash conversion, and Stage 2 trend.
"""

import sys
import os
import argparse

# Add predict/scripts to path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from data_fetcher import fetch_company_data
from forward_growth_pe import evaluate_forward_growth


def screen_candidates(tickers: list):
    print("=" * 115)
    print(" UNBIASED THEMATIC UNIVERSE SCREENER | MASTER SOURCE OF TRUTH (DETERMINISTIC ENGINE)")
    print(f" Total Candidates Evaluated: {len(tickers)}")
    print("=" * 115)

    tier1 = []
    tier2 = []
    rejects = []

    print(f"{'Ticker':<12} | {'CMP (₹)':<8} | {'Mcap (Cr)':<10} | {'P/E':<6} | {'2Y Fwd PE':<9} | {'Bull Up%':<8} | {'Exp CAGR':<8} | {'Verdict / Status':<35}")
    print("-" * 115)

    for ticker in tickers:
        clean = ticker.strip().upper()
        if not clean:
            continue
        try:
            res = evaluate_forward_growth(ticker=clean)
            cmp = res.get("cmp", 0.0) or 0.0
            mcap = res.get("mcap", 0.0) or 0.0
            pe = res.get("trailing_pe", 0.0) or 0.0
            fwd_pe = res.get("fwd_pe_expected", 0.0) or 0.0
            bull_up = res.get("return_bull_pct", 0.0) or 0.0
            exp_cagr = res.get("expected_cagr", 0.0) or 0.0
            verdict = res.get("verdict", "")
            
            # Classification Logic directly synchronized with Master Valuation Engine
            if "STRONG" in verdict:
                status = f"TIER 1: Strong Buy ({verdict[:22]})"
                tier1.append((clean, res))
            elif "WATCHLIST" in verdict or "ACCUMULATE" in verdict or (bull_up >= 50.0 and fwd_pe <= 80.0):
                status = f"TIER 2: Watchlist / Optionality"
                tier2.append((clean, res))
            else:
                status = f"REJECT: {verdict[:25]}"
                rejects.append((clean, res, verdict))

            print(f"{clean:<12} | {cmp:<8.1f} | {mcap:<10.1f} | {pe:<6.1f} | {fwd_pe:<9.1f} | {bull_up:<+8.1f}% | {exp_cagr:<+8.1f}% | {status:<35}")

        except Exception as e:
            print(f"{clean:<12} | Error running deterministic engine: {e}")

    print("\n" + "=" * 115)
    print(" SUMMARY AUDIT BREAKDOWN (DETERMINISTIC SINGLE SOURCE OF TRUTH)")
    print("=" * 115)
    print(f" • Tier 1 (Established Quality Compounders) [{len(tier1)}]: {[t[0] for t in tier1]}")
    print(f" • Tier 2 (Emerging Pure-Plays / Watchlist)  [{len(tier2)}]: {[t[0] for t in tier2]}")
    print(f" • Disqualified / Valuation & Growth Rejects [{len(rejects)}]: {[t[0] for t in rejects]}")
    print("=" * 115 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unbiased Multi-Ticker Thematic Screener")
    parser.add_argument("tickers", nargs="+", help="List of ticker symbols to screen (e.g. KPITTECH TATAELXSI TATATECH)")
    args = parser.parse_args()
    screen_candidates(args.tickers)
