#!/usr/bin/env python3
"""predict/scripts/backtest_smallcap250_set2.py.

Point-in-Time Backtest & Failure Mode Audit on a Fresh Second Sample (Set 2)
of 30 randomly sampled NIFTY Smallcap 250 constituents:
- Baseline Date: March 31, 2023 (Point-in-time trailing FY23 fundamentals & CMP)
- Holding Horizon: March 31, 2023 -> March 31, 2026 (Full 3-Year Compounding Cycle)
- Benchmark: NIFTY Smallcap 100 (+73.7%), NIFTY Midcap 100 (+80.1%), NIFTY 50 (+31.5%)
- Policy: Strict zero-cheat / zero-lookahead discipline via investable_execution.py:
  1. Formula-only growth underwriting (decide_growth from point-in-time FY23 sales CAGR + 1y acceleration).
  2. Normalized mid-cycle margin bridge (compute_normalized_margin_eps for cyclical troughs).
  3. Uniform target formula (uniform_targets without any custom turnaround bridges).
  4. Real close-price execution with transaction costs (0.5% entry + 0.5% exit).
  5. 3-Tranche Moonbag Protocol (30% @ 1.0x Bull, 30% @ 1.8x Bull, 40% Moonbag runner).
  6. Asymmetric Re-Rating Gate & Moat Proximity Buffer active.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from investable_execution import (
    decide_growth,
    uniform_targets,
    execute_investable,
    compute_normalized_margin_eps,
    evaluate_asymmetric_rerating_gate,
    evaluate_dynamic_debt_serviceability,
    evaluate_zero_debt_wc_gate,
    evaluate_moat_proximity_buffer
)

_DATA_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")
_REPORTS_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "reports")
CACHE_FILE = os.path.join(_DATA_DIR, "smallcap250_set2_cache.json")
OUTPUT_JSON = os.path.join(_DATA_DIR, "backtest_smallcap250_set2_results.json")


def clean_num(val):
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def run_backtest():
    print("=" * 100)
    print(" NIFTY SMALLCAP 250 POINT-IN-TIME BACKTEST (SET 2: 30 FRESH STOCKS)")
    print(" Baseline Date: March 31, 2023 | Horizon: March 31, 2026 (3 Full Fiscal Years)")
    print(" Execution: Real Closing Prices, 0.5% Entry Cost, 0.5% Exit Cost, 3-Tranche Moonbag")
    print("=" * 100)

    if not os.path.isfile(CACHE_FILE):
        print(f"Error: Cache file {CACHE_FILE} not found. Please run fetch_smallcap_set2_data.py first.")
        sys.exit(1)

    with open(CACHE_FILE, "r") as f:
        data = json.load(f)

    start_dt = pd.to_datetime("2023-03-31")
    end_dt = pd.to_datetime("2026-03-31")

    benchmarks = {
        "NIFTY 50": {"return": 31.5, "cagr": 9.6},
        "NIFTY Midcap 100": {"return": 80.1, "cagr": 21.7},
        "NIFTY Smallcap 100": {"return": 73.7, "cagr": 20.2}
    }

    records = []

    for ticker, item in data.items():
        name = item["name"]
        sector = item["sector"]
        disqualify_sector = item.get("disqualify_sector", False)
        fin = item["financials"]
        ymap = fin.get("year_map", {})

        # 1. Parse Price Chart & Point-in-Time Trajectory
        df_chart = pd.DataFrame(item["chart"])
        if df_chart.empty:
            continue
        df_chart["Date"] = pd.to_datetime(df_chart["Date"])
        df_chart = df_chart.sort_values("Date").reset_index(drop=True)

        sub_p0 = df_chart[df_chart["Date"] <= start_dt + pd.Timedelta(days=10)]
        sub_p1 = df_chart[df_chart["Date"] <= end_dt + pd.Timedelta(days=10)]

        if sub_p0.empty or sub_p1.empty:
            continue

        p0_row = sub_p0.iloc[-1]
        p1_row = sub_p1.iloc[-1]
        p0 = float(p0_row["Price"])
        p1 = float(p1_row["Price"])
        dma200_0 = float(p0_row.get("DMA200", 0.0)) if pd.notnull(p0_row.get("DMA200")) else 0.0
        dma50_0 = float(p0_row.get("DMA50", 0.0)) if pd.notnull(p0_row.get("DMA50")) else 0.0

        traj = df_chart[(df_chart["Date"] >= p0_row["Date"]) & (df_chart["Date"] <= p1_row["Date"])].copy()
        peak_price = float(traj["Price"].max()) if not traj.empty else p0
        peak_gain = ((peak_price - p0) / p0) * 100

        # Maximum Drawdown from running peak
        if not traj.empty:
            cummax = traj["Price"].cummax()
            dd = ((traj["Price"] - cummax) / cummax) * 100
            max_dd = float(dd.min())
        else:
            max_dd = 0.0

        bh_return = ((p1 - p0) / p0) * 100
        bh_cagr = (((p1 / p0) ** (1 / 3.0)) - 1) * 100 if p1 > 0 else -100

        # 2. Extract Point-in-Time Fundamentals (Strictly FY23 and Earlier)
        idx_23 = ymap.get("2023") if "2023" in ymap else ymap.get(2023)
        idx_22 = ymap.get("2022") if "2022" in ymap else ymap.get(2022)
        idx_20 = ymap.get("2020") if "2020" in ymap else ymap.get(2020)
        idx_26 = ymap.get("2026") if "2026" in ymap else ymap.get(2026)

        eps_23 = fin["eps"][idx_23] if idx_23 is not None and len(fin["eps"]) > idx_23 else 0.0
        sales_23 = fin["sales"][idx_23] if idx_23 is not None and len(fin["sales"]) > idx_23 else 0.0
        pat_23 = fin["pat"][idx_23] if idx_23 is not None and len(fin["pat"]) > idx_23 else 0.0

        sales_22 = fin["sales"][idx_22] if idx_22 is not None and len(fin["sales"]) > idx_22 else 0.0
        sales_20 = fin["sales"][idx_20] if idx_20 is not None and len(fin["sales"]) > idx_20 else 0.0
        pat_20 = fin["pat"][idx_20] if idx_20 is not None and len(fin["pat"]) > idx_20 else 0.0

        eps_26 = fin["eps"][idx_26] if idx_26 is not None and len(fin["eps"]) > idx_26 else 0.0
        sales_26 = fin["sales"][idx_26] if idx_26 is not None and len(fin["sales"]) > idx_26 else 0.0

        # Point-in-time growth metrics
        sales_cagr_3y = (((sales_23 / sales_20) ** (1 / 3.0)) - 1) * 100 if sales_23 > 0 and sales_20 > 0 else 0.0
        sales_1y = ((sales_23 / sales_22) - 1) * 100 if sales_23 > 0 and sales_22 > 0 else None

        # Prior years history for Normalized Mid-Cycle Margin Bridge (Flaw 2 Correction)
        prior_sales, prior_pat, prior_eps = [], [], []
        for y in sorted([int(k) for k in ymap.keys() if int(k) < 2023]):
            iy = ymap.get(str(y)) if str(y) in ymap else ymap.get(y)
            if iy is not None:
                if iy < len(fin.get("sales", [])):
                    prior_sales.append(fin["sales"][iy])
                if iy < len(fin.get("pat", [])):
                    prior_pat.append(fin["pat"][iy])
                if iy < len(fin.get("eps", [])):
                    prior_eps.append(fin["eps"][iy])

        base_eps, is_trough_base, med_npm = compute_normalized_margin_eps(
            sales=sales_23, pat=pat_23, eps=eps_23,
            sales_history=prior_sales, pat_history=prior_pat, eps_history=prior_eps
        )
        pe_0 = p0 / base_eps if base_eps > 0 else float("inf")

        # 4-Year Cash Conversion Reality (FY20 to FY23)
        cfo_list, pat_list = [], []
        for y in [2020, 2021, 2022, 2023]:
            iy = ymap.get(str(y)) if str(y) in ymap else ymap.get(y)
            if iy is not None:
                if len(fin.get("cfo", [])) > iy:
                    cfo_list.append(fin["cfo"][iy])
                if len(fin.get("pat", [])) > iy:
                    pat_list.append(fin["pat"][iy])
        cfo_pat_4y = sum(cfo_list) / sum(pat_list) if sum(pat_list) > 0 else 0.50

        # Point-in-time Debt / Equity
        debt_23 = fin.get("borrowings", [0])[idx_23] if idx_23 is not None and len(fin.get("borrowings", [])) > idx_23 else 0.0
        equity_23 = fin.get("equity", [0])[idx_23] if idx_23 is not None and len(fin.get("equity", [])) > idx_23 else 0.0
        reserves_23 = fin.get("reserves", [0])[idx_23] if idx_23 is not None and len(fin.get("reserves", [])) > idx_23 else 0.0
        networth_23 = equity_23 + reserves_23
        debt_equity_23 = debt_23 / networth_23 if networth_23 > 0 else 0.0

        # 3. Formula-Only Algorithmic Underwriting (Zero Ticker Name Lookahead)
        model_growth, bull_growth = decide_growth(sales_cagr_3y, sales_1y)
        fwd_pe_yr2, bull_target_price, bull_upside_pct = uniform_targets(base_eps, p0, model_growth, bull_growth)
        if fwd_pe_yr2 == float("inf"):
            fwd_pe_yr2 = pe_0

        # 4. Strict Quantitative Investment Gates (With Institutional Flaw Fixes)
        # Gate 1: Sunrise Growth Filter (Flaw 1 Correction: Asymmetric Re-Rating Gate)
        # Deep-value quality compounders with safe debt calibrate hurdle down to 14.0%
        growth_hurdle = evaluate_asymmetric_rerating_gate(
            current_pe=pe_0, roce=18.0, fwd_pe_yr2=fwd_pe_yr2,
            debt_equity=debt_equity_23, cfo_pat=cfo_pat_4y
        )
        is_deep_value = (growth_hurdle == 14.0)
        gate_growth = model_growth >= growth_hurdle

        # Gate 2: Valuation Hurdle (2-Year Forward P/E <= 50x)
        gate_pe = fwd_pe_yr2 <= 50.0

        # Gate 3: Bull Upside Hurdle (>= 50%)
        gate_upside = bull_upside_pct >= 50.0

        # Gate 4: Dynamic Debt Serviceability Gate & Zero-Debt Long-Cycle WC Gate
        debt_pass, debt_reason = evaluate_dynamic_debt_serviceability(debt_equity_23, cfo_pat_4y)
        cfo_pass, cfo_hurdle, cfo_reason = evaluate_zero_debt_wc_gate(debt_equity_23, cfo_pat_4y)
        forensic_pass = cfo_pass and debt_pass and (not disqualify_sector) and (base_eps > 0)

        # Gate 5: Technical Trend Stage 2 Gate with Moat Proximity Buffer (Flaw 4 Correction)
        # Structural franchises with fortress balance sheet can be accumulated within 13% below 200-DMA
        is_high_quality = (
            (debt_equity_23 <= 0.15 and cfo_pat_4y >= 0.80)
            or (debt_equity_23 <= 0.85 and cfo_pat_4y >= 1.50)
            or (debt_equity_23 <= 0.05 and cfo_pat_4y >= 0.30)
        )
        stage2_pass, stage2_reason = evaluate_moat_proximity_buffer(p0, dma200_0, is_high_quality=is_high_quality)

        # Verdict Assignment
        if disqualify_sector:
            verdict = "REJECT (SECTOR: Highly Leveraged Financial / Credit Fragility)"
            is_approved = False
            reject_category = "SECTOR_BLANKET_EXCLUSION"
        elif base_eps <= 0:
            verdict = "REJECT (DEPRESSED BASE: Negative Earnings Base)"
            is_approved = False
            reject_category = "DEPRESSED_BASE_VALUATION_TRAP"
        elif not gate_growth:
            verdict = f"REJECT (LOW-GROWTH TRAP: Projected CAGR {model_growth:.1f}% < {growth_hurdle:.0f}% Hurdle)"
            is_approved = False
            reject_category = "LOW_GROWTH_TRAP"
        elif not gate_pe:
            verdict = f"REJECT (VALUATION CEILING: 2Y Fwd PE {fwd_pe_yr2:.1f}x > 50x)"
            is_approved = False
            reject_category = "FORWARD_PE_OVERFLOW"
        elif not gate_upside:
            verdict = f"REJECT (INSUFFICIENT UPSIDE: Bull Upside {bull_upside_pct:+.1f}% < 50% Mandate)"
            is_approved = False
            reject_category = "INSUFFICIENT_BULL_UPSIDE"
        elif not forensic_pass:
            verdict = f"REJECT (FORENSIC/SOLVENCY: 4Y CFO/PAT {cfo_pat_4y:.2f}x, D/E {debt_equity_23:.2f}x - {debt_reason})"
            is_approved = False
            reject_category = "FORENSIC_CASH_DIVERGENCE"
        elif not stage2_pass:
            verdict = f"REJECT (STAGE 4 DOWNTREND: P0 ₹{p0:.1f} vs 200-DMA ₹{dma200_0:.1f} - {stage2_reason})"
            is_approved = False
            reject_category = "STAGE_4_DOWNTREND"
        else:
            trough_tag = f" [Mid-Cycle Normalized Base ₹{base_eps:.2f}]" if is_trough_base else ""
            rerate_tag = " [Asymmetric Re-Rating Gate]" if (is_deep_value and model_growth < 20.0) else ""
            prox_tag = " [Moat Pullback Entry]" if (dma200_0 > 0 and p0 < dma200_0) else ""
            verdict = f"APPROVED (STRONG BUY: Growth {model_growth:.1f}%, 2Y Fwd PE {fwd_pe_yr2:.1f}x, Bull Upside {bull_upside_pct:+.1f}%{rerate_tag}{trough_tag}{prox_tag})"
            is_approved = True
            reject_category = "NONE"

        # 5. Real Investable Execution on Closes (Flaw 5 Correction: 3-Tranche Moonbag Protocol)
        closes = traj["Price"].tolist() if not traj.empty else [p0, p1]
        realized_return, strategy_note = execute_investable(
            closes, p0, p1, bull_target_price, is_approved, staged_harvest=True
        )
        strat_ret = realized_return if is_approved else 0.0
        strat_cagr = (((1.0 + (strat_ret / 100.0)) ** (1 / 3.0)) - 1) * 100 if strat_ret > -100 and is_approved else 0.0

        # Type I & Type II Error Audits
        is_type_1_loss = is_approved and (strat_ret < 0)
        is_type_1_error = is_approved and (strat_ret < 0 or max_dd < -35.0)
        is_type_2_error = (not is_approved) and (bh_return > 80.0)

        # Realized 3Y fundamentals (for audit reporting)
        realized_eps_cagr = (((eps_26 / eps_23) ** (1 / 3.0)) - 1) * 100 if eps_26 > 0 and eps_23 > 0 else -100
        realized_sales_cagr = (((sales_26 / sales_23) ** (1 / 3.0)) - 1) * 100 if sales_26 > 0 and sales_23 > 0 else -100

        records.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "p0": round(p0, 2),
            "p1": round(p1, 2),
            "dma200_0": round(dma200_0, 2),
            "eps_23": round(eps_23, 2),
            "base_eps": round(base_eps, 2),
            "is_trough_base": is_trough_base,
            "sales_cagr_3y": round(sales_cagr_3y, 1),
            "sales_1y": round(sales_1y, 1) if sales_1y is not None else None,
            "model_growth": round(model_growth, 1),
            "bull_growth": round(bull_growth, 1),
            "pe_0": round(pe_0, 1),
            "fwd_pe_yr2": round(fwd_pe_yr2, 1),
            "bull_target_price": round(bull_target_price, 2),
            "bull_upside_pct": round(bull_upside_pct, 1),
            "cfo_pat_4y": round(cfo_pat_4y, 2),
            "debt_equity_23": round(debt_equity_23, 2),
            "stage2_pass": stage2_pass,
            "verdict": verdict,
            "is_approved": is_approved,
            "reject_category": reject_category,
            "realized_sales_cagr": round(realized_sales_cagr, 1),
            "realized_eps_cagr": round(realized_eps_cagr, 1),
            "bh_return": round(bh_return, 1),
            "bh_cagr": round(bh_cagr, 1),
            "peak_price": round(peak_price, 2),
            "peak_gain": round(peak_gain, 1),
            "max_dd": round(max_dd, 1),
            "strategy_return": round(strat_ret, 1),
            "strategy_cagr": round(strat_cagr, 1),
            "strategy_note": strategy_note,
            "is_type_1_loss": is_type_1_loss,
            "is_type_1_error": is_type_1_error,
            "is_type_2_error": is_type_2_error
        })

    # Summary Analytics
    app_recs = [r for r in records if r["is_approved"]]
    rej_recs = [r for r in records if not r["is_approved"]]

    app_bh_ret = np.mean([r["bh_return"] for r in app_recs]) if app_recs else 0.0
    app_strat_ret = np.mean([r["strategy_return"] for r in app_recs]) if app_recs else 0.0
    app_strat_cagr = np.mean([r["strategy_cagr"] for r in app_recs]) if app_recs else 0.0
    rej_bh_ret = np.mean([r["bh_return"] for r in rej_recs]) if rej_recs else 0.0

    win_rate = (len([r for r in app_recs if r["strategy_return"] > 0]) / len(app_recs) * 100) if app_recs else 0.0
    beat_smallcap_rate = (len([r for r in app_recs if r["strategy_return"] > 73.7]) / len(app_recs) * 100) if app_recs else 0.0

    type_1_losses = [r for r in records if r.get("is_type_1_loss")]
    type_1_cases = [r for r in records if r["is_type_1_error"]]
    type_2_cases = [r for r in records if r["is_type_2_error"]]

    results = {
        "period": "March 31, 2023 -> March 31, 2026 (3-Year Holding Period)",
        "universe_name": "NIFTY Smallcap 250 Sample Set 2 (30 Stocks)",
        "benchmarks": benchmarks,
        "analytics": {
            "total_evaluated": len(records),
            "approved_count": len(app_recs),
            "rejected_count": len(rej_recs),
            "approved_buy_and_hold_return": round(app_bh_ret, 1),
            "approved_strategy_realized_return": round(app_strat_ret, 1),
            "approved_strategy_realized_cagr": round(app_strat_cagr, 1),
            "rejected_average_return": round(rej_bh_ret, 1),
            "alpha_vs_nifty_smallcap": round(app_strat_ret - 73.7, 1),
            "alpha_vs_nifty_midcap": round(app_strat_ret - 80.1, 1),
            "alpha_vs_nifty_50": round(app_strat_ret - 31.5, 1),
            "win_rate": round(win_rate, 1),
            "beat_smallcap_benchmark_rate": round(beat_smallcap_rate, 1),
            "type_1_loss_count": len(type_1_losses),
            "type_1_error_count": len(type_1_cases),
            "type_2_error_count": len(type_2_cases),
        },
        "records": records,
        "type_1_losses": type_1_losses,
        "type_1_errors": type_1_cases,
        "type_2_errors": type_2_cases
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 100)
    print(" NIFTY SMALLCAP 250 (SET 2) INVESTABLE BACKTEST RESULTS (30 STOCKS)")
    print("=" * 100)
    print(f" Total Stocks Evaluated:                 {len(records)}")
    print(f" Approved Candidates:                    {len(app_recs)} ({len(app_recs)/len(records)*100:.1f}%)")
    print(f" Rejected Candidates:                    {len(rej_recs)} ({len(rej_recs)/len(records)*100:.1f}%)")
    print(f" Approved Realized Strategy Return:      {app_strat_ret:+.1f}% (CAGR: {app_strat_cagr:+.1f}% p.a.) [NET OF COSTS]")
    print(f" Approved Buy-and-Hold Return:           {app_bh_ret:+.1f}%")
    print(f" Rejected Basket Average Return:         {rej_bh_ret:+.1f}%")
    print(f" Alpha vs NIFTY Smallcap 100 (+73.7%):   {app_strat_ret - 73.7:+.1f}%")
    print(f" Alpha vs NIFTY Midcap 100 (+80.1%):     {app_strat_ret - 80.1:+.1f}%")
    print(f" Alpha vs NIFTY 50 (+31.5%):             {app_strat_ret - 31.5:+.1f}%")
    print(f" Win Rate:                               {win_rate:.1f}%")
    print("-" * 100)
    print(f" ⚠️  Type II Errors (Missed Multibaggers): {len(type_2_cases)}")
    for t2 in type_2_cases:
        print(f"   • {t2['ticker']:<12} (+{t2['bh_return']:>5.1f}% B&H): Rejected as [{t2['reject_category']}] - {t2['verdict'][:60]}")
    print(f" ⚠️  Type I Loss Events (Realized Negative Return): {len(type_1_losses)}")
    for t1 in type_1_losses:
        print(f"   • {t1['ticker']:<12} ({t1['strategy_return']:>+5.1f}% Return): Approved as Strong Buy")
    print("=" * 100)


if __name__ == "__main__":
    run_backtest()
