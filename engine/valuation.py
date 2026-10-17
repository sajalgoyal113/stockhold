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
    as_of_date: datetime = None
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
    
    # If P/E > 80x or Net Profit Margin < 2.5%, company is in early-profitability / hyper-expansion phase
    is_platform_compounder = (trailing_pe > 80.0 or npm < 0.025) and ttm_sales > 0
    
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
        verdict = "REJECT / GROWTH HURDLE MISS"
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
