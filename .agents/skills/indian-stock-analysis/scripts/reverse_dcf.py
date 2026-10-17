#!/usr/bin/env python3
"""
reverse_dcf.py - Expectations Investing & Reverse DCF Quantitative Engine
Based on Michael Mauboussin's Expectations Investing framework.

Calculates:
1. Implied 10-year FCF CAGR embedded in current Market Cap / Enterprise Value.
2. Sensitivity Matrix (WACC vs Terminal Growth Rate).
3. 4-State Probabilistic Valuation (Disaster, Bear, Base, Bull) with Expected Target Price,
   Asymmetry Ratio, and Margin of Safety.
"""

import sys
import argparse
import math

def calculate_implied_growth(enterprise_value, current_fcf, wacc, terminal_growth, years=10):
    """
    Finds the compound annual growth rate (g) of FCF over 'years' such that:
    EV = Sum_{t=1..N} [ FCF_0 * (1+g)^t / (1+wacc)^t ] + Terminal Value discounted.
    Terminal Value = FCF_N * (1+g_term) / (wacc - g_term) discounted by (1+wacc)^N.
    """
    if current_fcf <= 0:
        return None

    # Binary search for implied CAGR between -50% and +100%
    low_g = -0.50
    high_g = 1.50
    tolerance = 1e-4

    def get_ev(g):
        pv_fcf = 0.0
        fcf_t = current_fcf
        for t in range(1, years + 1):
            fcf_t *= (1 + g)
            pv_fcf += fcf_t / ((1 + wacc) ** t)
        
        # Terminal value at year N
        tv = (fcf_t * (1 + terminal_growth)) / (wacc - terminal_growth)
        pv_tv = tv / ((1 + wacc) ** years)
        return pv_fcf + pv_tv

    # Check boundaries
    if get_ev(low_g) > enterprise_value:
        return low_g
    if get_ev(high_g) < enterprise_value:
        return high_g

    for _ in range(100):
        mid_g = (low_g + high_g) / 2.0
        est_ev = get_ev(mid_g)
        if abs(est_ev - enterprise_value) < enterprise_value * tolerance:
            return mid_g
        if est_ev < enterprise_value:
            low_g = mid_g
        else:
            high_g = mid_g

    return (low_g + high_g) / 2.0

def dcf_valuation(current_fcf, growth_rate, wacc, terminal_growth, net_debt, shares_count, years=10):
    """Computes target equity value per share given explicit growth assumptions."""
    pv_fcf = 0.0
    fcf_t = current_fcf
    for t in range(1, years + 1):
        fcf_t *= (1 + growth_rate)
        pv_fcf += fcf_t / ((1 + wacc) ** t)
    
    tv = (fcf_t * (1 + terminal_growth)) / (wacc - terminal_growth)
    pv_tv = tv / ((1 + wacc) ** years)
    ev = pv_fcf + pv_tv
    equity_val = ev - net_debt
    target_price = equity_val / shares_count if shares_count > 0 else 0
    return ev, equity_val, target_price

def print_reverse_dcf_report(ticker, cmp, market_cap_cr, net_debt_cr, current_fcf_cr, wacc=0.115, terminal_growth=0.05, shares_cr=None):
    """
    All currency in ₹ Crores (Cr).
    """
    ev_cr = market_cap_cr + net_debt_cr
    if not shares_cr or shares_cr <= 0:
        shares_cr = market_cap_cr / cmp

    print(f"================================================================================")
    print(f" EXPECTATIONS INVESTING & REVERSE DCF ENGINE: {ticker.upper()}")
    print(f"================================================================================")
    print(f" Current Market Price (CMP):    ₹{cmp:,.2f}")
    print(f" Market Capitalization:          ₹{market_cap_cr:,.2f} Cr")
    print(f" Net Debt (Debt - Cash):         ₹{net_debt_cr:,.2f} Cr")
    print(f" Enterprise Value (EV):          ₹{ev_cr:,.2f} Cr")
    print(f" Base Free Cash Flow (FCF_0):    ₹{current_fcf_cr:,.2f} Cr")
    print(f" Cost of Capital (WACC):         {wacc*100:.2f}%")
    print(f" Terminal Growth Rate (g_term):  {terminal_growth*100:.2f}%")
    print(f" Implied Shares Count:           {shares_cr:,.2f} Cr shares")
    print(f"--------------------------------------------------------------------------------")

    implied_g = calculate_implied_growth(ev_cr, current_fcf_cr, wacc, terminal_growth)

    if implied_g is not None:
        print(f"\n>>> REVERSE DCF CONCLUSION:")
        print(f"    To justify the current EV of ₹{ev_cr:,.2f} Cr, the company must grow Free Cash Flow")
        print(f"    at a 10-year CAGR of {implied_g*100:.2f}% annually with a terminal growth of {terminal_growth*100:.1f}%.")
        
        # Reality benchmark
        if implied_g > 0.35:
            feasibility = "HEROIC / ULTRA-HIGH RISK (Implies >35% compounding for a decade; rare in Indian equity history)"
        elif implied_g > 0.22:
            feasibility = "AGGRESSIVE (Requires sustained high-growth moat and minimal reinvestment drag)"
        elif implied_g > 0.12:
            feasibility = "REALISTIC / MODERATE (Consistent with quality compounder execution)"
        elif implied_g > 0.05:
            feasibility = "CONSERVATIVE / VALUE (Significant pessimism priced in)"
        else:
            feasibility = "DISTRESSED / BARGAIN BASEMENT (Priced for secular decay or turnaround)"
        print(f"    Feasibility Assessment: {feasibility}")
    else:
        print("\n>>> Base FCF is negative or zero. Reverse DCF requires normalized steady-state FCF margin.")

    # Sensitivity Table (WACC vs Terminal Growth)
    print(f"\n--- SENSITIVITY TABLE: Implied 10-Yr FCF CAGR across WACC & Terminal Growth ---")
    wacc_range = [wacc - 0.015, wacc, wacc + 0.015]
    tg_range = [terminal_growth - 0.01, terminal_growth, terminal_growth + 0.01]
    
    header = f"{'WACC \\ g_term':<15}" + "".join([f"{tg*100:>12.1f}%" for tg in tg_range])
    print(header)
    print("-" * len(header))
    for w in wacc_range:
        row = f"{w*100:>10.2f}%    "
        for tg in tg_range:
            g = calculate_implied_growth(ev_cr, current_fcf_cr, w, tg)
            if g is not None:
                row += f"{g*100:>12.2f}%"
            else:
                row += f"{'N/A':>12}"
        print(row)

    # 4-State Probabilistic Valuation Model
    print(f"\n--- 4-STATE PROBABILISTIC VALUATION MATRIX ---")
    scenarios = [
        {"name": "Disaster / Tail-Risk", "prob": 0.10, "growth": -0.05, "wacc_adj": 0.02, "mult_label": "Severe compression / regulatory"},
        {"name": "Bear Case",            "prob": 0.25, "growth": 0.08,  "wacc_adj": 0.01, "mult_label": "Margin pressure / execution miss"},
        {"name": "Base Case",            "prob": 0.50, "growth": 0.18,  "wacc_adj": 0.00, "mult_label": "Consensus delivery & moat defense"},
        {"name": "Bull Case",            "prob": 0.15, "growth": 0.30,  "wacc_adj": -0.01,"mult_label": "TAM expansion & operating leverage"}
    ]

    expected_price = 0.0
    scenario_results = []
    for sc in scenarios:
        w_sc = wacc + sc["wacc_adj"]
        ev_sc, eq_sc, pt_sc = dcf_valuation(current_fcf_cr, sc["growth"], w_sc, terminal_growth, net_debt_cr, shares_cr)
        expected_price += sc["prob"] * pt_sc
        scenario_results.append({
            "name": sc["name"],
            "prob": sc["prob"],
            "growth": sc["growth"],
            "target": pt_sc,
            "return_pct": ((pt_sc - cmp) / cmp) * 100
        })

    print(f"{'Scenario':<22} | {'Prob':<6} | {'FCF CAGR':<10} | {'Target (₹)':<12} | {'Return (%)':<10}")
    print("-" * 72)
    for res in scenario_results:
        print(f"{res['name']:<22} | {res['prob']*100:>4.0f}% | {res['growth']*100:>8.1f}% | ₹{res['target']:>10.2f} | {res['return_pct']:>8.1f}%")
    
    print("-" * 72)
    ev_return = ((expected_price - cmp) / cmp) * 100
    bear_pt = scenario_results[1]["target"]
    bull_pt = scenario_results[3]["target"]
    
    downside = max(cmp - bear_pt, 1e-4)
    upside = max(bull_pt - cmp, 0)
    asymmetry = upside / downside if downside > 0 else 0

    print(f" EXPECTED VALUE (Weighted Target):  ₹{expected_price:,.2f}  ({ev_return:+.1f}%)")
    print(f" ASYMMETRY RATIO (Bull / Bear):     {asymmetry:.2f}x (Upside to Bull ₹{bull_pt:.1f} vs Downside to Bear ₹{bear_pt:.1f})")
    print(f" MARGIN OF SAFETY:                  {ev_return:.1f}%")
    print(f"================================================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reverse DCF & Probabilistic Valuation Engine")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g., ZOMATO, TRENT)")
    parser.add_argument("--cmp", type=float, required=True, help="Current Market Price (₹)")
    parser.add_argument("--mcap", type=float, required=True, help="Market Cap in ₹ Crores")
    parser.add_argument("--netdebt", type=float, default=0.0, help="Net Debt (Debt - Cash) in ₹ Crores (negative if net cash)")
    parser.add_argument("--fcf", type=float, required=True, help="Base Free Cash Flow in ₹ Crores")
    parser.add_argument("--wacc", type=float, default=0.115, help="WACC discount rate (default: 0.115 / 11.5%%)")
    parser.add_argument("--terminal-growth", type=float, default=0.05, help="Terminal growth rate (default: 0.05 / 5%%)")
    parser.add_argument("--shares", type=float, default=None, help="Shares count in Crores (optional)")

    args = parser.parse_args()
    print_reverse_dcf_report(
        ticker=args.ticker,
        cmp=args.cmp,
        market_cap_cr=args.mcap,
        net_debt_cr=args.netdebt,
        current_fcf_cr=args.fcf,
        wacc=args.wacc,
        terminal_growth=args.terminal_growth,
        shares_cr=args.shares
    )
