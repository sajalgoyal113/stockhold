#!/usr/bin/env python3
"""scripts/guidance_scorer.py - EXP2: guided-growth vs formula-growth scorer.

Compares production-path predictions (guidance-registry growth) against
backtest-path predictions (formula growth) on frozen PIT packs.

Registry entries with vintage support live in data/guidance_registry.json:
  {"TICKER": {"vintages": {"2023-03-31": {"base_cagr": 25.0, "bull_cagr": 32.0,
    "source": "<filing/call, page>", "as_of": "2023-02-14"}},
    "notes": "..."}}

Rules: entries MUST carry source + as_of at or before the vintage entry
date; anything later is lookahead and is rejected loudly. With zero
entries the script reports coverage and exits — it never fabricates
guidance. This keeps the production path (user-supplied growth) finally
measurable instead of taken on faith.
"""

import os
import sys
import json

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from investable_execution import uniform_targets  # noqa: E402

VINT_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data", "vintages")
WIN_ENTRY = {"W1_FY23": "2023-03-31", "W2_FY21": "2021-03-31"}


def main():
    cal = json.load(open(os.path.join(_SCRIPT_DIR, "pit_calibration.json")))
    reg = json.load(open(os.path.join(os.path.dirname(_SCRIPT_DIR), "data",
                                      "guidance_registry.json")))
    recs = {(r["window"], r["ticker"]): r for r in cal["records"]}
    packs = {}
    for w in WIN_ENTRY:
        p = os.path.join(VINT_DIR, f"decisions_{w}.json")
        packs[w] = json.load(open(p)) if os.path.isfile(p) else {}
    scored, guided_wins, formula_wins = 0, 0, []
    for ticker, entry in reg.items():
        if ticker.startswith("_"):
            continue
        for w, entry_date in WIN_ENTRY.items():
            vint = (entry.get("vintages") or {}).get(entry_date)
            r = recs.get((w, ticker))
            fr = packs.get(w, {}).get(ticker)
            if not vint or not r or not fr:
                continue
            if vint.get("as_of", "9") > entry_date:
                print(f" LOOKAHEAD REJECTED: {ticker} {w} as_of {vint.get('as_of')}")
                continue
            gb, gu = float(vint["base_cagr"]), float(vint.get("bull_cagr", vint["base_cagr"] + 6))
            _, _, gup = uniform_targets(fr["eps"], fr["p0"], gb, gu)
            fup = r["predicted_bull_upside"]
            real = r["realized_return"]
            scored += 1
            gerr, ferr = abs(gup - real), abs(fup - real)
            winner = "GUIDED" if gerr < ferr else "FORMULA"
            if winner == "GUIDED":
                guided_wins += 1
            else:
                formula_wins.append(f"{ticker} {w}")
            print(f" {ticker} {w}: guided_up={gup:+.0f}% formula_up={fup:+.0f}% "
                  f"real={real:+.1f}% -> {winner} "
                  f"(src: {vint.get('source', '?')})")
    print(f"\nScored {scored} vintage-guidance pairs: guided better {guided_wins}, "
          f"formula better {len(formula_wins)}")
    if scored == 0:
        print("No dated registry entries yet. Add source+as_of vintages to "
              "data/guidance_registry.json (never backfill from outcomes).")
    json.dump({"scored": scored, "guided_wins": guided_wins,
               "formula_wins": formula_wins},
              open(os.path.join(_SCRIPT_DIR, "guidance_score.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
