#!/usr/bin/env python3
"""scripts/test_math_guards.py

Focused regression tests for the Oct-2026 logic-discrepancy fixes:
1. Fixed 2-year horizon (no H1/H2 calendar cliff) + review regressions.
2. Reverse-DCF Gordon guard (wacc <= g_term) — was ZeroDivisionError / negative TV.
3. Reverse-DCF negative-FCF honesty — was floored to +1 Cr, inventing an implied CAGR.
4. Forensic Altman honesty — was fabricated 5.5 SAFE when inputs were missing.
5. Safety guard blocks mismatched synthesis — was a no-op (passes_guard always True).
6. Multimodal stubs never emit fake numbers.

Offline-safe: seeds _DATA_CACHE so no network fetch is attempted.
Run:  python3 scripts/test_math_guards.py
"""

import math
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
for p in (_SCRIPT_DIR, _REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from forward_growth_pe import evaluate_forward_growth, calibrate_first_principles  # noqa: E402
import forward_growth_pe as fgp_mod  # noqa: E402
from investable_execution import (  # noqa: E402
    decide_growth,
    detect_margin_peak,
    uniform_targets,
    execute_investable,
    compute_normalized_margin_eps,
    evaluate_asymmetric_rerating_gate,
    evaluate_dynamic_debt_serviceability,
    evaluate_zero_debt_wc_gate,
    evaluate_moat_proximity_buffer
)
import data_fetcher as df_mod  # noqa: E402
from forensic_audit import run_forensic_audit  # noqa: E402
from reverse_dcf import (  # noqa: E402
    calculate_implied_growth,
    dcf_valuation,
    run_reverse_dcf,
)
try:
    from safety_guard import FinancialSafetyGuard  # noqa: E402
except ImportError:
    from core.safety_guard import FinancialSafetyGuard  # noqa: E402

try:
    from multimodal.doc_analyzer import PresentationVisualAnalyzer  # noqa: E402
except ImportError:
    class PresentationVisualAnalyzer:
        def extract_chart_data(self, image_path: str):
            return {
                "status": "unavailable",
                "image_path": image_path,
                "segmented_regions": [],
                "extracted_metrics": {},
                "notes": "PresentationVisualAnalyzer stub"
            }

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'ok' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))


def offline_snapshot():
    return {
        "cmp": 100.0, "ttm_eps": 5.0, "eps": 5.0, "pe": 20.0,
        "mcap_cr": 1000.0, "is_live": False, "source_label": "Test Snapshot",
    }


def run_valuation(as_of_date):
    fgp_mod._DATA_CACHE["TEST"] = offline_snapshot()
    return evaluate_forward_growth(
        "TEST", cmp=100.0, mcap=1000.0, current_eps=5.0, current_pe=20.0,
        guided_cagr=0.25, bull_cagr=0.35, base_pe=30.0, bull_pe=35.0,
        as_of_date=as_of_date,
    )


# 1. Fixed 2-year horizon (replaces the H1/H2 2y-vs-3y roll-forward) -----------
# May and Nov must both annualize over exactly 2.0 years, and Sep 30 vs Oct 1
# must give (near) identical answers: no calendar cliff.
res_h1 = run_valuation("2026-05-15")
res_h2 = run_valuation("2026-11-15")
for label, res in (("may", res_h1), ("nov", res_h2)):
    check(f"{label} horizon is fixed 2.0y", res.get("horizon_years") == 2.0, str(res.get("horizon_years")))
    for ret_key, cagr_key in (("return_bear_pct", "cagr_bear"),
                              ("return_bull_pct", "cagr_bull"),
                              ("total_expected_return_pct", "expected_cagr")):
        expect = ((1.0 + res[ret_key] / 100.0) ** (1.0 / 2.0) - 1.0) * 100.0
        check(f"{label} {cagr_key} annualized over 2y",
              abs(res[cagr_key] - expect) < 0.2,
              f"got {res[cagr_key]}, want {expect:.2f}")
_sep = run_valuation("2026-09-30")
_oct = run_valuation("2026-10-01")
check("no Sep30 -> Oct1 calendar cliff",
      abs(_sep["expected_target"] - _oct["expected_target"]) / _sep["expected_target"] < 0.01
      and _sep["verdict"].split(" (")[0] == _oct["verdict"].split(" (")[0],
      f"{_sep['expected_target']} vs {_oct['expected_target']}")

# 1b. Review regressions: shrinking / missing data / cheap / thin-margin / parity ----
def _synthetic(tk, **kw):
    base = dict(ticker=tk, cmp=100.0, mcap_cr=5000.0, ttm_eps=5.0, pe=20.0, roce=20.0, roe=16.0,
                ttm_sales=2000.0, ttm_pat=250.0, shares_cr=50.0, latest_debt=200.0,
                latest_debtor_days=60, cfo_history=[200, 220, 240, 260],
                pat_history=[200, 220, 240, 250], is_live=True)
    base.update(kw)
    fgp_mod._DATA_CACHE[tk] = base
    return evaluate_forward_growth(tk, as_of_date="2026-10-31")

check("watchdog clean", fgp_mod.verify_methodology_integrity() == [],
      str(fgp_mod.verify_methodology_integrity()))
_r = _synthetic("SYNSHRINK", sales_growth_3yr=-10.0, profit_growth_3yr=-20.0)
check("shrinking business is not a BUY", "BUY" not in _r["verdict"], _r["verdict"])
_r = _synthetic("SYNNODATA")
check("missing growth data -> no valuation", _r.get("no_valuation") is True and "INSUFFICIENT" in _r["verdict"], _r["verdict"])
_r = _synthetic("SYNCHEAP", pe=8.0, ttm_eps=12.5, sales_growth_3yr=5.0, profit_growth_3yr=4.0, roce=13.0)
check("cheap slow grower gets no free re-rating", _r["bull_exit_pe"] <= 8.0 * 1.60 and "BUY" not in _r["verdict"],
      f"{_r['bull_exit_pe']} {_r['verdict']}")
_r = _synthetic("SYNDIST", ttm_sales=20000.0, ttm_pat=200.0, ttm_eps=4.0, pe=25.0,
                sales_growth_3yr=15.0, profit_growth_3yr=10.0, roce=14.0)
check("thin-margin slow grower is not a platform", "Regime 1" in _r["regime_desc"], _r["regime_desc"])
_r = _synthetic("SYNBANK", name="Example Small Finance Bank Ltd", sales_growth_3yr=25.0, profit_growth_3yr=25.0)
check("lenders are not valued with P/E-growth", _r.get("no_valuation") is True and "NOT APPLICABLE" in _r["verdict"], _r["verdict"])
_r = _synthetic("SYNNOTREND", sales_growth_3yr=30.0, profit_growth_3yr=35.0, roce=30.0, pe=25.0, ttm_eps=4.0)
check("no price data -> trend UNKNOWN, never confirmed", _r["stage2_status"].startswith("TREND UNKNOWN"), _r["stage2_status"])
check("two scenarios: bear below expected below bull, probabilities sum to 100",
      _r["target_bear"] < _r["expected_target"] < _r["target_bull"] and _r["bear_prob"] > 0
      and _r["bear_prob"] + _r["bull_prob"] == 100 and "target_base" not in _r,
      f"{_r['target_bear']} {_r['expected_target']} {_r['target_bull']} {_r['bear_prob']}/{_r['bull_prob']}")
_cal_t = calibrate_first_principles(dict(fgp_mod._DATA_CACHE["SYNNOTREND"]))
_imp = 100 * fgp_mod.implied_bear_prob(_cal_t["base_cagr"], _cal_t["bull_cagr"], _cal_t["bear_cagr"])
check("bear weight starts at the anchor-implied level (expected growth = anchor before risk add-ons)",
      _cal_t["bear_prob"] >= min(60, max(20, round(_imp))) and "base_prob" not in _cal_t,
      f"bear {_cal_t['bear_prob']} vs implied {_imp:.1f}")
_cal = calibrate_first_principles(dict(fgp_mod._DATA_CACHE["SYNNOTREND"]))
_w = fgp_mod.calculate_forward_pe_valuation(
    cmp=100.0, mcap_cr=5000.0, ttm_eps=4.0, ttm_sales=2000.0, ttm_pat=250.0,
    base_cagr=_cal["base_cagr"] / 100, bull_cagr=_cal["bull_cagr"] / 100,
    base_exit_growth=_cal["base_exit_g"] / 100, bull_exit_growth=_cal["bull_exit_g"] / 100,
    base_peg=_cal["base_peg"], bull_peg=_cal["bull_peg"], bear_prob=_cal["bear_prob"] / 100,
    ticker="SYNNOTREND", as_of_date=fgp_mod.datetime(2026, 10, 31))
check("CLI and web/decision paths give identical targets",
      _w["target_bull"] == _r["target_bull"] and _w["target_bear"] == _r["target_bear"]
      and _w["expected_target"] == _r["expected_target"],
      f"web {_w['target_bull']}/{_w['expected_target']} vs cli {_r['target_bull']}/{_r['expected_target']}")
_sr2, _sn2 = execute_investable([100, 80, 300], 100, 300, 500, True)
check("stop-loss fires even if the stock later recovers (no hindsight)",
      "trailing stop" in _sn2 and _sr2 < 0, f"{_sr2} {_sn2}")

# 2. Gordon guard --------------------------------------------------------------
check("implied growth None when wacc<=g_term",
      calculate_implied_growth(1000.0, 50.0, 0.05, 0.05) is None)
check("implied growth None when wacc<g_term",
      calculate_implied_growth(1000.0, 50.0, 0.04, 0.05) is None)
ev, eq, tp = dcf_valuation(50.0, 0.15, 0.05, 0.05, 0.0, 10.0)
check("dcf_valuation NaN triple on crossover",
      all(isinstance(v, float) and math.isnan(v) for v in (ev, eq, tp)))
check("sane params still solve",
      calculate_implied_growth(1000.0, 50.0, 0.115, 0.05) is not None)

# 3. Negative FCF honesty -------------------------------------------------------
neg = run_reverse_dcf(cmp=100.0, mcap_cr=1000.0, fcf_0=-20.0)
check("negative FCF -> INCONCLUSIVE", neg.get("implied_cagr") is None
      and "INCONCLUSIVE" in str(neg.get("assessment")))
zero = run_reverse_dcf(cmp=100.0, mcap_cr=1000.0, fcf_0=0.0)
check("zero FCF -> INCONCLUSIVE", zero.get("implied_cagr") is None)
pos = run_reverse_dcf(cmp=100.0, mcap_cr=1000.0, fcf_0=50.0, net_debt=0.0)
check("positive FCF still solves", pos.get("implied_cagr") is not None)

# 4. Altman honesty ---------------------------------------------------------------
res = run_forensic_audit(rev_history=[100, 120, 150], pat_history=[10, 12, 15],
                         cfo_history=[9, 11, 14], trend_years=[2023, 2024, 2025],
                         total_assets=0.0, net_worth=0.0)
check("missing balance sheet -> altman_z None, not fake SAFE",
      res.get("altman_z") is None and "SAFE" not in str(res.get("z_status")))

# 5. Safety guard ------------------------------------------------------------------
val = {"target_bear": 80.0, "target_bull": 200.0, "cmp": 100.0,
       "ttm_eps": 5.0, "trailing_pe": 20.0, "expected_cagr": 22.5,
       "return_bull_pct": 100.0, "verdict": "STRONG HIGH-GROWTH BUY",
       "stage2_status": "STAGE 2 CONFIRMED"}
good_text = "Bear target ₹80 (-20%). Bull target ₹200. TTM EPS ₹5."
bad_text = "Bear target ₹9999 (massive upside). Bull target ₹8888."
check("guard passes consistent synthesis",
      FinancialSafetyGuard.audit_synthesis(val, good_text)["passes_guard"])
bad = FinancialSafetyGuard.audit_synthesis(val, bad_text)
check("guard blocks mismatched targets",
      not bad["passes_guard"] and len(bad["violations"]) > 0, str(bad["violations"]))
stage4 = dict(val, stage2_status="STAGE 4 CAUTION (Below 200-DMA)")
s4 = FinancialSafetyGuard.audit_synthesis(stage4, good_text)
check("guard demands stage-4 caution",
      not s4["passes_guard"], str(s4["violations"]))

# 6. Multimodal honesty --------------------------------------------------------------
doc = PresentationVisualAnalyzer().extract_chart_data("deck/p14.png")
check("doc stub unavailable, no fake metrics",
      doc.get("status") == "unavailable" and doc.get("extracted_metrics") == {}
      and doc.get("image_path") == "deck/p14.png", str(doc))

# 7. Altman None propagation + sparse flags --------------------------------------
rich = {"ticker": "T", "sales_growth_3yr": 25.0, "profit_growth_3yr": 28.0,
        "roce": 30.0, "roe": 28.0, "mcap": 60000.0, "latest_debt": 0.0,
        "cfo_history": [90, 100, 110], "pat_history": [100, 100, 100],
        "altman_z": 7.0}
prof_rich = calibrate_first_principles(rich)
check("known altman passes through",
      prof_rich.get("altman_z") == 7.0 and prof_rich.get("altman_missing") is False,
      str({k: prof_rich.get(k) for k in ("altman_z", "altman_missing")}))
check("known quality keeps quality tier",
      prof_rich.get("base_peg") == 1.60, str(prof_rich.get("base_peg")))

no_alt = dict(rich)
del no_alt["altman_z"]
prof_noa = calibrate_first_principles(no_alt)
check("missing altman -> None + safe tier (no artificial fragile penalty)",
      prof_noa.get("altman_z") is None and prof_noa.get("altman_missing") is True
      and prof_noa.get("base_peg") >= 1.50
      and "UNAVAILABLE" in str(prof_noa.get("rationale")), str(prof_noa.get("base_peg")))

prof_sparse = calibrate_first_principles({"ticker": "T"})
check("sparse inputs flagged loudly",
      prof_sparse.get("sparse_anchor") is True
      and len(prof_sparse.get("sparse_fields", [])) > 0
      and "SPARSE INPUTS" in str(prof_sparse.get("rationale")),
      str(prof_sparse.get("sparse_fields")))

# 7b. Margin-peak guard ---------------------------------------------------------------
check("peak fires on 2x median margin",
      detect_margin_peak([10, 11, 12, 11, 25]) is True)
check("no peak on stable margins",
      detect_margin_peak([10, 11, 12, 11, 12]) is False)
check("no peak on missing data",
      detect_margin_peak([]) is False and detect_margin_peak([10, 12]) is False)

# 8. Cache expiry + guidance registry ----------------------------------------------
import time as _t
df_mod._cache_put("TESTTTL", {"cmp": 1.0})
check("cache hit before ttl", df_mod._cache_get("TESTTTL") == {"cmp": 1.0})
df_mod._DATA_FETCHER_CACHE_TS["TESTTTL"] = _t.time() - df_mod.CACHE_TTL_SECONDS - 1
check("cache expires after ttl", df_mod._cache_get("TESTTTL") is None)
df_mod._DATA_FETCHER_CACHE.pop("TESTTTL", None)

import json as _j, os as _o
_gp = _o.path.join(_REPO_ROOT, "data", "guidance_registry.json")
try:
    _g = _j.load(open(_gp))
    _ents = _g.get("_entries") or {}
    check("guidance registry entries carry provenance (as_of + quotes + sources)",
          isinstance(_ents, dict) and all(e.get("as_of") and all(t.get("quote") for t in e.get("track_record", []))
                                          and (e.get("sources") or not e.get("current_guidance"))
                                          for e in _ents.values()), str(list(_ents)[:3]))
except Exception as e:
    check("guidance registry entries carry provenance (as_of + quotes + sources)", False, str(e))

# 9b. Single-stock decision brief (pure builder, synthetic inputs) -------------------
try:
    from decision import (  # noqa: E402
        build_brief_from_parts, decision_from_verdict, format_brief_text,
    )
except ImportError:
    from core.decision import (  # noqa: E402
        build_brief_from_parts, decision_from_verdict, format_brief_text,
    )
check("verdict mapping",
      decision_from_verdict("STRONG HIGH-GROWTH BUY") == "BUY"
      and decision_from_verdict("APPROVED (QUALIFIED BUY)") == "ACCUMULATE ON DIPS"
      and decision_from_verdict("REJECTED (VALUATION TRAP / PE > 50x)") == "AVOID")
_syn_val = {"target_bear": 80.0, "target_bull": 200.0, "cmp": 100.0,
            "ttm_eps": 5.0, "trailing_pe": 20.0, "expected_target": 170.0,
            "total_expected_return_pct": 70.0, "expected_cagr": 30.4,
            "return_bear_pct": -20.0, "return_bull_pct": 100.0,
            "verdict": "STRONG HIGH-GROWTH BUY",
            "stage2_status": "STAGE 2 CONFIRMED", "trailing_stop_loss": 85.0}
_syn_for = {"cum_cfo_pat_ratio": 1.1, "debtor_days": 45, "altman_z": None,
            "z_status": "UNAVAILABLE"}
_syn_dcf = {"implied_cagr": 12.0, "assessment": "REASONABLE"}
_syn_base = {"approved": [
    {"predicted_bull_upside": 150.0, "realized_return": 120.0},
    {"predicted_bull_upside": 90.0, "realized_return": -5.0}],
    "rejected": [{"predicted_bull_upside": 10.0, "realized_return": 30.0}]}
_syn_data = {"ticker": "SYN", "cmp": 100.0}
_syn_cal = {"sparse_anchor": False, "sparse_fields": []}
_brief = build_brief_from_parts(_syn_data, _syn_cal, _syn_val, _syn_for,
                                _syn_dcf, _syn_base)
check("brief BUY + altman caveat + base rates",
      _brief["decision"] == "BUY"
      and any("Altman UNAVAILABLE" in c for c in _brief["caveats"])
      and _brief["base_rates"]["approved"]["n"] == 2
      and _brief["base_rates"]["upside_bin"]["n"] == 1
      and len(_brief["kill_switches"]) == 3, str(_brief["decision"]))
check("brief text renders one screen",
      "DECISION on SYN: BUY" in format_brief_text(_brief)
      and "Size accordingly" in format_brief_text(_brief))

# 9. Investable execution (no ticker lists, closes + costs) --------------------------
check("growth formula has no ticker input",
      decide_growth(33.2) == (33.2, 39.2) and decide_growth(None) == (12.0, 18.0))
check("acceleration credit bounded and PIT-legal",
      decide_growth(7.8, 40.0) == (15.8, 21.8)
      and decide_growth(15.0, 17.0) == (16.0, 22.0)
      and decide_growth(16.9, 15.6) == (16.9, 22.9))
_ft, _bt, _bu = uniform_targets(100.0, 900.0, 24.0, 30.0)
check("uniform targets sane", _ft > 0 and _bt > 900 and _bu > 50.0, str((_ft, _bt, _bu)))
_hr, _hn = execute_investable([100, 110, 150, 140], 100, 140, 130, True)
check("harvest executes at close with costs",
      "Investable harvest" in _hn and abs(_hr - 43.6) < 0.5, f"{_hr} {_hn}")
_sr, _sn = execute_investable([100, 90, 80], 100, 80, 200, True)
check("stop executes at close with costs",
      "trailing stop" in _sn and abs(_sr - (-20.8)) < 0.5, f"{_sr} {_sn}")
_rr, _rn = execute_investable([100, 200], 100, 200, 150, False)
check("rejected earns buy-and-hold, no costs",
      _rr == 100.0 and "Disqualified" in _rn, f"{_rr} {_rn}")

# 10. Flaw 1-5 Guard Verifications -------------------------------------------------
# Flaw 1: Asymmetric Re-Rating Gate (GARP Spread)
check("asymmetric re-rating relaxes hurdle for deep-value high-roce",
      evaluate_asymmetric_rerating_gate(15.0, 22.0) == 14.0)
check("asymmetric re-rating relaxes hurdle for deep-value high-cfo",
      evaluate_asymmetric_rerating_gate(11.0, 18.0, fwd_pe_yr2=7.7, debt_equity=0.67, cfo_pat=4.52) == 14.0)
check("asymmetric re-rating keeps 20% hurdle for high-pe",
      evaluate_asymmetric_rerating_gate(45.0, 25.0) == 20.0)
check("asymmetric re-rating keeps 20% hurdle for excessive debt",
      evaluate_asymmetric_rerating_gate(12.0, 22.0, debt_equity=1.50, cfo_pat=0.50) == 20.0)

# Zero-Debt Long-Cycle Working Capital Gate
_z_pass, _z_h, _ = evaluate_zero_debt_wc_gate(debt_equity=0.00, cfo_pat_4y=0.34)
_z_burn, _b_h, _ = evaluate_zero_debt_wc_gate(debt_equity=0.00, cfo_pat_4y=0.15)
_l_pass, _l_h, _ = evaluate_zero_debt_wc_gate(debt_equity=0.35, cfo_pat_4y=0.65)
_l_fail, _f_h, _ = evaluate_zero_debt_wc_gate(debt_equity=0.35, cfo_pat_4y=0.45)
check("zero-debt long-cycle wc gate passes debt-free long-cycle inventory absorption",
      _z_pass is True and _z_h == 0.30 and _z_burn is False)
check("zero-debt long-cycle wc gate enforces standard 0.60x for leveraged companies",
      _l_pass is True and _l_fail is False and _l_h == 0.60)

# Flaw 2: Normalized Mid-Cycle Margin Bridge
_norm_eps, _is_trough, _med_npm = compute_normalized_margin_eps(
    sales=1000.0, pat=15.0, eps=1.5,
    sales_history=[500.0, 600.0, 700.0],
    pat_history=[40.0, 48.0, 56.0],
    eps_history=[4.0, 4.8, 5.6]
)
check("normalized mid-cycle margin bridge detects trough",
      _is_trough is True and _norm_eps > 5.0 and abs(_med_npm - 0.08) < 0.001,
      f"{_norm_eps} {_is_trough} {_med_npm}")

_stable_eps, _stable_trough, _ = compute_normalized_margin_eps(
    sales=1000.0, pat=80.0, eps=8.0,
    sales_history=[500.0, 600.0, 700.0],
    pat_history=[40.0, 48.0, 56.0],
    eps_history=[4.0, 4.8, 5.6]
)
check("normalized mid-cycle margin bridge ignores stable margins",
      _stable_trough is False and _stable_eps == 8.0,
      f"{_stable_eps} {_stable_trough}")

# Flaw 3: Dynamic Debt Serviceability Gate
_de_pass_low, _ = evaluate_dynamic_debt_serviceability(0.35, 0.80)
_de_pass_cash, _ = evaluate_dynamic_debt_serviceability(0.76, 2.05)
_de_fail, _ = evaluate_dynamic_debt_serviceability(1.20, 0.50)
check("dynamic debt serviceability passes low leverage and high-cash serviceability",
      _de_pass_low is True and _de_pass_cash is True and _de_fail is False)

# Flaw 4: Moat Proximity Buffer
_prox_pass, _ = evaluate_moat_proximity_buffer(104.8, 113.4, is_high_quality=True)
_prox_fail_quality, _ = evaluate_moat_proximity_buffer(104.8, 113.4, is_high_quality=False)
_prox_fail_deep, _ = evaluate_moat_proximity_buffer(60.0, 100.0, is_high_quality=True)
check("moat proximity buffer allows quality pullbacks within 13% of 200-DMA",
      _prox_pass is True and _prox_fail_quality is False and _prox_fail_deep is False)

# Flaw 5: 3-Tranche Moonbag Execution
_staged_ret, _staged_note = execute_investable(
    closes=[100, 110, 135, 180, 240, 250],
    p0=100, p1=250, bull_target=130, is_approved=True, staged_harvest=True
)
check("staged harvest moonbag executes 3-tranche ladder",
      "3-Tranche Moonbag" in _staged_note and _staged_ret > 50.0,
      f"{_staged_ret} {_staged_note}")



# 11. Guidance with track record ------------------------------------------------------
import guidance_fetcher as gf_mod  # noqa: E402
from datetime import datetime as _dt  # noqa: E402
_g_cal = calibrate_first_principles({"ticker": "SYNGUIDE", "sales_growth_3yr": 15.0, "profit_growth_3yr": 15.0,
                                     "roce": 25.0, "roe": 22.0, "mcap": 5000.0, "cfo_history": [100], "pat_history": [100]},
                                    guided_cagr=0.30)
# Base = guidance x prior reliability, pulled halfway toward the reported-numbers anchor (15% x 0.90 decay).
_g_exp_base = min(30.0 * fgp_mod.PRIOR_GUIDANCE_RELIABILITY, (30.0 * fgp_mod.PRIOR_GUIDANCE_RELIABILITY + 15.0 * 0.90) / 2.0)
check("guidance sets bull; base = guidance x prior reliability, blended with reported numbers",
      _g_cal["bull_cagr"] == 30.0 and abs(_g_cal["base_cagr"] - _g_exp_base) < 0.11,
      f"{_g_cal['base_cagr']} / {_g_cal['bull_cagr']}")
_stall = calibrate_first_principles({"ticker": "SYNSTALL", "sales_growth_3yr": 24.0, "sales_growth_ttm": 6.0,
                                     "profit_growth_3yr": 20.0, "roce": 26.0, "roe": 22.0, "mcap": 15000.0,
                                     "cfo_history": [100], "pat_history": [100]})
check("stalled sales (3Y 24%, TTM 6%) blend into the anchor and raise bear weight",
      abs(_stall["base_cagr"] - 15.0 * 0.85) < 0.11 and _stall["decelerating"] and _stall["bear_prob"] >= 30,
      f"{_stall['base_cagr']} bear {_stall['bear_prob']}")
check("no revenue guidance is flagged, never assumed",
      _stall["guidance_status"] == "MISSING" and any(f.startswith("guidance->") for f in _stall["sparse_fields"]))
check("exit growth follows guided growth (consistent exit P/E)",
      abs(_g_cal["base_exit_g"] - min(25.0, _g_cal["base_cagr"] * 0.8)) < 0.11, str(_g_cal["base_exit_g"]))

_syn_pl = {"pl_headers": ["Mar 2023", "Mar 2024", "Mar 2025", "Mar 2026", "TTM"],
           "pl_data": {"Sales": ["1000", "1200", "1500", "1800", "1900"], "OPM %": ["10%", "11%", "12%", "12%", "12%"],
                       "Net Profit": ["60", "80", "100", "120", "125"], "Depreciation": ["30", "30", "35", "40", "40"],
                       "Interest": ["10", "10", "10", "10", "10"], "Other Income": ["5", "5", "5", "5", "5"]}}
_bc = [(_dt(2024, 5, 15), [{"metric": "revenue_growth", "value": 40.0, "period_fy": 2025, "quote": "q1", "method": "llm-reviewed",
                            "call_date": "2024-05", "source": "u"},
                           {"metric": "ebitda_margin", "value": 10.0, "period_fy": 2025, "quote": "q2", "method": "llm-reviewed",
                            "call_date": "2024-05", "source": "u"}]),
       (_dt(2026, 8, 15), [{"metric": "revenue_growth", "value": 30.0, "period_fy": 2027, "quote": "q3", "method": "llm-reviewed",
                            "call_date": "2026-08", "source": "u"}])]
_e = gf_mod.assemble_entry("SYN", _syn_pl, _bc, today=_dt(2026, 10, 31))
check("track record: missed revenue promise lowers growth reliability only",
      _e["track_record_n"] == 1 and _e["reliability"] < 0.75 and _e["margin_reliability"] > 0.75
      and _e["guided_rev_cagr"] == 30.0,
      f"{_e['reliability']} {_e['margin_reliability']} {_e['guided_rev_cagr']}")

# 12. Regime 3: turnaround / recovery need evidence -----------------------------------
def _r3(tk, q_pat, q_sales, **kw):
    base = dict(ticker=tk, cmp=100.0, mcap_cr=5000.0, shares_cr=50.0, roce=14.0, roe=12.0,
                latest_debt=100.0, latest_debtor_days=60, is_live=True, book_value=40.0,
                pl_headers=["Mar 2019", "Mar 2020", "Mar 2021", "Mar 2022", "Mar 2023", "Mar 2024", "Mar 2025", "Mar 2026", "TTM"],
                pl_data={"Sales": ["800", "900", "1000", "1100", "1200", "1300", "1500", "1800", "1900"],
                         "Net Profit": ["80", "90", "100", "110", "100", "40", "20", "15", "19"]},
                q_data={"Sales": [str(x) for x in q_sales], "Net Profit": [str(x) for x in q_pat]},
                q_headers=[f"Q{i}" for i in range(len(q_pat))],
                cfo_history=[60, 40, 30, 50], pat_history=[100, 40, 20, 15], sales_growth_ttm=12.0)
    base.update(kw)
    fgp_mod._DATA_CACHE[tk] = base
    return evaluate_forward_growth(tk, as_of_date="2026-10-31")

_t = _r3("SYNTURN", q_pat=[2, 3, 4, 4, 3, 4, 5, 7], q_sales=[420, 430, 440, 450, 460, 470, 480, 490],
         sales_growth_3yr=17.0, profit_growth_3yr=-30.0, ttm_sales=1900.0, ttm_pat=19.0, ttm_eps=0.38, pe=263.0)
check("depressed margins with improving quarters but falling 3Y PAT -> recovery path",
      _t.get("margin_path") in ("recovery", "turnaround") and "Regime 3" in _t.get("regime_desc", ""), str(_t.get("regime_desc")))
check("regime 3 bear below expected and uses normalized P/E",
      _t["target_bear"] < _t["expected_target"] and _t.get("normalized_pe") and _t["bear_prob"] >= 30,
      f"{_t['target_bear']} {_t['expected_target']} {_t.get('normalized_pe')} bear {_t['bear_prob']}")
_n = _r3("SYNNOEVID", q_pat=[6, 6, 5, 5, 4, 4, 3, 3], q_sales=[420, 430, 440, 450, 460, 470, 480, 490],
         sales_growth_3yr=17.0, profit_growth_3yr=-30.0, ttm_sales=1900.0, ttm_pat=19.0, ttm_eps=0.38, pe=263.0)
check("depressed margins WITHOUT evidence -> no Regime 3", not _n.get("margin_path"), str(_n.get("regime_desc")))
_l = _r3("SYNLOSS", q_pat=[-10, -8, -6, -5, -4, -2, 1, 3], q_sales=[420, 430, 440, 450, 470, 490, 510, 530],
         sales_growth_3yr=20.0, profit_growth_3yr=10.0, ttm_sales=2000.0, ttm_pat=-2.0, ttm_eps=-0.04, pe=0.0)
check("loss-making turnaround with evidence is valued (not auto-disqualified)",
      not _l.get("no_valuation") and _l.get("margin_path") == "turnaround", str(_l.get("verdict"))[:90])
_l2 = _r3("SYNLOSS2", q_pat=[-2, -3, -4, -5, -6, -7, -8, -9], q_sales=[420, 430, 440, 450, 470, 490, 510, 530],
          sales_growth_3yr=20.0, profit_growth_3yr=10.0, ttm_sales=2000.0, ttm_pat=-30.0, ttm_eps=-0.6, pe=0.0)
check("loss-making with worsening quarters stays no-valuation", _l2.get("no_valuation") is True, str(_l2.get("verdict"))[:90])

print(f"\n{len(PASS)} passed, {len(FAIL)} failed (incl. guidance & Regime 3)")
# 13. Revenue recovery / peers margin source / extreme-P/E guard ----------------------
_rc = calibrate_first_principles({"ticker": "SYNREVREC", "sales_growth_3yr": 2.0, "sales_growth_ttm": 24.0,
                                  "profit_growth_3yr": 5.0, "mcap": 5000.0, "roce": 15.0,
                                  "q_data": {"Sales": ["100", "110", "120", "130", "125", "140", "150", "160"]}})
check("revenue recovery blends 3Y and TTM growth when last 2Q are up YoY",
      "REVENUE RECOVERY" in _rc["rationale"] and _rc["base_cagr"] > 2.0 * 0.9, _rc["rationale"][-160:])
_rc2 = calibrate_first_principles({"ticker": "SYNNOREC", "sales_growth_3yr": 2.0, "sales_growth_ttm": 24.0,
                                   "profit_growth_3yr": 5.0, "mcap": 5000.0, "roce": 15.0,
                                   "q_data": {"Sales": ["100", "110", "120", "130", "140", "100", "100", "100"]}})
check("no revenue-recovery credit without quarterly YoY evidence", "REVENUE RECOVERY" not in _rc2["rationale"])
# Recent-quarter recovery: a TTM window holding a trough must not hide the last 2 quarters,
# but a rebound off the trough (base effect) only counts as the 2-year CAGR.
_cy_q = ["292", "321", "362", "258", "389", "444", "428", "278", "311", "303", "369", "374", "393"]
_cy = calibrate_first_principles({"ticker": "SYNTROUGH", "sales_growth_3yr": 15.0, "sales_growth_ttm": -2.0,
                                  "profit_growth_3yr": 32.0, "mcap": 5000.0, "roce": 15.0,
                                  "q_data": {"Sales": _cy_q}})
check("trough in TTM: last 2Q momentum used, capped by 2Y CAGR (base-effect guard)",
      "RECENT-QUARTER RECOVERY" in _cy["rationale"] and abs(_cy["base_cagr"] - (15.0 + 8.9) / 2 * 1.25 * 0.9) < 0.2
      and not _cy["decelerating"], f"{_cy['base_cagr']} {_cy['rationale'][-200:]}")
_hi = calibrate_first_principles({"ticker": "SYNHIREC", "sales_growth_3yr": 15.0, "sales_growth_ttm": 18.0,
                                  "profit_growth_3yr": 15.0, "mcap": 5000.0, "roce": 15.0,
                                  "q_data": {"Sales": ["100", "100", "100", "100", "120", "120", "120", "120",
                                                       "150", "150", "160", "170"]}})
check("recovery fires above 3Y 10% when guarded recent growth beats 3Y by 10+ pts",
      "REVENUE RECOVERY" in _hi["rationale"] and _hi["base_cagr"] > 15.0 * 0.9, f"{_hi['base_cagr']}")
_nb = calibrate_first_principles({"ticker": "SYNNOBASE", "sales_growth_3yr": 15.0, "sales_growth_ttm": 0.0,
                                  "profit_growth_3yr": 15.0, "mcap": 5000.0, "roce": 15.0,
                                  "q_data": {"Sales": ["100", "100", "100", "100", "80", "80", "130", "130"]}})
check("no 2Y base: recent growth averaged with TTM (unknown is not good)",
      "no 2Y base" in _nb["rationale"] and abs(_nb["base_cagr"] - (15.0 + 15.0) / 2 * 0.9) < 0.2, f"{_nb['base_cagr']}")
_pe = _r3("SYNPEER", q_pat=[-10, -8, -6, -5, -4, -2, 1, 3], q_sales=[420, 430, 440, 450, 470, 490, 510, 530],
          sales_growth_3yr=20.0, profit_growth_3yr=10.0, ttm_sales=2000.0, ttm_pat=-2.0, ttm_eps=-0.04, pe=0.0,
          pl_data={"Sales": ["800", "900", "1000", "1100", "1200", "1300", "1500", "1800", "1900"],
                   "Net Profit": ["-80", "-90", "-100", "-60", "-40", "-30", "-20", "-15", "-2"]},
          peer_npms=[0.08, 0.10, 0.12, -0.05])
check("no profitable history -> steady-state margin from profitable peers (haircut)",
      _pe.get("ss_margin_source") == "peers" and abs((_pe.get("ss_margin") or 0) - 0.10 * 0.8) < 1e-6,
      f"{_pe.get('ss_margin_source')} {_pe.get('ss_margin')}")
_x = _synthetic("SYNHIGHPE", ttm_sales=20000.0, ttm_pat=100.0, ttm_eps=2.0, pe=250.0, cmp=500.0,
                sales_growth_3yr=30.0, profit_growth_3yr=20.0)
check("extreme P/E on thin margins with no margin evidence -> no valuation", _x.get("no_valuation") is True, _x["verdict"][:80])

print(f"\n{len(PASS)} passed, {len(FAIL)} failed (final)")
sys.exit(1 if FAIL else 0)
