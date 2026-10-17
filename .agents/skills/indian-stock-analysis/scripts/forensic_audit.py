#!/usr/bin/env python3
"""
forensic_audit.py - Forensic Accounting & Balance Sheet Hygiene Engine
Audits earnings quality, cash conversion integrity, working capital strain,
and distress / manipulation metrics for Indian listed companies.
"""

import sys
import argparse

def compute_cfo_pat_ratio(cfo_list, pat_list):
    """
    Computes yearly and cumulative CFO/PAT ratio.
    cfo_list and pat_list should be ordered from oldest to latest year.
    """
    yearly_ratios = []
    for cfo, pat in zip(cfo_list, pat_list):
        if pat > 0:
            yearly_ratios.append(cfo / pat)
        elif cfo > 0:
            yearly_ratios.append(float('inf'))
        else:
            yearly_ratios.append(0.0)
    
    total_cfo = sum(cfo_list)
    total_pat = sum(pat_list)
    cum_ratio = total_cfo / total_pat if total_pat > 0 else (1.0 if total_cfo >= 0 else 0.0)
    return yearly_ratios, cum_ratio, total_cfo, total_pat

def evaluate_altman_z_em(working_capital, total_assets, retained_earnings, ebit, book_equity, total_liabilities):
    """
    Altman Z-Score for Emerging Markets (Z''-score):
    Z'' = 6.56*(X1) + 3.26*(X2) + 6.72*(X3) + 1.05*(X4)
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = Operating Income (EBIT) / Total Assets
    X4 = Book Value of Equity / Total Liabilities
    Thresholds:
      Z'' > 2.60: Safe Zone
      1.10 <= Z'' <= 2.60: Grey Zone
      Z'' < 1.10: Distress Zone
    """
    if total_assets <= 0 or total_liabilities <= 0:
        return None, "Invalid inputs"
    x1 = working_capital / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = book_equity / total_liabilities
    z_double_prime = (6.56 * x1) + (3.26 * x2) + (6.72 * x3) + (1.05 * x4)
    
    if z_double_prime > 2.60:
        zone = "SAFE ZONE (Low bankruptcy / distress probability)"
        status = "🟢 SAFE"
    elif z_double_prime >= 1.10:
        zone = "GREY ZONE (Moderate financial risk, monitor liquidity)"
        status = "🟡 GREY"
    else:
        zone = "DISTRESS ZONE (High insolvency / liquidity risk)"
        status = "🔴 DISTRESS"
    return z_double_prime, zone, status

def print_forensic_report(ticker, years, cfo_vals, pat_vals, revenue_vals, receivables_vals,
                          promoter_pledging=0.0, contingent_liab_pct=0.0,
                          z_score=None, z_zone=None, z_status=None):
    print(f"================================================================================")
    print(f" FORENSIC ACCOUNTING & EARNINGS QUALITY AUDIT: {ticker.upper()}")
    print(f"================================================================================")
    
    # 1. CFO vs PAT Analysis
    yearly_ratios, cum_ratio, total_cfo, total_pat = compute_cfo_pat_ratio(cfo_vals, pat_vals)
    print(f"\n1. CASH FLOW CONVERSION REALITY (CFO vs PAT)")
    print(f"--------------------------------------------------------------------------------")
    header = f"{'Year':<10}" + "".join([f"{y:>12}" for y in years])
    cfo_row = f"{'CFO (₹ Cr)':<10}" + "".join([f"{v:>12,.1f}" for v in cfo_vals])
    pat_row = f"{'PAT (₹ Cr)':<10}" + "".join([f"{v:>12,.1f}" for v in pat_vals])
    ratio_row = f"{'CFO/PAT':<10}" + "".join([f"{r:>12.2f}" for r in yearly_ratios])
    print(header)
    print(cfo_row)
    print(pat_row)
    print(ratio_row)
    print(f"--------------------------------------------------------------------------------")
    print(f" Cumulative CFO (Sum):  ₹{total_cfo:,.1f} Cr")
    print(f" Cumulative PAT (Sum):  ₹{total_pat:,.1f} Cr")
    print(f" Cumulative CFO/PAT:    {cum_ratio:.2f}x")
    
    if cum_ratio >= 1.0:
        cfo_status = "🟢 PRISTINE: Profits convert 100%+ into hard operating cash flow."
    elif cum_ratio >= 0.8:
        cfo_status = "🟢 ACCEPTABLE: Cash conversion is healthy (>80%)."
    elif cum_ratio >= 0.5:
        cfo_status = "🟡 CAUTION: Moderate divergence (<80%). Working capital is trapping profits."
    else:
        cfo_status = "🔴 SEVERE RED FLAG: Less than 50% of accounting profits convert to cash. Investigate revenue recognition!"
    print(f" Forensic Assessment:   {cfo_status}")

    # 2. Revenue vs Receivables Growth Check
    if len(revenue_vals) >= 2 and len(receivables_vals) >= 2:
        rev_growth = ((revenue_vals[-1] - revenue_vals[0]) / abs(revenue_vals[0])) * 100 if revenue_vals[0] != 0 else 0
        rec_growth = ((receivables_vals[-1] - receivables_vals[0]) / abs(receivables_vals[0])) * 100 if receivables_vals[0] != 0 else 0
        print(f"\n2. REVENUE RECOGNITION & WORKING CAPITAL STRAIN")
        print(f"--------------------------------------------------------------------------------")
        print(f" Revenue Growth ({years[0]} -> {years[-1]}):     {rev_growth:+.1f}%")
        print(f" Receivables Growth ({years[0]} -> {years[-1]}): {rec_growth:+.1f}%")
        
        if rec_growth > (rev_growth * 1.5) and rec_growth > 20:
            rec_status = "🔴 HIGH RISK: Trade receivables are compounding significantly faster than revenue. Risk of channel stuffing or unbilled revenue."
        elif rec_growth > rev_growth:
            rec_status = "🟡 ELEVATED: Receivables growing faster than top-line; monitor debtor collection cycles."
        else:
            rec_status = "🟢 HEALTHY: Receivables growth is disciplined and below top-line growth."
        print(f" Assessment: {rec_status}")

    # 3. Governance & Balance Sheet Health
    print(f"\n3. GOVERNANCE & BALANCE SHEET INTEGRITY")
    print(f"--------------------------------------------------------------------------------")
    print(f" Promoter Pledging:            {promoter_pledging:.2f}%")
    if promoter_pledging == 0:
        pledge_status = "🟢 ZERO: Zero promoter shares pledged."
    elif promoter_pledging < 10:
        pledge_status = "🟡 LOW: Under 10% pledged, monitor trend."
    elif promoter_pledging < 25:
        pledge_status = "🟠 ELEVATED: 10%-25% pledged, risk of margin-call forced selling during drawdowns."
    else:
        pledge_status = "🔴 CRITICAL RED FLAG: >25% of promoter holdings pledged. High structural distress risk."
    print(f" Pledging Audit:               {pledge_status}")

    print(f" Contingent Liabilities (% NW): {contingent_liab_pct:.1f}%")
    if contingent_liab_pct < 10:
        cont_status = "🟢 LOW: Contingent liabilities well below 10% of net worth."
    elif contingent_liab_pct < 25:
        cont_status = "🟡 MODERATE: 10%-25% of net worth, check tax disputes & guarantees."
    else:
        cont_status = "🔴 HIGH: >25% of net worth in contingent liabilities. Material hidden balance sheet claim."
    print(f" Contingent Liabilities Audit: {cont_status}")

    # 4. Altman Z-Score if calculated
    if z_score is not None:
        print(f"\n4. FINANCIAL DISTRESS / ALTMAN Z''-SCORE (EMERGING MARKETS)")
        print(f"--------------------------------------------------------------------------------")
        print(f" Altman Z''-Score:              {z_score:.2f} ({z_status})")
        print(f" Zone Interpretation:          {z_zone}")

    print(f"================================================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forensic Accounting and Earnings Quality Audit")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g., ZOMATO, TRENT)")
    parser.add_argument("--years", nargs="+", required=True, help="List of fiscal years (e.g. FY21 FY22 FY23 FY24 FY25)")
    parser.add_argument("--cfo", nargs="+", type=float, required=True, help="Operating cash flow values in ₹ Cr")
    parser.add_argument("--pat", nargs="+", type=float, required=True, help="PAT values in ₹ Cr")
    parser.add_argument("--rev", nargs="+", type=float, required=True, help="Revenue values in ₹ Cr")
    parser.add_argument("--rec", nargs="+", type=float, required=True, help="Receivables values in ₹ Cr")
    parser.add_argument("--pledge", type=float, default=0.0, help="Promoter pledging percentage (default: 0.0)")
    parser.add_argument("--contingent", type=float, default=0.0, help="Contingent liabilities as %% of Net Worth")
    parser.add_argument("--wc", type=float, default=None, help="Working capital in ₹ Cr (for Altman Z)")
    parser.add_argument("--assets", type=float, default=None, help="Total assets in ₹ Cr (for Altman Z)")
    parser.add_argument("--re", type=float, default=None, help="Retained earnings in ₹ Cr (for Altman Z)")
    parser.add_argument("--ebit", type=float, default=None, help="EBIT in ₹ Cr (for Altman Z)")
    parser.add_argument("--equity", type=float, default=None, help="Book equity in ₹ Cr (for Altman Z)")
    parser.add_argument("--liab", type=float, default=None, help="Total liabilities in ₹ Cr (for Altman Z)")

    args = parser.parse_args()
    
    z_score, z_zone, z_status = None, None, None
    if all(v is not None for v in [args.wc, args.assets, args.re, args.ebit, args.equity, args.liab]):
        z_score, z_zone, z_status = evaluate_altman_z_em(
            args.wc, args.assets, args.re, args.ebit, args.equity, args.liab
        )

    print_forensic_report(
        ticker=args.ticker,
        years=args.years,
        cfo_vals=args.cfo,
        pat_vals=args.pat,
        revenue_vals=args.rev,
        receivables_vals=args.rec,
        promoter_pledging=args.pledge,
        contingent_liab_pct=args.contingent,
        z_score=z_score,
        z_zone=z_zone,
        z_status=z_status
    )
