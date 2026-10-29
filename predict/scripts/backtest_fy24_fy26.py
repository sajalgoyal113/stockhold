#!/usr/bin/env python3
"""
predict/scripts/backtest_fy24_fy26.py - FY24 to FY26 Cross-Sectional Backtest Engine

Cross-Sectional Sample (20 Stocks):
- 5 Large Cap:  TRENT, HAL, POLYCAB, TITAN, ASIANPAINT
- 5 Mid Cap:    DIXON, KAYNES, PERSISTENT, CLEAN, PAGEIND
- 10 Small Cap: NEWGEN, GRAVITA, APARINDS, HBLENGINE, RATEGAIN, SJS, MAPMYINDIA, AHLUCONT, TANLA, IEX

Holding Period:
- Start Date: March 31, 2023 (FY23 base / Start of FY24)
- End Date:   March 31, 2026 (Full 3-Year Compounding Window)
"""

import os
import sys
import re
import json
import time
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from investable_execution import decide_growth, uniform_targets, execute_investable

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

UNIVERSE = [
    # 5 Large Cap
    {"ticker": "TRENT", "name": "Trent Ltd", "cat": "Large Cap", "sector": "Fashion Retail", "cid": 3467, "url_key": "TRENT", "is_turnaround": True},
    {"ticker": "HAL", "name": "Hindustan Aeronautics", "cat": "Large Cap", "sector": "Defense Aerospace", "cid": 1274307, "url_key": "HAL", "is_turnaround": False},
    {"ticker": "POLYCAB", "name": "Polycab India", "cat": "Large Cap", "sector": "Cables & Infra", "cid": 1274653, "url_key": "POLYCAB", "is_turnaround": False},
    {"ticker": "TITAN", "name": "Titan Company", "cat": "Large Cap", "sector": "Consumer Discretionary", "cid": 3437, "url_key": "TITAN", "is_turnaround": False},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "cat": "Large Cap", "sector": "Decorative Paints (Trap)", "cid": 295, "url_key": "ASIANPAINT", "is_turnaround": False},

    # 5 Mid Cap
    {"ticker": "DIXON", "name": "Dixon Technologies", "cat": "Mid Cap", "sector": "EMS & Mobile PLI", "cid": 1274137, "url_key": "DIXON", "is_turnaround": False},
    {"ticker": "KAYNES", "name": "Kaynes Technology", "cat": "Mid Cap", "sector": "Semiconductors & EMS", "cid": 1275358, "url_key": "KAYNES", "is_turnaround": False},
    {"ticker": "PERSISTENT", "name": "Persistent Systems", "cat": "Mid Cap", "sector": "Digital Engineering", "cid": 2458, "url_key": "PERSISTENT", "is_turnaround": False},
    {"ticker": "CLEAN", "name": "Clean Science & Tech", "cat": "Mid Cap", "sector": "Specialty Chemicals (Trap)", "cid": 1274890, "url_key": "CLEAN", "is_turnaround": False},
    {"ticker": "PAGEIND", "name": "Page Industries", "cat": "Mid Cap", "sector": "Apparel Retail (Trap)", "cid": 2389, "url_key": "PAGEIND", "is_turnaround": False},

    # 10 Small Cap
    {"ticker": "NEWGEN", "name": "Newgen Software", "cat": "Small Cap", "sector": "Enterprise SaaS", "cid": 1274251, "url_key": "NEWGEN", "is_turnaround": False},
    {"ticker": "GRAVITA", "name": "Gravita India", "cat": "Small Cap", "sector": "Circular Economy / Recycling", "cid": 1202, "url_key": "GRAVITA", "is_turnaround": False},
    {"ticker": "APARINDS", "name": "Apar Industries", "cat": "Small Cap", "sector": "Conductors & Specialty Oils", "cid": 211, "url_key": "APARINDS", "is_turnaround": False},
    {"ticker": "HBLENGINE", "name": "HBL Engineering (Power)", "cat": "Small Cap", "sector": "Kavach Rail & Batteries", "cid": 1295, "url_key": "HBLENGINE", "is_turnaround": False},
    {"ticker": "RATEGAIN", "name": "RateGain Travel Tech", "cat": "Small Cap", "sector": "Travel Tech SaaS", "cid": 1275119, "url_key": "RATEGAIN", "is_turnaround": False},
    {"ticker": "SJS", "name": "SJS Enterprises", "cat": "Small Cap", "sector": "Automotive Aesthetics", "cid": 1275092, "url_key": "SJS", "is_turnaround": False},
    {"ticker": "MAPMYINDIA", "name": "C.E. Info Systems", "cat": "Small Cap", "sector": "B2B Digital Maps", "cid": 1275122, "url_key": "MAPMYINDIA", "is_turnaround": False},
    {"ticker": "AHLUCONT", "name": "Ahluwalia Contracts", "cat": "Small Cap", "sector": "Institutional EPC", "cid": 96, "url_key": "AHLUCONT", "is_turnaround": False},
    {"ticker": "TANLA", "name": "Tanla Platforms", "cat": "Small Cap", "sector": "CPaaS (Growth Torpedo Trap)", "cid": 3355, "url_key": "TANLA", "is_turnaround": False},
    {"ticker": "IEX", "name": "Indian Energy Exchange", "cat": "Small Cap", "sector": "Power Exchange (Regulatory Trap)", "cid": 1274182, "url_key": "IEX", "is_turnaround": False}
]

BENCHMARKS = [
    {"ticker": "NIFTY", "name": "NIFTY 50", "cid": 1272594},
    {"ticker": "NMIDCAP100", "name": "NIFTY Midcap 100", "cid": 1272674}
]

def clean_num(val_str):
    if not val_str:
        return 0.0
    cleaned = re.sub(r"[^\d.-]", "", str(val_str))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def fetch_chart(cid: int, days: int = 1825) -> pd.DataFrame:
    try:
        url = f"https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200&days={days}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            data = r.json()
            datasets = data.get("datasets", [])
            df_price = pd.DataFrame()
            for ds in datasets:
                metric = ds.get("metric", "")
                vals = ds.get("values", [])
                if "Price" in metric or not metric:
                    temp = pd.DataFrame(vals, columns=["Date", "Price"])
                    temp["Date"] = pd.to_datetime(temp["Date"])
                    temp["Price"] = pd.to_numeric(temp["Price"], errors="coerce")
                    if df_price.empty:
                        df_price = temp
                    else:
                        df_price["Price"] = temp["Price"]
                elif "DMA50" in metric:
                    temp = pd.DataFrame(vals, columns=["Date", "DMA50"])
                    temp["Date"] = pd.to_datetime(temp["Date"])
                    temp["DMA50"] = pd.to_numeric(temp["DMA50"], errors="coerce")
                    df_price = pd.merge(df_price, temp, on="Date", how="left")
                elif "DMA200" in metric:
                    temp = pd.DataFrame(vals, columns=["Date", "DMA200"])
                    temp["Date"] = pd.to_datetime(temp["Date"])
                    temp["DMA200"] = pd.to_numeric(temp["DMA200"], errors="coerce")
                    df_price = pd.merge(df_price, temp, on="Date", how="left")
            return df_price
    except Exception as e:
        print(f"Error fetching chart for cid {cid}: {e}")
    return pd.DataFrame()

def fetch_company_financials(ticker: str) -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)
    urls = [
        f"https://www.screener.in/company/{ticker}/consolidated/",
        f"https://www.screener.in/company/{ticker}/"
    ]
    html = None
    for u in urls:
        try:
            r = session.get(u, timeout=10)
            if r.status_code == 200:
                html = r.text
                break
        except Exception:
            continue
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    def get_row(sec_id, pattern):
        sec = soup.find("section", id=sec_id)
        if not sec:
            return []
        table = sec.find("table")
        if not table:
            return []
        for tr in table.find("tbody").find_all("tr"):
            tds = tr.find_all("td")
            if tds and pattern.lower() in tds[0].text.lower():
                return [clean_num(td.text) for td in tds[1:]]
        return []

    pl_sec = soup.find("section", id="profit-loss")
    pl_headers = []
    if pl_sec and pl_sec.find("table") and pl_sec.find("table").find("thead"):
        pl_headers = [th.text.strip() for th in pl_sec.find("table").find("thead").find_all("th")[1:]]

    year_map = {}
    for idx, h in enumerate(pl_headers):
        m = re.search(r"(\d{4})", str(h))
        if m:
            year_map[int(m.group(1))] = idx

    return {
        "sales": get_row("profit-loss", "sales"),
        "pat": get_row("profit-loss", "net profit"),
        "eps": get_row("profit-loss", "eps"),
        "opm": get_row("profit-loss", "opm"),
        "cfo": get_row("cash-flow", "operating activity"),
        "year_map": year_map
    }

def run_backtest():
    print("=" * 80)
    print(" PREDICT MODEL BACKTEST ENGINE: FY24 to FY26 (20 Stocks Cross-Section)")
    print(" Period: March 31, 2023 -> March 31, 2026 (Full 3-Year Compounding Window)")
    print(" Universe: 5 Large Cap | 5 Mid Cap | 10 Small Cap")
    print("=" * 80)

    # 1. Fetch Benchmarks
    print("\n[1/4] Fetching Benchmark Returns...")
    bench_data = {}
    start_dt = pd.to_datetime("2023-03-31")
    end_dt = pd.to_datetime("2026-03-31")

    for b in BENCHMARKS:
        time.sleep(1.0)
        df = fetch_chart(b["cid"])
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"])
            df_sorted = df.sort_values("Date")
            p0_series = df_sorted[df_sorted["Date"] <= start_dt + pd.Timedelta(days=10)]
            p1_series = df_sorted[df_sorted["Date"] <= end_dt + pd.Timedelta(days=10)]
            if not p0_series.empty and not p1_series.empty:
                p0 = p0_series.iloc[-1]["Price"]
                p1 = p1_series.iloc[-1]["Price"]
                ret = ((p1 - p0) / p0) * 100
                cagr = (((p1 / p0) ** (1/3.0)) - 1) * 100
                bench_data[b["ticker"]] = {"name": b["name"], "p0": p0, "p1": p1, "return": ret, "cagr": cagr}
                print(f" -> {b['name']:16}: P0: {p0:.1f} | P1: {p1:.1f} | Return: {ret:+.1f}% | CAGR: {cagr:+.1f}%")

    # 2. Process Universe
    print("\n[2/4] Evaluating Point-in-Time Fundamentals at Start of FY24 (March 2023)...")
    records = []

    for item in UNIVERSE:
        ticker = item["ticker"]
        name = item["name"]
        cat = item["cat"]
        sector = item["sector"]
        cid = item["cid"]
        is_turnaround = item.get("is_turnaround", False)

        print(f" Processing {ticker:10} ({cat:9})...", end="", flush=True)
        time.sleep(1.2)

        # A. Fetch historical price chart
        df_chart = fetch_chart(cid)
        if df_chart.empty:
            print(" ❌ No chart data")
            continue

        df_chart["Date"] = pd.to_datetime(df_chart["Date"])
        df_chart = df_chart.sort_values("Date")

        sub_p0 = df_chart[df_chart["Date"] <= start_dt + pd.Timedelta(days=10)]
        sub_p1 = df_chart[df_chart["Date"] <= end_dt + pd.Timedelta(days=10)]

        if sub_p0.empty or sub_p1.empty:
            print(" ❌ Missing dates")
            continue

        p0_row = sub_p0.iloc[-1]
        p1_row = sub_p1.iloc[-1]
        p0 = float(p0_row["Price"])
        p1 = float(p1_row["Price"])
        dma200_0 = float(p0_row.get("DMA200", 0.0)) if pd.notnull(p0_row.get("DMA200")) else 0.0

        # Sub-period trajectory for drawdown and peak
        traj = df_chart[(df_chart["Date"] >= p0_row["Date"]) & (df_chart["Date"] <= p1_row["Date"])]
        peak_price = float(traj["Price"].max()) if not traj.empty else p0
        peak_gain = ((peak_price - p0) / p0) * 100

        # Max drawdown
        if not traj.empty:
            cummax = traj["Price"].cummax()
            dd = ((traj["Price"] - cummax) / cummax) * 100
            max_dd = float(dd.min())
        else:
            max_dd = 0.0

        # B. Fetch historical P&L for point-in-time FY23 numbers
        fin = fetch_company_financials(item["url_key"])
        ymap = fin.get("year_map", {})
        idx_23 = ymap.get(2023)
        idx_20 = ymap.get(2020)

        eps_23 = fin["eps"][idx_23] if idx_23 is not None and len(fin["eps"]) > idx_23 else (p0 / 40.0)
        sales_23 = fin["sales"][idx_23] if idx_23 is not None and len(fin["sales"]) > idx_23 else 0.0
        sales_20 = fin["sales"][idx_20] if idx_20 is not None and len(fin["sales"]) > idx_20 else 0.0
        idx_22 = ymap.get(2022)
        sales_22 = fin["sales"][idx_22] if idx_22 is not None and len(fin["sales"]) > idx_22 else 0.0
        sales_1y = ((sales_23 / sales_22) - 1) * 100 if sales_23 > 0 and sales_22 > 0 else None

        # 3-Yr Sales CAGR up to FY23
        sales_cagr_3y = (((sales_23 / sales_20) ** (1/3.0)) - 1) * 100 if sales_23 > 0 and sales_20 > 0 else 15.0

        # Point-in-time trailing P/E at start of FY24
        pe_0 = p0 / eps_23 if eps_23 > 0 else 50.0

        # Point-in-time CFO/PAT over 3 years (FY21, FY22, FY23)
        cfo_list = []
        pat_list = []
        for y in [2021, 2022, 2023]:
            iy = ymap.get(y)
            if iy is not None:
                if len(fin["cfo"]) > iy: cfo_list.append(fin["cfo"][iy])
                if len(fin["pat"]) > iy: pat_list.append(fin["pat"][iy])
        cfo_pat_3y = sum(cfo_list) / sum(pat_list) if sum(pat_list) > 0 else 0.50

        # C. Investable quantitative gates (no ticker lists, no turnaround
        # bridge, one uniform target formula — see investable_execution.py).
        # NOTE: `is_turnaround` in UNIVERSE is retained for documentation
        # only and plays no role in decisions.
        model_growth, bull_growth = decide_growth(sales_cagr_3y, sales_1y)
        gate_growth = model_growth >= 20.0

        fwd_pe_yr2, bull_target_price, bull_upside_pct = uniform_targets(
            eps_23, p0, model_growth, bull_growth)
        if fwd_pe_yr2 == float("inf"):
            fwd_pe_yr2 = pe_0
        gate_pe = fwd_pe_yr2 < 50.0
        gate_upside = bull_upside_pct >= 50.0

        # 4. Minervini Stage 2 Confirmation at entry (CMP > 200-DMA)
        gate_stage2 = (p0 >= dma200_0) if dma200_0 > 0 else True

        # 5. Forensic CFO/PAT >= 0.70 (or high-growth reinvestment)
        gate_forensic = (cfo_pat_3y >= 0.35) or (sales_cagr_3y >= 25.0)

        # Predict Model Decision
        if gate_growth and gate_pe and gate_upside and gate_stage2 and gate_forensic:
            verdict = "APPROVED (STRONG BUY)"
            is_approved = True
        elif gate_growth and gate_pe and gate_upside:
            verdict = "APPROVED (QUALIFIED BUY)"
            is_approved = True
        elif not gate_growth:
            verdict = "REJECTED (LOW GROWTH / STALLING)"
            is_approved = False
        elif not gate_pe:
            verdict = "REJECTED (VALUATION TRAP / PE > 50x)"
            is_approved = False
        else:
            verdict = "REJECTED (FAILED MOAT / RISK)"
            is_approved = False

        # Investable execution on CLOSES with costs (no peak-harvest fiction).
        bh_return = ((p1 - p0) / p0) * 100
        bh_cagr = (((p1 / p0) ** (1/3.0)) - 1) * 100
        closes = traj["Price"].tolist() if not traj.empty else [p0, p1]
        realized_return, strategy_note = execute_investable(
            closes, p0, p1, bull_target_price, is_approved)

        realized_cagr = (((1.0 + (realized_return / 100.0)) ** (1/3.0)) - 1) * 100 if realized_return > -100 else -100

        records.append({
            "ticker": ticker,
            "name": name,
            "cat": cat,
            "sector": sector,
            "p0": round(p0, 2),
            "p1": round(p1, 2),
            "pe_0": round(pe_0, 1),
            "fwd_pe_yr2": round(fwd_pe_yr2, 1),
            "sales_cagr_3y": round(sales_cagr_3y, 1),
            "sales_1y": round(sales_1y, 1) if sales_1y is not None else None,
            "model_growth": model_growth,
            "bull_growth": bull_growth,
            "cfo_pat_3y": round(cfo_pat_3y, 2),
            "verdict": verdict,
            "is_approved": is_approved,
            "bh_return": round(bh_return, 1),
            "bh_cagr": round(bh_cagr, 1),
            "peak_gain": round(peak_gain, 1),
            "max_dd": round(max_dd, 1),
            "realized_return": round(realized_return, 1),
            "realized_cagr": round(realized_cagr, 1),
            "strategy_note": strategy_note
        })
        print(f" -> P0: ₹{p0:,.1f} | P1: ₹{p1:,.1f} | Return: {bh_return:>+6.1f}% | Verdict: {verdict}")

    # 3. Aggregate Performance Analytics
    df_res = pd.DataFrame(records)

    app_df = df_res[df_res["is_approved"] == True]
    rej_df = df_res[df_res["is_approved"] == False]

    nifty_3y = bench_data.get("NIFTY", {}).get("return", 36.7)
    midcap_3y = bench_data.get("NMIDCAP100", {}).get("return", 90.6)

    app_bh_ret = app_df["bh_return"].mean() if not app_df.empty else 0.0
    app_real_ret = app_df["realized_return"].mean() if not app_df.empty else 0.0
    app_cagr = app_df["realized_cagr"].mean() if not app_df.empty else 0.0
    rej_ret = rej_df["bh_return"].mean() if not rej_df.empty else 0.0

    win_rate = (len(app_df[app_df["realized_return"] > 0]) / len(app_df) * 100) if not app_df.empty else 0.0
    alpha_nifty = app_real_ret - nifty_3y
    alpha_midcap = app_real_ret - midcap_3y

    # Segment breakdowns
    large_app = app_df[app_df["cat"] == "Large Cap"]
    mid_app = app_df[app_df["cat"] == "Mid Cap"]
    small_app = app_df[app_df["cat"] == "Small Cap"]

    print("\n" + "=" * 80)
    print(" BACKTEST SUMMARY: FY24 to FY26 (3-Year Cycle)")
    print("=" * 80)
    print(f" Total Stocks Tested:               {len(df_res)} (5 Large | 5 Mid | 10 Small)")
    print(f" Model Approved Stocks:             {len(app_df)} ({len(app_df)/len(df_res)*100:.0f}%)")
    print(f" Model Disqualified Stocks:         {len(rej_df)} ({len(rej_df)/len(df_res)*100:.0f}%)")
    print("--------------------------------------------------------------------------------")
    print(f" Approved Basket Realized Return:   {app_real_ret:+.1f}% (+{app_cagr:.1f}% CAGR)")
    print(f" Approved Basket Buy & Hold Return: {app_bh_ret:+.1f}%")
    print(f" Disqualified Basket Return:        {rej_ret:+.1f}%")
    print(f" NIFTY 50 Benchmark Return:         {nifty_3y:+.1f}% (+{bench_data.get('NIFTY',{}).get('cagr',11.0):.1f}% CAGR)")
    print(f" NIFTY Midcap 100 Return:           {midcap_3y:+.1f}% (+{bench_data.get('NMIDCAP100',{}).get('cagr',24.0):.1f}% CAGR)")
    print("--------------------------------------------------------------------------------")
    print(f" Alpha Generated vs NIFTY 50:       {alpha_nifty:+.1f}%")
    print(f" Alpha Generated vs Midcap 100:     {alpha_midcap:+.1f}%")
    print(f" Hit Rate / Win Rate:               {win_rate:.1f}%")
    print("--------------------------------------------------------------------------------")
    def _seg(ret_df):
        return f"{ret_df['realized_return'].mean():+.1f}%" if not ret_df.empty else "n/a (no approvals)"
    print(f" Large Cap Approved Realized Ret:   {_seg(large_app)} (Count: {len(large_app)})")
    print(f" Mid Cap Approved Realized Ret:     {_seg(mid_app)} (Count: {len(mid_app)})")
    print(f" Small Cap Approved Realized Ret:   {_seg(small_app)} (Count: {len(small_app)})")
    print("=" * 80)

    # Save outputs to JSON
    output_path = os.path.join(_SCRIPT_DIR, "backtest_fy24_fy26_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "period": "FY24 to FY26 (2023-03-31 -> 2026-03-31)",
            "benchmark_nifty": bench_data.get("NIFTY", {}),
            "benchmark_midcap": bench_data.get("NMIDCAP100", {}),
            "analytics": {
                "total_count": len(df_res),
                "approved_count": len(app_df),
                "rejected_count": len(rej_df),
                "approved_realized_return": round(app_real_ret, 1),
                "approved_realized_cagr": round(app_cagr, 1),
                "approved_bh_return": round(app_bh_ret, 1),
                "rejected_return": round(rej_ret, 1),
                "alpha_nifty": round(alpha_nifty, 1),
                "alpha_midcap": round(alpha_midcap, 1),
                "win_rate": round(win_rate, 1),
                "large_cap_realized": round(large_app['realized_return'].mean(), 1) if not large_app.empty else 0.0,
                "mid_cap_realized": round(mid_app['realized_return'].mean(), 1) if not mid_app.empty else 0.0,
                "small_cap_realized": round(small_app['realized_return'].mean(), 1) if not small_app.empty else 0.0
            },
            "records": records
        }, f, indent=2)

    print(f"\n[Artifact Saved] JSON analytics saved to: {output_path}")

if __name__ == "__main__":
    run_backtest()
