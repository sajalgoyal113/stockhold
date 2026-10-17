"""
engine/reverse_dcf.py - Bridge to Master Expectations Investing & Reverse DCF Engine

MASTER SOURCE OF TRUTH: .agents/skills/indian-stock-analysis/scripts/reverse_dcf.py
This module delegates core reverse DCF numerical root-finding directly to the institutional skill scripts.
"""

import os
import sys

# Resolve path to skill scripts
_SKILL_SCRIPTS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "indian-stock-analysis", "scripts")
)
if _SKILL_SCRIPTS_PATH not in sys.path:
    sys.path.insert(0, _SKILL_SCRIPTS_PATH)

try:
    from reverse_dcf import calculate_implied_growth as _skill_calculate_implied_growth
except ImportError:
    _skill_calculate_implied_growth = None


def run_reverse_dcf(
    cmp: float,
    mcap_cr: float,
    fcf_0: float,
    net_debt: float = 0.0,
    wacc: float = 0.115,
    g_term: float = 0.05
) -> dict:
    ev = mcap_cr + net_debt
    base_fcf = max(1.0, fcf_0)

    if _skill_calculate_implied_growth is not None:
        raw_g = _skill_calculate_implied_growth(ev, base_fcf, wacc, g_term, years=10)
        implied_cagr = (raw_g * 100.0) if raw_g is not None else 0.0
    else:
        implied_cagr = 20.0

    if implied_cagr < 15.0:
        assessment = "REALISTIC / MODEST (<15%)"
        color = "green"
    elif implied_cagr <= 25.0:
        assessment = "AGGRESSIVE (15% - 25%)"
        color = "orange"
    else:
        assessment = "HEROIC / PRICED TO PERFECTION (>25%)"
        color = "red"

    # Sensitivity Matrix across WACCs and Terminal Growths
    wacc_list = [0.10, 0.115, 0.13]
    g_term_list = [0.04, 0.05, 0.06]

    matrix = {}
    for w in wacc_list:
        w_key = f"{int(w*100)}%" if w != 0.115 else "11.5%"
        matrix[w_key] = {}
        for gt in g_term_list:
            gt_key = f"{int(gt*100)}%"
            if _skill_calculate_implied_growth is not None:
                cell_g = _skill_calculate_implied_growth(ev, base_fcf, w, gt, years=10)
                matrix[w_key][gt_key] = round(cell_g * 100.0, 1) if cell_g is not None else 0.0
            else:
                matrix[w_key][gt_key] = 20.0

    return {
        "ev": round(ev, 1),
        "fcf_0": round(base_fcf, 1),
        "wacc_pct": round(wacc * 100, 1),
        "g_term_pct": round(g_term * 100, 1),
        "implied_cagr": round(implied_cagr, 1),
        "assessment": assessment,
        "color": color,
        "sensitivity_matrix": matrix
    }
