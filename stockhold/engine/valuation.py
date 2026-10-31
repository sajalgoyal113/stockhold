#!/usr/bin/env python3
"""
forward_growth_pe.py - High-Growth Stock & 2-Year Forward P/E Valuation Engine

Implements the institutional growth and valuation framework:
- Fixed 2-year horizon from the as-of date; EPS compounded from the end of the TTM window.
- Bear / Base / Bull scenarios; every BUY must clear HURDLE_RATE on the expected value.
- Evaluates 2-Year Forward P/E against the <= 80x hurdle.
- Dynamically derives Base Case and Bull Case exit P/E multiples from expected growth rates at the end of the evaluation period.
- Requires explicit operational rationales for assumed growth rates.
- Verifies mandated >= 50% Bull Case 2-Year upside.
- Displays Latest Market Cap and generates clean, institutional terminal summary cards.
"""

import os
import sys
import json
import argparse
import math
from datetime import datetime
import pandas as pd
import numpy as np
import statistics


# ==============================================================================
# ARCHITECTURAL MODULE TOGGLES
# ==============================================================================
# Modules 1, 3, 4, 5, 6, 8, 9 are FULLY ACTIVE.
# Modules 2 and 7 are configurable and default to False pending user discussion.
ENABLE_MODULE_2_SGR_AND_DRAG = os.environ.get('ENABLE_MODULE_2', '0') == '1'
ENABLE_MODULE_7_REGIME_3_MARGIN_BRIDGE = os.environ.get('ENABLE_MODULE_7', '0') == '1'

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

def determine_fiscal_period(as_of_date=None, half_override=None, fy_override=None):
    """
    Determines running fiscal year, active quarter, and roll-forward targets.
    Indian Financial Year: April 1 to March 31.
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


KNOWN_COMPANY_PROFILES = {}  # Deprecated in favor of 100% first-principles fundamental derivation

# Fixed valuation horizon: targets are the price 2 years from the as-of date.
# (Replaces the H1/H2 roll-forward, which compounded 2 or 3 years depending on the
# calendar month and made verdicts flip between Sep 30 and Oct 1.)
HORIZON_YEARS = 2.0
# Minimum acceptable expected annual return for any BUY verdict. This is an
# ASSUMPTION (roughly a risk-free rate plus an equity risk premium), not a market
# fact: adjust it to your own required return.
HURDLE_RATE = 0.12
# Growth kill switch (decision brief): YoY quarterly sales growth below this for two straight
# quarters is an exit trigger, so it also blocks a new BUY.
KILL_SWITCH_SALES_YOY = 12.0


def derive_exit_pes(base_exit_g, bull_exit_g, base_peg, bull_peg, current_pe, is_fragile, q_factor=1.0,
                    rerate_ok=False):
    """Exit P/E = PEG x end-of-period growth (in %), with no free re-rating floors.

    Re-rating vs today's P/E is capped: up to 1.75x (base) / 2.25x (bull) only with KNOWN
    quality (rerate_ok), otherwise 1.25x / 1.6x; the market's current multiple is evidence too.
    Fragile companies (high debt, weak cash conversion, low ROCE) cannot re-rate:
    base is capped at 0.85x and bull at 1.05x the current P/E.
    """
    base = base_exit_g * base_peg * q_factor
    bull = bull_exit_g * bull_peg * q_factor
    cheap = 0.0 < current_pe < 22.0
    cap_base, cap_bull = (40.0, 55.0) if cheap else (60.0, 85.0)
    lo_base, lo_bull = 8.0, 10.0
    if current_pe > 0:
        if is_fragile:
            base_mult, bull_mult = 0.85, 1.05
        elif rerate_ok:
            base_mult, bull_mult = 1.75, 2.25
        else:
            base_mult, bull_mult = 1.25, 1.60
        base = min(base, current_pe * base_mult)
        bull = min(bull, current_pe * bull_mult)
        lo_base = min(lo_base, current_pe * base_mult)
        lo_bull = min(lo_bull, current_pe * bull_mult)
    base = max(lo_base, min(cap_base, base))
    bull = max(lo_bull, min(cap_bull, bull))
    bull = max(bull, base)
    return round(base, 1), round(bull, 1)


def implied_bear_prob(anchor_g, bull_g, bear_g):
    """Bear weight (0-1) that makes probability-weighted growth equal the growth anchor."""
    if bull_g - bear_g <= 1e-9:
        return 0.5
    return min(1.0, max(0.0, (bull_g - anchor_g) / (bull_g - bear_g)))


# Reliability assumed for guidance with no scored track record (0.75 prior x 0.9 confidence).
PRIOR_GUIDANCE_RELIABILITY = 0.675


def _annual_margins(company_data):
    """[(fy_label, sales, pat, npm)] for full fiscal years (TTM column excluded)."""
    heads = company_data.get("pl_headers") or []
    pl = company_data.get("pl_data") or {}
    sales, pats = pl.get("Sales") or [], pl.get("Net Profit") or []
    def _n(x):
        try:
            return float(str(x).replace(",", "").strip() or 0)
        except ValueError:
            return 0.0
    out = []
    for i, h in enumerate(heads):
        if str(h).strip().upper() == "TTM" or i >= len(sales) or i >= len(pats):
            continue
        sv, pv = _n(sales[i]), _n(pats[i])
        if sv > 0:
            out.append((str(h), sv, pv, pv / sv))
    return out


def _quarter_series(company_data):
    q = company_data.get("q_data") or {}
    def _n(x):
        try:
            return float(str(x).replace(",", "").strip() or 0)
        except ValueError:
            return 0.0
    return [_n(x) for x in (q.get("Sales") or [])], [_n(x) for x in (q.get("Net Profit") or [])]


def recent_sales_momentum(q_sales, sales_ttm_g=None):
    """Sales growth (%) of the last 2 quarters vs the same 2 quarters a year earlier.

    Returns (growth, note) only if each of the last 2 quarters is up YoY, else (None, "").
    Base-effect guard: a rebound off a trough year is not growth. With 10+ quarters the result is
    the lower of the 1-year growth and the 2-year CAGR vs the same 2 quarters two years earlier;
    without a 2-year base it is averaged with TTM growth (unknown is not good).
    """
    if len(q_sales) < 6 or not (q_sales[-1] > q_sales[-5] and q_sales[-2] > q_sales[-6]):
        return None, ""
    cur, prev = q_sales[-1] + q_sales[-2], q_sales[-5] + q_sales[-6]
    if prev <= 0:
        return None, ""
    g1 = (cur / prev - 1.0) * 100.0
    if len(q_sales) >= 10 and (q_sales[-9] + q_sales[-10]) > 0:
        g2 = ((cur / (q_sales[-9] + q_sales[-10])) ** 0.5 - 1.0) * 100.0
        return min(g1, g2), f"last 2Q {g1:+.1f}% YoY, {g2:+.1f}% 2Y CAGR (base-effect guard)"
    if sales_ttm_g is not None:
        return (g1 + float(sales_ttm_g)) / 2.0, f"last 2Q {g1:+.1f}% YoY, no 2Y base -> averaged with TTM"
    return g1, f"last 2Q {g1:+.1f}% YoY, no 2Y base"


def detect_margin_normalization(company_data, guidance_data, reliability, sales_3yr, pat_3yr, decay,
                                base_cagr, bull_cagr):
    """Regime 3 detection: current net margin far below a steady-state margin.

    Steady-state margin: guided PAT margin x reliability (concall guidance), else the company's
    own 2nd-best net margin of the last 10 fiscal years (needs >= 4 profitable years).
    Sub-types and the EVIDENCE each needs (no evidence -> no normalization):
      turnaround (revenue growing: early profitability / loss-making scale-up):
        3Y sales growth > 0, TTM sales growth > 0, and the last 2 quarters' net margin above the
        same 2 quarters a year earlier.
      recovery (business fell: 3Y sales < 5% or 3Y PAT < 0):
        last 2 quarters PAT up YoY (each), latest-quarter margin >= TTM margin, last FY CFO > 0.
    """
    info = {"margin_path": None}
    ttm_sales = float(company_data.get("ttm_sales") or 0.0)
    ttm_pat = float(company_data.get("ttm_pat") or 0.0)
    if ttm_sales <= 0 or not company_data.get("pl_data"):
        return info
    ttm_npm = ttm_pat / ttm_sales

    ss, src = None, None
    gm = guidance_data.get("guided_pat_margin")
    if gm:
        m_rel = guidance_data.get("margin_reliability") or reliability
        ss, src = float(gm) * min(1.0, float(m_rel)), "guidance"
    hist = _annual_margins(company_data)[-10:]
    pos = sorted([m for _, _, _, m in hist if m > 0], reverse=True)
    hist_ss = pos[1] if len(pos) >= 4 else None
    if ss is None and hist_ss is not None:
        ss, src = hist_ss, "history"
    if ss is None:
        # No guidance and no profitable history: median net margin of PROFITABLE peers
        # (>= 3 needed), haircut 20% because peers are only an analogy.
        peers = sorted(m for m in (company_data.get("peer_npms") or []) if m > 0)
        if len(peers) >= 3:
            ss, src = min(0.25, peers[len(peers) // 2]) * 0.80, "peers"
    if ss is None or ss < 0.03 or ttm_npm >= 0.5 * ss:
        return info

    q_sales, q_pat = _quarter_series(company_data)
    sales_ttm_g = company_data.get("sales_growth_ttm")
    cfo_h = company_data.get("cfo_history") or []
    fell = sales_3yr < 5.0 or pat_3yr < 0.0
    evidence, kind = [], None
    if not fell:
        ok = sales_3yr > 0 and (sales_ttm_g is None or float(sales_ttm_g) > 0)
        if len(q_sales) >= 6 and len(q_pat) >= 6 and ok:
            recent = sum(q_pat[-2:]) / max(1e-9, sum(q_sales[-2:]))
            year_ago = sum(q_pat[-6:-4]) / max(1e-9, sum(q_sales[-6:-4]))
            if recent > year_ago:
                kind = "turnaround"
                evidence.append(f"last-2Q NPM {recent*100:.1f}% vs {year_ago*100:.1f}% a year earlier; sales growing")
    else:
        if len(q_pat) >= 6 and len(q_sales) >= 1:
            yoy1 = q_pat[-1] > q_pat[-5]
            yoy2 = q_pat[-2] > q_pat[-6]
            latest_m = q_pat[-1] / q_sales[-1] if q_sales[-1] > 0 else -1
            cfo_ok = bool(cfo_h) and cfo_h[-1] > 0
            if yoy1 and yoy2 and latest_m >= ttm_npm and cfo_ok:
                kind = "recovery"
                evidence.append(f"PAT up YoY in each of the last 2 quarters; latest-Q NPM {latest_m*100:.1f}% >= TTM {ttm_npm*100:.1f}%; last FY CFO > 0")
    if kind is None:
        info["depressed_no_evidence"] = True
        info["note"] = (f" [DEPRESSED MARGIN: TTM NPM {ttm_npm*100:.1f}% vs steady-state {ss*100:.1f}% ({src}), "
                        f"but no recovery/turnaround evidence yet -> normal model]")
        return info

    g_guided = guidance_data.get("guided_rev_cagr")
    if g_guided is not None:
        g_bull = float(g_guided)
        g_base = g_bull * min(1.0, reliability)
    elif kind == "turnaround":
        g_base = max(0.0, min(30.0, sales_3yr * decay))
        g_bull = g_base + 4.0
    else:
        g5 = company_data.get("sales_growth_5yr")
        g_base = max(0.0, min(15.0, (float(g5) if g5 is not None else max(sales_3yr, 0.0)) * 0.8))
        g_bull = g_base + 4.0
    info.update({
        "margin_path": kind,
        "ss_margin": round(ss, 4),
        "ss_margin_source": src,
        "ttm_npm": round(ttm_npm, 4),
        "g_rev_base": round(g_base, 1),
        "g_rev_bull": round(min(48.0, g_bull), 1),
        "margin_evidence": "; ".join(evidence),
        "note": (f" [REGIME 3 {kind.upper()}: NPM {ttm_npm*100:.1f}% -> steady-state {ss*100:.1f}% ({src}); "
                 f"evidence: {'; '.join(evidence)}]"),
    })
    return info


def calibrate_first_principles(company_data: dict, guided_cagr: float = None, **kwargs) -> dict:
    """
    World-Class First-Principles Quantitative Calibration Engine.
    Zero hardcoded ticker profiles. Derives sustainable growth (SGR), empirical decayed velocity,
    endogenous dynamic exit P/E (Mauboussin/Damodaran), and Bayesian probability split directly
    from audited financial statement data and verified guidance registry.
    """
    # registry_ticker = the symbol the user asked for (Screener may resolve an alias)
    ticker = (company_data.get("registry_ticker") or company_data.get("ticker") or "").upper().replace(" ", "").replace("-", "")
    
    # Load central guidance & order book registry if available (Unified Source of Truth)
    guidance_data = {}
    candidate_paths = [
        os.path.join(os.path.dirname(_SCRIPT_DIR), "data", "guidance_registry.json"),
        os.path.join(os.path.dirname(os.path.dirname(_SCRIPT_DIR)), "predict", "data", "guidance_registry.json"),
    ]
    for gp in candidate_paths:
        if os.path.isfile(gp):
            try:
                with open(gp, "r", encoding="utf-8") as f:
                    all_g = json.load(f)
                    guidance_data = all_g.get(ticker) or all_g.get("_entries", {}).get(ticker, {})
                break
            except Exception:
                pass

    # Auto-extracted concall guidance (guidance_fetcher): registry entry if fresh, else a live
    # fetch for LIVE data only (company_data carries the Screener "concalls" list).
    if not guidance_data.get("guided_rev_cagr") and not guidance_data.get("guided_pat_margin") \
            and company_data.get("concalls") and os.environ.get("STOCKS_NO_GUIDANCE_FETCH") != "1":
        try:
            try:
                from guidance_fetcher import get_guidance
            except ImportError:
                try:
                    from engine.guidance_fetcher import get_guidance
                except ImportError:
                    from stockhold.engine.guidance_fetcher import get_guidance
            auto_g = get_guidance(ticker, data=company_data) or {}
            if auto_g:
                guidance_data = {**auto_g, **guidance_data}
        except Exception:
            pass
    manual_override = any(k in guidance_data for k in
                          ("base_cagr", "bull_cagr", "base_exit_g", "bull_exit_g", "base_exit_pe", "bull_exit_pe", "bear_prob"))

    # Load verified fundamental snapshot if company_data fields are sparse
    fund_paths = [
        os.path.join(os.path.dirname(_SCRIPT_DIR), "data", "portfolio_fundamentals.json"),
        os.path.join(os.path.dirname(os.path.dirname(_SCRIPT_DIR)), "predict", "data", "portfolio_fundamentals.json"),
    ]
    for fp in fund_paths:
        if os.path.isfile(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    fund_db = json.load(f)
                    if ticker in fund_db and isinstance(fund_db[ticker], dict):
                        frec = fund_db[ticker]
                        for fkey, fval in frec.items():
                            if company_data.get(fkey) is None and fval is not None:
                                company_data[fkey] = fval
                break
            except Exception:
                pass

    # 1. Financial Statement Metrics (sparse inputs are flagged, never silent).
    # Missing values stay None: an unknown metric must never be priced as a good one.
    def _opt_float(key):
        v = company_data.get(key)
        return float(v) if v is not None else None

    sparse_fields = []
    sales_3yr_raw = _opt_float("sales_growth_3yr")
    pat_3yr_raw = _opt_float("profit_growth_3yr")
    roce_raw = _opt_float("roce")
    roe_raw = _opt_float("roe") if company_data.get("roe") is not None else _opt_float("roe_3yr")
    if sales_3yr_raw is None:
        sparse_fields.append("sales_growth_3yr->MISSING (no growth anchor: insufficient data)")
    if pat_3yr_raw is None:
        sparse_fields.append("profit_growth_3yr->MISSING (treated as 0)")
    if roce_raw is None:
        sparse_fields.append("roce->MISSING (not eligible for quality tier)")
    if roe_raw is None:
        sparse_fields.append("roe->MISSING (SGR ceiling uses 12%)")
    if not company_data.get("cfo_history") or not company_data.get("pat_history"):
        sparse_fields.append("cfo/pat history->MISSING (not eligible for quality tier)")
    insufficient_data = sales_3yr_raw is None and guidance_data.get("guided_rev_cagr") is None
    sales_3yr = sales_3yr_raw if sales_3yr_raw is not None else 0.0
    pat_3yr = pat_3yr_raw if pat_3yr_raw is not None else 0.0
    roce = roce_raw if roce_raw is not None else 0.0
    roe = roe_raw if roe_raw is not None else 12.0
    debtor_days = float(company_data.get("latest_debtor_days") or 60.0)
    mcap = float(company_data.get("mcap") or company_data.get("mcap_cr") or 0.0)
    if mcap <= 0:
        sparse_fields.append("mcap->MISSING (size decay uses small-cap 0.90)")
    latest_debt = float(company_data.get("latest_debt") or 0.0)
    cmp = float(company_data.get("cmp") or 0.0)
    ttm_eps = float(company_data.get("ttm_eps") or 0.0)
    current_pe = float(company_data.get("pe") or (cmp / ttm_eps if ttm_eps > 0 else 0.0))
    # Altman: None means UNKNOWN. It is neutral (q-factor 1.0, no tier change):
    # it can neither upgrade nor downgrade a company.
    altman_raw = company_data.get("altman_z")
    altman_missing = altman_raw is None
    if altman_missing:
        sparse_fields.append("altman_z->UNAVAILABLE (neutral)")
    altman_z_for_math = float(altman_raw) if altman_raw is not None else 5.0

    # Cash conversion: Audited 4-year cumulative ratio (neutralizes capex lumps)
    cfo_h = company_data.get("cfo_history", [])
    pat_h = company_data.get("pat_history", [])
    cfo_pat_ratio = _opt_float("cfo_pat")
    if cfo_h and pat_h and sum(pat_h) > 0:
        cfo_pat_ratio = sum(cfo_h) / sum(pat_h)
    cfo_pat_known = cfo_pat_ratio is not None

    # Disqualification check (Promoter Pledging > 50%). Pledge data is not scraped
    # by data_fetcher; when absent it is flagged, not assumed zero.
    pledge_known = company_data.get("pledge_pct") is not None or bool(company_data.get("fy_trend"))
    pledge_pct = float(company_data.get("pledge_pct") or 0.0)
    for row in company_data.get("fy_trend", []):
        if row.get("pledge", 0) > pledge_pct:
            pledge_pct = row["pledge"]
    if not pledge_known:
        sparse_fields.append("pledge_pct->UNAVAILABLE (pledge check not performed)")

    debt_to_mcap = latest_debt / mcap if mcap > 0 else 0.0

    if pledge_pct > 50.0:
        return {
            "base_cagr": 0.0, "bull_cagr": 0.0, "bear_cagr": 0.0,
            "base_exit_g": 0.0, "bull_exit_g": 0.0,
            "base_exit_pe": 0.0, "bull_exit_pe": 0.0,
            "base_peg": 1.0, "bull_peg": 1.0,
            "bull_prob": 50, "bear_prob": 50,
            "rationale": f"Fundamentally Disqualified (Promoter Pledge {pledge_pct:.1f}% exceeds 50% safety limit)",
            "bull_reason": "Emergency debt restructuring or promoter stake bailout",
            "disqualified": True,
            "insufficient_data": insufficient_data,
            "is_platform": False,
            "is_fragile": True,
            "q_factor": 1.0,
            "roce": roce_raw,
            "cfo_pat_ratio": round(cfo_pat_ratio, 2) if cfo_pat_known else None,
            "debt_to_mcap": round(debt_to_mcap, 3),
            "altman_z": None,
            "altman_missing": True,
            "sparse_fields": ["disqualified: pledge path"],
            "sparse_anchor": True
        }

    # Regime 2 (platform operating leverage - Approach A):
    # Operating leverage needs evidence: thin margin (< 3.0%) at scale (TTM sales >= 1000 Cr),
    # hyper-growth (sales_3yr >= 25%), low debt (debt_to_mcap < 0.15), AND positive operating
    # cash flow (CFO > 0). A slow-growing distributor or cash-burning startup is disqualified.
    ttm_pat = company_data.get("ttm_pat") or 0.0
    ttm_sales = company_data.get("ttm_sales") or 0.0
    npm_curr = (ttm_pat / ttm_sales) if (ttm_sales > 0 and ttm_pat > 0) else None
    is_cfo_positive = (len(cfo_h) > 0 and (sum(cfo_h[-3:]) > 0 or cfo_h[-1] > 0)) or (cfo_pat_known and cfo_pat_ratio > 0.40)
    has_guidance = bool(guidance_data.get("guided_pat_margin") or guidance_data.get("guided_rev_cagr")
                        or guided_cagr is not None or kwargs.get("rev_cagr") is not None
                        or kwargs.get("target_margin_yr2") is not None or kwargs.get("base_growth_override") is not None)
    is_platform = (npm_curr is not None and npm_curr < 0.03 and ttm_sales >= 1000.0
                   and sales_3yr >= 25.0 and debt_to_mcap < 0.15 and is_cfo_positive and has_guidance)
    current_margin = None
    target_margin_yr2 = None
    if is_platform:
        current_margin = npm_curr
        # Approach A Target Margin Bridge: concall-guided steady-state NPM if on file,
        # else conservative platform steady-state benchmark (4.5%, capped at 5.0%).
        guided_npm = guidance_data.get("guided_pat_margin")
        if guided_npm is not None and float(guided_npm) > 0:
            target_margin_yr2 = float(guided_npm)
        else:
            target_margin_yr2 = max(npm_curr, min(0.045, max(0.035, npm_curr * 3.0)))

    # 2. Empirical Velocity & Base CAGR Anchor
    enable_m2 = kwargs.get('enable_module_2', ENABLE_MODULE_2_SGR_AND_DRAG)
    enable_m7 = kwargs.get('enable_module_7', ENABLE_MODULE_7_REGIME_3_MARGIN_BRIDGE)
    decay = (0.80 if mcap >= 50000.0 else (0.85 if mcap >= 10000.0 else 0.90)) if enable_m2 else 1.0

    # Trough-base guard: profit growth can lift the anchor only up to 1.25x sales growth
    # (a PAT rebound off a depressed base is not sustainable earnings velocity).
    pat_term = min(pat_3yr * 0.75, max(sales_3yr, 0.0) * 1.25)
    # Current sales momentum: TTM growth, unless the last 2 quarters (each up YoY, base-effect
    # guarded) show a stronger recovery the TTM window still hides (it can include a trough).
    revenue_recovery_note = ""
    sales_ttm_g = company_data.get("sales_growth_ttm")
    q_s, _q_p = _quarter_series(company_data)
    recent_g, recent_desc = recent_sales_momentum(q_s, sales_ttm_g)
    momentum_g = float(sales_ttm_g) if sales_ttm_g is not None else None
    momentum_label = "TTM sales"
    if recent_g is not None and (momentum_g is None or recent_g > momentum_g):
        if momentum_g is not None:
            revenue_recovery_note = (f" [RECENT-QUARTER RECOVERY: TTM sales {momentum_g:.1f}% but {recent_desc} "
                                     f"-> momentum {recent_g:.1f}%]")
        momentum_g = recent_g
        momentum_label = "Recent sales"
    # Revenue recovery: momentum clearly above the 3Y CAGR (a dip inside the window) with each of
    # the last 2 quarters up YoY -> the anchor blends 3Y and momentum growth (50/50).
    eff_sales_g = sales_3yr
    if (momentum_g is not None and recent_g is not None and momentum_g > sales_3yr + 10.0):
        eff_sales_g = (sales_3yr + momentum_g) / 2.0
        revenue_recovery_note += (f" [REVENUE RECOVERY: 3Y sales {sales_3yr:.1f}% vs {momentum_label.lower()} {momentum_g:.1f}% "
                                  f"with last 2Q up YoY -> growth anchor {eff_sales_g:.1f}%]")
    # Deceleration: momentum below the 3Y CAGR -> the anchor blends 3Y and momentum (50/50),
    # so a stalled business is not priced on its old growth rate.
    momentum_note = ""
    decelerating = False
    if momentum_g is not None and momentum_g < eff_sales_g:
        decelerating = momentum_g < 0.5 * sales_3yr
        eff_sales_g = (eff_sales_g + momentum_g) / 2.0
        momentum_note = (f" [DECELERATION: {momentum_label} {momentum_g:.1f}% < 3Y {sales_3yr:.1f}% "
                         f"-> growth anchor {eff_sales_g:.1f}%]")
    # Margin compression: TTM PAT (last 4Q) growing 5+ pts slower than TTM sales.
    margin_compressing = False
    if len(q_s) >= 8 and len(_q_p) >= 8 and sum(q_s[-8:-4]) > 0 and sum(_q_p[-8:-4]) > 0:
        q_sales_g = (sum(q_s[-4:]) / sum(q_s[-8:-4]) - 1.0) * 100.0
        q_pat_g = (sum(_q_p[-4:]) / sum(_q_p[-8:-4]) - 1.0) * 100.0
        if q_pat_g < q_sales_g - 5.0:
            margin_compressing = True
            momentum_note += (f" [MARGIN COMPRESSION: TTM PAT {q_pat_g:+.1f}% vs TTM sales {q_sales_g:+.1f}% "
                              f"-> 15% growth haircut]")
    pat_term = min(pat_3yr * 0.75, max(eff_sales_g, 0.0) * 1.25)
    historical_anchor = max(eff_sales_g, pat_term) * decay
    # Debt, working-capital & margin drag: 15% haircut per flag, at most 35% in total.
    drag_flags = [debt_to_mcap > 0.35, cfo_pat_known and cfo_pat_ratio < 0.60, debtor_days > 100,
                  margin_compressing]
    if enable_m2 and historical_anchor > 0 and any(drag_flags):
        historical_anchor *= max(0.65, 0.85 ** sum(drag_flags))
    # No growth floor: a shrinking business is projected at zero growth, never a positive default.
    base_cagr = round(max(0.0, min(40.0 if is_platform else 36.0, historical_anchor)), 1)

    # 3. Bull Case & Guidance Reconciliation
    # Management guidance (CLI --growth, or concall guidance from the registry / guidance_fetcher)
    # sets the BULL case (capped if it stretches past the sustainable-growth ceiling); the BASE
    # case is guidance x delivery reliability from the company's own guided-vs-actual record.
    guidance_stretch_note = ""
    guidance_note = ""
    sgr_ceiling = roe * 0.85 + (8.0 if roce >= 18.0 else 4.0)
    reliability = guidance_data.get("reliability")
    track_n = int(guidance_data.get("track_record_n") or 0)
    g_val = None
    if guided_cagr is not None and guided_cagr > 0:
        g_val = guided_cagr * 100.0 if guided_cagr <= 1.0 else guided_cagr
        g_src = "CLI guidance"
    elif guidance_data.get("guided_rev_cagr") is not None and not manual_override:
        g_val = float(guidance_data["guided_rev_cagr"])
        g_src = f"concall guidance ({guidance_data.get('as_of', '?')})"
    if reliability is None:
        reliability = PRIOR_GUIDANCE_RELIABILITY
    reliability = float(max(0.40, min(1.05, reliability)))
    if g_val is not None:
        if enable_m2:
            stretch_cap = max(sgr_ceiling * 1.25, max(eff_sales_g, 0.0) * 1.10)
            if g_val > stretch_cap:
                guidance_stretch_note = (f" [GUIDANCE STRETCH: Guided {g_val:.1f}% exceeds capacity cap {stretch_cap:.1f}% "
                                         f"(max of 1.25x SGR {sgr_ceiling:.1f}% and 1.1x demonstrated sales growth)]")
                bull_cagr = round(min(g_val, stretch_cap), 1)
            else:
                bull_cagr = round(float(g_val), 1)
        else:
            bull_cagr = round(float(g_val), 1)
        bull_cagr = max(0.0, min(48.0, bull_cagr))
        # Base = guidance x reliability, pulled halfway toward the momentum-adjusted historical
        # anchor when the reported numbers run below it (guidance never lifts base above itself).
        guided_base = max(0.0, min(40.0, bull_cagr * min(1.0, reliability)))
        history_base = base_cagr
        base_cagr = round(min(guided_base, (guided_base + history_base) / 2.0), 1)
        guidance_note = (f" [GUIDED {g_val:.1f}% via {g_src}; reliability {reliability:.2f} "
                         f"from {track_n} scored promise(s); reported-numbers anchor {history_base:.1f}% "
                         f"-> base {base_cagr:.1f}% / bull {bull_cagr:.1f}%]")
    else:
        # Bull kicker rises with demonstrated profit growth (4 to 12 pts); weak or
        # falling profits get the smallest kicker, never a larger one.
        kicker = min(12.0, max(4.0, pat_3yr * 0.12)) if pat_3yr > 0 else 4.0
        bull_cagr = round(min(48.0, base_cagr + kicker), 1)
    # Guidance must be on file before a conclusion: missing guidance is flagged, never assumed.
    if g_val is not None or manual_override:
        guidance_status = "REVENUE"
    elif guidance_data.get("guided_pat_margin"):
        guidance_status = "MARGIN ONLY"
    elif "reviewed" in str(guidance_data.get("method", "")):
        guidance_status = "REVIEWED: NONE GIVEN"
    else:
        guidance_status = "MISSING"
    if guidance_status != "REVENUE":
        sparse_fields.append(f"guidance->{guidance_status} (no current revenue guidance: growth rests on reported numbers"
                             + ("" if guidance_status.startswith("REVIEWED") else "; check the latest concall") + ")")

    # Invariant: Bull CAGR must always strictly exceed or equal Base CAGR
    if bull_cagr < base_cagr:
        bull_cagr = round(base_cagr + 4.0, 1)
    # Bear case: growth stalls to a quarter of base (or base minus 5 pts if base is ~0).
    bear_cagr = round(base_cagr * 0.25 if base_cagr > 0 else base_cagr - 5.0, 1)

    # 3b. Margin Normalization (Regime 3): earnings far below the company's steady-state margin.
    if enable_m7:
        margin_info = detect_margin_normalization(company_data, guidance_data, reliability,
                                                  sales_3yr, pat_3yr, decay, base_cagr, bull_cagr)
    else:
        margin_info = {}
    if margin_info.get("margin_path"):
        # Base/bull growth here are REVENUE growth; EPS comes from the margin bridge.
        base_cagr = margin_info["g_rev_base"]
        bull_cagr = max(margin_info["g_rev_bull"], base_cagr)
        bear_cagr = round(base_cagr * 0.25, 1)
        insufficient_data = False

    # 4. Endogenous Exit Multiples (Anchored to Balance Sheet Quality & Starting P/E)
    altman_known_weak = (not altman_missing) and (altman_z_for_math < 2.6)

    is_fragile = ((debt_to_mcap > 0.40) or (cfo_pat_known and cfo_pat_ratio < 0.40)
                  or (roce_raw is not None and roce_raw < 12.0) or altman_known_weak or (pledge_pct > 10.0))
    if is_platform and debt_to_mcap < 0.15 and is_cfo_positive:
        is_fragile = False
    # Quality tier requires KNOWN good ROCE and cash conversion.
    is_quality = (roce_raw is not None and roce_raw >= 25.0 and debt_to_mcap < 0.15
                  and cfo_pat_known and cfo_pat_ratio >= 0.80)

    if is_fragile:
        base_peg = 1.15
        bull_peg = 1.40
    elif is_quality or is_platform:
        base_peg = 1.60
        bull_peg = 1.85
    else:
        base_peg = 1.50
        bull_peg = 1.75

    # End-of-period growth: 80% of horizon growth, capped at 25% (very high growth
    # rarely persists beyond the forecast window).
    base_exit_g = round(min(25.0, base_cagr * 0.80), 1)
    bull_exit_g = round(min(25.0, bull_cagr * 0.80), 1)
    q_factor = (min(8.0, max(2.0, altman_z_for_math)) / 5.0) ** 0.20
    # Larger re-rating needs KNOWN good ROCE and cash conversion
    rerate_ok = (not is_fragile and roce_raw is not None and roce_raw >= 18.0
                 and cfo_pat_known and cfo_pat_ratio >= 0.80)
    base_exit_pe, bull_exit_pe = derive_exit_pes(base_exit_g, bull_exit_g, base_peg, bull_peg,
                                                 current_pe, is_fragile, q_factor, rerate_ok)

    # 5. Probability Scorecard (two scenarios: Bull / Bear). The bear weight starts at the level
    # that makes probability-weighted growth equal the growth anchor (base_cagr, the central
    # estimate - an input, not a scenario), then rises for fragility, weak cash conversion,
    # missing data and deteriorating momentum.
    def _bear_prob():
        if margin_info.get("margin_path"):
            # Normalization is a forecast of change. 40% keeps the old central path (60% of the
            # way to steady-state margin) as the expected value.
            bp = 40
            if (company_data.get("ttm_pat") or 0.0) <= 0:
                bp += 10
            if margin_info.get("ss_margin_source") == "history":
                bp += 5
            elif margin_info.get("ss_margin_source") == "peers":
                bp += 10
            if track_n >= 2 and reliability >= 0.85:
                bp -= 10
            return max(30, min(60, bp))
        bp = 100.0 * implied_bear_prob(base_cagr, bull_cagr, bear_cagr)
        if is_fragile:
            bp += 10
        if cfo_pat_known and cfo_pat_ratio < 0.60:
            bp += 5
        if insufficient_data:
            bp += 5
        if decelerating:
            bp += 10
        if margin_compressing:
            bp += 5
        if debtor_days > 120:
            bp += 5
        if altman_known_weak or pledge_pct > 5.0:
            bp += 5
        return int(round(max(20, min(60, bp))))
    bear_prob = _bear_prob()
    bull_prob = 100 - bear_prob

    sparse_prefix = f"[SPARSE INPUTS: {'; '.join(sparse_fields)}] " if sparse_fields else ""
    altman_tag = "UNAVAILABLE" if altman_missing else f"{altman_z_for_math:.2f}"
    roce_tag = f"{roce_raw:.0f}%" if roce_raw is not None else "N/A"
    cfo_tag = f"{cfo_pat_ratio:.2f}x" if cfo_pat_known else "N/A"
    rationale = f"{sparse_prefix}First-Principles Derivation (Sales 3Y {sales_3yr:.1f}%, PAT 3Y {pat_3yr:.1f}%, ROCE {roce_tag}, CFO/PAT {cfo_tag}, Gross Debt/Mcap {debt_to_mcap:.2f}x, Altman {altman_tag}) -> {bull_prob}% Bull / {bear_prob}% Bear allocation (growth anchor {base_cagr:.1f}%){guidance_stretch_note}{guidance_note}{revenue_recovery_note}{momentum_note}{margin_info.get('note', '')}"

    bull_reason = f"Flawless market share expansion, operating leverage, and sustained ROCE compounding (CAGR {bull_cagr:.1f}%)"
    bear_reason = f"Growth stalls and the multiple de-rates (CAGR {bear_cagr:.1f}%)"

    # Unified Source of Truth: apply verified guidance registry parameters if registered
    exit_pe_from_registry = False
    if guidance_data and manual_override:
        if "base_cagr" in guidance_data:
            base_cagr = float(guidance_data["base_cagr"])
        if "bull_cagr" in guidance_data:
            bull_cagr = float(guidance_data["bull_cagr"])
        if "bear_cagr" in guidance_data:
            bear_cagr = float(guidance_data["bear_cagr"])
        if "base_exit_g" in guidance_data:
            base_exit_g = float(guidance_data["base_exit_g"])
        if "bull_exit_g" in guidance_data:
            bull_exit_g = float(guidance_data["bull_exit_g"])
        if "base_exit_pe" in guidance_data:
            base_exit_pe = float(guidance_data["base_exit_pe"])
            exit_pe_from_registry = True
        if "bull_exit_pe" in guidance_data:
            bull_exit_pe = float(guidance_data["bull_exit_pe"])
            exit_pe_from_registry = True
        bear_prob = int(guidance_data["bear_prob"]) if "bear_prob" in guidance_data else _bear_prob()
        bull_prob = 100 - bear_prob
        if "bull_reason" in guidance_data:
            bull_reason = str(guidance_data["bull_reason"])
        rationale = f"Unified Registry Derivation ({guidance_data.get('notes', 'Registered institutional guidance')}) -> {bull_prob}% Bull / {bear_prob}% Bear"

    guidance_quote = None
    if guidance_data.get("current_guidance"):
        for it in guidance_data["current_guidance"]:
            if it.get("quote"):
                guidance_quote = it["quote"]
                break
    if not guidance_quote and guidance_data.get("track_record"):
        for tr in guidance_data["track_record"]:
            if tr.get("quote"):
                guidance_quote = tr["quote"]
                break
    if not guidance_quote and guidance_data.get("notes"):
        guidance_quote = guidance_data["notes"]

    return {
        "base_cagr": base_cagr,
        "bull_cagr": bull_cagr,
        "bear_cagr": bear_cagr,
        "base_exit_g": base_exit_g,
        "bull_exit_g": bull_exit_g,
        "base_exit_pe": base_exit_pe,
        "bull_exit_pe": bull_exit_pe,
        "exit_pe_from_registry": exit_pe_from_registry,
        "base_peg": base_peg,
        "bull_peg": bull_peg,
        "bull_prob": bull_prob,
        "bear_prob": bear_prob,
        "cfo_pat_ratio": round(cfo_pat_ratio, 2) if cfo_pat_known else None,
        "roce": roce_raw,
        "debt_to_mcap": round(debt_to_mcap, 3),
        "is_fragile": is_fragile,
        "is_quality": is_quality,
        "rerate_ok": rerate_ok,
        "q_factor": q_factor,
        "rationale": rationale,
        "bull_reason": bull_reason,
        "bear_reason": bear_reason,
        "is_platform": is_platform,
        "current_margin": current_margin,
        "target_margin_yr2": target_margin_yr2,
        "rev_cagr": (base_cagr / 100.0) if is_platform else None,
        "altman_z": None if altman_missing else round(altman_z_for_math, 2),
        "altman_missing": altman_missing,
        "insufficient_data": insufficient_data,
        "guidance_status": guidance_status,
        "is_guidance_anchored": (guidance_status == "REVENUE"),
        "guidance_quote": guidance_quote,
        "guidance_method": guidance_data.get("method"),
        "decelerating": decelerating,
        "margin_compressing": margin_compressing,
        "guidance_reliability": reliability,
        "guidance_track_n": track_n,
        "guided_rev_cagr": g_val,
        "guidance_as_of": guidance_data.get("as_of"),
        "guidance_sources": guidance_data.get("sources", []),
        **{k: v for k, v in margin_info.items() if k != "note"},
        "sparse_fields": sparse_fields,
        "sparse_anchor": len(sparse_fields) > 0
    }

calibrate_stock_parameters = calibrate_first_principles
_DATA_CACHE = {}

def verify_methodology_integrity() -> list:
    """
    Methodology regression watchdog (checks both directions: optimism AND pessimism).
    Each check encodes a failure mode the model has had before:
    1. A shrinking business must never be projected as a grower.
    2. Missing growth data must be flagged insufficient, never defaulted to a growth rate.
    3. Weak profit growth must never get a bigger bull kicker than strong profit growth.
    4. A slow-growing thin-margin business is not a Regime 2 platform.
    5. A healthy 25% compounder keeps a sane, non-suppressed exit multiple (PEG 1.4x-2.0x).
    6. A cheap, slow, non-fragile stock gets no free re-rating floor.
    7. A business whose TTM sales growth has stalled is not priced on its old 3Y growth rate.
    Returns any detected methodology alerts.
    """
    alerts = []
    shrink = calibrate_first_principles({
        "ticker": "SYN_SHRINK", "sales_growth_3yr": -10.0, "profit_growth_3yr": -20.0,
        "roce": 15.0, "roe": 14.0, "mcap": 5000.0, "cfo_history": [100, 100], "pat_history": [100, 100]})
    if shrink["base_cagr"] > 0.0:
        alerts.append(f"Shrinking business projected at +{shrink['base_cagr']}% base growth")

    nodata = calibrate_first_principles({"ticker": "SYN_NODATA", "mcap": 5000.0})
    if not nodata.get("insufficient_data"):
        alerts.append("Missing sales growth not flagged as insufficient data")

    up = calibrate_first_principles({"ticker": "SYN_UP", "sales_growth_3yr": 10.0, "profit_growth_3yr": 40.0, "mcap": 5000.0})
    down = calibrate_first_principles({"ticker": "SYN_DN", "sales_growth_3yr": 10.0, "profit_growth_3yr": -5.0, "mcap": 5000.0})
    if (down["bull_cagr"] - down["base_cagr"]) > (up["bull_cagr"] - up["base_cagr"]):
        alerts.append("Bull kicker inverted: falling profits get a larger bull uplift than rising profits")

    distrib = calibrate_first_principles({
        "ticker": "SYN_DIST", "sales_growth_3yr": 12.0, "profit_growth_3yr": 10.0, "mcap": 5000.0,
        "ttm_sales": 20000.0, "ttm_pat": 200.0})
    if distrib.get("is_platform"):
        alerts.append("Slow-growing thin-margin business classified as Regime 2 platform")

    qual = calibrate_first_principles({
        "ticker": "SYN_QUAL", "sales_growth_3yr": 25.0, "profit_growth_3yr": 30.0,
        "roce": 26.0, "roe": 24.0, "mcap": 25000.0, "latest_debt": 500.0,
        "cfo_history": [100, 150, 200], "pat_history": [100, 140, 190],
        "cmp": 500.0, "ttm_eps": 20.0, "pe": 25.0})
    if not (1.40 <= qual["base_peg"] <= 2.0 and 1.40 <= qual["bull_peg"] <= 2.0):
        alerts.append(f"PEG out of sane band: base {qual['base_peg']} / bull {qual['bull_peg']}")
    if qual["base_exit_pe"] < 20.0:
        alerts.append(f"Exit PE suppressed: Base Exit PE {qual['base_exit_pe']}x on ~21% growth")

    cheap = calibrate_first_principles({
        "ticker": "SYN_CHEAP", "sales_growth_3yr": 5.0, "profit_growth_3yr": 4.0, "roce": 15.0,
        "mcap": 5000.0, "cfo_history": [100], "pat_history": [100], "cmp": 100.0, "ttm_eps": 12.5, "pe": 8.0})
    if cheap["base_exit_pe"] > 8.0 * 1.25:
        alerts.append(f"Free re-rating: 8x P/E, 5% grower gets {cheap['base_exit_pe']}x base exit")

    stall = calibrate_first_principles({
        "ticker": "SYN_STALL", "sales_growth_3yr": 24.0, "sales_growth_ttm": 6.0, "profit_growth_3yr": 20.0,
        "roce": 26.0, "roe": 22.0, "mcap": 15000.0, "cfo_history": [100], "pat_history": [100]})
    if stall["base_cagr"] >= 24.0 * 0.85 * 0.75:
        alerts.append(f"Stalled business (3Y 24%, TTM 6%) priced at {stall['base_cagr']}% base growth")

    return alerts

def evaluate_forward_growth(ticker, cmp=0.0, mcap=None, current_eps=0.0, current_pe=0.0,
                             enable_module_2=False, enable_module_7=False,
                             guided_cagr=None, bull_cagr=None,
                             base_exit_growth=None, bull_exit_growth=None,
                             base_peg=1.6, bull_peg=1.85,
                             bull_reason=None,
                             dilution_pct_annual=0.0, margin_expansion_pct_annual=0.0,
                             historical_guidance_reliability=1.0,
                             target_eps_yr2=None, rev_cagr=None,
                             current_margin=None, target_margin_yr2=None,
                             as_of_date=None, half_override=None, fy_override=None,
                             base_pe=None, bull_pe=None,
                             hist_floor_pe=None, peer_pe=None,
                              sector_growth=None,
                              dma200=None, dma50=None, ears_status=None,
                              normalized_margin=None,
                              is_duopoly=False, cyclical_normal=False,
                              **kwargs):
    clean_ticker = (ticker or "").upper().replace(" ", "").replace("-", "")
    live_data = None

    integrity_alerts = verify_methodology_integrity()
    if integrity_alerts:
        for alert in integrity_alerts:
            print(f"⚠️  [METHODOLOGY INTEGRITY ALERT] {alert}")

    # Auto-fetch live consolidated quote if CMP/EPS missing or perform sanity drift check
    global _DATA_CACHE
    if clean_ticker in _DATA_CACHE:
        live_data = _DATA_CACHE[clean_ticker]
    else:
        try:
            from data_fetcher import fetch_company_data
            live_data = fetch_company_data(clean_ticker)
            if live_data:
                _DATA_CACHE[clean_ticker] = live_data
        except Exception:
            pass

    try:
        if live_data and live_data.get("cmp") and live_data.get("cmp") > 0:
            live_cmp = float(live_data["cmp"])
            is_live = live_data.get("is_live", False)
            source_label = live_data.get("source_label", "Screener Consolidated" if is_live else "Offline Snapshot")
            
            if cmp <= 0:
                cmp = live_cmp
                if is_live:
                    print(f"[AUTO-FETCHED] Live CMP: ₹{cmp:,.2f} from {source_label}")
                else:
                    print(f"⚠️  [STALE CACHE WARNING] Auto-fetched CMP: ₹{cmp:,.2f} from {source_label}. (Mandatory live quote cross-check required!)")
            else:
                drift = (cmp - live_cmp) / live_cmp
                if abs(drift) > 0.02:
                    print(f"\n⚠️  [PRICE DRIFT WARNING] Specified CMP (₹{cmp:,.2f}) deviates by {drift*100:+.1f}% from {source_label} CMP (₹{live_cmp:,.2f})!")
            
            if current_eps <= 0 and (live_data.get("ttm_eps") or live_data.get("eps")):
                current_eps = float(live_data.get("ttm_eps") or live_data.get("eps"))
                print(f"[AUTO-FETCHED] Rolling Consolidated TTM EPS: ₹{current_eps:.2f}")
            
            if current_eps > 0 and cmp > 0:
                current_pe = cmp / current_eps
            elif current_pe <= 0 and live_data.get("pe"):
                current_pe = float(live_data["pe"])
                
            if mcap is None and (live_data.get("mcap_cr") or live_data.get("mcap")):
                mcap = float(live_data.get("mcap_cr") or live_data.get("mcap"))
    except Exception:
        pass

    if current_eps <= 0 and kwargs.get("fallback_eps"):
        current_eps = float(kwargs["fallback_eps"])
    if current_pe <= 0 and kwargs.get("fallback_pe"):
        current_pe = float(kwargs["fallback_pe"])

    # Extract DMA200 and DMA50 from chart data if available
    if dma200 is None and live_data and isinstance(live_data.get("chart_df"), pd.DataFrame) and not live_data["chart_df"].empty:
        cdf = live_data["chart_df"]
        if "DMA200" in cdf.columns and pd.notnull(cdf["DMA200"].iloc[-1]):
            dma200 = float(cdf["DMA200"].iloc[-1])
        if "DMA50" in cdf.columns and pd.notnull(cdf["DMA50"].iloc[-1]):
            dma50 = float(cdf["DMA50"].iloc[-1])

    # Refinement 1: Auto-detect Mega-Cap Contracted Cash Duopoly (Rule 14)
    if not is_duopoly and mcap and mcap >= 50000.0 and live_data:
        cfo_h = live_data.get("cfo_history", [])
        pat_h = live_data.get("pat_history", [])
        if cfo_h and pat_h and sum(pat_h) > 0:
            cfo_pat_tot = sum(cfo_h) / sum(pat_h)
            if cfo_pat_tot >= 2.5:
                is_duopoly = True
                print(f"[AUTO-DETECTED] Mega-Cap Cash Generator (Mcap ₹{mcap:,.0f} Cr, 4-Yr CFO/PAT {cfo_pat_tot:.1f}x) -> label only; hurdles are NOT relaxed")

    # Peak Margin Stress-Test: applied to every company (no hardcoded ticker list).
    # If TTM operating margin is > 1.25x the median of prior years, project from
    # median-margin EPS instead of peak EPS.
    if live_data and live_data.get("pl_data", {}).get("OPM %"):
        try:
            from data_fetcher import clean_num
            opm_strs = live_data["pl_data"]["OPM %"]
            clean_opms = [clean_num(x) for x in opm_strs if clean_num(x) > 0]
            if len(clean_opms) >= 5:
                med_opm = float(np.median(clean_opms[:-1]))
                curr_opm = float(clean_opms[-1])
                if curr_opm > 1.25 * med_opm and med_opm > 0:
                    print(f"\n⚠️  [CYCLICAL MARGIN PEAK DETECTED] TTM OPM ({curr_opm:.1f}%) exceeds 1.25x 5-Yr Median ({med_opm:.1f}%). Stress-testing with Normalized Median Margin EPS (GEMINI.md Rule 15)")
                    if current_eps > 0:
                        normalized_base_eps = current_eps * (med_opm / curr_opm)
                        print(f"    Normalized Base EPS: ₹{normalized_base_eps:.2f} (Anchored from Peak TTM ₹{current_eps:.2f})")
                        current_eps = normalized_base_eps
        except Exception:
            pass

    # Extract EARS (Earnings Revision & Acceleration) status with March-Quarter Seasonality Normalization
    if ears_status is None and live_data:
        q_headers = live_data.get("q_headers", [])
        raw_pats = live_data.get("q_data", {}).get("Net Profit", [])
        try:
            from data_fetcher import clean_num
            pats = [clean_num(p) for p in raw_pats]
            if len(pats) >= 6 and len(q_headers) >= 6:
                # Same-Quarter YoY Acceleration (Eliminates Q4 March seasonality)
                q0, q0_name = pats[-1], q_headers[-1]
                q0_py, q0_py_name = pats[-5], q_headers[-5]
                yoy_q0 = ((q0 - q0_py) / q0_py) * 100 if q0_py > 0 else 0.0

                q1, q1_name = pats[-2], q_headers[-2]
                q1_py = pats[-6]
                yoy_q1 = ((q1 - q1_py) / q1_py) * 100 if q1_py > 0 else 0.0

                # A smaller decline is not acceleration: the sign of YoY growth is checked first.
                if yoy_q0 < 0 and yoy_q1 < 0:
                    ears_status = f"EARNINGS CONTRACTION ({q0_name} YoY {yoy_q0:+.1f}%, {q1_name} YoY {yoy_q1:+.1f}% | 2 straight quarters of falling PAT)"
                elif yoy_q0 < 0:
                    ears_status = f"DETERIORATING ({q0_name} YoY {yoy_q0:+.1f}% after {q1_name} YoY {yoy_q1:+.1f}% | Seasonally Normalized)"
                elif yoy_q0 > yoy_q1:
                    ears_status = f"POSITIVE ACCELERATION ({q0_name} YoY {yoy_q0:+.1f}% > {q1_name} YoY {yoy_q1:+.1f}% | Seasonally Normalized)"
                else:
                    ears_status = f"MODERATING MOMENTUM ({q0_name} YoY {yoy_q0:+.1f}% vs {q1_name} YoY {yoy_q1:+.1f}% | Seasonally Normalized)"
            elif len(pats) >= 5 and len(q_headers) >= 5:
                q0, q0_name = pats[-1], q_headers[-1]
                q0_py = pats[-5]
                yoy_q0 = ((q0 - q0_py) / q0_py) * 100 if q0_py > 0 else 0.0
                ears_status = f"STEADY EXPANSION ({q0_name} YoY {yoy_q0:+.1f}% | Seasonally Normalized)"
            else:
                ears_status = "EARS UNKNOWN (insufficient quarterly data)"
        except Exception:
            ears_status = "EARS UNKNOWN (quarterly data could not be parsed)"
    elif ears_status is None:
        ears_status = "EARS UNKNOWN (no quarterly data)"

    # Handle pe and eps aliases from kwargs
    if current_pe <= 0 and "pe" in kwargs and kwargs["pe"] is not None:
        current_pe = float(kwargs["pe"])
    if current_eps <= 0 and "eps" in kwargs and kwargs["eps"] is not None:
        current_eps = float(kwargs["eps"])

    # Fallback to known company profile if cmp, eps, or mcap are still missing
    if clean_ticker in KNOWN_COMPANY_PROFILES:
        prof_init = KNOWN_COMPANY_PROFILES[clean_ticker]
        if cmp <= 0 and prof_init.get("cmp"):
            cmp = float(prof_init["cmp"])
        if current_eps <= 0 and prof_init.get("current_eps"):
            current_eps = float(prof_init["current_eps"])
        if current_pe <= 0 and prof_init.get("current_pe"):
            current_pe = float(prof_init["current_pe"])
        if mcap is None and prof_init.get("mcap"):
            mcap = float(prof_init["mcap"])

    if current_eps <= 0 and current_pe > 0:
        current_eps = cmp / current_pe
    elif current_pe <= 0 and current_eps > 0:
        current_pe = cmp / current_eps

    if _is_lender(live_data, ticker):
        return _no_valuation_result(
            ticker, cmp, mcap, current_eps,
            "NOT APPLICABLE / NO VALUATION (Bank / NBFC / Insurer: P/E-growth model unsuitable for lenders)",
            ears_status=ears_status)

    # Derive growth, exit multiples, and probability split using pure first-principles fundamental calibration
    if live_data is not None:
        live_data.setdefault("ticker", clean_ticker)
        live_data["registry_ticker"] = clean_ticker
    prof = calibrate_first_principles(live_data or {"ticker": clean_ticker, "cmp": cmp, "mcap": mcap}, guided_cagr=guided_cagr)
    print(f"[FIRST-PRINCIPLES DERIVATION] {prof.get('rationale')}")
    margin_path = prof.get("margin_path")

    if current_eps <= 0 and not margin_path:
        return _no_valuation_result(
            ticker, cmp, mcap, current_eps,
            "DISQUALIFIED / NO VALUATION (Loss-Making / Negative TTM EPS, no turnaround evidence: P/E model not applicable)",
            ears_status="TORPEDO ALERT (Loss-Making TTM PAT)")

    if (not margin_path and not prof.get("is_platform") and current_pe > 100.0 and live_data
            and (prof.get("depressed_no_evidence") or (float(live_data.get("ttm_sales") or 0) > 0
                 and float(live_data.get("ttm_pat") or 0) / float(live_data.get("ttm_sales")) < 0.03))):
        return _no_valuation_result(
            ticker, cmp, mcap, current_eps,
            f"NO VALUATION (Trailing P/E {current_pe:.0f}x on thin/depressed earnings and no steady-state margin "
            f"evidence from guidance, history or peers: a P/E target would be meaningless)",
            ears_status=ears_status)

    base_growth_override = kwargs.get("base_growth_override")
    explicit_growth = (guided_cagr is not None or target_eps_yr2 is not None or rev_cagr is not None
                       or base_growth_override is not None)
    if prof.get("insufficient_data") and not explicit_growth:
        return _no_valuation_result(
            ticker, cmp, mcap, current_eps,
            "INSUFFICIENT DATA / NO VALUATION (3Y sales growth unavailable: no growth anchor)",
            ears_status=ears_status)

    is_fragile = bool(prof.get("is_fragile"))
    q_factor = float(prof.get("q_factor") or 1.0)
    bear_cagr = kwargs.get("bear_cagr")
    bear_prob = kwargs.get("bear_prob")

    if prof:
        if margin_path:
            pass  # Regime 3 sets EPS from the margin bridge below
        elif prof.get("is_platform"):
            if current_margin is None and prof.get("current_margin") is not None:
                current_margin = prof.get("current_margin")
            if target_margin_yr2 is None and prof.get("target_margin_yr2") is not None:
                target_margin_yr2 = prof.get("target_margin_yr2")
            if rev_cagr is None and target_eps_yr2 is None:
                rev_cagr = guided_cagr if guided_cagr is not None else (prof.get("rev_cagr") or (prof["base_cagr"] / 100.0))
        elif target_eps_yr2 is None and rev_cagr is None:
            # Base growth: an explicit override (web app / decision brief pass already-calibrated
            # growth) or the calibration, which already folds in CLI/concall guidance x reliability.
            guided_cagr = base_growth_override if base_growth_override is not None else prof["base_cagr"] / 100.0
        if bull_cagr is None and prof.get("bull_cagr") is not None:
            bull_cagr = prof["bull_cagr"] / 100.0
        if bear_cagr is None and prof.get("bear_cagr") is not None:
            bear_cagr = prof["bear_cagr"] / 100.0
        if base_exit_growth is None and prof.get("base_exit_g") is not None:
            base_exit_growth = prof["base_exit_g"] / 100.0
        if bull_exit_growth is None and prof.get("bull_exit_g") is not None:
            bull_exit_growth = prof["bull_exit_g"] / 100.0
        if base_peg == 1.6 and prof.get("base_peg") is not None:
            base_peg = prof.get("base_peg")
        if bull_peg == 1.85 and prof.get("bull_peg") is not None:
            bull_peg = prof.get("bull_peg")
        if bear_prob is None and prof.get("bear_prob") is not None:
            bear_prob = prof["bear_prob"] / 100.0
        if bull_reason is None and prof.get("bull_reason") is not None:
            bull_reason = prof.get("bull_reason")
        if dilution_pct_annual == 0.0 and prof.get("dilution") is not None:
            dilution_pct_annual = prof.get("dilution")
        # Exit P/Es are recomputed below from the FINAL growth/PEG inputs so every
        # entry point (CLI, web app, decision brief) gets identical multiples. Only
        # a registered guidance override is taken verbatim.
        if prof.get("exit_pe_from_registry"):
            if base_pe is None:
                base_pe = prof.get("base_exit_pe")
            if bull_pe is None:
                bull_pe = prof.get("bull_exit_pe")
        if hist_floor_pe is None and prof.get("hist_floor_pe") is not None:
            hist_floor_pe = prof.get("hist_floor_pe")
        if peer_pe is None and prof.get("peer_pe") is not None:
            peer_pe = prof.get("peer_pe")
        if sector_growth is None and prof.get("sector_growth") is not None:
            sector_growth = prof.get("sector_growth")

    # Defensive normalization: convert percentages (> 1.0) to decimal representation
    if rev_cagr is not None and rev_cagr > 1.0:
        rev_cagr /= 100.0
    if guided_cagr is not None and guided_cagr > 1.0:
        guided_cagr /= 100.0
    if bull_cagr is not None and bull_cagr > 1.0:
        bull_cagr /= 100.0
    if bear_cagr is not None and abs(bear_cagr) > 1.0:
        bear_cagr /= 100.0
    if base_exit_growth is not None and base_exit_growth > 1.0:
        base_exit_growth /= 100.0
    if bull_exit_growth is not None and bull_exit_growth > 1.0:
        bull_exit_growth /= 100.0
    if bear_prob is not None and bear_prob > 1.0:
        bear_prob /= 100.0

    # Fixed 2-year horizon. EPS is compounded from the END of the TTM window (not from
    # the last fiscal year), so the TTM's head start is not compounded twice.
    period = determine_fiscal_period(as_of_date, half_override, fy_override)
    as_of_dt = period["dt"]
    ttm_end = _ttm_end_date(live_data, as_of_dt)
    target_dt_yr1 = as_of_dt + pd.DateOffset(years=1)
    target_dt_yr2 = as_of_dt + pd.DateOffset(years=int(HORIZON_YEARS))
    comp_yr1 = max(0.0, (target_dt_yr1 - ttm_end).days / 365.25)
    comp_yr2 = max(0.0, (target_dt_yr2 - ttm_end).days / 365.25)
    horizon_yrs = HORIZON_YEARS
    regime_desc = "Regime 1: Steady-State Margin Growth"

    norm_pe = None
    bear_note = ""
    # CASE M (Regime 3): Margin Normalization - turnaround / early profitability / recovery.
    # EPS = revenue at horizon x scenario margin / shares; margins move from today's TTM net
    # margin toward the steady-state margin (bull: all the way, bear: no improvement; the growth
    # anchor path at 60% of the way is the central estimate used to set the bear exit and weight).
    if margin_path:
        ld = live_data or {}
        m_sales = float(ld.get("ttm_sales") or 0.0)
        shares = float(ld.get("shares_cr") or ((mcap / cmp) if (mcap and cmp > 0) else 0.0))
        if m_sales <= 0 or shares <= 0:
            return _no_valuation_result(ticker, cmp, mcap, current_eps,
                                        "INSUFFICIENT DATA / NO VALUATION (Regime 3 needs TTM sales and share count)",
                                        ears_status=ears_status)
        ss_m = float(prof["ss_margin"])
        cur_m = float(prof["ttm_npm"])
        g_b = base_growth_override if base_growth_override is not None else prof["base_cagr"] / 100.0
        g_u = max(g_b, bull_cagr if bull_cagr is not None else g_b + 0.04)
        g_r = bear_cagr if bear_cagr is not None else g_b * 0.25
        m_base = cur_m + 0.6 * (ss_m - cur_m)
        frac1 = comp_yr1 / comp_yr2 if comp_yr2 > 0 else 0.5

        def _eps(g, m_end, yrs, frac=1.0):
            m = cur_m + (m_end - cur_m) * frac
            return m_sales * ((1.0 + g) ** yrs) * m / shares

        eps_base_yr2 = _eps(g_b, m_base, comp_yr2)
        eps_bull_yr2 = _eps(g_u, ss_m, comp_yr2)
        eps_bull_yr1 = _eps(g_u, ss_m, comp_yr1, frac1)
        eps_bear_yr2 = _eps(g_r, cur_m, comp_yr2)
        base_net_growth, bull_net_growth, bear_net_growth = g_b, g_u, min(g_r, g_b)
        norm_pe = cmp / (m_sales * ss_m / shares)
        regime_desc = (f"Regime 3: Margin Normalization ({margin_path}) | NPM {cur_m*100:.1f}% -> "
                       f"{ss_m*100:.1f}% steady-state ({prof.get('ss_margin_source')}), Rev CAGR base {g_b*100:.1f}% / "
                       f"bull {g_u*100:.1f}% | Normalized P/E {norm_pe:.1f}x")

    # CASE A: Explicit Target EPS provided (interpreted as EPS for the TTM ending at the horizon date)
    elif target_eps_yr2 is not None and target_eps_yr2 > 0:
        eps_base_yr2 = target_eps_yr2
        base_net_growth = (eps_base_yr2 / current_eps) ** (1.0 / comp_yr2) - 1.0
        regime_desc = f"Regime 2: Direct Consensus / Line-Item Build (Horizon Base EPS ₹{target_eps_yr2:.2f})"
        bull_net_growth = max(bull_cagr, base_net_growth * 1.25) if bull_cagr is not None else base_net_growth * 1.25

    # CASE B: Non-linear Margin Expansion Model (Platform / Early Profitability - Approach A)
    elif rev_cagr is not None and current_margin is not None and target_margin_yr2 is not None:
        if current_margin <= 0:
            raise ValueError("Error: current_margin must be > 0 for margin expansion model.")
        effective_rev_cagr = rev_cagr * historical_guidance_reliability
        rev_multiplier_yr2 = (1.0 + effective_rev_cagr) ** comp_yr2
        margin_multiplier = target_margin_yr2 / current_margin
        pat_multiplier_yr2 = rev_multiplier_yr2 * margin_multiplier
        net_pat_cagr = (pat_multiplier_yr2 ** (1.0 / comp_yr2)) - 1.0
        base_net_growth = net_pat_cagr - dilution_pct_annual
        eps_base_yr2 = current_eps * ((1.0 + base_net_growth) ** comp_yr2)
        bull_net_growth = max(bull_cagr if bull_cagr is not None else 0.0, base_net_growth * 1.20)
        regime_desc = (f"Regime 2: Operating Leverage & Margin Expansion (Approach A) "
                       f"({current_margin*100:.2f}% -> {target_margin_yr2*100:.2f}% NPM, Rev CAGR {effective_rev_cagr*100:.1f}%)")

        # Approach A Bear Scenario for Platform: top-line revenue growth slows to ~50% of guided,
        # and margin expansion partially stalls (reaching only 25% of target improvement).
        if bear_cagr is None or (prof and bear_cagr == (prof.get("bear_cagr", 0.0) / 100.0)):
            bear_rev_cagr = effective_rev_cagr * 0.50
            bear_margin = max(current_margin, current_margin + 0.25 * (target_margin_yr2 - current_margin))
            bear_pat_mult = ((1.0 + bear_rev_cagr) ** comp_yr2) * (bear_margin / current_margin)
            bear_net_growth = (bear_pat_mult ** (1.0 / comp_yr2)) - 1.0
            bear_cagr = bear_net_growth

    # CASE C: Standard Linear Model
    else:
        if guided_cagr is None:
            raise ValueError("Error: Must specify either --growth, --target-eps-yr2, or (--rev-cagr, --current-margin, --target-margin-yr2).")
        base_net_growth = (guided_cagr * historical_guidance_reliability) - dilution_pct_annual + margin_expansion_pct_annual
        eps_base_yr2 = current_eps * ((1.0 + base_net_growth) ** comp_yr2)
        bull_net_growth = max(bull_cagr, base_net_growth) if bull_cagr is not None else base_net_growth * 1.25

    # Bull Scenario Projections
    if not margin_path:
        eps_bull_yr1 = current_eps * ((1.0 + bull_net_growth) ** comp_yr1)
        eps_bull_yr2 = current_eps * ((1.0 + bull_net_growth) ** comp_yr2)

    # CASE D: Normalized Turnaround Margin Bridge (only with real sales and share count)
    if normalized_margin is not None and normalized_margin > 0 and not margin_path:
        ttm_sales = live_data.get("ttm_sales", 0.0) if live_data else 0.0
        shares = live_data.get("shares_cr", 0.0) if live_data else 0.0
        if ttm_sales > 0 and shares > 0:
            eff_rev = rev_cagr if rev_cagr is not None else (guided_cagr if guided_cagr is not None else 0.0)
            norm_rev_yr2 = ttm_sales * ((1.0 + eff_rev) ** comp_yr2)
            norm_eps_yr2 = norm_rev_yr2 * normalized_margin / shares
            if norm_eps_yr2 > eps_base_yr2:
                eps_base_yr2 = norm_eps_yr2
                base_net_growth = (eps_base_yr2 / current_eps) ** (1.0 / comp_yr2) - 1.0
                bull_net_growth = max(bull_cagr if bull_cagr else 0.0, base_net_growth * 1.25)
                eps_bull_yr1 = current_eps * ((1.0 + bull_net_growth) ** comp_yr1)
                eps_bull_yr2 = current_eps * ((1.0 + bull_net_growth) ** comp_yr2)
                regime_desc = f"Regime 2: Normalized Turnaround Bridge ({normalized_margin*100:.1f}% Benchmark NPM, Rev CAGR {eff_rev*100:.1f}%)"
        else:
            print("⚠️  [NORMALIZED MARGIN SKIPPED] TTM sales or share count unavailable; not fabricating a revenue base.")

    # Bear Scenario: growth stalls and the multiple de-rates
    if not margin_path:
        if bear_cagr is None:
            bear_cagr = base_net_growth * 0.25 if base_net_growth > 0 else base_net_growth - 0.05
        bear_net_growth = min(bear_cagr, base_net_growth)
        eps_bear_yr2 = current_eps * ((1.0 + bear_net_growth) ** comp_yr2)

    # Determine End-Period Growth Rates
    base_exit_g = base_exit_growth if base_exit_growth is not None else min(0.25, base_net_growth * 0.80)
    bull_exit_g = bull_exit_growth if bull_exit_growth is not None else min(0.25, bull_net_growth * 0.80)

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

    # Exit P/E: one shared derivation (derive_exit_pes) for every entry point
    # Regime 3 measures re-rating against the NORMALIZED P/E (price / steady-state EPS today):
    # trailing P/E on depressed earnings is meaningless.
    ref_pe = norm_pe if margin_path else current_pe
    derived_base_pe, derived_bull_pe = derive_exit_pes(
        base_exit_g * 100, bull_exit_g * 100, base_peg, bull_peg, ref_pe, is_fragile, q_factor,
        bool(prof.get("rerate_ok")))
    if base_pe is None:
        base_pe = derived_base_pe
        if hist_floor_pe is not None:
            base_pe = max(base_pe, hist_floor_pe)
    if bull_pe is None:
        bull_pe = max(derived_bull_pe, base_pe)
        if peer_pe is not None:
            bull_pe = min(bull_pe, round(peer_pe * 1.10, 1))
    # Bear exit: 70% of the base multiple, and at most 0.8x today's multiple (a real de-rating)
    bear_pe = base_pe * 0.70
    if ref_pe and ref_pe > 0:
        bear_pe = min(bear_pe, ref_pe * 0.80)
    bear_pe = round(max(5.0, bear_pe), 1)

    # Valuations. Two scenarios (Bull / Bear). The growth anchor (base_net_growth / eps_base_*)
    # is the central estimate that sets the bear growth, the bear exit multiple and the bear
    # weight; it is not a scenario and has no target of its own.
    fwd_pe_yr2_bull = cmp / eps_bull_yr2 if eps_bull_yr2 > 0 else float('inf')

    def _ann(target):
        return (((target / cmp) ** (1.0 / horizon_yrs)) - 1) * 100 if target > 0 else -100

    bull_target_price = eps_bull_yr2 * bull_pe
    bull_upside_pct = ((bull_target_price - cmp) / cmp) * 100
    bull_annualized_cagr = _ann(bull_target_price)

    bear_target_price = max(0.0, eps_bear_yr2 * bear_pe)
    if margin_path and eps_bear_yr2 <= 0:
        # Turnaround fails while still loss-making: fall back to book value per share (reported),
        # else an explicit assumed 50% drawdown.
        bvps = float((live_data or {}).get("book_value") or 0.0)
        if bvps > 0:
            bear_target_price = min(cmp, bvps)
            bear_note = f"Bear = book value/share ₹{bvps:,.2f} (turnaround fails, still loss-making)"
        else:
            bear_target_price = cmp * 0.5
            bear_note = "Bear = ASSUMED 50% drawdown (loss-making, no book value available)"
    bear_upside_pct = ((bear_target_price - cmp) / cmp) * 100
    bear_annualized_cagr = _ann(bear_target_price)

    # Probability weighting across Bull / Bear. Without a calibrated weight, the bear weight is
    # the one that makes probability-weighted growth equal the growth anchor.
    if bear_prob is None:
        bear_prob = implied_bear_prob(base_net_growth, bull_net_growth, bear_net_growth)
    bear_prob = min(1.0, max(0.0, bear_prob))
    bull_prob = 1.0 - bear_prob
    expected_growth = bull_prob * bull_net_growth + bear_prob * bear_net_growth
    expected_eps_yr2 = bull_prob * eps_bull_yr2 + bear_prob * eps_bear_yr2
    fwd_pe_yr2_exp = cmp / expected_eps_yr2 if expected_eps_yr2 > 0 else float('inf')
    peg_ratio_yr2_exp = fwd_pe_yr2_exp / (expected_growth * 100) if expected_growth > 0 else float('inf')

    # Quality inputs come from the calibration; unknown values are NOT treated as good.
    roce_val = prof.get("roce")
    cfo_pat_val = prof.get("cfo_pat_ratio")
    debt_mcap_val = prof.get("debt_to_mcap")

    # Asymmetric Re-Rating Gate (GARP Spread): requires KNOWN quality evidence
    known_quality = ((roce_val is not None and roce_val >= 20.0)
                     or (cfo_pat_val is not None and cfo_pat_val >= 1.50)
                     or (debt_mcap_val is not None and debt_mcap_val <= 0.05 and roce_val is not None and roce_val >= 15.0))
    is_deep_value_compounder = (0 < current_pe <= 18.0 or fwd_pe_yr2_exp <= 18.0) and known_quality and not is_fragile
    growth_hurdle = 0.14 if is_deep_value_compounder else 0.20
    bull_upside_threshold = 50.0

    # Growth filter on probability-weighted growth (bull alone is too easy to clear)
    mid_growth = expected_growth
    passes_growth_filter = mid_growth >= growth_hurdle
    if margin_path:
        # Regime 3 upside comes from margins, not volume; require real revenue growth (the revenue
        # growth anchor) for a turnaround (>= 10%), none for a recovery. Value is tested below.
        growth_hurdle = 0.10 if margin_path == "turnaround" else 0.0
        passes_growth_filter = base_net_growth >= growth_hurdle
    passes_pe_filter = fwd_pe_yr2_exp <= 80.0
    passes_bull_upside_mandate = bull_upside_pct >= bull_upside_threshold

    fy_curr_str = f"FY{period['running_fy'] % 100}"
    fy_base_str = f"TTM to {ttm_end.strftime('%b %Y')}"
    fy_yr1_str = f"TTM to {target_dt_yr1.strftime('%b %Y')}"
    fy_yr2_str = f"TTM to {target_dt_yr2.strftime('%b %Y')}"

    # Default reasons if not provided
    if not bull_reason:
        bull_reason = f"Flawless execution, market share consolidation, and strong operational leverage (CAGR {bull_net_growth*100:.1f}%)"
    bear_reason = (prof.get("bear_reason") if prof else None) or f"Growth stalls and the multiple de-rates (CAGR {bear_net_growth*100:.1f}%)"
    if margin_path:
        bear_reason = bear_note or f"Margins do not improve from {prof['ttm_npm']*100:.1f}% and the multiple de-rates"

    print("================================================================================")
    print(f" HIGH-GROWTH & 2-YEAR FORWARD P/E ENGINE: {ticker.upper()}")
    print("================================================================================")
    print(f" Valuation Model:                    {regime_desc}")
    if sector_desc:
        print(f" Sector Runway & TAM Growth:         {sector_desc}")
    print(f" As-of Date:                         {as_of_dt.strftime('%Y-%m-%d')} ({period['quarter']} {fy_curr_str})")
    print(f" Target Horizons:                    1-Yr: {fy_yr1_str} ({comp_yr1:.2f} yrs comp) | 2-Yr: {fy_yr2_str} ({comp_yr2:.2f} yrs comp)")
    print(f" Current Market Price (CMP):         ₹{cmp:,.2f}")
    if mcap is not None:
        print(f" Latest Market Cap:                   ₹{mcap:,.1f} Cr")
    print(f" Current Base ({fy_base_str}) EPS:  ₹{current_eps:,.2f}")
    print(f" Current Trailing P/E:               {current_pe:.1f}x")
    if dilution_pct_annual > 0:
        print(f" Annual Equity Dilution (ESOP/QIP):  {dilution_pct_annual*100:.1f}%")
    print("--------------------------------------------------------------------------------")
    print(f" Growth Anchor (central estimate, not a scenario): {base_net_growth*100:.1f}% CAGR")
    print(f"   Probability-Weighted EPS Growth:  {expected_growth*100:.1f}% ({bull_prob*100:.0f}% Bull / {bear_prob*100:.0f}% Bear)")
    print(f"   Expected 2-Yr ({fy_yr2_str}) EPS: ₹{expected_eps_yr2:,.2f}  |  2-Yr Forward P/E: {fwd_pe_yr2_exp:.1f}x")
    print(f"   2-Yr Forward PEG Ratio:           {peg_ratio_yr2_exp:.2f}x")
    print("--------------------------------------------------------------------------------")
    print(f" Bull Case CAGR ({bull_reason}):")
    print(f"   Projected Net EPS CAGR:           {bull_net_growth*100:.1f}% CAGR")
    print(f"   Projected 2-Yr ({fy_yr2_str}) EPS: ₹{eps_bull_yr2:,.2f}  |  2-Yr Forward P/E: {fwd_pe_yr2_bull:.1f}x")
    print(f"   Expected End-Period Growth Rate:  {bull_exit_g*100:.1f}% -> Dynamic Bull Exit P/E: {bull_pe:.1f}x")
    print("--------------------------------------------------------------------------------")
    print(f" Bear Case CAGR ({bear_reason}):")
    print(f"   Projected Net EPS CAGR:           {bear_net_growth*100:.1f}% CAGR")
    print(f"   Projected 2-Yr ({fy_yr2_str}) EPS: ₹{eps_bear_yr2:,.2f}  |  Bear Exit P/E: {bear_pe:.1f}x")
    print("--------------------------------------------------------------------------------")

    print("\n>>> CRITERIA SCORECARD:")
    c1_mark = "✅ PASS" if passes_growth_filter else "❌ FAIL"
    c2_mark = "✅ PASS" if passes_pe_filter else "❌ FAIL"
    c3_mark = "✅ PASS" if passes_bull_upside_mandate else "❌ FAIL"
    hurdle_str = (f"{growth_hurdle*100:.1f}% (Regime 3 revenue growth)" if margin_path
                  else ("14.0% (Asymmetric Re-Rating Gate)" if is_deep_value_compounder else "20.0%"))
    g_label = "Revenue growth anchor" if margin_path else "Prob-weighted growth"
    g_shown = base_net_growth if margin_path else mid_growth
    print(f" 1. Growth Filter ({g_label}):  {c1_mark} ({g_shown*100:.1f}% vs {hurdle_str} threshold)")
    print(f" 2. 2-Year Forward P/E <= 80x Filter:      {c2_mark} ({fwd_pe_yr2_exp:.1f}x on expected EPS vs 80.0x threshold)")
    print(f" 3. Bull 2-Yr Upside >= 50% Filter:        {c3_mark} ({bull_upside_pct:+.1f}% at {bull_pe:.1f}x Bull exit)")

    print(f"\n--- 2-YEAR SCENARIO VALUATION MATRIX ({fy_yr2_str}) ---")
    header = f"{'Scenario':<12} | {'Horizon CAGR':<14} | {'End Growth':<12} | {'Exit P/E':<10} | {'Target Price (₹)':<18} | {'Total Return':<14} | {'Annualized CAGR':<16}"
    print(header)
    print("-" * len(header))
    print(f"{'Bear Case':<12} | {bear_net_growth*100:>10.1f}%   | {'-':>8}     | {bear_pe:>6.1f}x   | ₹{bear_target_price:>12.2f}    | {bear_upside_pct:>+10.1f}%   | {bear_annualized_cagr:>+12.1f}%")
    print(f"{'Bull Case':<12} | {bull_net_growth*100:>10.1f}%   | {bull_exit_g*100:>8.1f}%   | {bull_pe:>6.1f}x   | ₹{bull_target_price:>12.2f}    | {bull_upside_pct:>+10.1f}%   | {bull_annualized_cagr:>+12.1f}%")
    print("-" * len(header))

    prob_weighted_target = (bull_prob * bull_target_price) + (bear_prob * bear_target_price)
    prob_weighted_return = ((prob_weighted_target - cmp) / cmp) * 100
    prob_weighted_cagr = _ann(prob_weighted_target)

    # Verdict: every BUY must clear the required-return hurdle on the EXPECTED value
    # (bear case included), not just a bull-case upside.
    hurdle_pct = HURDLE_RATE * 100
    if not passes_growth_filter:
        verdict = f"REJECT / LOW-GROWTH TRAP (Projected growth {mid_growth*100:.1f}% below {growth_hurdle*100:.0f}% hurdle rate)"
    elif not passes_pe_filter:
        verdict = f"REJECT (2-year forward P/E {fwd_pe_yr2_exp:.1f}x on expected EPS exceeds 80x safety ceiling)"
    elif not passes_bull_upside_mandate:
        verdict = f"REJECT (Bull Upside {bull_upside_pct:+.1f}% fails mandated {bull_upside_threshold:.0f}% hurdle)"
    elif prob_weighted_cagr < hurdle_pct:
        verdict = f"REJECT (Expected CAGR {prob_weighted_cagr:+.1f}% p.a. below {hurdle_pct:.0f}% required return)"
    elif bear_upside_pct >= -30.0:
        verdict = f"STRONG HIGH-GROWTH BUY (Expected CAGR {prob_weighted_cagr:+.1f}% p.a., Bull {bull_upside_pct:+.1f}%, Bear {bear_upside_pct:+.1f}%)"
    else:
        verdict = f"QUALIFIED GROWTH BUY (Expected CAGR {prob_weighted_cagr:+.1f}% p.a., Bull {bull_upside_pct:+.1f}%, Bear {bear_upside_pct:+.1f}%: size for the drawdown)"

    cash_harvest_target = bull_target_price
    cash_harvest_upside = bull_upside_pct
    trailing_stop_loss = round(cmp * 0.85, 2)

    # Technical Stage 2 Gate. Missing price data is UNKNOWN, never "confirmed".
    is_high_quality = bool(prof.get("is_quality"))
    if dma200 is not None and dma200 > 0:
        if cmp > dma200 and (dma50 is None or dma50 > dma200):
            stage2_status = f"STAGE 2 CONFIRMED (Bullish Acceleration | CMP ₹{cmp:,.2f} > 200-DMA ₹{dma200:,.2f})"
        elif cmp > dma200 and dma50 <= dma200:
            stage2_status = f"STAGE 2 TRANSITION / RECOVERY (CMP ₹{cmp:,.2f} > 200-DMA ₹{dma200:,.2f})"
        elif is_high_quality and cmp >= dma200 * 0.87:
            stage2_status = f"STAGE 2 PULLBACK ACCUMULATION (Franchise Moat | CMP ₹{cmp:,.2f} within 13% of 200-DMA ₹{dma200:,.2f})"
        else:
            stage2_status = f"STAGE 4 CAUTION (Below 200-DMA ₹{dma200:,.2f} | High Drawdown Risk)"
    else:
        stage2_status = "TREND UNKNOWN (no 200-DMA data: technical gate not verified)"

    # Momentum gates: no BUY while PAT is contracting or the growth kill switch is already tripped.
    kill_switch_note = None
    from data_fetcher import clean_num
    q_sales_live = [clean_num(x) for x in (live_data or {}).get("q_data", {}).get("Sales", [])] if live_data else []
    if len(q_sales_live) >= 6 and q_sales_live[-5] > 0 and q_sales_live[-6] > 0:
        s_yoy0 = (q_sales_live[-1] / q_sales_live[-5] - 1.0) * 100.0
        s_yoy1 = (q_sales_live[-2] / q_sales_live[-6] - 1.0) * 100.0
        if s_yoy0 < KILL_SWITCH_SALES_YOY and s_yoy1 < KILL_SWITCH_SALES_YOY:
            kill_switch_note = (f"YoY sales {s_yoy1:+.1f}% / {s_yoy0:+.1f}% in the last 2 quarters, "
                                f"below the {KILL_SWITCH_SALES_YOY:.0f}% kill switch")
    if "BUY" in verdict:
        if str(ears_status).startswith("EARNINGS CONTRACTION"):
            verdict = f"WATCHLIST / EARNINGS CONTRACTION - WAIT FOR PAT GROWTH (fundamentals pass: {verdict})"
        elif kill_switch_note:
            verdict = f"WATCHLIST / GROWTH KILL SWITCH ACTIVE ({kill_switch_note}; fundamentals pass: {verdict})"
    # The trend gate now affects the verdict: no BUY into a Stage 4 downtrend.
    if "BUY" in verdict:
        if stage2_status.startswith("STAGE 4"):
            verdict = f"WATCHLIST / STAGE 4 - WAIT FOR TREND (fundamentals pass: {verdict})"
        elif stage2_status.startswith("TREND UNKNOWN"):
            verdict = f"{verdict} [TREND UNVERIFIED]"
        if any(x.startswith(("roce->", "cfo/pat")) for x in prof.get("sparse_fields", [])):
            verdict = f"{verdict} [SPARSE DATA: ROCE / cash conversion unverified]"
        if prof.get("guidance_status") in ("MISSING", "MARGIN ONLY"):
            verdict = f"{verdict} [NO REVENUE GUIDANCE: check the latest concall before acting]"
        elif prof.get("guidance_status") == "REVIEWED: NONE GIVEN":
            verdict = f"{verdict} [NO REVENUE GUIDANCE GIVEN: management did not quantify growth]"

    print("\n================================================================================")
    print(" VALUATION & EXPECTED TARGET PRICE SUMMARY (FROM LAST CLOSING PRICE)")
    print("================================================================================")
    print(f" Last Closing Price (CMP):            ₹{cmp:,.2f}")
    if mcap is not None:
        print(f" Latest Market Cap:                   ₹{mcap:,.1f} Cr")
    print(f" Target Time Horizon:                 {horizon_yrs:.0f}-Year Horizon (to {target_dt_yr2.strftime('%d %b %Y')})")
    print(f" Expected Target Price (Wtd Avg):     ₹{prob_weighted_target:,.2f}")
    print(f" Total Expected Return:               {prob_weighted_return:+.1f}% from CMP")
    print(f" Annualized Expected Return (CAGR):   {prob_weighted_cagr:+.1f}% p.a. (hurdle {hurdle_pct:.0f}%)")
    print(f" Dynamic Probability Allocation:      {bull_prob*100:.0f}% Bull / {bear_prob*100:.0f}% Bear")
    print(f" Technical Trend Gate (Stage 2):      {stage2_status}")
    print(f" Quarterly EARS Rating:               {ears_status}")
    print(f" Cash Harvesting Target (50% Trim):   ₹{cash_harvest_target:,.2f} ({cash_harvest_upside:+.1f}%)")
    print(f" Dynamic Trailing Stop-Loss:          ₹{trailing_stop_loss:,.2f} (-15.0% Capital Protection)")
    print(f" Final Conviction Verdict:            {verdict}")
    print("================================================================================")
    print("\n--- UNDERLYING SCENARIO TARGET BREAKDOWN & EXPLANATION ---")
    print(f" • Bear Case Target ({bear_prob*100:.0f}% Prob):   ₹{bear_target_price:,.2f} ({bear_upside_pct:+.1f}%) | Exit P/E: {bear_pe:.1f}x")
    print(f"   Rationale: {bear_reason}")
    print(f" • Bull Case Target ({bull_prob*100:.0f}% Prob):   ₹{bull_target_price:,.2f} ({bull_upside_pct:+.1f}%) | Exit P/E: {bull_pe:.1f}x on {bull_exit_g*100:.1f}% end-growth")
    print(f"   Rationale: {bull_reason}")
    print("================================================================================\n")

    return {
        "ticker": ticker.upper(),
        "cmp": cmp,
        "mcap": mcap,
        "no_valuation": False,
        "regime": f"Fixed {horizon_yrs:.0f}-Year Horizon",
        "regime_desc": regime_desc,
        "regime_model": regime_desc,
        "base_fy": fy_base_str,
        "target_yr1_fy": fy_yr1_str,
        "target_yr2_fy": fy_yr2_str,
        "comp_years_yr1": round(comp_yr1, 2),
        "comp_years_yr2": round(comp_yr2, 2),
        "horizon_years": horizon_yrs,
        "current_eps": round(current_eps, 2),
        "current_pe": round(current_pe, 1),
        "ttm_eps": round(current_eps, 2),
        "trailing_pe": round(current_pe, 1),
        "anchor_cagr": round(base_net_growth, 4),
        "expected_growth": round(expected_growth, 4),
        "bull_cagr": round(bull_net_growth, 4),
        "bear_cagr": round(bear_net_growth, 4),
        "bull_exit_pe": round(bull_pe, 1),
        "bear_exit_pe": round(bear_pe, 1),
        "bull_exit_growth": round(bull_exit_g, 4),
        "expected_eps_yr2": round(expected_eps_yr2, 2),
        "eps_bull_yr1": round(eps_bull_yr1, 2),
        "eps_bull_yr2": round(eps_bull_yr2, 2),
        "eps_bear_yr2": round(eps_bear_yr2, 2),
        "fwd_pe_expected": round(fwd_pe_yr2_exp, 1),
        "fwd_pe_bull": round(fwd_pe_yr2_bull, 1),
        "target_bull": round(bull_target_price, 2),
        "target_bear": round(bear_target_price, 2),
        "return_bull_pct": round(bull_upside_pct, 1),
        "return_bear_pct": round(bear_upside_pct, 1),
        "cagr_bull": round(bull_annualized_cagr, 1),
        "cagr_bear": round(bear_annualized_cagr, 1),
        "bull_prob": round(bull_prob * 100),
        "bear_prob": round(bear_prob * 100),
        "expected_target": round(prob_weighted_target, 2),
        "total_expected_return_pct": round(prob_weighted_return, 1),
        "expected_cagr": round(prob_weighted_cagr, 1),
        "hurdle_rate_pct": hurdle_pct,
        "pass_growth": passes_growth_filter,
        "pass_fwd_pe": passes_pe_filter,
        "pass_upside": passes_bull_upside_mandate,
        "verdict": verdict,
        "verdict_color": _verdict_color(verdict),
        "buy_low": round(prob_weighted_target / 1.25, 1),
        "buy_high": round(prob_weighted_target / 1.10, 1),
        "bull_reason": bull_reason,
        "bear_reason": bear_reason,
        "sector_growth": sector_growth,
        "sector_desc": sector_desc,
        "stage2_status": stage2_status,
        "ears_status": ears_status,
        "kill_switch_note": kill_switch_note,
        "guidance_status": prof.get("guidance_status"),
        "guided_rev_cagr": prof.get("guided_rev_cagr"),
        "cash_harvest_target": round(cash_harvest_target, 2),
        "cash_harvest_upside": round(cash_harvest_upside, 1),
        "trailing_stop_loss": trailing_stop_loss,
        "sparse_fields": prof.get("sparse_fields", []),
        "margin_path": margin_path,
        "ss_margin": prof.get("ss_margin"),
        "ss_margin_source": prof.get("ss_margin_source"),
        "normalized_pe": round(norm_pe, 1) if norm_pe else None,
        "guidance_reliability": prof.get("guidance_reliability"),
        "guidance_track_n": prof.get("guidance_track_n"),
        "guided_rev_cagr": prof.get("guided_rev_cagr"),
        "guidance_as_of": prof.get("guidance_as_of"),
    }


def _verdict_color(verdict: str) -> str:
    v = (verdict or "").upper()
    if "REJECT" in v or "DISQUALIFIED" in v or "NO VALUATION" in v:
        return "red"
    if "WATCHLIST" in v:
        return "orange"
    if "STRONG" in v:
        return "green"
    if "QUALIFIED" in v:
        return "blue"
    return "red"


def _is_lender(live_data, ticker) -> bool:
    """Banks / NBFCs / insurers: earnings are driven by leverage and credit costs, so a
    P/E-growth model is the wrong tool. Heuristic on company name and description."""
    name = str((live_data or {}).get("name") or ticker or "").lower()
    about = str((live_data or {}).get("about") or "").lower()
    sector = str((live_data or {}).get("sector") or "").lower()
    padded_name = f" {name} "
    name_hits = (" bank ", " bank,", "finance", "financial services", "fincorp", "finserv",
                 "insurance", "housing fin")
    about_hits = ("nbfc", "non-banking financial", "non banking financial", "small finance bank",
                  "scheduled commercial bank", "housing finance company", "life insurance company",
                  "general insurance company")
    sector_hits = ("bank", "nbfc", "finance", "insurance")
    return (any(h in padded_name for h in name_hits)
            or any(h in about for h in about_hits)
            or any(h in sector for h in sector_hits))


def _ttm_end_date(live_data, as_of_dt):
    """End date of the trailing-twelve-month window behind TTM EPS.
    Uses the last reported quarter header (e.g. 'Sep 2026'); otherwise assumes the
    latest quarter-end at least 45 days before the as-of date (typical results lag)."""
    try:
        q = (live_data or {}).get("last_4_quarters") or []
        if q:
            dt = datetime.strptime(str(q[-1]).strip(), "%b %Y")
            return pd.Timestamp(dt) + pd.offsets.MonthEnd(0)
    except Exception:
        pass
    ref = pd.Timestamp(as_of_dt) - pd.Timedelta(days=45)
    return pd.offsets.QuarterEnd(startingMonth=3).rollback(ref).normalize()


def _no_valuation_result(ticker, cmp, mcap, current_eps, verdict, ears_status=None):
    """Result for companies the model cannot value. No fabricated targets: targets equal
    CMP and returns are 0.0 with no_valuation=True (callers must not read them as a forecast)."""
    print(f"⚠️  [NO VALUATION] {ticker}: {verdict}")
    return {
        "ticker": (ticker or "").upper(),
        "cmp": cmp,
        "mcap": mcap,
        "no_valuation": True,
        "current_eps": round(current_eps, 2),
        "ttm_eps": round(current_eps, 2),
        "current_pe": round(cmp / current_eps, 1) if current_eps > 0 else 0.0,
        "trailing_pe": round(cmp / current_eps, 1) if current_eps > 0 else 0.0,
        "target_bull": cmp, "target_bear": cmp,
        "return_bull_pct": 0.0, "return_bear_pct": 0.0,
        "cagr_bull": 0.0, "cagr_bear": 0.0,
        "expected_target": cmp,
        "total_expected_return_pct": 0.0,
        "expected_cagr": 0.0,
        "bull_exit_pe": 0.0, "bear_exit_pe": 0.0,
        "fwd_pe_expected": 0.0, "fwd_pe_bull": 0.0,
        "expected_eps_yr2": 0.0, "eps_bull_yr2": 0.0, "eps_bear_yr2": 0.0,
        "anchor_cagr": 0.0, "expected_growth": 0.0, "bull_cagr": 0.0, "bear_cagr": 0.0,
        "bull_prob": 0, "bear_prob": 0,
        "bull_reason": "No valuation", "bear_reason": "No valuation",
        "stage2_status": "NOT EVALUATED",
        "ears_status": ears_status or "NOT EVALUATED",
        "cash_harvest_target": cmp,
        "cash_harvest_upside": 0.0,
        "trailing_stop_loss": round(cmp * 0.85, 2),
        "pass_growth": False, "pass_fwd_pe": False, "pass_upside": False,
        "verdict": verdict,
        "verdict_color": "red",
    }


def generate_summary_card(res: dict) -> str:
    """Generates the institutional top summary card string from a valuation result dict."""
    return f"""================================================================================
 VALUATION & EXPECTED TARGET PRICE SUMMARY (FROM LAST CLOSING PRICE)
================================================================================
 Last Closing Price (CMP):            ₹{res.get('cmp', 0.0):,.2f}
 Latest Market Cap:                   ₹{res.get('mcap', 0.0):,.1f} Cr
 Target Time Horizon:                 2-Year Horizon ({res.get('base_fy', 'TTM')} -> {res.get('target_yr2_fy', '+2Y')})
 Expected Target Price (Wtd Avg):     ₹{res.get('expected_target', 0.0):,.2f}
 Total Expected Return:               {res.get('total_expected_return_pct', 0.0):+.1f}% from CMP
 Annualized Expected Return (CAGR):   {res.get('expected_cagr', 0.0):+.1f}% p.a.
 Dynamic Probability Allocation:      {res.get('bull_prob', 0)}% Bull / {res.get('bear_prob', 0)}% Bear
 Bear Case Target:                    ₹{res.get('target_bear', 0.0):,.2f} ({res.get('return_bear_pct', 0.0):+.1f}%)
 Technical Trend Gate (Stage 2):      {res.get('stage2_status', 'TREND UNKNOWN')}
 Quarterly EARS Rating:               {res.get('ears_status', 'EARS UNKNOWN')}
 Cash Harvesting Target (50% Trim):   ₹{res.get('cash_harvest_target', res.get('target_bull', 0.0)):,.2f} ({res.get('cash_harvest_upside', res.get('return_bull_pct', 0.0)):+.1f}%)
 Dynamic Trailing Stop-Loss:          ₹{res.get('trailing_stop_loss', 0.0):,.2f} (-15.0% Capital Protection)
 Final Conviction Verdict:            {res.get('verdict', 'N/A')}
================================================================================"""


def prepare_valuation_params(
    data: dict,
    calibrated: dict,
    base_cagr_override: float = None,
    bull_cagr_override: float = None,
    base_exit_growth_override: float = None,
    bull_exit_growth_override: float = None,
    base_peg_override: float = None,
    bull_peg_override: float = None,
    bear_prob_override: float = None,
    regime_override: str = "Auto",
    as_of_date: datetime = None
) -> dict:
    """
    Canonical valuation parameter preparation shared identically across:
    - Master CLI (predict/scripts/run_cli.py)
    - Institutional Decision Engine (predict/scripts/decision.py)
    - Web Dashboard (stockhold/app.py)

    Guarantees parameter symmetry, eliminates falsy-zero traps on bear probability,
    and extracts technical indicators DMA200/DMA50 directly from chart history.
    """
    clean_ticker = (data.get("ticker") or data.get("registry_ticker") or "STOCK").upper().strip()

    # 1. Resolve bear probability cleanly without treating 0 as falsy
    if bear_prob_override is not None:
        bp = float(bear_prob_override)
    elif calibrated.get("bear_prob") is not None:
        bp = float(calibrated["bear_prob"]) / 100.0
    else:
        bp = 0.20
    if bp > 1.0:
        bp /= 100.0
    bear_prob = min(1.0, max(0.0, bp))
    bull_prob = 1.0 - bear_prob

    # 2. Extract technical indicators DMA200/DMA50 from chart history
    dma200 = None
    dma50 = None
    cdf = data.get("chart_df")
    if isinstance(cdf, pd.DataFrame) and not cdf.empty:
        if "DMA200" in cdf.columns and pd.notnull(cdf["DMA200"].iloc[-1]):
            dma200 = float(cdf["DMA200"].iloc[-1])
        if "DMA50" in cdf.columns and pd.notnull(cdf["DMA50"].iloc[-1]):
            dma50 = float(cdf["DMA50"].iloc[-1])

    # 3. Prime global cache to avoid redundant secondary network calls
    if clean_ticker:
        global _DATA_CACHE
        _DATA_CACHE[clean_ticker] = data

    # 4. Resolve growth and exit inputs with clean fallbacks
    base_cagr = base_cagr_override if base_cagr_override is not None else (calibrated.get("base_cagr", 20.0) / 100.0)
    bull_cagr = bull_cagr_override if bull_cagr_override is not None else (calibrated.get("bull_cagr", 25.0) / 100.0)
    base_exit_g = base_exit_growth_override if base_exit_growth_override is not None else (calibrated.get("base_exit_g", 16.0) / 100.0)
    bull_exit_g = bull_exit_growth_override if bull_exit_growth_override is not None else (calibrated.get("bull_exit_g", 20.0) / 100.0)
    base_peg = base_peg_override if base_peg_override is not None else float(calibrated.get("base_peg", 1.60))
    bull_peg = bull_peg_override if bull_peg_override is not None else float(calibrated.get("bull_peg", 1.85))

    return {
        "cmp": data["cmp"],
        "mcap_cr": data["mcap_cr"],
        "ttm_eps": data["ttm_eps"],
        "ttm_sales": data.get("ttm_sales", 0.0),
        "ttm_pat": data.get("ttm_pat", 0.0),
        "shares_cr": data.get("shares_cr", 0.0),
        "base_cagr": base_cagr,
        "bull_cagr": bull_cagr,
        "base_exit_growth": base_exit_g,
        "bull_exit_growth": bull_exit_g,
        "base_peg": base_peg,
        "bull_peg": bull_peg,
        "bear_prob": bear_prob,
        "bull_prob": bull_prob,
        "bear_cagr": (calibrated.get("bear_cagr") or 0.0) / 100.0,
        "base_reason": calibrated.get("base_reason"),
        "bull_reason": calibrated.get("bull_reason"),
        "dilution_pct_annual": calibrated.get("dilution", 0.0),
        "current_margin": calibrated.get("current_margin"),
        "target_margin_yr2": calibrated.get("target_margin_yr2"),
        "regime_override": regime_override,
        "ticker": clean_ticker,
        "dma200": dma200,
        "dma50": dma50,
        "as_of_date": as_of_date,
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
    base_exit_growth: float = None,
    bull_exit_growth: float = None,
    base_peg: float = 1.60,
    bull_peg: float = 1.85,
    bull_reason: str = None,
    dilution_pct_annual: float = 0.0,
    current_margin: float = None,
    target_margin_yr2: float = None,
    as_of_date: datetime = None,
    regime_override: str = "Auto",
    ticker: str = "STOCK",
    dma200: float = None,
    dma50: float = None,
    ears_status: str = None,
    normalized_margin: float = None,
    is_duopoly: bool = False,
    cyclical_normal: bool = False,
    **kwargs
) -> dict:
    """
    High-level forward growth & dynamic exit P/E valuation interface.
    Auto-detects Regime 1 (steady-state margin) vs Regime 2 (platform operating leverage),
    calibrates against known profiles and directives, and computes FY+1/FY+2 projections.
    """
    clean_tick = ticker.upper().replace(" ", "").replace("-", "")
    npm = (ttm_pat / ttm_sales) if (ttm_sales > 0 and ttm_pat > 0) else 0.10

    if regime_override == "Regime 2 (Platform)":
        is_platform = True
        detection_reason = "Manual Override: Forced to Regime 2 (Platform Operating Leverage)"
    elif regime_override == "Regime 1 (Steady-State)":
        is_platform = False
        detection_reason = "Manual Override: Forced to Regime 1 (Steady-State Margin Compounder)"
    else:
        # Regime 2 only when calibrate_first_principles found evidence (thin margin at scale,
        # >= 25% sales growth, low debt) and supplied a margin bridge; a thin margin alone is not enough.
        is_platform = current_margin is not None and target_margin_yr2 is not None

        if is_platform:
            detection_reason = (
                f"Auto-Detected: Regime 2 (Platform Operating Leverage). Net Profit Margin {npm*100:.2f}% at scale "
                f"(₹{ttm_sales:,.0f} Cr revenue) with >= 25% 3Y sales growth and low debt (calibration evidence)."
            )
        else:
            detection_reason = (
                f"Auto-Detected: Regime 1 (Steady-State Margin Compounder). Net Profit Margin of "
                f"{npm*100:.2f}%; valuation is driven by top-line volume compounding."
            )

    if is_platform:
        rev_cagr = base_cagr
        curr_m = current_margin if current_margin is not None else npm
        tgt_m = target_margin_yr2 if target_margin_yr2 is not None else max(npm, min(0.045, npm * 2.0))
        
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
            bull_reason=bull_reason,
            dilution_pct_annual=dilution_pct_annual,
            as_of_date=as_of_date,
            dma200=dma200,
            dma50=dma50,
            ears_status=ears_status,
            normalized_margin=normalized_margin,
            is_duopoly=is_duopoly,
            cyclical_normal=cyclical_normal,
            **kwargs
        )
    else:
        res = evaluate_forward_growth(
            ticker=ticker,
            cmp=cmp,
            mcap=mcap_cr,
            current_eps=ttm_eps,
            base_growth_override=base_cagr,
            bull_cagr=bull_cagr,
            base_exit_growth=base_exit_growth,
            bull_exit_growth=bull_exit_growth,
            base_peg=base_peg,
            bull_peg=bull_peg,
            bull_reason=bull_reason,
            dilution_pct_annual=dilution_pct_annual,
            as_of_date=as_of_date,
            dma200=dma200,
            dma50=dma50,
            ears_status=ears_status,
            normalized_margin=normalized_margin,
            is_duopoly=is_duopoly,
            cyclical_normal=cyclical_normal,
            **kwargs
        )

    res["detection_reason"] = detection_reason
    res["is_platform"] = is_platform
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2-Year Forward Growth & P/E Valuation Engine")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. DIXON, COFORGE, IXIGO)")
    parser.add_argument("--cmp", type=float, default=0.0, help="Current Market Price (₹). If omitted or 0, automatically fetched from Screener Consolidated.")
    parser.add_argument("--mcap", type=float, default=None, help="Latest Market Cap in ₹ Crores")
    parser.add_argument("--eps", type=float, default=0.0, help="Current Base/TTM EPS (₹)")
    parser.add_argument("--pe", type=float, default=0.0, help="Current Trailing P/E multiple")
    
    # Growth rates and rationale
    parser.add_argument("--growth", "--base-growth", dest="growth", type=float, default=None, help="Growth anchor (central estimate) 2-yr EPS CAGR (e.g. 0.15 for 15%%)")
    parser.add_argument("--bull-growth", type=float, default=None, help="Bull case 2-3 yr CAGR (e.g. 0.22 for 22%%)")
    parser.add_argument("--base-exit-growth", type=float, default=None, help="End-of-period growth on the growth anchor; sets the bear exit P/E (e.g. 0.15)")
    parser.add_argument("--bull-exit-growth", type=float, default=None, help="Expected ongoing growth rate at end of evaluation period for Bull Case (e.g. 0.22)")
    parser.add_argument("--base-peg", type=float, default=1.6, help="Justified PEG on the growth anchor; sets the bear exit P/E (default: 1.6)")
    parser.add_argument("--bull-peg", type=float, default=1.85, help="Justified PEG for Bull Case in Indian market (default: 1.85)")
    parser.add_argument("--bull-reason", type=str, default=None, help="Operational reason for Bull Case growth assumption")
    parser.add_argument("--bear-prob", type=float, default=None, help="Bear case probability (e.g. 0.30); bull = 1 - bear. Default: implied from the growth anchor")

    # Dilution and adjustments
    parser.add_argument("--dilution", type=float, default=0.0, help="Annual share dilution rate from QIP/ESOP (default: 0.0)")
    parser.add_argument("--margin-expansion", type=float, default=0.0, help="Annual net margin expansion/contraction (default: 0.0)")
    parser.add_argument("--haircut", type=float, default=1.0, help="Reliability haircut on guidance (1.0 = 100%%, 0.85 = 15%% haircut)")
    
    # Fiscal period overrides
    parser.add_argument("--date", type=str, default=None, help="As-of date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--half", type=str, choices=["H1", "H2", "h1", "h2"], default=None, help="Explicit H1 / H2 regime override")
    parser.add_argument("--fy", type=int, default=None, help="Explicit running financial year override (e.g. 27 or 2027)")
    
    # Manual multiple overrides (optional)
    parser.add_argument("--base-pe", type=float, default=None, help="Override the growth-anchor exit P/E (sets the bear exit P/E)")
    parser.add_argument("--bull-pe", type=float, default=None, help="Override Bull case exit P/E multiple")
    parser.add_argument("--hist-floor-pe", type=float, default=None, help="Historical trough/cyclical quality floor P/E")
    parser.add_argument("--peer-pe", type=float, default=None, help="Comparable peer group median P/E benchmark")
    parser.add_argument("--sector-growth", type=float, default=None, help="Industry / TAM annual growth rate (e.g. 0.20 for 20%%)")

    # Non-linear operating leverage & turnaround options
    parser.add_argument("--target-eps-yr2", type=float, default=None, help="Explicit Yr 2 consensus EPS in ₹ (for platform compounders)")
    parser.add_argument("--rev-cagr", type=float, default=None, help="Expected Revenue CAGR over horizon (e.g. 0.35 for 35%%)")
    parser.add_argument("--current-margin", type=float, default=None, help="Current Net Profit Margin (e.g. 0.0064 for 0.64%%)")
    parser.add_argument("--target-margin-yr2", type=float, default=None, help="Target Yr 2 Net Profit Margin (e.g. 0.03 for 3.0%%)")
    parser.add_argument("--normalized-margin", type=float, default=None, help="Benchmark NPM for turnaround/suppressed base bridge (e.g. 0.06 for 6%%)")

    # Technical Stage 2 & Cash Earning Overrides
    parser.add_argument("--dma200", type=float, default=None, help="200-Day Moving Average Price (₹)")
    parser.add_argument("--dma50", type=float, default=None, help="50-Day Moving Average Price (₹)")
    parser.add_argument("--ears-status", type=str, default=None, help="Quarterly EARS rating status override")

    # Refinements 1 & 2 Overrides
    parser.add_argument("--enable-module-2", action="store_true", default=False, help="Enable Module 2: SGR Capacity Cap, Size Decay, and 15% Debt/WC Drag Haircuts (pending discussion)")
    parser.add_argument("--enable-module-7", action="store_true", default=False, help="Enable Module 7: Regime 3 Margin Normalization for Turnarounds (pending discussion)")
    parser.add_argument("--duopoly", action="store_true", help="Flag company as Contracted Mega-Cap Cash Duopoly (Rule 14)")
    parser.add_argument("--cyclical-normal", action="store_true", help="Stress-test cyclical peak margin against 5-yr median OPM (Rule 15)")

    args = parser.parse_args()
    evaluate_forward_growth(
        ticker=args.ticker,
        cmp=args.cmp,
        mcap=args.mcap,
        current_eps=args.eps,
        current_pe=args.pe,
        guided_cagr=args.growth,
        bull_cagr=args.bull_growth,
        base_exit_growth=args.base_exit_growth,
        bull_exit_growth=args.bull_exit_growth,
        base_peg=args.base_peg,
        bull_peg=args.bull_peg,
        bull_reason=args.bull_reason,
        bear_prob=args.bear_prob,
        dilution_pct_annual=args.dilution,
        margin_expansion_pct_annual=args.margin_expansion,
        historical_guidance_reliability=args.haircut,
        target_eps_yr2=args.target_eps_yr2,
        rev_cagr=args.rev_cagr,
        current_margin=args.current_margin,
        target_margin_yr2=args.target_margin_yr2,
        as_of_date=args.date,
        half_override=args.half,
        fy_override=args.fy,
        base_pe=args.base_pe,
        bull_pe=args.bull_pe,
        hist_floor_pe=args.hist_floor_pe,
        peer_pe=args.peer_pe,
        sector_growth=args.sector_growth,
        dma200=args.dma200,
        dma50=args.dma50,
        ears_status=args.ears_status,
        normalized_margin=args.normalized_margin,
        is_duopoly=args.duopoly,
        cyclical_normal=args.cyclical_normal
    )

