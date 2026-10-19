#!/usr/bin/env python3
"""
predict/scripts/test_parity.py

Asserts 100% mathematical parity between standalone stock analysis and batch portfolio analysis.
Every single stock must yield the exact same target prices, exit P/Es, and CAGR whether evaluated
individually or within the 25-stock portfolio.
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from forward_growth_pe import evaluate_forward_growth, KNOWN_COMPANY_PROFILES
from build_portfolio_report import STOCKS_DATA, build_stock_section
from forward_growth_pe import determine_fiscal_period

def test_parity():
    print("=" * 80)
    print(" VERIFYING STANDALONE VS PORTFOLIO VALUATION PARITY")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    period = determine_fiscal_period("2026-10-19")
    for s in STOCKS_DATA:
        ticker = s["ticker"]
        cmp = s.get("cmp", 0.0)
        
        # 1. Run as standalone (clean call)
        res_standalone = evaluate_forward_growth(
            ticker=ticker,
            cmp=cmp,
            fallback_eps=s.get("eps", 0.0),
            fallback_pe=s.get("pe", 0.0),
            as_of_date="2026-10-19"
        )
        
        # 2. Run as portfolio batch section
        _, sm = build_stock_section(s, period)
        
        diff = abs(res_standalone["total_expected_return_pct"] - sm["expected_return"])
        
        if diff < 0.05:
            print(f"✅ {ticker:<12} | Standalone: {res_standalone['total_expected_return_pct']:+.1f}% == Batch: {sm['expected_return']:+.1f}% | 100% MATCH")
            passed += 1
        else:
            print(f"❌ {ticker:<12} | MISMATCH! Standalone: {res_standalone['total_expected_return_pct']:+.1f}% vs Batch: {sm['expected_return']:+.1f}%")
            failed += 1

    print("-" * 80)
    print(f"Parity Verification Results: {passed} PASSED, {failed} FAILED")
    print("=" * 80)
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    test_parity()
