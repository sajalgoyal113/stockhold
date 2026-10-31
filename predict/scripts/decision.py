"""core/decision.py - Single-stock buy-or-not decision brief.

Answers "should I buy TICKER?" deterministically: live fundamentals +
calibrated valuation + forensics + reverse-DCF + safety guard, anchored
with historical base rates from scripts/pit_calibration.json.

Deliberately NOT an AI chat: every number is computed, the guard checks
internal consistency, and forensic / reverse-DCF red flags can only make
the decision more cautious. The base-rate box is context, not validation:
the historical backtests were hand-picked samples with a hindsight stop-loss
(since fixed), and in them rejected names often outperformed approved ones.
"""

import os
import sys
import json
from typing import Dict, Any, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)

try:
    from forward_growth_pe import calculate_forward_pe_valuation, calibrate_stock_parameters, prepare_valuation_params, KILL_SWITCH_SALES_YOY
except ImportError:
    try:
        from valuation import calculate_forward_pe_valuation, calibrate_stock_parameters, prepare_valuation_params, KILL_SWITCH_SALES_YOY
    except ImportError:
        try:
            from engine.valuation import calculate_forward_pe_valuation, calibrate_stock_parameters, prepare_valuation_params, KILL_SWITCH_SALES_YOY
        except ImportError:
            from stockhold.engine.valuation import calculate_forward_pe_valuation, calibrate_stock_parameters, prepare_valuation_params, KILL_SWITCH_SALES_YOY

try:
    from forensic_audit import run_forensic_audit, forensic_inputs_from_data
except ImportError:
    try:
        from forensics import run_forensic_audit, forensic_inputs_from_data
    except ImportError:
        try:
            from engine.forensics import run_forensic_audit, forensic_inputs_from_data
        except ImportError:
            from stockhold.engine.forensics import run_forensic_audit, forensic_inputs_from_data

try:
    from data_fetcher import fetch_company_data
except ImportError:
    try:
        from engine.data_fetcher import fetch_company_data
    except ImportError:
        from stockhold.engine.data_fetcher import fetch_company_data

try:
    from reverse_dcf import run_reverse_dcf
except ImportError:
    try:
        from engine.reverse_dcf import run_reverse_dcf
    except ImportError:
        from stockhold.engine.reverse_dcf import run_reverse_dcf

try:
    from safety_guard import FinancialSafetyGuard
except ImportError:
    try:
        from engine.safety_guard import FinancialSafetyGuard
    except ImportError:
        from stockhold.engine.safety_guard import FinancialSafetyGuard

_CANDIDATE_CALIBRATION_PATHS = [
    os.path.join(_SCRIPT_DIR, "pit_calibration.json"),
    os.path.join(_REPO_ROOT, "scripts", "pit_calibration.json"),
    os.path.join(_REPO_ROOT, "predict", "scripts", "pit_calibration.json"),
    os.path.join(os.path.dirname(_REPO_ROOT), "predict", "scripts", "pit_calibration.json"),
    os.path.join(_REPO_ROOT, "data", "pit_calibration.json"),
]
CALIBRATION_PATH = next((p for p in _CANDIDATE_CALIBRATION_PATHS if os.path.isfile(p)), _CANDIDATE_CALIBRATION_PATHS[0])

UPSIDE_BINS = [(None, 75.0), (75.0, 125.0), (125.0, 200.0), (200.0, None)]


def load_base_rates(path: str = CALIBRATION_PATH) -> Dict[str, Any]:
    """Historical cohorts from frozen PIT packs and Smallcap 250 audits.
    Returns {} when absent — the brief then says base rates are unavailable instead of inventing."""
    recs = []
    try:
        cal = json.load(open(path))
        recs.extend(cal.get("records", []))
    except (OSError, ValueError):
        pass

    # Load Smallcap 250 backtest records (Flaw 1-5 corrected engine)
    _candidate_data_dirs = [
        os.path.join(os.path.dirname(_SCRIPT_DIR), "data"),
        os.path.join(_REPO_ROOT, "data"),
        os.path.join(_REPO_ROOT, "predict", "data"),
        os.path.join(os.path.dirname(_REPO_ROOT), "predict", "data"),
    ]
    data_dir = next((d for d in _candidate_data_dirs if os.path.isdir(d)), _candidate_data_dirs[0])
    smallcap_recs = []
    for fn, w in [("backtest_smallcap250_results.json", "SMALLCAP_SET1"), ("backtest_smallcap250_set2_results.json", "SMALLCAP_SET2")]:
        fp = os.path.join(data_dir, fn)
        if os.path.isfile(fp):
            try:
                sd = json.load(open(fp))
                for r in sd.get("records", []):
                    is_app = bool(r.get("is_approved"))
                    ret = float((r.get("strategy_return") if is_app else r.get("bh_return")) or 0.0)
                    smallcap_recs.append({
                        "ticker": r["ticker"],
                        "window": w,
                        "p0": r["p0"],
                        "p1": r["p1"],
                        "sales_3y": r.get("sales_cagr_3y", 0.0),
                        "sales_1y": r.get("sales_1y", 0.0),
                        "predicted_bull_upside": r.get("bull_upside_pct", 0.0),
                        "is_approved": is_app,
                        "realized_return": ret,
                        "hit_positive": ret > 0,
                        "strategy_note": r.get("strategy_note", "")
                    })
            except Exception:
                pass

    all_recs = recs + smallcap_recs
    if not all_recs:
        return {}
    appr = [r for r in all_recs if r.get("is_approved")]
    rej = [r for r in all_recs if not r.get("is_approved")]
    sc_appr = [r for r in smallcap_recs if r.get("is_approved")]
    sc_rej = [r for r in smallcap_recs if not r.get("is_approved")]

    return {
        "records": all_recs,
        "approved": appr,
        "rejected": rej,
        "n_windows": len(all_recs),
        "smallcap_approved": sc_appr,
        "smallcap_rejected": sc_rej
    }


def _cohort(recs: list) -> Dict[str, Any]:
    n = len(recs)
    if not n:
        return {"n": 0, "hit_rate": None, "mean": None}
    mean = sum(r["realized_return"] for r in recs) / n
    hit = sum(1 for r in recs if r["realized_return"] > 0) / n * 100
    return {"n": n, "hit_rate": round(hit, 1), "mean": round(mean, 1)}


def decision_from_verdict(verdict: str) -> str:
    v = (verdict or "").upper()
    if "NO VALUATION" in v or "INSUFFICIENT DATA" in v or "NOT APPLICABLE" in v:
        return "NO CALL"
    if "REJECT" in v or "DISQUALIFIED" in v or "AVOID" in v:
        return "AVOID"
    if "WATCHLIST" in v:
        return "WAIT"
    if "STRONG" in v:
        return "BUY"
    return "ACCUMULATE ON DIPS"


def forensic_overrides(decision: str, forensic_res: dict, dcf_res: dict, val_res: dict):
    """Forensics and reverse-DCF can only make a decision MORE cautious.
    Returns (decision, list_of_reasons)."""
    reasons = []
    if decision not in ("BUY", "ACCUMULATE ON DIPS"):
        return decision, reasons
    cfo_pat = forensic_res.get("cum_cfo_pat_ratio")
    if cfo_pat is not None and cfo_pat < 0.50:
        reasons.append(f"4Y CFO/PAT {cfo_pat}x < 0.50x (profits not converting to cash)")
    if (forensic_res.get("de_ratio") or 0.0) > 1.0:
        reasons.append(f"Debt/Equity {forensic_res.get('de_ratio')}x > 1.0x")
    az = forensic_res.get("altman_z")
    if az is not None and az < 1.10:
        reasons.append(f"Altman Z'' {az} in distress zone")
    if reasons:
        return "AVOID", reasons
    implied = dcf_res.get("implied_cagr")
    bull_g = val_res.get("bull_cagr")
    if implied is not None and bull_g is not None and implied > bull_g * 100:
        reasons.append(f"Reverse-DCF: price implies {implied}% 10Y FCF CAGR, above the bull-case "
                       f"{bull_g*100:.1f}% EPS CAGR (market already prices more than our bull case)")
        return ("ACCUMULATE ON DIPS" if decision == "BUY" else "WAIT"), reasons
    return decision, reasons


def build_brief_from_parts(data: dict, calibrated: dict, val_res: dict,
                           forensic_res: dict, dcf_res: dict,
                           base_rates: dict) -> Dict[str, Any]:
    """Pure brief builder (no I/O): all inputs passed in, unit-testable."""
    ticker = data.get("ticker", "?")
    cmp = float(data.get("cmp", 0.0) or 0.0)
    verdict = val_res.get("verdict", "")
    decision, override_reasons = forensic_overrides(
        decision_from_verdict(verdict), forensic_res, dcf_res, val_res)

    canonical = (f"Bear target Rs.{val_res.get('target_bear')} Bull target "
                 f"Rs.{val_res.get('target_bull')} TTM EPS Rs.{val_res.get('ttm_eps')}. "
                 f"{val_res.get('stage2_status', '')}")
    guard = FinancialSafetyGuard.audit_synthesis(val_res, canonical)

    appr = _cohort(base_rates.get("approved", []))
    rej = _cohort(base_rates.get("rejected", []))
    bull_up = float(val_res.get("return_bull_pct") or 0.0)
    bin_cohort = {"n": 0, "hit_rate": None, "mean": None}
    for lo, hi in UPSIDE_BINS:
        in_bin = [r for r in base_rates.get("approved", [])
                  if (lo is None or r["predicted_bull_upside"] >= lo)
                  and (hi is None or r["predicted_bull_upside"] < hi)]
        if (lo is None or bull_up >= lo) and (hi is None or bull_up < hi):
            bin_cohort = _cohort(in_bin)
            break

    stop = val_res.get("trailing_stop_loss") or round(cmp * 0.85, 1)
    debtor = forensic_res.get("debtor_days")
    kill_switches = [
        f"Price: exit if it closes below Rs.{stop} (trailing stop).",
        f"Growth: exit if YoY sales growth prints below {KILL_SWITCH_SALES_YOY:.0f}% for two straight quarters.",
        (f"Working capital: exit if debtor days expand 25+ days above today's {debtor}d."
         if debtor else "Working capital: exit on debtor-day expansion without cash conversion."),
    ]
    caveats = []
    if calibrated.get("guided_rev_cagr") is not None:
        caveats.append(f"GUIDANCE: management guides {calibrated['guided_rev_cagr']:.1f}% revenue growth "
                       f"(as of {calibrated.get('guidance_as_of')}); delivery reliability "
                       f"{calibrated.get('guidance_reliability', 0):.2f} from {calibrated.get('guidance_track_n', 0)} scored promise(s).")
    elif calibrated.get("guidance_status") == "REVIEWED: NONE GIVEN":
        caveats.append("NO REVENUE GUIDANCE GIVEN: concalls were reviewed and management did not quantify growth; "
                       "targets rest on reported numbers only.")
    elif calibrated.get("guidance_status") in ("MISSING", "MARGIN ONLY"):
        caveats.append(f"NO REVENUE GUIDANCE ({calibrated.get('guidance_status')}): growth targets rest on reported numbers only. "
                       "Read the latest concall and register guidance before acting.")
    if val_res.get("kill_switch_note"):
        caveats.append(f"KILL SWITCH ALREADY TRIPPED: {val_res['kill_switch_note']}.")
    if calibrated.get("decelerating") or calibrated.get("margin_compressing"):
        caveats.append("MOMENTUM: " + ", ".join(x for x, on in (("sales decelerating vs 3Y CAGR", calibrated.get("decelerating")),
                                                               ("margins compressing", calibrated.get("margin_compressing"))) if on)
                       + " (growth anchor haircut, bear weight raised).")
    if calibrated.get("margin_path"):
        caveats.append(f"REGIME 3 {str(calibrated['margin_path']).upper()}: valued on margin normalization to "
                       f"{(calibrated.get('ss_margin') or 0)*100:.1f}% ({calibrated.get('ss_margin_source')}); "
                       f"evidence: {calibrated.get('margin_evidence')}.")
    elif calibrated.get("depressed_no_evidence"):
        caveats.append("DEPRESSED MARGINS without recovery evidence: valued on current earnings (no normalization credit).")
    if calibrated.get("sparse_anchor"):
        caveats.append("SPARSE INPUTS: " + "; ".join(calibrated.get("sparse_fields", [])))
    for r in override_reasons:
        caveats.append("DECISION OVERRIDE: " + r)
    if forensic_res.get("altman_z") is None:
        caveats.append("Altman UNAVAILABLE: solvency not scored (treated as neutral, neither safe nor fragile).")
    caveats.append("BASE RATES: historical cohorts come from hand-picked samples and a 2023-26 bull market; "
                   "they are not evidence the model beats the index.")
    if not guard.get("passes_guard"):
        caveats.append("GUARD FLAG: " + "; ".join(guard.get("violations", [])))
    upside = float(val_res.get("total_expected_return_pct") or 0.0)
    rationale_bits = [
        f"Bear Rs.{val_res.get('target_bear')} ({val_res.get('return_bear_pct')}%) / "
        f"Bull Rs.{val_res.get('target_bull')} ({val_res.get('return_bull_pct')}%)",
        f"Expected Rs.{val_res.get('expected_target')} ({upside:+.1f}%) at "
        f"{val_res.get('expected_cagr')}% CAGR",
        f"Forensics: CFO/PAT {forensic_res.get('cum_cfo_pat_ratio')}x, "
        f"debtor {debtor}d; DCF: {dcf_res.get('assessment')}",
    ]
    return {"ticker": ticker, "decision": decision, "verdict": verdict,
            "rationale": rationale_bits, "kill_switches": kill_switches,
            "caveats": caveats, "guard": guard,
            "base_rates": {"approved": appr, "rejected": rej,
                           "smallcap_approved": base_rates.get("smallcap_approved", []),
                           "smallcap_rejected": base_rates.get("smallcap_rejected", []),
                           "upside_bin": bin_cohort},
            "valuation": val_res, "forensics": forensic_res,
            "reverse_dcf": dcf_res}


def build_decision_brief(ticker: str, base_cagr: Optional[float] = None,
                         bull_cagr: Optional[float] = None) -> Dict[str, Any]:
    """Live brief: fetch -> calibrate -> value -> audit -> base rates."""
    t = (ticker or "").upper().strip()
    data = fetch_company_data(t)
    data["registry_ticker"] = t
    calibrated = calibrate_stock_parameters(data)
    params = prepare_valuation_params(
        data=data,
        calibrated=calibrated,
        base_cagr_override=base_cagr,
        bull_cagr_override=bull_cagr,
    )
    val_res = calculate_forward_pe_valuation(**params)
    forensic_res = run_forensic_audit(**forensic_inputs_from_data(data))
    latest_fcf = data["fcf_history"][-1] if data.get("fcf_history") else 0.0
    latest_cfo = data["cfo_history"][-1] if data.get("cfo_history") else 0.0
    if latest_fcf > 0:
        base_fcf = latest_fcf
    elif latest_cfo > 0:
        base_fcf = latest_cfo * 0.75
    elif data.get("ttm_pat", 0.0) > 0:
        base_fcf = data["ttm_pat"] * 0.80
    else:
        base_fcf = max(50.0, data.get("ttm_sales", 0.0) * 0.03)
    dcf_res = run_reverse_dcf(cmp=data["cmp"], mcap_cr=data["mcap_cr"], fcf_0=base_fcf)
    return build_brief_from_parts(data, calibrated, val_res, forensic_res,
                                  dcf_res, load_base_rates())


def format_brief_text(brief: Dict[str, Any]) -> str:
    """One-screen CLI rendering of the brief."""
    b = brief["base_rates"]
    lines = [f"DECISION on {brief['ticker']}: {brief['decision']} ({brief['verdict']})", ""]
    lines.append("Why:")
    lines += [f"  - {x}" for x in brief["rationale"]]
    if brief["caveats"]:
        lines.append("Caveats (read before acting):")
        lines += [f"  ! {x}" for x in brief["caveats"]]
    lines.append("Kill switches (exit triggers, not suggestions):")
    lines += [f"  {i+1}. {k}" for i, k in enumerate(brief["kill_switches"])]
    a, r, u = b["approved"], b["rejected"], b["upside_bin"]
    sc_a = _cohort(brief.get("base_rates", {}).get("smallcap_approved", []))
    sc_r = _cohort(brief.get("base_rates", {}).get("smallcap_rejected", []))
    if a.get("n"):
        n_total = a["n"] + (r.get("n") or 0)
        lines += ["", f"Base rates ({a['n']} approved of {n_total} historical evaluations): "
                      f"{a['hit_rate']}% positive, mean {a['mean']:+.1f}%"
                      + (f" vs rejected mean {r['mean']:+.1f}% (n={r['n']})." if r.get("n") else ".")]
        if sc_a.get("n"):
            spread = sc_a['mean'] - (sc_r.get('mean') or 0.0)
            lines.append(f"Smallcap samples ({sc_a['n']} approved): {sc_a['hit_rate']}% positive, "
                         f"mean {sc_a['mean']:+.1f}%, spread vs rejected {spread:+.1f}pp "
                         f"(hand-picked names, no index comparison).")
        if u.get("n"):
            lines.append(f"Names with similar upside: {u['n']} names, "
                         f"{u['hit_rate']}% positive, mean {u['mean']:+.1f}%.")
        lines.append("Historical samples are small and biased; not proof of an edge. Size accordingly.")
    else:
        lines.append("Base rates unavailable: no calibrated history loaded.")
    return "\n".join(lines)
