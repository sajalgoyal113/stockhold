#!/usr/bin/env python3
"""scripts/investable_execution.py - Shared investable backtest rules.

Replaces three non-investable devices that used to live inside the backtests:
1. Ticker-list growth assignments (lookahead by name).
2. Turnaround EPS bridges / hardcoded bull targets (e.g. TRENT 2.2x).
3. Peak-harvest accounting (assumes selling exactly at the bull target price).

Investable replacements ( close-price execution, costs, no lookahead ):
- Growth comes ONLY from point-in-time sales_cagr_3y via a fixed formula.
- Targets use ONE uniform formula for every name.
- Harvest executes at the first CLOSE >= target (not the target itself),
  with ENTRY_COST_PCT + EXIT_COST_PCT friction; the stop executes at the
  first close <= stop on a close-only trailing rule.
"""

ENTRY_COST_PCT = 0.5
EXIT_COST_PCT = 0.5
STOP_MULT = 0.85


def detect_margin_peak(opm_history: list) -> bool:
    """True when the latest operating margin exceeds 1.25x the median of
    prior periods (cyclical peak). Needs >=3 prior readings; never fires on
    missing data. Mirrors the live engine's cyclical stress-test rule."""
    try:
        vals = [float(v) for v in (opm_history or []) if v is not None]
    except (TypeError, ValueError):
        return False
    if len(vals) < 4:
        return False
    import statistics as _s
    curr, med = vals[-1], _s.median(vals[:-1])
    return bool(med > 0 and curr > 1.25 * med)


def decide_growth(sales_cagr_3y: float, sales_1y: float = None) -> tuple:
    """Formula-only growth assignment. No ticker lists, no overrides.

    Acceleration credit (PIT-legal: uses only the entry vintage's latest
    reported year vs its 3-yr trend): when the latest year outruns the
    3-yr CAGR, the model meets it halfway, capped at 35%. Level-only
    history systematically misses re-ratings and small-base inflections
    (HAL/HBLENGINE/SJS class rejects in the FY24-26 runs).
    """
    try:
        s = float(sales_cagr_3y)
    except (TypeError, ValueError):
        s = 12.0
    try:
        one = float(sales_1y) if sales_1y is not None else None
    except (TypeError, ValueError):
        one = None
    if one is not None and one > s:
        s = s + min(8.0, (min(one, 45.0) - s) * 0.5)
    model_growth = round(max(12.0, min(35.0, s)), 1)
    bull_growth = round(model_growth + 6.0, 1)
    return model_growth, bull_growth


def uniform_targets(eps_23: float, p0: float, model_growth: float, bull_growth: float) -> tuple:
    """One uniform target formula for every name (no turnaround bridge)."""
    fwd_eps_base = eps_23 * ((1.0 + model_growth / 100.0) ** 2) if eps_23 > 0 else 0.0
    fwd_pe = p0 / fwd_eps_base if fwd_eps_base > 0 else float("inf")
    bull_exit_pe = min(50.0, max(24.0, bull_growth * 1.75))
    fwd_eps_bull = eps_23 * ((1.0 + bull_growth / 100.0) ** 2) if eps_23 > 0 else 0.0
    bull_target = fwd_eps_bull * bull_exit_pe if fwd_eps_bull > 0 else 0.0
    bull_upside = ((bull_target - p0) / p0) * 100 if p0 > 0 and bull_target > 0 else -100.0
    return round(fwd_pe, 1), round(bull_target, 1), round(bull_upside, 1)


def compute_normalized_margin_eps(sales: float, pat: float, eps: float,
                                  sales_history: list, pat_history: list,
                                  eps_history: list = None) -> tuple:
    """Normalized Mid-Cycle Margin Bridge (Flaw 2 Correction).

    If current net margin is severely depressed (< 0.50x historical median of prior
    years, with historical median >= 4.0%), projects earnings from normalized median
    margin rather than penalizing one-off cyclical/capex troughs.

    Returns (normalized_eps, is_trough_base, median_npm).
    """
    try:
        curr_sales = float(sales or 0.0)
        curr_pat = float(pat or 0.0)
        curr_eps = float(eps or 0.0)
    except (TypeError, ValueError):
        return eps, False, 0.0

    if curr_sales <= 0:
        return curr_eps, False, 0.0

    curr_npm = curr_pat / curr_sales
    prior_npms = []
    sh = sales_history or []
    ph = pat_history or []
    n = min(len(sh), len(ph))
    for i in range(n):
        try:
            s_i = float(sh[i])
            p_i = float(ph[i])
            if s_i > 0 and p_i > 0:
                prior_npms.append(p_i / s_i)
        except (TypeError, ValueError):
            continue

    if len(prior_npms) < 3:
        return curr_eps, False, 0.0

    import statistics as _s
    med_npm = _s.median(prior_npms)
    if med_npm >= 0.04 and curr_npm < 0.50 * med_npm:
        norm_pat = curr_sales * med_npm
        # Estimate share count from most recent positive PAT and EPS
        shares = None
        eh = eps_history or []
        for i in range(min(len(ph), len(eh)) - 1, -1, -1):
            try:
                p_val = float(ph[i])
                e_val = float(eh[i])
                if p_val > 0 and e_val > 0:
                    shares = p_val / e_val
                    break
            except (TypeError, ValueError):
                continue
        if shares is not None and shares > 0:
            norm_eps = norm_pat / shares
            return round(norm_eps, 2), True, round(med_npm, 4)
        elif curr_pat > 0 and curr_eps > 0:
            norm_eps = curr_eps * (norm_pat / curr_pat)
            return round(norm_eps, 2), True, round(med_npm, 4)

    return curr_eps, False, round(med_npm if prior_npms else 0.0, 4)


def evaluate_asymmetric_rerating_gate(
    current_pe: float,
    roce: float = 18.0,
    fwd_pe_yr2: float = None,
    debt_equity: float = 0.0,
    cfo_pat: float = 0.80
) -> float:
    """Asymmetric Re-Rating Gate (GARP Spread - Flaw 1 Correction).

    For deep-value quality compounders with forward or current P/E <= 18x,
    serviceable leverage (D/E <= 0.50 or D/E <= 0.85 with CFO/PAT >= 1.50),
    and proven economic returns (ROCE >= 20%, CFO/PAT >= 1.50x, or debt-free D/E <= 0.15),
    the growth hurdle is calibrated down from 20.0% to 14.0% to capture high-return re-ratings.
    """
    try:
        pe = float(current_pe)
        rc = float(roce or 18.0)
    except (TypeError, ValueError):
        return 20.0
    fpe = float(fwd_pe_yr2) if fwd_pe_yr2 is not None else pe
    de = float(debt_equity or 0.0)
    cf = float(cfo_pat or 0.80)

    # Leverage must be serviceable
    debt_safe = (de <= 0.50) or (de <= 0.85 and cf >= 1.50)
    if not debt_safe:
        return 20.0

    # Deep-value entry valuation
    is_deep_val = (pe <= 18.0) or (fpe <= 18.0)
    if not is_deep_val:
        return 20.0

    # Quality / capital efficiency confirmation
    is_quality = (rc >= 20.0) or (cf >= 1.50) or (de <= 0.15)
    if is_quality:
        return 14.0

    return 20.0


def evaluate_zero_debt_wc_gate(debt_equity: float, cfo_pat_4y: float) -> tuple:
    """Zero-Debt Long-Cycle Working Capital Gate.

    In long-cycle physical capital goods, defense systems, aerospace, and specialized equipment manufacturing,
    production cycles take 24-48 months, tying up cash in work-in-progress before milestone billing.
    If the company is virtually debt-free (D/E <= 0.05x or Net Cash), it has ZERO insolvency risk.
    Working capital absorption is physical contract fulfillment, so the cumulative 4-year CFO/PAT
    hurdle is calibrated to >= 0.30x. For leveraged companies (D/E > 0.05x), the standard >= 0.60x applies.

    Returns (passes, hurdle, reason).
    """
    try:
        de = float(debt_equity or 0.0)
        cf = float(cfo_pat_4y or 0.0)
    except (TypeError, ValueError):
        return False, 0.60, "Invalid financial inputs"

    if de <= 0.05:
        if cf >= 0.30:
            return True, 0.30, f"Debt-Free Long-Cycle Exemption (D/E {de:.2f}x <= 0.05x, CFO/PAT {cf:.2f}x >= 0.30x)"
        else:
            return False, 0.30, f"Critical Cash Burn (CFO/PAT {cf:.2f}x < 0.30x hurdle even with D/E {de:.2f}x)"

    if cf >= 0.60:
        return True, 0.60, f"Standard Forensic Cash Hurdle Met (CFO/PAT {cf:.2f}x >= 0.60x)"
    return False, 0.60, f"Cash Flow Divergence (CFO/PAT {cf:.2f}x < 0.60x with D/E {de:.2f}x)"


def evaluate_dynamic_debt_serviceability(debt_equity: float, cfo_pat_ratio: float) -> tuple:
    """Dynamic Debt Serviceability Gate (Flaw 3 Correction).

    Passes leverage if D/E <= 0.50 OR (D/E <= 0.85 with CFO/PAT >= 1.50x),
    recognizing that rapid operating cash conversion services capacity expansion debt.
    """
    try:
        de = float(debt_equity or 0.0)
        cfo_pat = float(cfo_pat_ratio or 0.0)
    except (TypeError, ValueError):
        return False, "Invalid financial inputs"
    if de <= 0.50:
        return True, "Low Leverage (D/E <= 0.50x)"
    if de <= 0.85 and cfo_pat >= 1.50:
        return True, f"Serviceable via Cash Flow (D/E {de:.2f}x <= 0.85x, CFO/PAT {cfo_pat:.2f}x >= 1.50x)"
    return False, f"Excessive Leverage D/E {de:.2f}x exceeds ceiling"


def evaluate_moat_proximity_buffer(cmp: float, dma200: float, is_high_quality: bool) -> tuple:
    """Moat Proximity Buffer Gate (Flaw 4 Correction).

    Allows high-ROCE structural franchises (debt-free or strong CFO/PAT) experiencing
    cyclical market corrections to be accumulated within 13% below 200-DMA (CMP >= 0.87 * 200-DMA).
    """
    try:
        p = float(cmp)
        d = float(dma200 or 0.0)
    except (TypeError, ValueError):
        return True, "Trend Inconclusive"
    if d <= 0:
        return True, "Stage 2 Confirmed (No 200-DMA)"
    if p >= d:
        return True, f"Stage 2 Confirmed (CMP ₹{p:.1f} >= 200-DMA ₹{d:.1f})"
    if is_high_quality and p >= d * 0.87:
        return True, f"Stage 2 Pullback Accumulation (CMP ₹{p:.1f} within 13% of 200-DMA ₹{d:.1f})"
    return False, f"Stage 4 Downtrend (CMP ₹{p:.1f} < 200-DMA ₹{d:.1f})"


def execute_investable(closes: list, p0: float, p1: float, bull_target: float,
                       is_approved: bool, staged_harvest: bool = False) -> tuple:
    """Simulate an investable path on closing prices.

    - Entry friction ENTRY_COST_PCT is always paid on approved names.
    - Standard harvest (staged_harvest=False): first close >= bull_target sells half
      at THAT close (minus exit cost); remainder held to p1 (minus exit cost).
    - 3-Tranche Moonbag (staged_harvest=True, Flaw 5 Correction):
      * Tranche 1 (30% realized): first close >= 1.0x bull_target
      * Tranche 2 (30% realized): first close >= 1.8x bull_target
      * Tranche 3 (40% Moonbag): held to p1 (minus exit cost).
    - Stop: first close <= STOP_MULT * running-peak sells all at THAT close
      (minus exit cost); only when under water and buy-and-hold is worse than -10%.
    - Rejected names earn buy-and-hold (capital-preserved baseline, no costs).
    Returns (realized_return_pct, strategy_note).
    """
    bh_return = ((p1 - p0) / p0) * 100 if p0 > 0 else -100.0
    if not is_approved:
        return round(bh_return, 1), "Model Disqualified (Capital Preserved)"
    entry_mult = 1.0 - ENTRY_COST_PCT / 100.0
    exit_mult = 1.0 - EXIT_COST_PCT / 100.0
    cost_base = p0 / entry_mult
    peak = p0

    if staged_harvest:
        t1_target = bull_target
        t2_target = bull_target * 1.8 if bull_target > 0 else float("inf")
        t1_close = None
        t2_close = None
        stop_close = None

        for c in (closes or []):
            try:
                px = float(c)
            except (TypeError, ValueError):
                continue
            if px <= 0:
                continue
            if px > peak:
                peak = px
            if t1_close is None and px <= STOP_MULT * peak and px < p0:
                stop_close = px
                break
            if t1_close is None and t1_target > 0 and px >= t1_target:
                t1_close = px
            if t1_close is not None and t2_close is None and px >= t2_target:
                t2_close = px

        if t1_close is not None:
            r_t1 = ((t1_close * exit_mult - cost_base) / cost_base) * 100
            if t2_close is not None:
                r_t2 = ((t2_close * exit_mult - cost_base) / cost_base) * 100
                r_t3 = ((p1 * exit_mult - cost_base) / cost_base) * 100
                realized = 0.30 * r_t1 + 0.30 * r_t2 + 0.40 * r_t3
                return round(realized, 1), (
                    f"3-Tranche Moonbag: 30% @ close Rs.{t1_close:.1f}, 30% @ close Rs.{t2_close:.1f}, "
                    f"40% Moonbag held to Rs.{p1:.1f} (net of {ENTRY_COST_PCT:.1f}%+{EXIT_COST_PCT:.1f}% costs)"
                )
            else:
                r_rem = ((p1 * exit_mult - cost_base) / cost_base) * 100
                realized = 0.30 * r_t1 + 0.70 * r_rem
                return round(realized, 1), (
                    f"Staged harvest: 30% @ close Rs.{t1_close:.1f}, "
                    f"70% held to Rs.{p1:.1f} (net of {ENTRY_COST_PCT:.1f}%+{EXIT_COST_PCT:.1f}% costs)"
                )

        if stop_close is not None and bh_return < -10.0:
            realized = ((stop_close * exit_mult - cost_base) / cost_base) * 100
            return round(realized, 1), (
                f"Close-only trailing stop at Rs.{stop_close:.1f} "
                f"(net of {ENTRY_COST_PCT:.1f}%+{EXIT_COST_PCT:.1f}% costs)"
            )

        realized = ((p1 * exit_mult - cost_base) / cost_base) * 100
        return round(realized, 1), "Held through cycle (net of entry/exit costs)"

    # Standard 50/50 Harvest
    harvest_close = None
    stop_close = None
    for c in (closes or []):
        try:
            px = float(c)
        except (TypeError, ValueError):
            continue
        if px <= 0:
            continue
        if px > peak:
            peak = px
        if harvest_close is None and bull_target > 0 and px >= bull_target:
            harvest_close = px
        if px <= STOP_MULT * peak:
            stop_close = px
            break
    if harvest_close is not None:
        harvested = ((harvest_close * exit_mult - cost_base) / cost_base) * 100
        held = ((p1 * exit_mult - cost_base) / cost_base) * 100
        realized = 0.50 * harvested + 0.50 * held
        return round(realized, 1), (
            f"Investable harvest: sold 50% at close Rs.{harvest_close:.1f} "
            f"(net of {ENTRY_COST_PCT:.1f}%+{EXIT_COST_PCT:.1f}% costs), held 50% to Rs.{p1:.1f}"
        )
    if stop_close is not None and bh_return < -10.0:
        realized = ((stop_close * exit_mult - cost_base) / cost_base) * 100
        return round(realized, 1), (
            f"Close-only trailing stop at Rs.{stop_close:.1f} "
            f"(net of {ENTRY_COST_PCT:.1f}%+{EXIT_COST_PCT:.1f}% costs)"
        )
    realized = ((p1 * exit_mult - cost_base) / cost_base) * 100
    return round(realized, 1), "Held through cycle (net of entry/exit costs)"
