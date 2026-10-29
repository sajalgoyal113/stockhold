#!/usr/bin/env python3
"""scripts/threshold_sweep.py - EXP1: fit gate thresholds on frozen PIT packs.

Offline: recomputes gates per name-window from frozen decision packs +
calibration records under a threshold grid. Growth formula is FIXED
(targets and realized outcomes are reused as-is); only the pass/fail
gates vary. Reports precision, mean approved/rejected realized return,
and approval spread per combo. Saves scripts/threshold_sweep.json.
"""

import os
import sys
import json
import itertools

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from investable_execution import decide_growth, uniform_targets  # noqa: E402

VINT_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data", "vintages")


def main():
    cal = json.load(open(os.path.join(_SCRIPT_DIR, "pit_calibration.json")))
    packs = {}
    for w in ("W1_FY23", "W2_FY21"):
        p = os.path.join(VINT_DIR, f"decisions_{w}.json")
        packs[w] = json.load(open(p)) if os.path.isfile(p) else {}
    recs = cal["records"]
    grid = {
        "growth_t": [15.0, 18.0, 20.0, 22.0],
        "pe_t": [40.0, 50.0, 60.0],
        "upside_t": [40.0, 50.0, 60.0],
        "stage2": [True, False],
        "forensic": [True, False],
    }
    rows = []
    for g_t, pe_t, u_t, st2, fo in itertools.product(
            grid["growth_t"], grid["pe_t"], grid["upside_t"],
            grid["stage2"], grid["forensic"]):
        appr, rej = [], []
        for r in recs:
            fr = packs.get(r["window"], {}).get(r["ticker"])
            if not fr:
                continue
            mg, bg = decide_growth(r["sales_3y"], r.get("sales_1y"))
            fwd, _, up = uniform_targets(fr["eps"], fr["p0"], mg, bg)
            if fwd == float("inf"):
                fwd = fr["p0"] / fr["eps"] if fr["eps"] > 0 else 1e9
            cfo = sum(fr.get("cfo", []))
            pat = sum(fr.get("pat", []))
            cfo_pat = cfo / pat if pat > 0 else 0.50
            ok = (mg >= g_t and fwd < pe_t and up >= u_t
                  and ((fr["p0"] >= fr["dma200_0"]) if (st2 and fr["dma200_0"] > 0) else True)
                  and ((cfo_pat >= 0.35 or r["sales_3y"] >= 25.0) if fo else True))
            (appr if ok else rej).append(r["realized_return"])
        n = len(appr)
        hit = sum(1 for x in appr if x > 0) / n * 100 if n else 0.0
        ma = sum(appr) / n if n else 0.0
        mr = sum(rej) / len(rej) if rej else 0.0
        rows.append({"g": g_t, "pe": pe_t, "up": u_t, "stage2": st2, "fo": fo,
                     "n": n, "hit": round(hit, 1), "mean_appr": round(ma, 1),
                     "mean_rej": round(mr, 1), "spread": round(ma - mr, 1)})
    rows.sort(key=lambda r: r["spread"], reverse=True)
    print("TOP 15 by approval spread (approved minus rejected mean, n>=8):")
    shown = 0
    for r in rows:
        if r["n"] >= 8 and shown < 15:
            print(f" g>={r['g']:.0f} pe<{r['pe']:.0f} up>={r['up']:.0f} "
                  f"st2={int(r['stage2'])} fo={int(r['fo'])} | n={r['n']:3} "
                  f"hit={r['hit']:5.1f}% appr={r['mean_appr']:+7.1f}% "
                  f"rej={r['mean_rej']:+7.1f}% spread={r['spread']:+7.1f}%")
            shown += 1
    cur = next(r for r in rows if r["g"] == 20 and r["pe"] == 50
               and r["up"] == 50 and r["stage2"] and r["fo"])
    print(f"\nCURRENT (20/50/50+st2+fo): n={cur['n']} hit={cur['hit']}% "
          f"appr={cur['mean_appr']:+.1f}% rej={cur['mean_rej']:+.1f}% "
          f"spread={cur['spread']:+.1f}%")
    json.dump({"combos": rows, "current": cur},
              open(os.path.join(_SCRIPT_DIR, "threshold_sweep.json"), "w"), indent=1)
    print("Saved scripts/threshold_sweep.json")


if __name__ == "__main__":
    main()
