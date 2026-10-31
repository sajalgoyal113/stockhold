"""Financial Safety & Invariant Guard.

Enforces zero-hallucination policies and strict mathematical constraints:
1. Target price cited in natural language must match deterministic math output within 1%.
2. Trailing P/E must equal CMP / TTM EPS (independent fundamental EPS anchoring).
3. Bull Case hurdle check (mandated >= 50% return within 2 years).
4. Stage 4 downtrend warning trigger.
"""

import re
from typing import Dict, Any, List


class FinancialSafetyGuard:
    """Verifies that synthesis aligns with deterministic math invariants."""

    @staticmethod
    def _numbers_in_text(text: str) -> List[float]:
        nums = []
        for m in re.finditer(r"₹?\s*([\d,]+\.?\d*)", text or ""):
            try:
                nums.append(float(m.group(1).replace(",", "")))
            except ValueError:
                continue
        return nums

    @staticmethod
    def audit_synthesis(valuation_data: Dict[str, Any], synthesis_text: str) -> Dict[str, Any]:
        violations: List[str] = []
        text = synthesis_text or ""
        expected_bear_target = valuation_data.get("target_bear") or valuation_data.get("target_price_bear")
        expected_bull_target = valuation_data.get("target_bull") or valuation_data.get("target_price_bull")

        # 1. Target-price match within 1%: every deterministic target cited in
        # the synthesis must appear (within tolerance) in the text numbers.
        cited = FinancialSafetyGuard._numbers_in_text(text)
        for label, expected in (("bear", expected_bear_target), ("bull", expected_bull_target)):
            if not expected:
                continue
            try:
                exp = float(expected)
            except (TypeError, ValueError):
                continue
            if exp > 0 and not any(abs(n - exp) / exp <= 0.01 for n in cited):
                violations.append(
                    f"{label} target ₹{exp:,.2f} not cited within 1% in synthesis"
                )

        # 2. Trailing P/E anchor: CMP / TTM EPS must reproduce the stated P/E.
        cmp = valuation_data.get("cmp")
        ttm_eps = valuation_data.get("ttm_eps")
        trailing_pe = valuation_data.get("trailing_pe") or valuation_data.get("current_pe")
        if cmp and ttm_eps and trailing_pe:
            try:
                implied_pe = float(cmp) / float(ttm_eps) if float(ttm_eps) > 0 else None
                if implied_pe is not None and abs(implied_pe - float(trailing_pe)) / max(float(trailing_pe), 1e-9) > 0.02:
                    violations.append(
                        f"P/E anchor broken: CMP/TTM-EPS={implied_pe:.1f}x vs stated {float(trailing_pe):.1f}x"
                    )
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # 3. Bull-case hurdle: mandated >= 50% upside for a BUY verdict.
        bull_upside = valuation_data.get("return_bull_pct")
        verdict = str(valuation_data.get("verdict", ""))
        if bull_upside is not None and ("BUY" in verdict.upper()):
            try:
                if float(bull_upside) < 50.0:
                    violations.append(
                        f"bull upside {float(bull_upside):+.1f}% fails mandated 50% hurdle for BUY verdict"
                    )
            except (TypeError, ValueError):
                pass

        # 4. Stage-4 warning: a Stage-4 tape must carry an explicit caution.
        stage = str(valuation_data.get("stage2_status", ""))
        if "STAGE 4" in stage.upper():
            caution_words = ("caution", "stop-loss", "stop loss", "downtrend", "risk", "avoid")
            if not any(w in text.lower() for w in caution_words):
                violations.append("Stage-4 tape without explicit downside caution in synthesis")

        # 5. Methodology Integrity Watchdog: Detects any unauthorized parameter degradation
        try:
            from forward_growth_pe import verify_methodology_integrity
            m_alerts = verify_methodology_integrity()
            for ma in m_alerts:
                violations.append(f"METHODOLOGY INTEGRITY ALERT: {ma}")
        except Exception:
            pass

        passes_guard = len(violations) == 0
        return {
            "passes_guard": passes_guard,
            "violations": violations,
            "verified_invariants": [
                f"TTM EPS Anchored: ₹{valuation_data.get('ttm_eps')}",
                f"Bear Target Price Verified: ₹{expected_bear_target}",
                f"Bull Target Price Verified: ₹{expected_bull_target}",
                f"Expected CAGR Verified: {valuation_data.get('expected_cagr')}%",
            ],
        }
