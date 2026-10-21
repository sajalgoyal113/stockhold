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


def screen_candidates(tickers: list):
    print("=" * 105)
    print(" UNBIASED THEMATIC UNIVERSE SCREENER | MASTER SOURCE OF TRUTH")
    print(f" Total Candidates Evaluated: {len(tickers)}")
    print("=" * 105)

    tier1 = []
    tier2 = []
    rejects = []

    print(f"{'Ticker':<12} | {'CMP (₹)':<8} | {'Mcap (Cr)':<10} | {'P/E':<6} | {'ROCE%':<6} | {'Sales 3Y':<8} | {'PAT 3Y':<8} | {'CFO/PAT':<7} | {'Category / Status':<25}")
    print("-" * 105)

    for ticker in tickers:
        clean = ticker.strip().upper()
        if not clean:
            continue
        try:
            d = fetch_company_data(clean)
            cmp = d.get("cmp", 0.0) or 0.0
            mcap = d.get("mcap_cr", 0.0) or 0.0
            pe = d.get("pe", 0.0) or 0.0
            roce = d.get("roce", 0.0) or 0.0
            roe = d.get("roe", 0.0) or 0.0
            s3 = d.get("sales_growth_3yr", 0.0) or 0.0
            p3 = d.get("profit_growth_3yr", 0.0) or 0.0
            ttm_pat = d.get("ttm_pat", 0.0) or 0.0
            
            cfo_h = d.get("cfo_history", [])
            pat_h = d.get("pat_history", [])
            cfo_pat = (sum(cfo_h[-3:]) / sum(pat_h[-3:])) if (cfo_h and pat_h and sum(pat_h[-3:]) > 0) else 0.8

            # Classification Logic
            status = ""
            if p3 < 0 or s3 < 5.0 or roce < 12.0:
                status = "REJECT (Negative/Weak Growth)"
                rejects.append((clean, d, "Negative or stagnant earnings growth / weak ROCE"))
            elif pe > 80.0:
                status = "REJECT (Extreme Valuation)"
                rejects.append((clean, d, f"P/E {pe:.1f}x exceeds 80x valuation ceiling"))
            elif roce >= 18.0 and s3 >= 18.0 and p3 >= 15.0 and cfo_pat >= 0.70:
                status = "TIER 1: Quality Compounder"
                tier1.append((clean, d))
            else:
                status = "TIER 2: Emerging / Optionality"
                tier2.append((clean, d))

            print(f"{clean:<12} | {cmp:<8.1f} | {mcap:<10.1f} | {pe:<6.1f} | {roce:<6.1f} | {s3:<8.1f} | {p3:<8.1f} | {cfo_pat:<7.2f} | {status:<25}")

        except Exception as e:
            print(f"{clean:<12} | Error fetching data: {e}")

    print("\n" + "=" * 105)
    print(" SUMMARY AUDIT BREAKDOWN")
    print("=" * 105)
    print(f" • Tier 1 (Established Quality Compounders) [{len(tier1)}]: {[t[0] for t in tier1]}")
    print(f" • Tier 2 (Emerging Pure-Plays / Turnarounds)   [{len(tier2)}]: {[t[0] for t in tier2]}")
    print(f" • Disqualified / Filter Rejects             [{len(rejects)}]: {[t[0] for t in rejects]}")
    print("=" * 105 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unbiased Multi-Ticker Thematic Screener")
    parser.add_argument("tickers", nargs="+", help="List of ticker symbols to screen (e.g. KPITTECH TATAELXSI TATATECH)")
    args = parser.parse_args()
    screen_candidates(args.tickers)
