from datetime import datetime
import math

def calculate_forward_pe_valuation(
    cmp: float,
    mcap_cr: float,
    ttm_eps: float,
    ttm_sales: float = 0.0,
    ttm_pat: float = 0.0,
    shares_cr: float = 0.0,
    base_cagr: float = 0.20,
    bull_cagr: float = 0.25,
    base_exit_growth: float = 0.16,
    bull_exit_growth: float = 0.22,
    base_peg: float = 1.60,
    bull_peg: float = 1.85,
    base_prob: float = 0.55,
    bull_prob: float = 0.45,
    as_of_date: datetime = None,
    regime_override: str = "Auto"
):
    if as_of_date is None:
        as_of_date = datetime.now()
        
    month = as_of_date.month
    year = as_of_date.year
    
    # Financial year calculation (April to March)
    if month >= 4:
        running_fy = year + 1
        is_h1 = (month <= 9)
    else:
        running_fy = year
        is_h1 = False
        
    last_reported_fy = running_fy - 1
    
    if is_h1:
        regime_period = "H1 (Q1/Q2)"
        target_yr1_fy = f"FY{running_fy % 100}"
        target_yr2_fy = f"FY{(running_fy + 1) % 100}"
        comp_years_yr1 = 1
        comp_years_yr2 = 2
    else:
        regime_period = "H2 (Q3/Q4 Roll-Forward)"
        target_yr1_fy = f"FY{(running_fy + 1) % 100}"
        target_yr2_fy = f"FY{(running_fy + 2) % 100}"
        comp_years_yr1 = 2
        comp_years_yr2 = 3

    # Detect Regime: Regime 1 (Steady-State Margin) vs Regime 2 (Platform Operating Leverage)
    npm = (ttm_pat / ttm_sales) if (ttm_sales > 0 and ttm_pat > 0) else 0.10
    trailing_pe = (cmp / ttm_eps) if ttm_eps > 0 else 999.0
    
    # Rigorous Classification:
    # Regime 2 (Platform Operating Leverage) applies ONLY when Net Margin is genuinely suppressed (<2.0%)
    # despite substantial business scale (Sales >= ₹1,000 Cr), creating room for non-linear margin expansion (3x-5x).
    # Companies with normal/mature margins (e.g. Cyient DLM at 5.8%, Dixon at 3.5%, Kaynes at 8.5%)
    # belong strictly to Regime 1 (Steady-State Margin Compounders).
    if regime_override == "Regime 2 (Platform)":
        is_platform_compounder = True
        detection_reason = "Manual Override: Forced to Regime 2 (Platform Operating Leverage)"
    elif regime_override == "Regime 1 (Steady-State)":
        is_platform_compounder = False
        detection_reason = "Manual Override: Forced to Regime 1 (Steady-State Margin Compounder)"
    else:
        is_platform_compounder = (npm < 0.020) and (ttm_sales >= 1000.0)
        if is_platform_compounder:
            detection_reason = f"Auto-Detected: Regime 2 (Platform Operating Leverage). Net Profit Margin is suppressed at {npm*100:.2f}% (<2.0%) at scale (₹{ttm_sales:,.0f} Cr revenue), indicating non-linear operating leverage potential."
        else:
            detection_reason = f"Auto-Detected: Regime 1 (Steady-State Margin Compounder). Net Profit Margin of {npm*100:.2f}% (>=2.0%) represents normal operating margins; valuation is driven by top-line volume compounding."
    
    if is_platform_compounder:
        regime_model = "Regime 2: Platform Operating Leverage & Margin Expansion"
        # In Regime 2, revenue compounds aggressively while net margins expand towards steady-state
        rev_cagr_base = max(0.35, base_cagr * 1.6)
        rev_cagr_bull = max(0.42, bull_cagr * 1.7)
        
        target_margin_base = max(0.045, min(0.065, npm * 4.0)) # Expands to 4.5% - 6.5% NPM
        target_margin_bull = max(0.060, min(0.085, npm * 6.0)) # Expands to 6.0% - 8.5% NPM
        
        rev_base_yr1 = ttm_sales * math.pow(1 + rev_cagr_base, comp_years_yr1)
        rev_base_yr2 = ttm_sales * math.pow(1 + rev_cagr_base, comp_years_yr2)
        
        rev_bull_yr1 = ttm_sales * math.pow(1 + rev_cagr_bull, comp_years_yr1)
        rev_bull_yr2 = ttm_sales * math.pow(1 + rev_cagr_bull, comp_years_yr2)
        
        # Intermediate margin progression
        margin_base_yr1 = npm + (target_margin_base - npm) * 0.5
        margin_bull_yr1 = npm + (target_margin_bull - npm) * 0.5
        
        pat_base_yr1 = rev_base_yr1 * margin_base_yr1
        pat_base_yr2 = rev_base_yr2 * target_margin_base
        
        pat_bull_yr1 = rev_bull_yr1 * margin_bull_yr1
        pat_bull_yr2 = rev_bull_yr2 * target_margin_bull
        
        effective_shares = shares_cr if shares_cr > 0 else (mcap_cr / cmp if cmp > 0 else 1.0)
        
        eps_base_yr1 = pat_base_yr1 / effective_shares
        eps_base_yr2 = pat_base_yr2 / effective_shares
        
        eps_bull_yr1 = pat_bull_yr1 / effective_shares
        eps_bull_yr2 = pat_bull_yr2 / effective_shares
        
        # High-growth platform compounders warrant 45x - 60x exit multiples given 30%+ runway
        base_exit_pe = max(45.0, round(base_exit_growth * 100 * max(1.8, base_peg), 1))
        bull_exit_pe = max(60.0, round(bull_exit_growth * 100 * max(2.0, bull_peg), 1))
        
    else:
        regime_model = "Regime 1: Steady-State Margin Growth"
        base_exit_pe = round(base_exit_growth * 100 * base_peg, 1)
        bull_exit_pe = round(bull_exit_growth * 100 * bull_peg, 1)

        eps_base_yr1 = ttm_eps * math.pow(1 + base_cagr, comp_years_yr1)
        eps_base_yr2 = ttm_eps * math.pow(1 + base_cagr, comp_years_yr2)
        
        eps_bull_yr1 = ttm_eps * math.pow(1 + bull_cagr, comp_years_yr1)
        eps_bull_yr2 = ttm_eps * math.pow(1 + bull_cagr, comp_years_yr2)

    # Target Prices at 2-Year Horizon
    target_base = eps_base_yr2 * base_exit_pe
    target_bull = eps_bull_yr2 * bull_exit_pe

    # Returns
    return_base_pct = ((target_base - cmp) / cmp) * 100 if cmp > 0 else 0.0
    return_bull_pct = ((target_bull - cmp) / cmp) * 100 if cmp > 0 else 0.0

    horizon_years = 2.0  # 2-year forward horizon
    cagr_base = (math.pow(1 + (return_base_pct / 100.0), 1.0 / horizon_years) - 1.0) * 100 if return_base_pct > -100 else -100.0
    cagr_bull = (math.pow(1 + (return_bull_pct / 100.0), 1.0 / horizon_years) - 1.0) * 100

    # Probability-Weighted Expected Value
    norm_prob_base = base_prob / (base_prob + bull_prob)
    norm_prob_bull = bull_prob / (base_prob + bull_prob)
    
    expected_target = (norm_prob_base * target_base) + (norm_prob_bull * target_bull)
    total_expected_return_pct = ((expected_target - cmp) / cmp) * 100 if cmp > 0 else 0.0
    expected_cagr = (math.pow(1 + (total_expected_return_pct / 100.0), 1.0 / horizon_years) - 1.0) * 100 if total_expected_return_pct > -100 else -100.0

    # Forward P/E at current price
    fwd_pe_base = cmp / eps_base_yr2 if eps_base_yr2 > 0 else 0.0
    fwd_pe_bull = cmp / eps_bull_yr2 if eps_bull_yr2 > 0 else 0.0

    # Scorecard criteria
    pass_growth = (base_cagr >= 0.20 or bull_cagr >= 0.20)
    pass_fwd_pe = (fwd_pe_base < 50.0)
    pass_upside = (return_bull_pct >= 50.0)

    # Conviction Verdict
    if not pass_upside:
        verdict = "WATCHLIST / VALUATION TRAP (Bull <50%)"
        verdict_color = "red"
    elif return_base_pct < -5.0:
        verdict = "ACCUMULATE ON DIPS / HIGH STARTING P/E"
        verdict_color = "orange"
    elif return_base_pct >= 10.0 and return_bull_pct >= 50.0:
        verdict = "STRONG CONVICTION BUY"
        verdict_color = "green"
    else:
        verdict = "QUALIFIED GROWTH BUY"
        verdict_color = "blue"

    # Buy trigger range
    buy_low = target_base / (1.0 + 0.25)
    buy_high = target_base / (1.0 + 0.10)

    return {
        "regime": regime_period,
        "regime_model": regime_model,
        "is_platform": is_platform_compounder,
        "detection_reason": detection_reason,
        "base_fy": f"FY{last_reported_fy % 100}",
        "target_yr1_fy": target_yr1_fy,
        "target_yr2_fy": target_yr2_fy,
        "comp_years_yr1": comp_years_yr1,
        "comp_years_yr2": comp_years_yr2,
        "ttm_eps": ttm_eps,
        "trailing_pe": trailing_pe,
        "base_cagr": base_cagr,
        "bull_cagr": bull_cagr,
        "base_exit_pe": base_exit_pe,
        "bull_exit_pe": bull_exit_pe,
        "eps_base_yr1": round(eps_base_yr1, 2),
        "eps_base_yr2": round(eps_base_yr2, 2),
        "eps_bull_yr1": round(eps_bull_yr1, 2),
        "eps_bull_yr2": round(eps_bull_yr2, 2),
        "fwd_pe_base": round(fwd_pe_base, 1),
        "fwd_pe_bull": round(fwd_pe_bull, 1),
        "target_base": round(target_base, 2),
        "target_bull": round(target_bull, 2),
        "return_base_pct": round(return_base_pct, 1),
        "return_bull_pct": round(return_bull_pct, 1),
        "cagr_base": round(cagr_base, 1),
        "cagr_bull": round(cagr_bull, 1),
        "base_prob": round(norm_prob_base * 100),
        "bull_prob": round(norm_prob_bull * 100),
        "expected_target": round(expected_target, 2),
        "total_expected_return_pct": round(total_expected_return_pct, 1),
        "expected_cagr": round(expected_cagr, 1),
        "pass_growth": pass_growth,
        "pass_fwd_pe": pass_fwd_pe,
        "pass_upside": pass_upside,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "buy_low": round(buy_low, 1),
        "buy_high": round(buy_high, 1)
    }

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
