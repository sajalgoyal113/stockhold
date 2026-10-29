#!/usr/bin/env python3
"""scripts/test_math_guards.py

Focused regression tests for the Oct-2026 logic-discrepancy fixes:
1. Horizon-aware CAGR annualization (H1: 2 yrs, H2: 3 yrs) — was hardcoded **0.5.
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


# 1. Horizon-aware annualization ---------------------------------------------
# May-2026 -> H1 regime (comp_years_yr2 == 2); Nov-2026 -> H2 (== 3).
res_h1 = run_valuation("2026-05-15")
res_h2 = run_valuation("2026-11-15")
check("h1 horizon is 2y", res_h1.get("comp_years_yr2") == 2, str(res_h1.get("comp_years_yr2")))
check("h2 horizon is 3y", res_h2.get("comp_years_yr2") == 3, str(res_h2.get("comp_years_yr2")))

for label, res in (("h1", res_h1), ("h2", res_h2)):
    yrs = res["comp_years_yr2"]
    for ret_key, cagr_key in (("return_base_pct", "cagr_base"),
                              ("return_bull_pct", "cagr_bull"),
                              ("total_expected_return_pct", "expected_cagr")):
        expect = ((1.0 + res[ret_key] / 100.0) ** (1.0 / yrs) - 1.0) * 100.0
        check(f"{label} {cagr_key} uses {yrs}y horizon",
              abs(res[cagr_key] - expect) < 0.2,
              f"got {res[cagr_key]}, want {expect:.2f}")

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
val = {"target_base": 150.0, "target_bull": 200.0, "cmp": 100.0,
       "ttm_eps": 5.0, "trailing_pe": 20.0, "expected_cagr": 22.5,
       "return_bull_pct": 100.0, "verdict": "STRONG HIGH-GROWTH BUY",
       "stage2_status": "STAGE 2 CONFIRMED"}
good_text = "Base target ₹150 (50% upside). Bull target ₹200. TTM EPS ₹5."
bad_text = "Base target ₹9999 (massive upside). Bull target ₹8888."
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
      prof_rich.get("base_peg") == 1.40, str(prof_rich.get("base_peg")))

no_alt = dict(rich)
del no_alt["altman_z"]
prof_noa = calibrate_first_principles(no_alt)
check("missing altman -> None + fragile tier + penalty",
      prof_noa.get("altman_z") is None and prof_noa.get("altman_missing") is True
      and prof_noa.get("base_peg") == 0.85
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
    check("guidance registry explicit, empty by default",
          isinstance(_g.get("_entries"), dict) and len(_g.get("_entries")) == 0, str(_g.keys()))
except Exception as e:
    check("guidance registry explicit, empty by default", False, str(e))

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
_syn_val = {"target_base": 150.0, "target_bull": 200.0, "cmp": 100.0,
            "ttm_eps": 5.0, "trailing_pe": 20.0, "expected_target": 170.0,
            "total_expected_return_pct": 70.0, "expected_cagr": 30.4,
            "return_base_pct": 50.0, "return_bull_pct": 100.0,
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

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
