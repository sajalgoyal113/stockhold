"""
engine/valuation.py - Master High-Growth Stock & 2-Year Forward P/E Valuation Engine

MASTER SOURCE OF TRUTH: predict/scripts/forward_growth_pe.py
This module delegates forward compounding calculations, dynamic exit multiple derivations,
calendar roll-forward mapping, and probability weighting directly to the predict master engine.
"""

import os
import sys
import re
import math
from datetime import datetime

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
    from forward_growth_pe import (
        determine_fiscal_period,
        KNOWN_COMPANY_PROFILES,
        calibrate_stock_parameters,
        evaluate_forward_growth,
        calculate_forward_pe_valuation as _master_calculate_forward_pe_valuation,
        generate_summary_card
    )
except ImportError:
    _master_calculate_forward_pe_valuation = None

# --- 1. FISCAL PERIOD ROLL-FORWARD MAPPING (GEMINI.md Rule 6) ---

def determine_fiscal_period(as_of_date=None, half_override=None, fy_override=None):
    """
    Determines running fiscal year, active quarter, and roll-forward targets.
    Indian Financial Year runs April 1 to March 31.
    """
    if as_of_date is None:
        dt = datetime.now()
    elif isinstance(as_of_date, datetime):
        dt = as_of_date
    else:
        try:
            dt = datetime.strptime(str(as_of_date), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format '{as_of_date}'. Use YYYY-MM-DD.")
            
    month = dt.month
    year = dt.year
    
    if fy_override is not None:
        running_fy = fy_override if fy_override >= 100 else 2000 + fy_override
    else:
        running_fy = year + 1 if month >= 4 else year
        
    if half_override is not None:
        half = half_override.upper()
        if half not in ["H1", "H2"]:
            raise ValueError(f"Invalid half '{half}'. Must be H1 or H2.")
        quarter = "Q1/Q2" if half == "H1" else "Q3/Q4"
    else:
        if 4 <= month <= 6:
            quarter = "Q1"
            half = "H1"
        elif 7 <= month <= 9:
            quarter = "Q2"
            half = "H1"
        elif 10 <= month <= 12:
            quarter = "Q3"
            half = "H2"
        else:
            quarter = "Q4"
            half = "H2"
            
    base_fy = running_fy - 1
    
    if half == "H1":
        # H1 Regime: Market focuses on current year and next year
        target_fy_yr1 = running_fy
        target_fy_yr2 = running_fy + 1
        comp_years_yr1 = 1
        comp_years_yr2 = 2
    else:
        # H2 Regime: Multiples roll forward as H1 has concluded
        target_fy_yr1 = running_fy + 1
        target_fy_yr2 = running_fy + 2
        comp_years_yr1 = 2
        comp_years_yr2 = 3
        
    return {
        "dt": dt,
        "running_fy": running_fy,
        "quarter": quarter,
        "half": half,
        "base_fy": base_fy,
        "target_fy_yr1": target_fy_yr1,
        "target_fy_yr2": target_fy_yr2,
        "comp_years_yr1": comp_years_yr1,
        "comp_years_yr2": comp_years_yr2,
    }


# --- 2. FORWARD GROWTH & DYNAMIC P/E EVALUATION ENGINE ---

def evaluate_forward_growth(
    ticker, cmp, mcap=None, current_eps=0.0, current_pe=0.0,
    guided_cagr=None, bull_cagr=None,
    base_exit_growth=None, bull_exit_growth=None,
    base_peg=1.6, bull_peg=1.85,
    base_reason=None, bull_reason=None,
    base_prob=None, bull_prob=None,
    dilution_pct_annual=0.0, margin_expansion_pct_annual=0.0,
    historical_guidance_reliability=1.0,
    target_eps_yr2=None, rev_cagr=None,
    current_margin=None, target_margin_yr2=None,
    as_of_date=None, half_override=None, fy_override=None,
    base_pe=None, bull_pe=None,
    hist_floor_pe=None, peer_pe=None,
    sector_growth=None,
    **kwargs
):
    """
    Projects EPS for FY+1 and FY+2 across Base and Bull scenarios with dynamic exit multiples.
    Strictly follows GEMINI.md Rule 6.
    """
    if current_eps <= 0 and current_pe > 0:
        current_eps = cmp / current_pe
    elif current_pe <= 0 and current_eps > 0:
        current_pe = cmp / current_eps

    if current_eps <= 0:
        raise ValueError("Error: Both current_eps and current_pe cannot be <= 0.")

    # Check if ticker has a known company profile
    clean_ticker = (ticker or "").upper().replace(" ", "").replace("-", "")
    if clean_ticker in KNOWN_COMPANY_PROFILES:
        prof = KNOWN_COMPANY_PROFILES[clean_ticker]
        if guided_cagr is None and target_eps_yr2 is None and rev_cagr is None:
            if prof.get("is_platform") and prof.get("current_margin") and prof.get("target_margin_yr2"):
                current_margin = prof.get("current_margin")
                target_margin_yr2 = prof.get("target_margin_yr2")
                rev_cagr = prof["base_cagr"] / 100.0
            else:
                guided_cagr = prof["base_cagr"] / 100.0
        if bull_cagr is None and prof.get("bull_cagr") is not None:
            bull_cagr = prof["bull_cagr"] / 100.0
        if base_exit_growth is None and prof.get("base_exit_g") is not None:
            base_exit_growth = prof["base_exit_g"] / 100.0
        if bull_exit_growth is None and prof.get("bull_exit_g") is not None:
            bull_exit_growth = prof["bull_exit_g"] / 100.0
        if base_peg == 1.6 and prof.get("base_peg") is not None:
            base_peg = prof.get("base_peg")
        if bull_peg == 1.85 and prof.get("bull_peg") is not None:
            bull_peg = prof.get("bull_peg")
        if base_prob is None and prof.get("base_prob") is not None:
            base_prob = prof["base_prob"] / 100.0
        if bull_prob is None and prof.get("bull_prob") is not None:
            bull_prob = prof["bull_prob"] / 100.0
        if base_reason is None and prof.get("base_reason") is not None:
            base_reason = prof.get("base_reason")
        if bull_reason is None and prof.get("bull_reason") is not None:
            bull_reason = prof.get("bull_reason")
        if dilution_pct_annual == 0.0 and prof.get("dilution") is not None:
            dilution_pct_annual = prof.get("dilution")
        if base_pe is None and prof.get("base_pe") is not None:
            base_pe = prof.get("base_pe")
        if bull_pe is None and prof.get("bull_pe") is not None:
            bull_pe = prof.get("bull_pe")
        if hist_floor_pe is None and prof.get("hist_floor_pe") is not None:
            hist_floor_pe = prof.get("hist_floor_pe")
        if peer_pe is None and prof.get("peer_pe") is not None:
            peer_pe = prof.get("peer_pe")
        if sector_growth is None and prof.get("sector_growth") is not None:
            sector_growth = prof.get("sector_growth")

    period = determine_fiscal_period(as_of_date, half_override, fy_override)
    regime_desc = "Regime 1: Steady-State Margin Growth"

    # CASE A: Explicit Target EPS provided
    if target_eps_yr2 is not None and target_eps_yr2 > 0:
        eps_base_yr2 = target_eps_yr2
        base_net_growth = (eps_base_yr2 / current_eps) ** (1.0 / period["comp_years_yr2"]) - 1.0
        eps_base_yr1 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr1"])
        regime_desc = f"Regime 2: Direct Consensus / Line-Item Build (Yr 2 Base EPS ₹{target_eps_yr2:.2f})"
        bull_net_growth = max(bull_cagr, base_net_growth * 1.25) if bull_cagr is not None else base_net_growth * 1.25

    # CASE B: Non-linear Margin Expansion Model (Platform / Early Profitability)
    elif rev_cagr is not None and current_margin is not None and target_margin_yr2 is not None:
        if current_margin <= 0:
            raise ValueError("Error: current_margin must be > 0 for margin expansion model.")
        effective_rev_cagr = rev_cagr * historical_guidance_reliability
        rev_multiplier_yr2 = (1.0 + effective_rev_cagr) ** period["comp_years_yr2"]
        margin_multiplier = target_margin_yr2 / current_margin
        pat_multiplier_yr2 = rev_multiplier_yr2 * margin_multiplier
        net_pat_cagr = (pat_multiplier_yr2 ** (1.0 / period["comp_years_yr2"])) - 1.0
        base_net_growth = net_pat_cagr - dilution_pct_annual
        eps_base_yr1 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr1"])
        eps_base_yr2 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr2"])
        bull_net_growth = max(bull_cagr, base_net_growth * 1.20) if bull_cagr is not None else base_net_growth * 1.20
        regime_desc = (f"Regime 2: Operating Leverage & Margin Expansion "
                       f"({current_margin*100:.2f}% -> {target_margin_yr2*100:.2f}% NPM, Rev CAGR {effective_rev_cagr*100:.1f}%)")

    # CASE C: Standard Linear Model
    else:
        if guided_cagr is None:
            raise ValueError("Error: Must specify either guided_cagr, target_eps_yr2, or (rev_cagr, current_margin, target_margin_yr2).")
        base_net_growth = (guided_cagr * historical_guidance_reliability) - dilution_pct_annual + margin_expansion_pct_annual
        eps_base_yr1 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr1"])
        eps_base_yr2 = current_eps * ((1.0 + base_net_growth) ** period["comp_years_yr2"])
        bull_net_growth = max(bull_cagr, base_net_growth) if bull_cagr is not None else base_net_growth * 1.25

    # Bull Scenario Projections
    eps_bull_yr1 = current_eps * ((1.0 + bull_net_growth) ** period["comp_years_yr1"])
    eps_bull_yr2 = current_eps * ((1.0 + bull_net_growth) ** period["comp_years_yr2"])

    # Determine End-Period Growth Rates
    base_exit_g = base_exit_growth if base_exit_growth is not None else base_net_growth
    bull_exit_g = bull_exit_growth if bull_exit_growth is not None else bull_net_growth

    # Sector Runway Calibration & Market Share Alpha
    sector_desc = None
    if sector_growth is not None and sector_growth > 0:
        if sector_growth >= 0.18:
            sector_tier = "Secular Sunrise (10+ Yr Runway)"
            sector_mult = 1.10
        elif sector_growth >= 0.10:
            sector_tier = "GDP+ Compounding (5-7 Yr Runway)"
            sector_mult = 1.00
        else:
            sector_tier = "Cyclical / Mature (Terminal Deceleration Risk)"
            sector_mult = 0.85
        
        base_peg = round(base_peg * sector_mult, 2)
        bull_peg = round(bull_peg * sector_mult, 2)
        base_alpha = (base_exit_g - sector_growth) * 100
        bull_alpha = (bull_exit_g - sector_growth) * 100
        sector_desc = f"{sector_tier} | Industry TAM CAGR: {sector_growth*100:.1f}% (Base Alpha: {base_alpha:+.1f}%, Bull Alpha: {bull_alpha:+.1f}%)"

    # Dynamic P/E Derivation based on end-of-period growth rate with Triangulation
    if base_pe is None:
        base_pe = round(base_peg * (base_exit_g * 100), 1)
        base_pe = max(15.0, base_pe)  # Floor at 15x
        if hist_floor_pe is not None:
            base_pe = max(base_pe, hist_floor_pe)
    if bull_pe is None:
        bull_pe = round(bull_peg * (bull_exit_g * 100), 1)
        bull_pe = max(base_pe + 5.0, bull_pe)  # Bull P/E higher than Base
        if peer_pe is not None:
            bull_pe = min(bull_pe, round(peer_pe * 1.10, 1))

    # Valuations
    fwd_pe_yr1_base = cmp / eps_base_yr1 if eps_base_yr1 > 0 else float('inf')
    fwd_pe_yr2_base = cmp / eps_base_yr2 if eps_base_yr2 > 0 else float('inf')
    fwd_pe_yr2_bull = cmp / eps_bull_yr2 if eps_bull_yr2 > 0 else float('inf')

    peg_ratio_yr2_base = fwd_pe_yr2_base / (base_net_growth * 100) if base_net_growth > 0 else float('inf')

    base_target_price = eps_base_yr2 * base_pe
    base_upside_pct = ((base_target_price - cmp) / cmp) * 100
    base_annualized_cagr = (((base_target_price / cmp) ** 0.5) - 1) * 100 if base_target_price > 0 else -100

    bull_target_price = eps_bull_yr2 * bull_pe
    bull_upside_pct = ((bull_target_price - cmp) / cmp) * 100
    bull_annualized_cagr = (((bull_target_price / cmp) ** 0.5) - 1) * 100 if bull_target_price > 0 else -100

    passes_growth_filter = base_net_growth >= 0.20 or bull_net_growth >= 0.20
    passes_pe_filter = fwd_pe_yr2_base < 50.0
    passes_bull_upside_mandate = bull_upside_pct >= 50.0

    fy_curr_str = f"FY{period['running_fy'] % 100}"
    fy_base_str = f"FY{period['base_fy'] % 100}"
    fy_yr1_str = f"FY{period['target_fy_yr1'] % 100}"
    fy_yr2_str = f"FY{period['target_fy_yr2'] % 100}"

    # Default reasons if not provided
    if not base_reason:
        base_reason = f"Execution friction, delayed milestone delivery, or moderate volume ramp (CAGR {base_net_growth*100:.1f}%)"
    if not bull_reason:
        bull_reason = f"Flawless execution, market share consolidation, and strong operational leverage (CAGR {bull_net_growth*100:.1f}%)"

    # Dynamic probability weighting based on company-specific execution risk
    if base_prob is None:
        base_prob = 0.65  # Default 65% Base / 35% Bull reflecting execution conservatism
    bull_prob = 1.0 - base_prob if bull_prob is None else bull_prob

    # Normalize if user passed both
    total_prob = base_prob + bull_prob
    base_prob = base_prob / total_prob
    bull_prob = bull_prob / total_prob

    prob_weighted_target = (base_prob * base_target_price) + (bull_prob * bull_target_price)
    prob_weighted_return = ((prob_weighted_target - cmp) / cmp) * 100
    prob_weighted_cagr = (((prob_weighted_target / cmp) ** 0.5) - 1.0) * 100 if prob_weighted_target > 0 else -100

    if passes_bull_upside_mandate and base_upside_pct >= 15.0 and base_net_growth >= 0.20:
        verdict = f"STRONG HIGH-GROWTH BUY (Bull Upside {bull_upside_pct:+.1f}%, Base {base_upside_pct:+.1f}%, Expected CAGR {prob_weighted_cagr:+.1f}% p.a.)"
    elif passes_bull_upside_mandate and base_upside_pct >= 0.0:
        verdict = f"QUALIFIED GROWTH BUY (Bull Upside {bull_upside_pct:+.1f}%, but Base Return {base_upside_pct:+.1f}% provides modest cushion)"
    elif passes_bull_upside_mandate and base_upside_pct < 0.0:
        verdict = f"REJECT / HIGH VALUATION TRAP (Bull Upside {bull_upside_pct:+.1f}%, but Base Case suffers capital loss {base_upside_pct:+.1f}% due to high starting P/E)"
    elif not passes_growth_filter:
        verdict = f"REJECT (Projected growth below 20% hurdle rate)"
    else:
        verdict = f"REJECT (2-year forward P/E {fwd_pe_yr2_base:.1f}x exceeds 50x hurdle or Bull Upside < 50%)"

    return {
        "ticker": ticker.upper(),
        "cmp": cmp,
        "mcap": mcap,
        "regime": f"{period['half']} Roll-Forward Regime",
        "regime_desc": regime_desc,
        "regime_model": regime_desc,
        "base_fy": fy_base_str,
        "target_yr1_fy": fy_yr1_str,
        "target_yr2_fy": fy_yr2_str,
        "comp_years_yr1": period["comp_years_yr1"],
        "comp_years_yr2": period["comp_years_yr2"],
        "current_eps": round(current_eps, 2),
        "current_pe": round(current_pe, 1),
        "ttm_eps": round(current_eps, 2),
        "trailing_pe": round(current_pe, 1),
        "base_cagr": round(base_net_growth, 4),
        "bull_cagr": round(bull_net_growth, 4),
        "base_exit_g": base_exit_g,
        "bull_exit_g": bull_exit_g,
        "base_exit_pe": round(base_pe, 1),
        "bull_exit_pe": round(bull_pe, 1),
        "eps_base_yr1": round(eps_base_yr1, 2),
        "eps_base_yr2": round(eps_base_yr2, 2),
        "eps_bull_yr1": round(eps_bull_yr1, 2),
        "eps_bull_yr2": round(eps_bull_yr2, 2),
        "fwd_pe_base": round(fwd_pe_yr2_base, 1),
        "fwd_pe_bull": round(fwd_pe_yr2_bull, 1),
        "target_base": round(base_target_price, 2),
        "target_bull": round(bull_target_price, 2),
        "return_base_pct": round(base_upside_pct, 1),
        "return_bull_pct": round(bull_upside_pct, 1),
        "cagr_base": round(base_annualized_cagr, 1),
        "cagr_bull": round(bull_annualized_cagr, 1),
        "base_prob": round(base_prob * 100),
        "bull_prob": round(bull_prob * 100),
        "expected_target": round(prob_weighted_target, 2),
        "total_expected_return_pct": round(prob_weighted_return, 1),
        "expected_cagr": round(prob_weighted_cagr, 1),
        "pass_growth": passes_growth_filter,
        "pass_fwd_pe": passes_pe_filter,
        "pass_upside": passes_bull_upside_mandate,
        "verdict": verdict,
        "verdict_color": "green" if "STRONG" in verdict else ("blue" if "QUALIFIED" in verdict else ("orange" if "ACCUMULATE" in verdict else "red")),
        "buy_low": round(base_target_price / 1.25, 1),
        "buy_high": round(base_target_price / 1.10, 1),
        "base_reason": base_reason,
        "bull_reason": bull_reason,
        "sector_growth": sector_growth,
        "sector_desc": sector_desc
    }


# --- 3. COMPANY PROFILES & DYNAMIC PROBABILITY CALIBRATION (GEMINI.md Rule 6) ---

KNOWN_COMPANY_PROFILES = {
    "ETERNAL": {
        "base_cagr": 35, "bull_cagr": 42,
        "base_exit_g": 28.0, "bull_exit_g": 35.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 50, "bull_prob": 50,
        "dilution": 0.02,
        "current_margin": 0.0064, "target_margin_yr2": 0.045,
        "rationale": "Elite Founder-Led execution (Deepinder Goyal); consistently meets/beats aggressive guidance $\\implies$ 50/50 balanced weighting (GEMINI.md Rule 6)",
        "base_reason": "Execution friction in dark store ramp; competitive pressure from Zepto/Swiggy capping net margin at 4.5%",
        "bull_reason": "Blinkit scale economics, dark store density, and food delivery operating leverage driving net margin to 6.5%",
        "is_platform": True
    },
    "CYIENTDLM": {
        "base_cagr": 22, "bull_cagr": 32,
        "base_exit_g": 20.0, "bull_exit_g": 25.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 65, "bull_prob": 35,
        "rationale": "High customer concentration (Honeywell 40%+) & working capital intensity $\\implies$ 65% Base / 35% Bull margin-of-safety penalty (GEMINI.md Rule 6)",
        "base_reason": "Aerospace box-build conversion lag, extended component validation cycles, and working capital bottlenecks",
        "bull_reason": "Flawless execution of record ₹2,814 Cr backlog, Honeywell Micro VCS ramp, and margin expansion to 12.5%",
        "is_platform": False
    },
    "IXIGO": {
        "base_cagr": 16, "bull_cagr": 28,
        "base_exit_g": 16.0, "bull_exit_g": 26.0,
        "base_peg": 1.25, "bull_peg": 1.60,
        "base_prob": 75, "bull_prob": 25,
        "rationale": "High regulatory vulnerability and sovereign supplier trap (IRCTC dependency) $\\implies$ 75% Base / 25% Bull margin-of-safety dominance (GEMINI.md Rule 6)",
        "base_reason": "Moderating railway/bus growth (~13-16%), ongoing take-rate headwinds in flights, and IRCTC policy risk",
        "bull_reason": "Flawless execution: hotel segment explodes (3x GTV expansion), flight commissions stabilize, AbhiBus commands private bus market",
        "is_platform": False
    },
    "DIXON": {
        "base_cagr": 30, "bull_cagr": 40,
        "base_exit_g": 25.0, "bull_exit_g": 32.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 50, "bull_prob": 50,
        "rationale": "Elite Founder-Led execution (Atul Lall); dominant EMS market share and PLI compounding $\\implies$ 50/50 balanced weighting (GEMINI.md Rule 6)",
        "base_reason": "Component localization delays, smartphone assembly margin competition, or supply chain bottlenecks",
        "bull_reason": "Explosive smartphone export PLI ramp (Motorola/Xiaomi/Ismartu), IT hardware PLI scale, and OSAT integration",
        "is_platform": False
    },
    "TRENT": {
        "base_cagr": 28, "bull_cagr": 38,
        "base_exit_g": 24.0, "bull_exit_g": 32.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 50, "bull_prob": 50,
        "rationale": "Elite execution credibility; unparalleled fast-fashion supply chain dominance $\\implies$ 50/50 balanced weighting (GEMINI.md Rule 6)",
        "base_reason": "Same-store sales growth (SSSG) moderation in mature Zudio clusters and tier-2 competitive discounting",
        "bull_reason": "Hyper-accelerated Zudio store rollouts (200+ annually), Star Bazaar grocery turnaround, and international expansion",
        "is_platform": False
    },
    "KAYNES": {
        "base_cagr": 32, "bull_cagr": 42,
        "base_exit_g": 26.0, "bull_exit_g": 34.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 50, "bull_prob": 50,
        "rationale": "High-credibility specialized EMS & OSAT pioneer with massive order visibility $\\implies$ 50/50 balanced weighting (GEMINI.md Rule 6)",
        "base_reason": "Sanand OSAT facility commercialization lag and aerospace component qualification lead-times",
        "bull_reason": "Commercial operation of Sanand semiconductor OSAT, defense electronics localization, and multi-year export ramp",
        "is_platform": False
    },
    "POLYCAB": {
        "base_cagr": 20, "bull_cagr": 28,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 50, "bull_prob": 50,
        "rationale": "Market-leading distribution moat & Project Leap delivery $\\implies$ 50/50 balanced weighting (GEMINI.md Rule 6)",
        "base_reason": "Real estate construction cycle moderation and volatile copper/aluminum commodity raw material pass-through lags",
        "bull_reason": "Project Leap distribution expansion, infrastructure capex tailwinds, and aggressive export penetration",
        "is_platform": False
    },
    "HAL": {
        "base_cagr": 18, "bull_cagr": 25,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Sovereign defense monopoly with multi-year order book visibility (5x+ revenue) $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "GE-404 engine supply chain bottlenecks and extended government milestone verification schedules",
        "bull_reason": "Record ₹1.2 Lakh Cr defense backlog execution, Tejas Mk1A delivery ramp, and indigenous defense export breakthroughs",
        "is_platform": False
    },
    "BEL": {
        "base_cagr": 18, "bull_cagr": 25,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Contracted defense electronics monopoly with high margin resilience $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Electronic component procurement cycle elongation and lumpy quarterly milestone billings",
        "bull_reason": "QRSAM, naval radar suites, electronic warfare systems rollout, and non-defense diversification",
        "is_platform": False
    },
    "CDSL": {
        "base_cagr": 22, "bull_cagr": 30,
        "base_exit_g": 20.0, "bull_exit_g": 26.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Contracted duopoly with >70% active demat market share and zero credit risk $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Retail demat account additions cool off after market all-time highs; annual issuer fee growth moderates",
        "bull_reason": "Systematic retail financialization, soaring transaction volumes, pledged share charges, and insurance repository scale",
        "is_platform": False
    },
    "COFORGE": {
        "base_cagr": 20, "bull_cagr": 26,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Consistent industry-leading execution with solid order intake $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Cigniti integration friction, discretionary BFS budget delays, and higher integration amortizations",
        "bull_reason": "Synergies from Cigniti acquisition, $2B revenue run-rate milestone, and multi-year order intake records",
        "is_platform": False
    },
    "NETWEB": {
        "base_cagr": 35, "bull_cagr": 45,
        "base_exit_g": 28.0, "bull_exit_g": 36.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 50, "bull_prob": 50,
        "rationale": "Direct beneficiary of national AI computing infrastructure capex $\\implies$ 50/50 balanced weighting (GEMINI.md Rule 6)",
        "base_reason": "GPU allocation bottlenecks from NVIDIA and lumpy enterprise AI capex disbursement cycles",
        "bull_reason": "Explosive Sovereign AI cloud buildouts in India, NVIDIA partnership scale, and Tyrone AI server deployments",
        "is_platform": False
    },
    "PERSISTENT": {
        "base_cagr": 20, "bull_cagr": 27,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Tier-1 digital engineering compounder with robust deal-win momentum $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Tech vendor consolidation pressure and delayed enterprise software sales cycles",
        "bull_reason": "Digital engineering leadership, healthcare/life sciences expansion, and GenAI client pilots conversion",
        "is_platform": False
    },
    "KPITTECH": {
        "base_cagr": 22, "bull_cagr": 30,
        "base_exit_g": 20.0, "bull_exit_g": 26.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Pure-play mobility software specialist with deep OEM architecture integration $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Global OEM EV program delays and European automotive discretionary R&D budget pressures",
        "bull_reason": "SDV (Software-Defined Vehicle) architectural shift, middleware leadership, and commercial vehicle electrification",
        "is_platform": False
    },
    "TATAELXSI": {
        "base_cagr": 18, "bull_cagr": 25,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Premium design-led ER&D leader with zero net debt and pristine ROE $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Media & telecom vertical headwinds and delayed design-to-production OEM signoffs",
        "bull_reason": "Transportation SDV design wins, medical device software regulatory clearances, and design-led engineering moat",
        "is_platform": False
    },
    "SUZLON": {
        "base_cagr": 24, "bull_cagr": 35,
        "base_exit_g": 20.0, "bull_exit_g": 26.0,
        "base_peg": 1.50, "bull_peg": 1.75,
        "base_prob": 65, "bull_prob": 35,
        "rationale": "Turnaround wind OEM with massive cyclical order book but transmission infrastructure risks $\\implies$ 65/35 margin-of-safety allocation (GEMINI.md Rule 6)",
        "base_reason": "Right-of-way and power grid evacuation infrastructure bottlenecks delaying wind farm project execution",
        "bull_reason": "Clean balance sheet turnaround, commercial & industrial (C&I) order book surge (5+ GW), and 3.x MW turbine ramp",
        "is_platform": False
    },
    "ANGELONE": {
        "base_cagr": 22, "bull_cagr": 30,
        "base_exit_g": 18.0, "bull_exit_g": 25.0,
        "base_peg": 1.40, "bull_peg": 1.65,
        "base_prob": 65, "bull_prob": 35,
        "rationale": "Fintech brokerage with high ROE but elevated regulatory scrutiny on F&O derivatives $\\implies$ 65/35 margin-of-safety allocation (GEMINI.md Rule 6)",
        "base_reason": "SEBI index derivatives regulations curbing retail F&O volume churn and raising compliance costs",
        "bull_reason": "Aggressive market share capture in tier-2/3 cities, loan distribution, and wealth management platform monetization",
        "is_platform": False
    },
    "PAYTM": {
        "base_cagr": 22, "bull_cagr": 32,
        "base_exit_g": 20.0, "bull_exit_g": 26.0,
        "base_peg": 1.50, "bull_peg": 1.75,
        "base_prob": 65, "bull_prob": 35,
        "rationale": "High merchant distribution scale recovering from regulatory shocks $\\implies$ 65/35 margin-of-safety allocation (GEMINI.md Rule 6)",
        "base_reason": "Merchant soundbox price competition and regulatory transition friction in payment partner banks",
        "bull_reason": "Merchant device subscription lock-in, DLG loan distribution recovery, and cost rationalization driving operating EBITDA",
        "is_platform": False
    },
    "POLICYBZR": {
        "base_cagr": 24, "bull_cagr": 34,
        "base_exit_g": 20.0, "bull_exit_g": 28.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 60, "bull_prob": 40,
        "rationale": "Market-dominant insurtech platform with network scale $\\implies$ 60/40 balanced allocation (GEMINI.md Rule 6)",
        "base_reason": "Health insurance premium inflation customer resistance and direct composite insurance license competition",
        "bull_reason": "90%+ online insurance distribution monopoly, Paisabazaar credit turnaround, and operating leverage surge",
        "is_platform": False
    },
    "JYOTICNC": {
        "base_cagr": 25, "bull_cagr": 35,
        "base_exit_g": 22.0, "bull_exit_g": 28.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "Specialized 5-axis CNC machine tool import substitution leader with multi-year order book $\\implies$ 55/45 institutional standard (GEMINI.md Rule 6)",
        "base_reason": "Extended customer installation and validation timelines for complex 5-axis aerospace machining centers",
        "bull_reason": "Massive aerospace & defense import substitution demand, record order book execution, and debt elimination",
        "is_platform": False
    },
    "PRESTIGE": {
        "base_cagr": 20, "bull_cagr": 28,
        "base_exit_g": 18.0, "bull_exit_g": 24.0,
        "base_peg": 1.50, "bull_peg": 1.75,
        "base_prob": 60, "bull_prob": 40,
        "rationale": "Tier-1 pan-India real estate developer with robust pre-sales velocity $\\implies$ 60/40 institutional allocation (GEMINI.md Rule 6)",
        "base_reason": "Municipal approval delays for major NCR/Mumbai township launches and residential mortgage rate sensitivities",
        "bull_reason": "Record pre-sales booking milestones, aggressive pan-India expansion (NCR/Mumbai), and hospitality/retail REIT monetizations",
        "is_platform": False
    },
    "SONACOMS": {
        "base_cagr": 20, "bull_cagr": 32,
        "base_exit_g": 17.0, "bull_exit_g": 28.0,
        "base_peg": 1.60, "bull_peg": 1.85,
        "base_pe": 36.0, "bull_pe": 52.0,
        "hist_floor_pe": 36.0, "peer_pe": 52.0, "sector_growth": 0.20,
        "base_prob": 55, "bull_prob": 45,
        "rationale": "High OEM client concentration (Tesla 21%) & Western EV adoption volatility $\\implies$ 55% Base / 45% Bull allocation (GEMINI.md Rule 6); exit multiples triangulated with 36x historical net-cash quality floor and 52x Tier-1 peer median",
        "base_reason": "Global OEM EV program delays, European automotive market softness, and slower US EV adoption",
        "bull_reason": "Traction motor ramp, Escorts Kubota railway division synergies, and order book execution (₹24,000 Cr+)",
        "is_platform": False
    }
}


def calibrate_stock_parameters(company_data: dict) -> dict:
    """
    Calibrates growth, exit multiples, and dynamic probability split strictly matching GEMINI.md directives.
    """
    ticker = (company_data.get("ticker") or "").upper().replace(" ", "").replace("-", "")
    if ticker in KNOWN_COMPANY_PROFILES:
        profile = KNOWN_COMPANY_PROFILES[ticker].copy()
        profile["bull_prob"] = 100 - profile["base_prob"]
        return profile

    sales_3yr = company_data.get("sales_growth_3yr") or 0.0
    pat_3yr = company_data.get("profit_growth_3yr") or 0.0
    roe_3yr = company_data.get("roe_3yr") or 0.0
    roce = company_data.get("roce") or 0.0
    debtor_days = company_data.get("latest_debtor_days") or 60.0
    about = (company_data.get("about") or "").lower()

    cum_cfo = sum(company_data.get("cfo_history", []))
    cum_pat = sum(company_data.get("pat_history", []))
    cfo_pat_ratio = (cum_cfo / cum_pat) if cum_pat > 0 else 0.5

    # 1. Archetype 4: Sovereign Supplier / High Regulatory Vulnerability
    is_sovereign_trap = any(w in about for w in ["irctc", "railway ticket", "sovereign", "concessionaire", "toll"])
    if is_sovereign_trap:
        base_cagr = 16
        bull_cagr = 28
        base_exit_g = 16.0
        bull_exit_g = 26.0
        base_peg = 1.25
        bull_peg = 1.60
        base_prob = 75
        rationale = "High regulatory vulnerability or sovereign supplier trap $\\implies$ 75% Base / 25% Bull margin-of-safety dominance (GEMINI.md Archetype 4)"
        base_reason = "Moderating top-line growth under supplier take-rate caps or regulatory intervention"
        bull_reason = "Flawless category expansion, multi-modal market share capture, and high-margin ancillary revenue"

    # 2. Archetype 1: Elite Execution & Secular Sunrise Compounder
    elif (sales_3yr >= 25.0 or pat_3yr >= 25.0) and cfo_pat_ratio >= 0.70 and roce >= 18.0:
        base_cagr = min(35, max(25, int(round(sales_3yr * 0.85)))) if sales_3yr > 0 else 25
        bull_cagr = min(48, base_cagr + 10)
        base_exit_g = min(28.0, max(22.0, round(base_cagr * 0.85, 1)))
        bull_exit_g = min(36.0, max(28.0, round(bull_cagr * 0.85, 1)))
        base_peg = 1.60
        bull_peg = 1.85
        base_prob = 50
        rationale = f"Elite execution & cash conversion (CFO/PAT {cfo_pat_ratio:.1f}x, ROCE {roce:.0f}%) $\\implies$ 50/50 balanced weighting (GEMINI.md Archetype 1)"
        base_reason = f"Execution friction, milestone delays, or temporary margin capping (CAGR {base_cagr}%)"
        bull_reason = f"Flawless execution, market share consolidation, and strong operational leverage (CAGR {bull_cagr}%)"

    # 3. Archetype 3: Working Capital Friction or Client Concentration Drag
    elif cfo_pat_ratio < 0.40 or debtor_days > 130:
        base_cagr = 22
        bull_cagr = 32
        base_exit_g = 20.0
        bull_exit_g = 25.0
        base_peg = 1.60
        bull_peg = 1.85
        base_prob = 65
        rationale = f"Working capital friction (CFO/PAT {cfo_pat_ratio:.1f}x, Debtor Days {debtor_days:.0f}d) $\\implies$ 65/35 margin-of-safety allocation (GEMINI.md Archetype 3)"
        base_reason = "Working capital conversion lag, delayed milestone delivery, or customer concentration deferrals"
        bull_reason = "Order book conversion acceleration, working capital normalization, and operating leverage"

    # 4. Archetype 2: Mature Contracted Oligopoly / Stable Sunrise Franchise
    else:
        base_cagr = min(25, max(20, int(round(sales_3yr * 0.9)))) if sales_3yr > 0 else 20
        bull_cagr = base_cagr + 8
        base_exit_g = min(22.0, max(18.0, round(base_cagr * 0.85, 1)))
        bull_exit_g = min(28.0, max(22.0, round(bull_cagr * 0.85, 1)))
        base_peg = 1.60
        bull_peg = 1.85
        base_prob = 55
        rationale = "Mature contracted franchise with high operational stability $\\implies$ 55/45 institutional standard (GEMINI.md Archetype 2)"
        base_reason = f"Steady-state volume compounding with legacy margin discipline (CAGR {base_cagr}%)"
        bull_reason = f"Market share capture, capacity additions, and pricing power (CAGR {bull_cagr}%)"

    return {
        "base_cagr": base_cagr,
        "bull_cagr": bull_cagr,
        "base_exit_g": base_exit_g,
        "bull_exit_g": bull_exit_g,
        "base_peg": base_peg,
        "bull_peg": bull_peg,
        "base_prob": base_prob,
        "bull_prob": 100 - base_prob,
        "cfo_pat_ratio": round(cfo_pat_ratio, 2),
        "rationale": rationale,
        "base_reason": base_reason,
        "bull_reason": bull_reason,
        "is_platform": (company_data.get("ttm_pat", 0.0) / company_data.get("ttm_sales", 1.0) < 0.02) and (company_data.get("ttm_sales", 0.0) >= 1000.0)
    }


# --- 4. STREAMLIT APPLICATION INTERFACE ---

def calculate_forward_pe_valuation(
    cmp: float,
    mcap_cr: float,
    ttm_eps: float,
    ttm_sales: float = 0.0,
    ttm_pat: float = 0.0,
    shares_cr: float = 0.0,
    base_cagr: float = 0.20,
    bull_cagr: float = 0.25,
    base_exit_growth: float = None,
    bull_exit_growth: float = None,
    base_peg: float = 1.60,
    bull_peg: float = 1.85,
    base_prob: float = 0.65,
    bull_prob: float = 0.35,
    base_reason: str = None,
    bull_reason: str = None,
    dilution_pct_annual: float = 0.0,
    current_margin: float = None,
    target_margin_yr2: float = None,
    as_of_date: datetime = None,
    regime_override: str = "Auto",
    ticker: str = "STOCK",
    **kwargs
) -> dict:
    """
    Evaluates 2-year forward growth and dynamic exit P/E valuation.
    Delegates directly to master forward_growth_pe engine if available.
    """
    if _master_calculate_forward_pe_valuation is not None:
        return _master_calculate_forward_pe_valuation(
            cmp=cmp,
            mcap_cr=mcap_cr,
            ttm_eps=ttm_eps,
            ttm_sales=ttm_sales,
            ttm_pat=ttm_pat,
            shares_cr=shares_cr,
            base_cagr=base_cagr,
            bull_cagr=bull_cagr,
            base_exit_growth=base_exit_growth,
            bull_exit_growth=bull_exit_growth,
            base_peg=base_peg,
            bull_peg=bull_peg,
            base_prob=base_prob,
            bull_prob=bull_prob,
            base_reason=base_reason,
            bull_reason=bull_reason,
            dilution_pct_annual=dilution_pct_annual,
            current_margin=current_margin,
            target_margin_yr2=target_margin_yr2,
            as_of_date=as_of_date,
            regime_override=regime_override,
            ticker=ticker,
            **kwargs
        )

    clean_tick = ticker.upper().replace(" ", "").replace("-", "")
    npm = (ttm_pat / ttm_sales) if (ttm_sales > 0 and ttm_pat > 0) else 0.10

    if regime_override == "Regime 2 (Platform)":
        is_platform = True
        detection_reason = "Manual Override: Forced to Regime 2 (Platform Operating Leverage)"
    elif regime_override == "Regime 1 (Steady-State)":
        is_platform = False
        detection_reason = "Manual Override: Forced to Regime 1 (Steady-State Margin Compounder)"
    else:
        if clean_tick in KNOWN_COMPANY_PROFILES and "is_platform" in KNOWN_COMPANY_PROFILES[clean_tick]:
            is_platform = KNOWN_COMPANY_PROFILES[clean_tick]["is_platform"]
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

    if is_platform:
        # In Regime 2, rev_cagr is top-line growth (base_cagr), operating leverage expands margin to target_margin_yr2
        rev_cagr = base_cagr
        curr_m = current_margin if current_margin is not None else npm
        tgt_m = target_margin_yr2 if target_margin_yr2 is not None else max(0.045, min(0.065, npm * 4.0))
        
        res = evaluate_forward_growth(
            ticker=ticker,
            cmp=cmp,
            mcap=mcap_cr,
            current_eps=ttm_eps,
            rev_cagr=rev_cagr,
            current_margin=curr_m,
            target_margin_yr2=tgt_m,
            bull_cagr=bull_cagr,
            base_exit_growth=base_exit_growth,
            bull_exit_growth=bull_exit_growth,
            base_peg=base_peg,
            bull_peg=bull_peg,
            base_reason=base_reason,
            bull_reason=bull_reason,
            base_prob=base_prob,
            bull_prob=bull_prob,
            dilution_pct_annual=dilution_pct_annual,
            as_of_date=as_of_date
        )
    else:
        res = evaluate_forward_growth(
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
            base_reason=base_reason,
            bull_reason=bull_reason,
            base_prob=base_prob,
            bull_prob=bull_prob,
            dilution_pct_annual=dilution_pct_annual,
            as_of_date=as_of_date
        )

    res["detection_reason"] = detection_reason
    res["is_platform"] = is_platform
    return res
