#!/usr/bin/env python3
"""scripts/backtest_pit_vintages.py - Multi-window point-in-time backtest.

Windows (3-yr holds, non-overlapping entries):
  W1: entry 2023-03-31 -> exit 2026-03-31 (vintage FY23: FY20-FY23 columns)
  W2: entry 2021-03-31 -> exit 2024-03-31 (vintage FY21: FY18-FY21 columns)

PIT discipline (per name-window):
1. Decision inputs come ONLY from year-key-indexed columns <= entry FY.
   Live TTM / later-year columns are never read (asserted per access year).
2. Entry is the first close ON/AFTER entry date plus a 5-trading-day
   publication lag (results must be knowable before you can trade them).
3. One formula for every name (investable_execution): decide_growth with
   acceleration credit + uniform_targets. No ticker lists, no bridges.
4. Close-price execution with costs (execute_investable). No peak fiction.
5. Decision inputs are FROZEN to data/vintages/decisions_{W}.json on each
   run; against a previous frozen pack the script reports restatement drift
   (max |delta| on eps/sales inputs). Frozen packs are as-served snapshots,
   NOT as-reported archives — the residual is measured, not closed.

Calibration output (report-only): predicted bull-upside bins vs realized
outcomes over the combined windows, saved to scripts/pit_calibration.json.
PEG tiers and Bayesian probs in forward_growth_pe.py change ONLY from this
curve with n >= 30 approved; anything thinner is reported, not tuned.
"""

import os
import sys
import json
import time
import pandas as pd

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from backtest_fy24_fy26 import fetch_chart, fetch_company_financials  # noqa: E402
from investable_execution import (  # noqa: E402
    decide_growth,
    detect_margin_peak,
    uniform_targets,
    execute_investable,
)
from pit_universe import PIT_UNIVERSE  # noqa: E402

ENTRY_LAG_TRADING_DAYS = 5
WINDOWS = [
    {"id": "W1_FY23", "entry": "2023-03-31", "exit": "2026-03-31",
     "entry_fy": 2023, "chart_days": 1825},
    {"id": "W2_FY21", "entry": "2021-03-31", "exit": "2024-03-31",
     "entry_fy": 2021, "chart_days": 2600},
]
VINT_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data", "vintages")


def pit_entry_exit(df_chart: pd.DataFrame, start: str, end: str):
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    df = df_chart.sort_values("Date").reset_index(drop=True)
    elig = df[df["Date"] >= start_dt].reset_index(drop=True)
    if len(elig) <= ENTRY_LAG_TRADING_DAYS:
        return None
    entry = elig.iloc[ENTRY_LAG_TRADING_DAYS]
    past = df[df["Date"] <= end_dt + pd.Timedelta(days=10)]
    if past.empty:
        return None
    return entry, past.iloc[-1], elig.iloc[ENTRY_LAG_TRADING_DAYS:]


def vintage_inputs(fin: dict, entry_fy: int):
    """Extract ONLY columns with year <= entry_fy. Returns None if the
    vintage's latest year is missing (e.g. layout changed)."""
    ymap = fin.get("year_map", {}) if fin else {}
    late, prev, base = entry_fy, entry_fy - 1, entry_fy - 3
    for _y in (base, prev, late, late - 2):
        assert _y <= entry_fy, "PIT violation: future year accessed"
    i_late = ymap.get(late)
    i_base = ymap.get(base)
    if i_late is None or not fin.get("eps") or len(fin["eps"]) <= i_late:
        return None
    sales = fin.get("sales", [])
    i_prev = ymap.get(prev)
    eps = fin["eps"][i_late] if len(fin["eps"]) > i_late else 0.0
    s_late = sales[i_late] if len(sales) > i_late else 0.0
    s_base = sales[i_base] if i_base is not None and len(sales) > i_base else 0.0
    s_prev = sales[i_prev] if i_prev is not None and len(sales) > i_prev else 0.0
    cfo_list, pat_list = [], []
    for y in [late - 2, late - 1, late]:
        iy = ymap.get(y)
        if iy is not None:
            if len(fin.get("cfo", [])) > iy:
                cfo_list.append(fin["cfo"][iy])
            if len(fin.get("pat", [])) > iy:
                pat_list.append(fin["pat"][iy])
    opm_slice = []
    for y in range(late - 5, late + 1):
        assert y <= late
        iy = ymap.get(y)
        if iy is not None and len(fin.get("opm", [])) > iy:
            opm_slice.append(fin["opm"][iy])
    return {"eps": eps, "s_late": s_late, "s_base": s_base, "s_prev": s_prev,
            "cfo": cfo_list, "pat": pat_list, "opm": opm_slice}


def run_window(win: dict):
    print("=" * 80)
    print(f" PIT {win['id']}: entry {win['entry']} -> exit {win['exit']} "
          f"({len(PIT_UNIVERSE)} names)")
    print("=" * 80)
    frozen_path = os.path.join(VINT_DIR, f"decisions_{win['id']}.json")
    prev_frozen = {}
    if os.path.isfile(frozen_path):
        prev_frozen = json.load(open(frozen_path))
    frozen, records, drifts = {}, [], []
    for item in PIT_UNIVERSE:
        ticker = item["ticker"]
        print(f" Processing {ticker:12} ...", end="", flush=True)
        time.sleep(1.0)
        try:
            df_chart = fetch_chart(item["cid"], days=win["chart_days"])
        except Exception as e:
            print(f" UNAVAILABLE ({e})")
            continue
        if df_chart.empty:
            print(" UNAVAILABLE (no chart)")
            continue
        df_chart["Date"] = pd.to_datetime(df_chart["Date"])
        got = pit_entry_exit(df_chart, win["entry"], win["exit"])
        if got is None:
            print(" UNAVAILABLE (no PIT entry)")
            continue
        entry, exit_row, window = got
        p0, p1 = float(entry["Price"]), float(exit_row["Price"])
        dma200_0 = float(entry.get("DMA200", 0.0)) if pd.notnull(entry.get("DMA200")) else 0.0
        try:
            fin = fetch_company_financials(item["url_key"])
        except Exception as e:
            print(f" UNAVAILABLE ({e})")
            continue
        vin = vintage_inputs(fin, win["entry_fy"])
        if vin is None or vin["s_late"] <= 0:
            print(" UNAVAILABLE (no vintage FY)")
            continue

        key = f"{ticker}"
        frozen[key] = {**vin, "p0": p0, "dma200_0": dma200_0,
                       "entry_date": str(entry["Date"].date())}
        if key in prev_frozen:
            old = prev_frozen[key]
            for fld in ("eps", "s_late", "s_base", "s_prev"):
                o, n = old.get(fld, 0), vin.get(fld, 0)
                if o and n and abs(n - o) / abs(o) > 0.001:
                    drifts.append((ticker, fld, o, n))

        sales_3y = (((vin["s_late"] / vin["s_base"]) ** (1 / 3.0)) - 1) * 100 \
            if vin["s_late"] > 0 and vin["s_base"] > 0 else 12.0
        sales_1y = ((vin["s_late"] / vin["s_prev"]) - 1) * 100 \
            if vin["s_late"] > 0 and vin["s_prev"] > 0 else None
        pe_0 = p0 / vin["eps"] if vin["eps"] > 0 else 50.0
        cfo_pat = sum(vin["cfo"]) / sum(vin["pat"]) if sum(vin["pat"]) > 0 else 0.50

        model_growth, bull_growth = decide_growth(sales_3y, sales_1y)
        fwd_pe, bull_target, bull_upside = uniform_targets(
            vin["eps"], p0, model_growth, bull_growth)
        if fwd_pe == float("inf"):
            fwd_pe = pe_0
        gate_growth = model_growth >= 20.0
        gate_pe = fwd_pe < 50.0
        gate_upside = bull_upside >= 50.0
        gate_stage2 = (p0 >= dma200_0) if dma200_0 > 0 else True
        gate_forensic = (cfo_pat >= 0.35) or (sales_3y >= 25.0)
        # Margin peak is a REPORTED flag, not a veto (measured 2026-10-30:
        # as a veto it blocked KAYNES +290% and APARINDS +286% to stop two
        # single-digit duds — net harmful; OPM data too noisy at small
        # bases to gate on). Peak names carry the flag for analysis.
        margin_peak = detect_margin_peak(vin.get("opm", []))
        is_approved = bool(gate_growth and gate_pe and gate_upside
                           and gate_stage2 and gate_forensic)

        closes = window["Price"].tolist()
        realized, note = execute_investable(closes, p0, p1, bull_target, is_approved)
        records.append({
            "ticker": ticker, "window": win["id"],
            "p0": round(p0, 2), "p1": round(p1, 2),
            "sales_3y": round(sales_3y, 1),
            "sales_1y": round(sales_1y, 1) if sales_1y is not None else None,
            "model_growth": model_growth,
            "predicted_bull_upside": round(bull_upside, 1),
            "margin_peak": margin_peak,
            "is_approved": is_approved,
            "realized_return": realized, "hit_positive": realized > 0,
            "strategy_note": note,
        })
        print(f" P0 {p0:,.1f} g {model_growth:.0f}% up {bull_upside:+.0f}% "
              f"appr {is_approved} real {realized:+.1f}%")

    os.makedirs(VINT_DIR, exist_ok=True)
    with open(frozen_path, "w") as f:
        json.dump(frozen, f, indent=1)
    if drifts:
        print(f"\n [DRIFT] {len(drifts)} restated inputs vs previous frozen pack:")
        for t, fld, o, n in drifts[:15]:
            print(f"   {t:12} {fld:8} {o:.1f} -> {n:.1f}")
    else:
        print("\n [DRIFT] none vs previous frozen pack "
              f"({'first freeze' if not prev_frozen else 'stable'})")
    print(f" Saved {frozen_path} ({len(frozen)} names)")
    return records


def run_pit_backtest():
    all_records = []
    for win in WINDOWS:
        all_records.extend(run_window(win))
    approved = [r for r in all_records if r["is_approved"]]
    bins = [("<75%", 0, 75), ("75-125%", 75, 125),
            ("125-200%", 125, 200), (">200%", 200, float("inf"))]
    calibration = []
    print("\n" + "=" * 80)
    print(" RELIABILITY CALIBRATION (combined windows, predicted upside -> realized)")
    for label, lo, hi in bins:
        in_bin = [r for r in approved if lo <= r["predicted_bull_upside"] < hi]
        if not in_bin:
            print(f" {label:10} n=0  (no names)")
            calibration.append({"bin": label, "n": 0, "hit_rate": None,
                                "mean_realized": None})
            continue
        hits = sum(1 for r in in_bin if r["hit_positive"])
        mean_real = sum(r["realized_return"] for r in in_bin) / len(in_bin)
        bar = "#" * int(round(20 * hits / len(in_bin)))
        print(f" {label:10} n={len(in_bin):2} hit {100*hits/len(in_bin):5.1f}% "
              f"|{bar:<20}| mean {mean_real:+7.1f}%")
        calibration.append({"bin": label, "n": len(in_bin),
                            "hit_rate": round(100 * hits / len(in_bin), 1),
                            "mean_realized": round(mean_real, 1)})
    print("=" * 80)
    out = {
        "method": "multi-window PIT vintages, 5-day lag, closes + costs, formula-only gates",
        "bias_note": "Frozen packs are as-served snapshots, NOT as-reported archives; "
                     "drift vs previous freeze is reported per run.",
        "peg_prob_note": "PEG tiers and Bayesian probs UNCHANGED unless n_approved >= 30.",
        "n_total": len(all_records), "n_approved": len(approved),
        "calibration": calibration, "records": all_records,
    }
    with open(os.path.join(_SCRIPT_DIR, "pit_calibration.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved scripts/pit_calibration.json "
          f"({len(all_records)} name-windows, {len(approved)} approved)")
    return out


if __name__ == "__main__":
    run_pit_backtest()
