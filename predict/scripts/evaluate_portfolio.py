#!/usr/bin/env python3
"""
predict/scripts/evaluate_portfolio.py - Portfolio Batch Valuation & Upside Analyzer

Evaluates any watchlist or custom basket of Indian equities against the
institutional high-growth & anti-fragility framework:
- Active H1/H2 calendar regime detection.
- Deterministic 2-year forward P/E compounding with dynamic exit P/E multiples.
- Aggregated equal-weighted and market-cap weighted portfolio upside calculations.
- Generates institutional summaries and markdown reports.
"""

import os
import sys
import argparse
import json
from datetime import datetime

# Add predict/scripts to path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from forward_growth_pe import evaluate_forward_growth, determine_fiscal_period


def evaluate_portfolio(stocks: list, as_of_date=None, export_md=None):
    """
    Evaluates a list of stock parameter dictionaries.
    """
    period = determine_fiscal_period(as_of_date)
    results = []
    
    print("\n" + "="*80)
    print(f" PORTFOLIO BATCH AUDIT | REGIME: {period['quarter']} ({period['running_fy']}) -> {period['half']} Roll-Forward")
    print(f" Target Horizons: 1-Yr FY{period['target_fy_yr1'] % 100} | 2-Yr FY{period['target_fy_yr2'] % 100}")
    print("="*80 + "\n")

    for s in stocks:
        ticker = s.get("ticker", "UNKNOWN").upper()
        name = s.get("name", ticker)
        cmp = float(s.get("cmp", 0.0))
        mcap = float(s.get("mcap", 0.0)) if s.get("mcap") else None
        pe = float(s.get("pe", 0.0)) if s.get("pe") else 0.0
        growth = float(s["growth"]) if ("growth" in s and s["growth"] is not None) else None
        bull_growth = float(s["bull_growth"]) if ("bull_growth" in s and s["bull_growth"] is not None) else (growth * 1.25 if growth else None)
        base_exit = float(s["base_exit_growth"]) if ("base_exit_growth" in s and s["base_exit_growth"] is not None) else (growth * 0.9 if growth else None)
        bull_exit = float(s["bull_exit_growth"]) if ("bull_exit_growth" in s and s["bull_exit_growth"] is not None) else (bull_growth * 0.9 if bull_growth else None)
        bear_prob = float(s["bear_prob"]) if ("bear_prob" in s and s["bear_prob"] is not None) else None
        bull_reason = s.get("bull_reason")
        disqualified = s.get("disqualified", False)

        if disqualified:
            results.append({
                "ticker": ticker,
                "name": name,
                "cmp": cmp,
                "mcap": mcap or 0.0,
                "current_pe": pe,
                "verdict": "REJECT / DISQUALIFIED",
                # No valuation: targets = CMP and 0% returns (never a fabricated -45% forecast)
                "target_bear": cmp,
                "return_bear_pct": 0.0,
                "target_bull": cmp,
                "return_bull_pct": 0.0,
                "expected_target": cmp,
                "total_expected_return_pct": 0.0,
                "expected_cagr": 0.0,
                "bear_prob": int((bear_prob or 0.50) * 100),
                "bull_prob": 100 - int((bear_prob or 0.50) * 100),
                "disqualified": True,
                "bear_reason": "Severe structural, regulatory or corporate governance distress",
                "bull_reason": bull_reason or "Emergency restructuring or debt workout"
            })
            continue

        res = evaluate_forward_growth(
            ticker=ticker,
            cmp=cmp,
            mcap=mcap,
            current_pe=pe,
            guided_cagr=growth,
            bull_cagr=bull_growth,
            base_exit_growth=base_exit,
            bull_exit_growth=bull_exit,
            bear_prob=bear_prob,
            bull_reason=bull_reason,
            as_of_date=as_of_date
        )
        res["name"] = name
        res["disqualified"] = False
        results.append(res)

    # Calculate portfolio aggregates
    total_mcap = sum(r["mcap"] for r in results)
    eq_exp_return = sum(r["total_expected_return_pct"] for r in results) / len(results)
    eq_exp_cagr = sum(r["expected_cagr"] for r in results) / len(results)

    mcap_exp_return = sum(r["total_expected_return_pct"] * r["mcap"] for r in results) / total_mcap if total_mcap > 0 else eq_exp_return
    mcap_exp_cagr = sum(r["expected_cagr"] * r["mcap"] for r in results) / total_mcap if total_mcap > 0 else eq_exp_cagr

    buys = [r for r in results if ("STRONG" in r["verdict"] or "QUALIFIED" in r["verdict"]) and not r.get("disqualified", False)]
    buys_mcap = sum(b["mcap"] for b in buys)
    buys_eq_return = sum(b["total_expected_return_pct"] for b in buys) / len(buys) if buys else 0.0
    buys_eq_cagr = sum(b["expected_cagr"] for b in buys) / len(buys) if buys else 0.0
    buys_mcap_return = sum(b["total_expected_return_pct"] * b["mcap"] for b in buys) / buys_mcap if buys_mcap > 0 else 0.0
    buys_mcap_cagr = sum(b["expected_cagr"] * b["mcap"] for b in buys) / buys_mcap if buys_mcap > 0 else 0.0

    print("\n" + "="*120)
    print("PORTFOLIO VALUATION SUMMARY TABLE")
    print("="*120)
    fmt = "{:<3} | {:<20} | {:>9} | {:>8} | {:>11} | {:>11} | {:>11} | {:>10} | {:<25}"
    print(fmt.format("No", "Company", "CMP (₹)", "TTM P/E", "Bear Return", "Bull Upside", "Exp Return", "Exp CAGR", "Verdict"))
    print("-" * 120)
    for idx, r in enumerate(results, 1):
        pe_str = f"{r['current_pe']:.1f}x" if r['current_pe'] > 0 else "N/A"
        v_short = r["verdict"].split("(")[0].strip()
        print(fmt.format(idx, r["name"][:20], f"₹{r['cmp']:.2f}", pe_str, f"{r['return_bear_pct']:+.1f}%", f"{r['return_bull_pct']:+.1f}%", f"{r['total_expected_return_pct']:+.1f}%", f"{r['expected_cagr']:+.1f}%", v_short[:25]))
    print("="*120)

    print(f"\nTotal Portfolio Stocks: {len(results)} | Total Market Cap: ₹{total_mcap:,.1f} Cr")
    print(f"All Stocks Equal-Weighted Expected Return: {eq_exp_return:+.1f}% (CAGR: {eq_exp_cagr:+.1f}% p.a.)")
    print(f"All Stocks Market-Cap Weighted Expected Return: {mcap_exp_return:+.1f}% (CAGR: {mcap_exp_cagr:+.1f}% p.a.)")
    print(f"\nApproved Conviction Buys ({len(buys)} stocks | ₹{buys_mcap:,.1f} Cr Mcap):")
    print(f"High-Conviction Equal-Weighted Expected Return: {buys_eq_return:+.1f}% (CAGR: {buys_eq_cagr:+.1f}% p.a.)")
    print(f"High-Conviction Market-Cap Weighted Return: {buys_mcap_return:+.1f}% (CAGR: {buys_mcap_cagr:+.1f}% p.a.)")

    return {
        "results": results,
        "total_mcap": total_mcap,
        "eq_exp_return": eq_exp_return,
        "eq_exp_cagr": eq_exp_cagr,
        "mcap_exp_return": mcap_exp_return,
        "mcap_exp_cagr": mcap_exp_cagr,
        "buys": buys,
        "buys_eq_return": buys_eq_return,
        "buys_eq_cagr": buys_eq_cagr,
        "buys_mcap_return": buys_mcap_return,
        "buys_mcap_cagr": buys_mcap_cagr
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a stock portfolio using forward P/E engine")
    parser.add_argument("--json", type=str, help="Path to JSON file containing array of stock parameters")
    parser.add_argument("--date", type=str, default=None, help="As-of date in YYYY-MM-DD")
    args = parser.parse_args()

    if args.json and os.path.isfile(args.json):
        with open(args.json, "r") as f:
            data = json.load(f)
        evaluate_portfolio(data, as_of_date=args.date)
    else:
        print("Please provide a valid JSON stock portfolio file via --json.")
