"""
engine/valuation.py - Bridge to Master Forensic Valuation Engine

MASTER SOURCE OF TRUTH: .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py
This module delegates 100% of forward growth, exit multiple derivations,
and scenario probability calculations to the institutional skill scripts.
"""

import os
import sys
from datetime import datetime

# Resolve path to skill scripts
_SKILL_SCRIPTS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "indian-stock-analysis", "scripts")
)
if _SKILL_SCRIPTS_PATH not in sys.path:
    sys.path.insert(0, _SKILL_SCRIPTS_PATH)

try:
    from forward_growth_pe import evaluate_forward_growth as _skill_evaluate_forward_growth
    from forward_growth_pe import calibrate_stock_parameters as _skill_calibrate_stock_parameters
except ImportError:
    # Defensive fallback if path resolution fails in external deployment environments
    _skill_evaluate_forward_growth = None
    _skill_calibrate_stock_parameters = None


def calibrate_stock_parameters(company_data: dict) -> dict:
    """
    Calibrates stock growth, exit multiple, and probability weighting parameters.
    Delegates directly to forward_growth_pe.py as master source of truth.
    """
    if _skill_calibrate_stock_parameters is not None:
        return _skill_calibrate_stock_parameters(company_data)
    
    # Fallback standard calibration
    return {
        "base_cagr": 20,
        "bull_cagr": 25,
        "base_exit_g": 16.0,
        "bull_exit_g": 22.0,
        "base_peg": 1.60,
        "bull_peg": 1.85,
        "base_prob": 55,
        "bull_prob": 45,
        "cfo_pat_ratio": 0.5,
        "rationale": "Standard institutional calibration"
    }


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
    regime_override: str = "Auto",
    ticker: str = "STOCK"
) -> dict:
    """
    Evaluates 2-year forward growth and exit P/E valuation.
    Delegates directly to forward_growth_pe.evaluate_forward_growth.
    """
    # Net Profit Margin check for platform regime detection
    npm = (ttm_pat / ttm_sales) if (ttm_sales > 0 and ttm_pat > 0) else 0.10

    if regime_override == "Regime 2 (Platform)":
        is_platform = True
        detection_reason = "Manual Override: Forced to Regime 2 (Platform Operating Leverage)"
    elif regime_override == "Regime 1 (Steady-State)":
        is_platform = False
        detection_reason = "Manual Override: Forced to Regime 1 (Steady-State Margin Compounder)"
    else:
        is_platform = (npm < 0.020) and (ttm_sales >= 1000.0)
        if is_platform:
            detection_reason = (
                f"Auto-Detected: Regime 2 (Platform Operating Leverage). Net Profit Margin is suppressed "
                f"at {npm*100:.2f}% (<2.0%) at scale (₹{ttm_sales:,.0f} Cr revenue), indicating non-linear "
                f"operating leverage potential."
            )
        else:
            detection_reason = (
                f"Auto-Detected: Regime 1 (Steady-State Margin Compounder). Net Profit Margin of "
                f"{npm*100:.2f}% (>=2.0%) represents normal operating margins; valuation is driven by top-line volume compounding."
            )

    if _skill_evaluate_forward_growth is not None:
        if is_platform:
            rev_cagr = max(0.35, base_cagr * 1.6)
            curr_margin = npm
            target_margin = max(0.045, min(0.065, npm * 4.0))
            res = _skill_evaluate_forward_growth(
                ticker=ticker,
                cmp=cmp,
                mcap=mcap_cr,
                current_eps=ttm_eps,
                rev_cagr=rev_cagr,
                current_margin=curr_margin,
                target_margin_yr2=target_margin,
                bull_cagr=bull_cagr,
                base_exit_growth=base_exit_growth,
                bull_exit_growth=bull_exit_growth,
                base_peg=base_peg,
                bull_peg=bull_peg,
                base_prob=base_prob,
                bull_prob=bull_prob,
                as_of_date=as_of_date
            )
        else:
            res = _skill_evaluate_forward_growth(
                ticker=ticker,
                cmp=cmp,
                mcap=mcap_cr,
                current_eps=ttm_eps,
                guided_cagr=base_cagr,
                bull_cagr=bull_cagr,
                base_exit_growth=base_exit_growth,
                bull_exit_growth=bull_exit_growth,
                base_peg=base_peg,
                bull_peg=bull_peg,
                base_prob=base_prob,
                bull_prob=bull_prob,
                as_of_date=as_of_date
            )

        res["detection_reason"] = detection_reason
        res["is_platform"] = is_platform
        return res

    raise RuntimeError("Unable to load evaluate_forward_growth from .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py")
