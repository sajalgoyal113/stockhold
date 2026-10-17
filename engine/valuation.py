from datetime import datetime
import math

def calculate_forward_pe_valuation(
    cmp: float,
    mcap_cr: float,
    ttm_eps: float,
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
        regime = "H1 (Q1/Q2)"
        target_yr1_fy = f"FY{running_fy % 100}"
        target_yr2_fy = f"FY{(running_fy + 1) % 100}"
        comp_years_yr1 = 1
        comp_years_yr2 = 2
    else:
        regime = "H2 (Q3/Q4 Roll-Forward)"
        target_yr1_fy = f"FY{(running_fy + 1) % 100}"
        target_yr2_fy = f"FY{(running_fy + 2) % 100}"
        comp_years_yr1 = 2
        comp_years_yr2 = 3

    # Dynamic exit multiples
    base_exit_pe = round(base_exit_growth * 100 * base_peg, 1)
    bull_exit_pe = round(bull_exit_growth * 100 * bull_peg, 1)

    # EPS projections
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
    buy_low = target_base / (1.0 + 0.25)  # price giving 25% base cushion
    buy_high = target_base / (1.0 + 0.10) # price giving 10% base cushion

    return {
        "regime": regime,
        "base_fy": f"FY{last_reported_fy % 100}",
        "target_yr1_fy": target_yr1_fy,
        "target_yr2_fy": target_yr2_fy,
        "comp_years_yr1": comp_years_yr1,
        "comp_years_yr2": comp_years_yr2,
        "ttm_eps": ttm_eps,
        "trailing_pe": cmp / ttm_eps if ttm_eps > 0 else 0.0,
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
