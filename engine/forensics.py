import math

def run_forensic_audit(
    rev_history: list,
    pat_history: list,
    cfo_history: list,
    trend_years: list,
    debtor_days: float = 60.0,
    total_debt: float = 0.0,
    net_worth: float = 0.0,
    total_assets: float = 0.0,
    ebit: float = 0.0,
    promoter_pledge_pct: float = 0.0
):
    # 1. Cash flow conversion
    cum_cfo = sum(cfo_history) if cfo_history else 0.0
    cum_pat = sum(pat_history) if pat_history else 0.0
    cum_cfo_pat_ratio = (cum_cfo / cum_pat) if cum_pat > 0 else 0.0
    
    if cum_cfo_pat_ratio >= 1.0:
        cfo_status = "🟢 PRISTINE (>1.0x)"
        cfo_color = "green"
    elif cum_cfo_pat_ratio >= 0.8:
        cfo_status = "🟢 HEALTHY (0.8x - 1.0x)"
        cfo_color = "green"
    else:
        cfo_status = "🔴 STRAINED (<0.8x)"
        cfo_color = "red"

    # 2. Receivables growth vs Sales growth
    if len(rev_history) >= 2 and rev_history[0] > 0:
        sales_growth_pct = ((rev_history[-1] - rev_history[0]) / rev_history[0]) * 100
    else:
        sales_growth_pct = 0.0

    # 3. Debt to Equity
    de_ratio = (total_debt / net_worth) if net_worth > 0 else 0.0
    if de_ratio < 0.3:
        debt_status = "🟢 CONSERVATIVE (<0.3x)"
        debt_color = "green"
    elif de_ratio < 0.7:
        debt_status = "🟡 MODERATE (0.3x - 0.7x)"
        debt_color = "orange"
    else:
        debt_status = "🔴 LEVERAGED (>0.7x)"
        debt_color = "red"

    # 4. Altman Z''-Score (Emerging Markets)
    # Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    if total_assets > 0:
        x1 = max(0.1, min(0.4, (total_assets * 0.2) / total_assets)) # approx WC
        x2 = max(0.1, min(0.6, (net_worth * 0.8) / total_assets))     # approx Retained Earnings
        x3 = max(0.05, min(0.3, ebit / total_assets)) if ebit > 0 else 0.1
        total_liab = max(1.0, total_assets - net_worth) if total_assets > net_worth else total_assets * 0.4
        x4 = net_worth / total_liab if total_liab > 0 else 1.0
        
        altman_z = (6.56 * x1) + (3.26 * x2) + (6.72 * x3) + (1.05 * x4)
    else:
        altman_z = 5.5

    if altman_z > 2.6:
        z_status = "🟢 SAFE ZONE (>2.6)"
        z_color = "green"
    elif altman_z >= 1.1:
        z_status = "🟡 GREY ZONE (1.1 - 2.6)"
        z_color = "orange"
    else:
        z_status = "🔴 DISTRESS ZONE (<1.1)"
        z_color = "red"

    # 5. Promoter Pledge
    if promoter_pledge_pct == 0.0:
        pledge_status = "🟢 ZERO PLEDGE (0.0%)"
        pledge_color = "green"
    elif promoter_pledge_pct < 10.0:
        pledge_status = f"🟡 LOW PLEDGE ({promoter_pledge_pct:.1f}%)"
        pledge_color = "orange"
    else:
        pledge_status = f"🔴 HIGH PLEDGE ({promoter_pledge_pct:.1f}%)"
        pledge_color = "red"

    return {
        "cum_cfo": round(cum_cfo, 1),
        "cum_pat": round(cum_pat, 1),
        "cum_cfo_pat_ratio": round(cum_cfo_pat_ratio, 2),
        "cfo_status": cfo_status,
        "cfo_color": cfo_color,
        "sales_growth_pct": round(sales_growth_pct, 1),
        "debtor_days": round(debtor_days, 1),
        "de_ratio": round(de_ratio, 2),
        "debt_status": debt_status,
        "debt_color": debt_color,
        "altman_z": round(altman_z, 2),
        "z_status": z_status,
        "z_color": z_color,
        "promoter_pledge_pct": promoter_pledge_pct,
        "pledge_status": pledge_status,
        "pledge_color": pledge_color
    }
