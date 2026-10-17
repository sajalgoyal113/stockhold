#!/usr/bin/env python3
"""
forward_growth_pe.py - High-Growth Stock & 2-Year Forward P/E Valuation Engine

Implements the institutional growth and valuation framework:
- H1 (Q1/Q2: Apr 1 - Sep 30) vs H2 (Q3/Q4: Oct 1 - Mar 31) Roll-Forward Framework.
- Computes FY+1 and FY+2 Target EPS with exact compounding powers from base.
- Evaluates 2-Year Forward P/E against the < 50x hurdle.
- Dynamically derives Base Case and Bull Case exit P/E multiples from expected growth rates at the end of the evaluation period.
- Requires explicit operational rationales for assumed growth rates.
- Omits Bear Case scenario; evaluates Base vs Bull upside asymmetry.
- Verifies mandated >= 50% Bull Case 2-Year upside.
- Displays Latest Market Cap and generates clean, institutional terminal summary cards.
"""

import sys
import argparse
import math
from datetime import datetime

def determine_fiscal_period(as_of_date=None, half_override=None, fy_override=None):
    """
    Determines running fiscal year, active quarter, and roll-forward targets.
    Indian Financial Year: April 1 to March 31.
    """
    if as_of_date is None:
        dt = datetime.now()
    elif isinstance(as_of_date, datetime):
        dt = as_of_date
    else:
        try:
            dt = datetime.strptime(str(as_of_date), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format '{as_of_date}'. Use YYYY-MM-DD.")
            
    month = dt.month
    year = dt.year
    
    if fy_override is not None:
        running_fy = fy_override if fy_override >= 100 else 2000 + fy_override
    else:
        running_fy = year + 1 if month >= 4 else year
        
    if half_override is not None:
        half = half_override.upper()
        if half not in ["H1", "H2"]:
            raise ValueError(f"Invalid half '{half}'. Must be H1 or H2.")
        quarter = "Q1/Q2" if half == "H1" else "Q3/Q4"
    else:
        if 4 <= month <= 6:
            quarter = "Q1"
            half = "H1"
        elif 7 <= month <= 9:
            quarter = "Q2"
            half = "H1"
        elif 10 <= month <= 12:
            quarter = "Q3"
            half = "H2"
        else:
            quarter = "Q4"
            half = "H2"
            
    base_fy = running_fy - 1
    
    if half == "H1":
        # H1 Regime: Market focuses on current year and next year
        target_fy_yr1 = running_fy
        target_fy_yr2 = running_fy + 1
        comp_years_yr1 = 1
        comp_years_yr2 = 2
    else:
        # H2 Regime: Multiples roll forward as H1 has concluded
        target_fy_yr1 = running_fy + 1
        target_fy_yr2 = running_fy + 2
        comp_years_yr1 = 2
        comp_years_yr2 = 3
        
    return {
        "dt": dt,
        "running_fy": running_fy,
        "quarter": quarter,
        "half": half,
        "base_fy": base_fy,
        "target_fy_yr1": target_fy_yr1,
        "target_fy_yr2": target_fy_yr2,
        "comp_years_yr1": comp_years_yr1,
        "comp_years_yr2": comp_years_yr2,
    }

def evaluate_forward_growth(ticker, cmp, mcap=None, current_eps=0.0, current_pe=0.0,
                             guided_cagr=None, bull_cagr=None,
                             base_exit_growth=None, bull_exit_growth=None,
                             base_peg=1.6, bull_peg=1.85,
                             base_reason=None, bull_reason=None,
                             base_prob=None, bull_prob=None,
                             dilution_pct_annual=0.0, margin_expansion_pct_annual=0.0,
                             historical_guidance_reliability=1.0,
                             target_eps_yr2=None, rev_cagr=None,
                             current_margin=None, target_margin_yr2=None,
                             as_of_date=None, half_override=None, fy_override=None,
                             base_pe=None, bull_pe=None):
    """
    Projects EPS for FY+1 and FY+2 across Base and Bull scenarios with dynamic exit multiples.
    """
    if current_eps <= 0 and current_pe > 0:
        current_eps = cmp / current_pe
    elif current_pe <= 0 and current_eps > 0:
        current_pe = cmp / current_eps

    if current_eps <= 0:
        raise ValueError("Error: Both current_eps and current_pe cannot be <= 0.")

    period = determine_fiscal_period(as_of_date, half_override, fy_override)
    regime_desc = "Regime 1: Steady-State Margin Growth"

    # CASE A: Explicit Target EPS provided
    if target_eps_yr2 is not None and target_eps_yr2 > 0:
        eps_base_yr2 = target_eps_yr2
        base_net_growth = (eps_base_yr2 / current_eps) ** (1.0 / period["comp_years_yr2"]) - 1.0
        eps_base_yr1 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr1"])
        regime_desc = f"Regime 2: Direct Consensus / Line-Item Build (Yr 2 Base EPS ₹{target_eps_yr2:.2f})"
        bull_net_growth = max(bull_cagr, base_net_growth * 1.25) if bull_cagr is not None else base_net_growth * 1.25

    # CASE B: Non-linear Margin Expansion Model (Platform / Early Profitability)
    elif rev_cagr is not None and current_margin is not None and target_margin_yr2 is not None:
        if current_margin <= 0:
            raise ValueError("Error: current_margin must be > 0 for margin expansion model.")
        effective_rev_cagr = rev_cagr * historical_guidance_reliability
        rev_multiplier_yr2 = (1.0 + effective_rev_cagr) ** period["comp_years_yr2"]
        margin_multiplier = target_margin_yr2 / current_margin
        pat_multiplier_yr2 = rev_multiplier_yr2 * margin_multiplier
        net_pat_cagr = (pat_multiplier_yr2 ** (1.0 / period["comp_years_yr2"])) - 1.0
        base_net_growth = net_pat_cagr - dilution_pct_annual
        eps_base_yr1 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr1"])
        eps_base_yr2 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr2"])
        bull_net_growth = max(bull_cagr, base_net_growth * 1.20) if bull_cagr is not None else base_net_growth * 1.20
        regime_desc = (f"Regime 2: Operating Leverage & Margin Expansion "
                       f"({current_margin*100:.2f}% -> {target_margin_yr2*100:.2f}% NPM, Rev CAGR {effective_rev_cagr*100:.1f}%)")

    # CASE C: Standard Linear Model
    else:
        if guided_cagr is None:
            raise ValueError("Error: Must specify either --growth, --target-eps-yr2, or (--rev-cagr, --current-margin, --target-margin-yr2).")
        base_net_growth = (guided_cagr * historical_guidance_reliability) - dilution_pct_annual + margin_expansion_pct_annual
        eps_base_yr1 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr1"])
        eps_base_yr2 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr2"])
        bull_net_growth = max(bull_cagr, base_net_growth) if bull_cagr is not None else base_net_growth * 1.25

    # Bull Scenario Projections
    eps_bull_yr1 = current_eps * ((1.0 + bull_net_growth) ** period["comp_years_yr1"])
    eps_bull_yr2 = current_eps * ((1.0 + bull_net_growth) ** period["comp_years_yr2"])

    # Determine End-Period Growth Rates
    base_exit_g = base_exit_growth if base_exit_growth is not None else base_net_growth
    bull_exit_g = bull_exit_growth if bull_exit_growth is not None else bull_net_growth

    # Dynamic P/E Derivation based on end-of-period growth rate
    if base_pe is None:
        base_pe = round(base_peg * (base_exit_g * 100), 1)
        base_pe = max(15.0, base_pe)  # Floor at 15x
    if bull_pe is None:
        bull_pe = round(bull_peg * (bull_exit_g * 100), 1)
        bull_pe = max(base_pe + 5.0, bull_pe)  # Bull P/E higher than Base

    # Valuations
    fwd_pe_yr1_base = cmp / eps_base_yr1 if eps_base_yr1 > 0 else float('inf')
    fwd_pe_yr2_base = cmp / eps_base_yr2 if eps_base_yr2 > 0 else float('inf')
    fwd_pe_yr2_bull = cmp / eps_bull_yr2 if eps_bull_yr2 > 0 else float('inf')

    peg_ratio_yr2_base = fwd_pe_yr2_base / (base_net_growth * 100) if base_net_growth > 0 else float('inf')

    base_target_price = eps_base_yr2 * base_pe
    base_upside_pct = ((base_target_price - cmp) / cmp) * 100
    base_annualized_cagr = (((base_target_price / cmp) ** 0.5) - 1) * 100 if base_target_price > 0 else -100

    bull_target_price = eps_bull_yr2 * bull_pe
    bull_upside_pct = ((bull_target_price - cmp) / cmp) * 100
    bull_annualized_cagr = (((bull_target_price / cmp) ** 0.5) - 1) * 100 if bull_target_price > 0 else -100

    passes_growth_filter = base_net_growth >= 0.20 or bull_net_growth >= 0.20
    passes_pe_filter = fwd_pe_yr2_base < 50.0
    passes_bull_upside_mandate = bull_upside_pct >= 50.0

    fy_curr_str = f"FY{period['running_fy'] % 100}"
    fy_base_str = f"FY{period['base_fy'] % 100}"
    fy_yr1_str = f"FY{period['target_fy_yr1'] % 100}"
    fy_yr2_str = f"FY{period['target_fy_yr2'] % 100}"

    # Default reasons if not provided
    if not base_reason:
        base_reason = f"Execution friction, delayed milestone delivery, or moderate volume ramp (CAGR {base_net_growth*100:.1f}%)"
    if not bull_reason:
        bull_reason = f"Flawless execution, market share consolidation, and strong operational leverage (CAGR {bull_net_growth*100:.1f}%)"

    print("================================================================================")
    print(f" HIGH-GROWTH & 2-YEAR FORWARD P/E ENGINE: {ticker.upper()}")
    print("================================================================================")
    print(f" Valuation Model:                    {regime_desc}")
    print(f" Operating Period:                   {period['quarter']} ({fy_curr_str}) -> {period['half']} Roll-Forward Regime")
    print(f" Target Horizons:                    1-Yr Target: {fy_yr1_str} ({period['comp_years_yr1']} yrs comp) | 2-Yr Target: {fy_yr2_str} ({period['comp_years_yr2']} yrs comp)")
    print(f" Current Market Price (CMP):         ₹{cmp:,.2f}")
    if mcap is not None:
        print(f" Latest Market Cap:                   ₹{mcap:,.1f} Cr")
    print(f" Current Base ({fy_base_str}/TTM) EPS:       ₹{current_eps:,.2f}")
    print(f" Current Trailing P/E:               {current_pe:.1f}x")
    if dilution_pct_annual > 0:
        print(f" Annual Equity Dilution (ESOP/QIP):  {dilution_pct_annual*100:.1f}%")
    print("--------------------------------------------------------------------------------")
    print(f" Base Case CAGR ({base_reason}):")
    print(f"   Projected Net EPS CAGR:           {base_net_growth*100:.1f}% CAGR")
    print(f"   Projected 1-Yr ({fy_yr1_str}) EPS:        ₹{eps_base_yr1:,.2f}  |  1-Yr Forward P/E: {fwd_pe_yr1_base:.1f}x")
    print(f"   Projected 2-Yr ({fy_yr2_str}) EPS:        ₹{eps_base_yr2:,.2f}  |  2-Yr Forward P/E: {fwd_pe_yr2_base:.1f}x")
    print(f"   Expected End-Period Growth Rate:  {base_exit_g*100:.1f}% -> Dynamic Base Exit P/E: {base_pe:.1f}x")
    print(f"   2-Yr Forward PEG Ratio:           {peg_ratio_yr2_base:.2f}x")
    print("--------------------------------------------------------------------------------")
    print(f" Bull Case CAGR ({bull_reason}):")
    print(f"   Projected Net EPS CAGR:           {bull_net_growth*100:.1f}% CAGR")
    print(f"   Projected 2-Yr ({fy_yr2_str}) EPS:        ₹{eps_bull_yr2:,.2f}  |  2-Yr Forward P/E: {fwd_pe_yr2_bull:.1f}x")
    print(f"   Expected End-Period Growth Rate:  {bull_exit_g*100:.1f}% -> Dynamic Bull Exit P/E: {bull_pe:.1f}x")
    print("--------------------------------------------------------------------------------")

    print("\n>>> CRITERIA SCORECARD:")
    c1_mark = "✅ PASS" if passes_growth_filter else "❌ FAIL"
    c2_mark = "✅ PASS" if passes_pe_filter else "❌ FAIL"
    c3_mark = "✅ PASS" if passes_bull_upside_mandate else "❌ FAIL"
    print(f" 1. 20%+ Projected Growth Filter:          {c1_mark} (Base: {base_net_growth*100:.1f}%, Bull: {bull_net_growth*100:.1f}% vs 20.0% threshold)")
    print(f" 2. 2-Year Forward P/E < 50x Filter:       {c2_mark} ({fwd_pe_yr2_base:.1f}x Base vs 50.0x threshold)")
    print(f" 3. Mandated 50%+ Bull 2-Yr Upside Filter: {c3_mark} ({bull_upside_pct:+.1f}% vs +50.0% mandate at {bull_pe:.1f}x Bull exit)")

    print(f"\n--- 2-YEAR SCENARIO VALUATION MATRIX ({fy_yr2_str}) ---")
    header = f"{'Scenario':<12} | {'Horizon CAGR':<14} | {'End Growth':<12} | {'Exit P/E':<10} | {'Target Price (₹)':<18} | {'Total Return':<14} | {'Annualized CAGR':<16}"
    print(header)
    print("-" * len(header))
    print(f"{'Base Case':<12} | {base_net_growth*100:>10.1f}%   | {base_exit_g*100:>8.1f}%   | {base_pe:>6.1f}x   | ₹{base_target_price:>12.2f}    | {base_upside_pct:>+10.1f}%   | {base_annualized_cagr:>+12.1f}%")
    print(f"{'Bull Case':<12} | {bull_net_growth*100:>10.1f}%   | {bull_exit_g*100:>8.1f}%   | {bull_pe:>6.1f}x   | ₹{bull_target_price:>12.2f}    | {bull_upside_pct:>+10.1f}%   | {bull_annualized_cagr:>+12.1f}%")
    print("-" * len(header))

    # Institutional Verdict Logic: Evaluates synthesis of Base and Bull scenarios
    # Dynamic probability weighting based on company-specific execution risk
    if base_prob is None:
        base_prob = 0.65  # Default 65% Base / 35% Bull reflecting execution conservatism
    bull_prob = 1.0 - base_prob if bull_prob is None else bull_prob

    # Normalize if user passed both
    total_prob = base_prob + bull_prob
    base_prob = base_prob / total_prob
    bull_prob = bull_prob / total_prob

    prob_weighted_target = (base_prob * base_target_price) + (bull_prob * bull_target_price)
    prob_weighted_return = ((prob_weighted_target - cmp) / cmp) * 100
    prob_weighted_cagr = (((prob_weighted_target / cmp) ** 0.5) - 1.0) * 100 if prob_weighted_target > 0 else -100

    if passes_bull_upside_mandate and base_upside_pct >= 15.0 and base_net_growth >= 0.20:
        verdict = f"STRONG HIGH-GROWTH BUY (Bull Upside {bull_upside_pct:+.1f}%, Base {base_upside_pct:+.1f}%, Expected CAGR {prob_weighted_cagr:+.1f}% p.a.)"
    elif passes_bull_upside_mandate and base_upside_pct >= 0.0:
        verdict = f"QUALIFIED GROWTH BUY (Bull Upside {bull_upside_pct:+.1f}%, but Base Return {base_upside_pct:+.1f}% provides modest cushion)"
    elif passes_bull_upside_mandate and base_upside_pct < 0.0:
        verdict = f"REJECT / HIGH VALUATION TRAP (Bull Upside {bull_upside_pct:+.1f}%, but Base Case suffers capital loss {base_upside_pct:+.1f}% due to high starting P/E)"
    elif not passes_growth_filter:
        verdict = f"REJECT (Projected growth below 20% hurdle rate)"
    else:
        verdict = f"REJECT (2-year forward P/E {fwd_pe_yr2_base:.1f}x exceeds 50x hurdle or Bull Upside < 50%)"

    print("\n================================================================================")
    print(" VALUATION & EXPECTED TARGET PRICE SUMMARY (FROM LAST CLOSING PRICE)")
    print("================================================================================")
    print(f" Last Closing Price (CMP):            ₹{cmp:,.2f}")
    if mcap is not None:
        print(f" Latest Market Cap:                   ₹{mcap:,.1f} Cr")
    print(f" Target Time Horizon:                 2-Year Horizon ({fy_base_str} to {fy_yr2_str})")
    print(f" Expected Target Price (Wtd Avg):     ₹{prob_weighted_target:,.2f}")
    print(f" Total Expected Return:               {prob_weighted_return:+.1f}% from CMP")
    print(f" Annualized Expected Return (CAGR):   {prob_weighted_cagr:+.1f}% p.a.")
    print(f" Dynamic Probability Allocation:      {base_prob*100:.0f}% Base / {bull_prob*100:.0f}% Bull")
    print(f" Final Conviction Verdict:            {verdict}")
    print("================================================================================")
    print("\n--- UNDERLYING SCENARIO TARGET BREAKDOWN & EXPLANATION ---")
    print(f" • Base Case Target ({base_prob*100:.0f}% Prob):   ₹{base_target_price:,.2f} ({base_upside_pct:+.1f}%) | Exit P/E: {base_pe:.1f}x on {base_exit_g*100:.1f}% end-growth")
    print(f"   Rationale: {base_reason}")
    print(f" • Bull Case Target ({bull_prob*100:.0f}% Prob):   ₹{bull_target_price:,.2f} ({bull_upside_pct:+.1f}%) | Exit P/E: {bull_pe:.1f}x on {bull_exit_g*100:.1f}% end-growth")
    print(f"   Rationale: {bull_reason}")
    print("================================================================================\n")

    return {
        "ticker": ticker.upper(),
        "cmp": cmp,
        "mcap": mcap,
        "regime": f"{period['half']} Roll-Forward Regime",
        "regime_desc": regime_desc,
        "regime_model": regime_desc,
        "base_fy": fy_base_str,
        "target_yr1_fy": fy_yr1_str,
        "target_yr2_fy": fy_yr2_str,
        "comp_years_yr1": period["comp_years_yr1"],
        "comp_years_yr2": period["comp_years_yr2"],
        "current_eps": round(current_eps, 2),
        "current_pe": round(current_pe, 1),
        "ttm_eps": round(current_eps, 2),
        "trailing_pe": round(current_pe, 1),
        "base_cagr": round(base_net_growth, 4),
        "bull_cagr": round(bull_net_growth, 4),
        "base_exit_pe": round(base_pe, 1),
        "bull_exit_pe": round(bull_pe, 1),
        "eps_base_yr1": round(eps_base_yr1, 2),
        "eps_base_yr2": round(eps_base_yr2, 2),
        "eps_bull_yr1": round(eps_bull_yr1, 2),
        "eps_bull_yr2": round(eps_bull_yr2, 2),
        "fwd_pe_base": round(fwd_pe_yr2_base, 1),
        "fwd_pe_bull": round(fwd_pe_yr2_bull, 1),
        "target_base": round(base_target_price, 2),
        "target_bull": round(bull_target_price, 2),
        "return_base_pct": round(base_upside_pct, 1),
        "return_bull_pct": round(bull_upside_pct, 1),
        "cagr_base": round(base_annualized_cagr, 1),
        "cagr_bull": round(bull_annualized_cagr, 1),
        "base_prob": round(base_prob * 100),
        "bull_prob": round(bull_prob * 100),
        "expected_target": round(prob_weighted_target, 2),
        "total_expected_return_pct": round(prob_weighted_return, 1),
        "expected_cagr": round(prob_weighted_cagr, 1),
        "pass_growth": passes_growth_filter,
        "pass_fwd_pe": passes_pe_filter,
        "pass_upside": passes_bull_upside_mandate,
        "verdict": verdict,
        "verdict_color": "green" if "STRONG" in verdict else ("blue" if "QUALIFIED" in verdict else ("orange" if "ACCUMULATE" in verdict else "red")),
        "buy_low": round(base_target_price / 1.25, 1),
        "buy_high": round(base_target_price / 1.10, 1),
        "base_reason": base_reason,
        "bull_reason": bull_reason
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2-Year Forward Growth & P/E Valuation Engine")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. DIXON, COFORGE, IXIGO)")
    parser.add_argument("--cmp", type=float, required=True, help="Current Market Price (₹)")
    parser.add_argument("--mcap", type=float, default=None, help="Latest Market Cap in ₹ Crores")
    parser.add_argument("--eps", type=float, default=0.0, help="Current Base/TTM EPS (₹)")
    parser.add_argument("--pe", type=float, default=0.0, help="Current Trailing P/E multiple")
    
    # Growth rates and rationale
    parser.add_argument("--growth", "--base-growth", dest="growth", type=float, default=None, help="Base case 2-3 yr CAGR (e.g. 0.15 for 15%%)")
    parser.add_argument("--bull-growth", type=float, default=None, help="Bull case 2-3 yr CAGR (e.g. 0.22 for 22%%)")
    parser.add_argument("--base-exit-growth", type=float, default=None, help="Expected ongoing growth rate at end of evaluation period for Base Case (e.g. 0.15)")
    parser.add_argument("--bull-exit-growth", type=float, default=None, help="Expected ongoing growth rate at end of evaluation period for Bull Case (e.g. 0.22)")
    parser.add_argument("--base-peg", type=float, default=1.6, help="Justified PEG for Base Case in Indian market (default: 1.6)")
    parser.add_argument("--bull-peg", type=float, default=1.85, help="Justified PEG for Bull Case in Indian market (default: 1.85)")
    parser.add_argument("--base-reason", type=str, default=None, help="Operational reason for Base Case growth assumption")
    parser.add_argument("--bull-reason", type=str, default=None, help="Operational reason for Bull Case growth assumption")
    parser.add_argument("--base-prob", type=float, default=None, help="Dynamic probability weighting for Base Case (e.g. 0.65 for 65%%)")
    parser.add_argument("--bull-prob", type=float, default=None, help="Dynamic probability weighting for Bull Case (e.g. 0.35 for 35%%)")

    # Dilution and adjustments
    parser.add_argument("--dilution", type=float, default=0.0, help="Annual share dilution rate from QIP/ESOP (default: 0.0)")
    parser.add_argument("--margin-expansion", type=float, default=0.0, help="Annual net margin expansion/contraction (default: 0.0)")
    parser.add_argument("--haircut", type=float, default=1.0, help="Reliability haircut on guidance (1.0 = 100%%, 0.85 = 15%% haircut)")
    
    # Fiscal period overrides
    parser.add_argument("--date", type=str, default=None, help="As-of date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--half", type=str, choices=["H1", "H2", "h1", "h2"], default=None, help="Explicit H1 / H2 regime override")
    parser.add_argument("--fy", type=int, default=None, help="Explicit running financial year override (e.g. 27 or 2027)")
    
    # Manual multiple overrides (optional)
    parser.add_argument("--base-pe", type=float, default=None, help="Override Base case exit P/E multiple")
    parser.add_argument("--bull-pe", type=float, default=None, help="Override Bull case exit P/E multiple")

    # Non-linear operating leverage options
    parser.add_argument("--target-eps-yr2", type=float, default=None, help="Explicit Yr 2 consensus EPS in ₹ (for platform compounders)")
    parser.add_argument("--rev-cagr", type=float, default=None, help="Expected Revenue CAGR over horizon (e.g. 0.35 for 35%%)")
    parser.add_argument("--current-margin", type=float, default=None, help="Current Net Profit Margin (e.g. 0.0064 for 0.64%%)")
    parser.add_argument("--target-margin-yr2", type=float, default=None, help="Target Yr 2 Net Profit Margin (e.g. 0.03 for 3.0%%)")

    args = parser.parse_args()
    evaluate_forward_growth(
        ticker=args.ticker,
        cmp=args.cmp,
        mcap=args.mcap,
        current_eps=args.eps,
        current_pe=args.pe,
        guided_cagr=args.growth,
        bull_cagr=args.bull_growth,
        base_exit_growth=args.base_exit_growth,
        bull_exit_growth=args.bull_exit_growth,
        base_peg=args.base_peg,
        bull_peg=args.bull_peg,
        base_reason=args.base_reason,
        bull_reason=args.bull_reason,
        base_prob=args.base_prob,
        bull_prob=args.bull_prob,
        dilution_pct_annual=args.dilution,
        margin_expansion_pct_annual=args.margin_expansion,
        historical_guidance_reliability=args.haircut,
        target_eps_yr2=args.target_eps_yr2,
        rev_cagr=args.rev_cagr,
        current_margin=args.current_margin,
        target_margin_yr2=args.target_margin_yr2,
        as_of_date=args.date,
        half_override=args.half,
        fy_override=args.fy,
        base_pe=args.base_pe,
        bull_pe=args.bull_pe
    )

def calibrate_stock_parameters(company_data: dict) -> dict:
    sales_3yr = company_data.get("sales_growth_3yr")
    pat_3yr = company_data.get("profit_growth_3yr")
    roe_3yr = company_data.get("roe_3yr")
    
    # 1. Base Case CAGR: Anchor realistically to recent momentum
    if sales_3yr is not None and sales_3yr > 0:
        if sales_3yr >= 50.0:
            base_cagr = min(30, max(22, int(round(sales_3yr * 0.45))))
        elif sales_3yr >= 30.0:
            base_cagr = min(26, max(20, int(round(sales_3yr * 0.65))))
        elif sales_3yr >= 20.0:
            base_cagr = min(23, max(18, int(round(sales_3yr * 0.85))))
        else:
            base_cagr = max(14, min(20, int(round(sales_3yr))))
    else:
        rev_hist = company_data.get("rev_history", [])
        if len(rev_hist) >= 2 and rev_hist[0] > 0 and rev_hist[-1] > rev_hist[0]:
            n_yrs = len(rev_hist) - 1
            calc_cagr = (math.pow(rev_hist[-1] / rev_hist[0], 1.0 / n_yrs) - 1.0) * 100
            base_cagr = max(15, min(28, int(round(calc_cagr * 0.65))))
        else:
            base_cagr = 20

    # 2. Bull Case CAGR: typically +6% to +8% over Base Case
    bull_cagr = min(45, base_cagr + (8 if (sales_3yr or base_cagr) >= 25 else 6))

    # 3. Base Exit Growth: anchored to ROE and terminal reinvestment rate
    if roe_3yr is not None and roe_3yr > 0:
        base_exit_g = min(20.0, max(14.0, round(roe_3yr * 0.6, 1)))
    else:
        base_exit_g = 16.0
    bull_exit_g = min(25.0, round(base_exit_g * 1.3, 1))

    # 4. Probability Weighting (calibrated to cash conversion & governance)
    cum_cfo = sum(company_data.get("cfo_history", []))
    cum_pat = sum(company_data.get("pat_history", []))
    cfo_pat_ratio = (cum_cfo / cum_pat) if cum_pat > 0 else 0.5

    if cfo_pat_ratio >= 0.80 and (sales_3yr or base_cagr) >= 22:
        base_prob = 50
        rationale = f"Elite execution & cash conversion (CFO/PAT {cfo_pat_ratio:.1f}x) $\\implies$ 50/50 balanced weighting"
    elif cfo_pat_ratio >= 0.50:
        base_prob = 55
        rationale = f"Solid operational delivery (CFO/PAT {cfo_pat_ratio:.1f}x) $\\implies$ 55/45 institutional standard"
    elif cfo_pat_ratio < 0.20:
        base_prob = 65
        rationale = f"Working capital friction (CFO/PAT {cfo_pat_ratio:.1f}x) $\\implies$ 65/35 margin-of-safety penalty"
    else:
        base_prob = 60
        rationale = "Prudent institutional allocation"

    return {
        "base_cagr": base_cagr,
        "bull_cagr": bull_cagr,
        "base_exit_g": base_exit_g,
        "bull_exit_g": bull_exit_g,
        "base_peg": 1.60,
        "bull_peg": 1.85,
        "base_prob": base_prob,
        "bull_prob": 100 - base_prob,
        "cfo_pat_ratio": round(cfo_pat_ratio, 2),
        "rationale": rationale
    }
