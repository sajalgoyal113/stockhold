"""
engine/forensics.py - Bridge to Master Forensic Accounting Engine

MASTER SOURCE OF TRUTH: predict/scripts/forensic_audit.py
This module delegates core forensic calculations (CFO/PAT conversion reality,
Altman Z''-Score for emerging markets) directly to the predict engines.
"""

import os
import sys

# Try multiple candidate paths to locate predict/scripts
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_PATHS = [
    os.path.abspath(os.path.join(_CURRENT_DIR, "..", "..", "predict", "scripts")),
    os.path.abspath(os.path.join(_CURRENT_DIR, "..", "predict", "scripts")),
    os.path.abspath(os.path.join(_CURRENT_DIR, "predict", "scripts")),
    os.path.abspath(os.path.join(os.getcwd(), "predict", "scripts")),
    os.path.abspath(os.path.join(os.getcwd(), "..", "predict", "scripts")),
]

for p in _CANDIDATE_PATHS:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
        break

try:
    from forensic_audit import (
        run_forensic_audit as _master_run_forensic_audit,
        compute_cfo_pat_ratio,
        evaluate_altman_z_em
    )
except ImportError:
    _master_run_forensic_audit = None
    compute_cfo_pat_ratio = None
    evaluate_altman_z_em = None


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
) -> dict:
    if _master_run_forensic_audit is not None:
        return _master_run_forensic_audit(
            rev_history=rev_history,
            pat_history=pat_history,
            cfo_history=cfo_history,
            trend_years=trend_years,
            debtor_days=debtor_days,
            total_debt=total_debt,
            net_worth=net_worth,
            total_assets=total_assets,
            ebit=ebit,
            promoter_pledge_pct=promoter_pledge_pct
        )

    # 1. Cash flow conversion via master skill function
    if compute_cfo_pat_ratio is not None and cfo_history and pat_history:
        _, cum_cfo_pat_ratio, cum_cfo, cum_pat = compute_cfo_pat_ratio(cfo_history, pat_history)
    else:
        cum_cfo = sum(cfo_history) if cfo_history else 0.0
        cum_pat = sum(pat_history) if pat_history else 0.0
        cum_cfo_pat_ratio = (cum_cfo / cum_pat) if cum_pat > 0 else 0.0

    if cum_cfo_pat_ratio >= 1.0:
        cfo_status = "🟢 PRISTINE (>1.0x)"
        cfo_color = "green"
    elif cum_cfo_pat_ratio >= 0.8:
        cfo_status = "🟢 HEALTHY (0.8x - 1.0x)"
        cfo_color = "green"
    elif cum_cfo_pat_ratio >= 0.5:
        cfo_status = "🟡 CAUTION (0.5x - 0.8x)"
        cfo_color = "orange"
    else:
        cfo_status = "🔴 STRAINED (<0.5x)"
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

    # 4. Altman Z''-Score (Emerging Markets) via master skill function
    if evaluate_altman_z_em is not None and total_assets > 0:
        working_capital = total_assets * 0.20
        retained_earnings = net_worth * 0.80
        total_liab = max(1.0, total_assets - net_worth) if total_assets > net_worth else total_assets * 0.40
        altman_z, zone, z_status = evaluate_altman_z_em(
            working_capital=working_capital,
            total_assets=total_assets,
            retained_earnings=retained_earnings,
            ebit=ebit,
            book_equity=net_worth,
            total_liabilities=total_liab
        )
        if altman_z is None:
            altman_z = 5.5
            z_status = "🟢 SAFE ZONE (>2.6)"
            z_color = "green"
        elif altman_z > 2.6:
            z_color = "green"
            z_status = f"🟢 SAFE ZONE ({altman_z:.2f} > 2.6)"
        elif altman_z >= 1.1:
            z_color = "orange"
            z_status = f"🟡 GREY ZONE ({altman_z:.2f})"
        else:
            z_color = "red"
            z_status = f"🔴 DISTRESS ZONE ({altman_z:.2f} < 1.1)"
    else:
        altman_z = 5.5
        z_status = "🟢 SAFE ZONE (>2.6)"
        z_color = "green"

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
