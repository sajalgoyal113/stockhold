#!/usr/bin/env python3
"""
predict/scripts/backtest_predict_model.py - Institutional Historical Backtest Engine

Backtests the Predict Forward Growth & Dynamic Exit P/E valuation framework on Indian listed equities:
- Evaluates 32 cross-sectional companies over multi-year cycles:
  * Window 1 (2021 -> 2023): Inflation, Rate Hikes & Tech/Smallcap De-rating Shock
  * Window 2 (2022 -> 2024): Domestic Capex, Defense, Electronics & Retail Supercycle
  * Window 3 (2023 -> 2025/2026): Selectivity, Operating Leverage & Market Maturation
  * Window 4 (2021 -> 2026): Full 5-Year Structural Compounding Horizon
- Reconstructs point-in-time fundamentals: Trailing EPS, 3-Yr Sales CAGR, 3-Yr CFO/PAT, Net Debt.
- Evaluates King Filter gates: Sector Vector, Forensic Hygiene, Growth >= 20%, Fwd P/E < 50x, Bull Upside >= 50%.
- Benchmarks against NIFTY 50 and NIFTY Midcap 100.
- Simulates Enhanced Model (Predict 2.0) with Trend Gate (Minervini Stage 2), Profit Harvesting, and Trailing Stops.
- Exports structured report and JSON analytics to predict/reports/ and predict/scripts/.
"""

import os
import sys
import re
import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from forward_growth_pe import KNOWN_COMPANY_PROFILES

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

UNIVERSE = [
    # Tier 1 Compounders & Sunrise Leaders
    {"ticker": "DIXON", "name": "Dixon Technologies", "sector": "EMS & Mobile PLI"},
    {"ticker": "TRENT", "name": "Trent Ltd", "sector": "Fashion Retail"},
    {"ticker": "POLYCAB", "name": "Polycab India", "sector": "Cables & Infra"},
    {"ticker": "HAL", "name": "Hindustan Aeronautics", "sector": "Defense Aviation"},
    {"ticker": "BEL", "name": "Bharat Electronics", "sector": "Defense Electronics"},
    {"ticker": "KAYNES", "name": "Kaynes Technology", "sector": "Semiconductors & EMS"},
    {"ticker": "KPITTECH", "name": "KPIT Technologies", "sector": "Automotive Software"},
    {"ticker": "PERSISTENT", "name": "Persistent Systems", "sector": "Digital Engineering"},
    {"ticker": "COFORGE", "name": "Coforge", "sector": "Enterprise IT"},
    {"ticker": "CDSL", "name": "CDSL", "sector": "Capital Markets Depository"},
    {"ticker": "TATAELXSI", "name": "Tata Elxsi", "sector": "Design & ER&D"},
    {"ticker": "NETWEB", "name": "Netweb Technologies", "sector": "AI Supercomputing"},

    # Growth / Valuation Trap & Deceleration Test Cases
    {"ticker": "CLEAN", "name": "Clean Science & Tech", "sector": "Specialty Chemicals"},
    {"ticker": "SYRMA", "name": "Syrma SGS Technology", "sector": "EMS Electronics"},
    {"ticker": "TANLA", "name": "Tanla Platforms", "sector": "CPaaS / Tech"},
    {"ticker": "PAGEIND", "name": "Page Industries", "sector": "Apparel Retail"},
    {"ticker": "BERGEPAINT", "name": "Berger Paints", "sector": "Paints & Coatings"},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "sector": "Decorative Paints"},
    {"ticker": "IEX", "name": "Indian Energy Exchange", "sector": "Power Exchange"},

    # Capex / Mid-Small Cap Sunrise
    {"ticker": "JYOTICNC", "name": "Jyoti CNC Automation", "sector": "Aerospace Machining"},
    {"ticker": "SJS", "name": "SJS Enterprises", "sector": "Automotive Aesthetics"},
    {"ticker": "MAPMYINDIA", "name": "C.E. Info Systems", "sector": "B2B Digital Maps"},
    {"ticker": "AHLUCONT", "name": "Ahluwalia Contracts", "sector": "EPC Construction"},
    {"ticker": "SAMHI", "name": "Samhi Hotels", "sector": "Hospitality Asset Owner"},
    {"ticker": "YATHARTH", "name": "Yatharth Hospital", "sector": "Healthcare Services"},
    {"ticker": "ARE&M", "name": "Amara Raja Energy", "sector": "BESS & EV Battery"},
    {"ticker": "SONACOMS", "name": "Sona BLW Precision", "sector": "EV Driveline"},

    # Turnaround / Platform Compounders
    {"ticker": "ETERNAL", "name": "Zomato / Blinkit", "sector": "Quick-Commerce"},
    {"ticker": "PAYTM", "name": "Paytm (One97)", "sector": "Fintech Payments"},
    {"ticker": "POLICYBZR", "name": "PB Fintech", "sector": "Insurtech Platform"},

    # Disqualified / Fragile Gate Test Cases
    {"ticker": "UTKARSHBNK", "name": "Utkarsh Small Finance Bank", "sector": "Banking / High Leverage"},
    {"ticker": "SUZLON", "name": "Suzlon Energy", "sector": "Wind Power Turnaround"}
]

BENCHMARKS = [
    {"ticker": "NIFTY", "cid": 1272594, "name": "NIFTY 50"},
    {"ticker": "NMIDCAP100", "cid": 1272674, "name": "NIFTY Midcap 100"}
]


def clean_num(val_str):
    if not val_str:
        return 0.0
    cleaned = re.sub(r"[^\d.-]", "", str(val_str))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def fetch_benchmark_chart(cid: int) -> pd.DataFrame:
    try:
        url = f"https://www.screener.in/api/company/{cid}/chart/?q=Price&days=1825"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            vals = r.json().get("datasets", [{}])[0].get("values", [])
            df = pd.DataFrame(vals, columns=["Date", "Price"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
            return df
    except Exception as e:
        print(f"Error fetching benchmark {cid}: {e}")
    return pd.DataFrame()


def scrape_full_company(ticker: str) -> dict:
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
        return None

    soup = BeautifulSoup(html, "html.parser")
    m = re.search(r'data-company-id=\"(\d+)\"', html) or re.search(r'/api/company/(\d+)/', html)
    cid = int(m.group(1)) if m else None

    def get_row_data(sec_id, pattern):
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

    sales_arr = get_row_data("profit-loss", "sales")
    pat_arr = get_row_data("profit-loss", "net profit")
    eps_arr = get_row_data("profit-loss", "eps")
    cfo_arr = get_row_data("cash-flow", "operating activity")
    borrowings_arr = get_row_data("balance-sheet", "borrowings")
    fixed_assets_arr = get_row_data("balance-sheet", "fixed assets")

    # Extract P&L headers
    pl_section = soup.find("section", id="profit-loss")
    pl_headers = []
    if pl_section:
        table = pl_section.find("table")
        if table and table.find("thead"):
            th_cells = table.find("thead").find_all("th")
            pl_headers = [th.text.strip() for th in th_cells[1:]]

    # Map headers to integer fiscal years
    year_map = {}
    for idx, h in enumerate(pl_headers):
        m_yr = re.search(r"(\d{4})", str(h))
        if m_yr:
            year_map[int(m_yr.group(1))] = idx

    # Fetch 5-year price chart with DMA200
    chart_df = pd.DataFrame()
    if cid:
        try:
            cr = session.get(f"https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200&days=1825", timeout=10)
            if cr.status_code == 200:
                datasets = cr.json().get("datasets", [])
                if datasets and datasets[0].get("values"):
                    chart_df = pd.DataFrame(datasets[0]["values"], columns=["Date", "Price"])
                    chart_df["Date"] = pd.to_datetime(chart_df["Date"])
                    chart_df["Price"] = pd.to_numeric(chart_df["Price"], errors="coerce")
                    for d in datasets:
                        if d.get("metric") == "DMA200":
                            dma = pd.DataFrame(d["values"], columns=["Date", "DMA200"])
                            dma["Date"] = pd.to_datetime(dma["Date"])
                            dma["DMA200"] = pd.to_numeric(dma["DMA200"], errors="coerce")
                            chart_df = pd.merge(chart_df, dma, on="Date", how="left")
        except Exception:
            pass

    return {
        "ticker": ticker,
        "cid": cid,
        "year_map": year_map,
        "sales": sales_arr,
        "pat": pat_arr,
        "eps": eps_arr,
        "cfo": cfo_arr,
        "borrowings": borrowings_arr,
        "fixed_assets": fixed_assets_arr,
        "chart_df": chart_df
    }


def get_price_data(chart_df: pd.DataFrame, target_date: str) -> tuple:
    if chart_df is None or chart_df.empty:
        return None, None
    sub = chart_df[chart_df["Date"] <= target_date]
    if sub.empty:
        return None, None
    row = sub.iloc[-1]
    p = float(row["Price"]) if pd.notnull(row["Price"]) else None
    dma = float(row["DMA200"]) if "DMA200" in row and pd.notnull(row["DMA200"]) else None
    return p, dma


def reconstruct_pit(stock_info: dict, as_of_year: int) -> dict:
    ym = stock_info["year_map"]
    if as_of_year not in ym:
        return None
    curr_i = ym[as_of_year]

    eps = stock_info["eps"][curr_i] if curr_i < len(stock_info["eps"]) else 0.0
    pat = stock_info["pat"][curr_i] if curr_i < len(stock_info["pat"]) else 0.0
    sales = stock_info["sales"][curr_i] if curr_i < len(stock_info["sales"]) else 0.0

    prev_3y = as_of_year - 3
    sales_3y_cagr = 0.0
    pat_3y_cagr = 0.0
    if prev_3y in ym:
        p_i = ym[prev_3y]
        s_prev = stock_info["sales"][p_i] if p_i < len(stock_info["sales"]) else 0.0
        p_prev = stock_info["pat"][p_i] if p_i < len(stock_info["pat"]) else 0.0
        if s_prev > 0 and sales > 0:
            sales_3y_cagr = round(((sales / s_prev) ** (1.0 / 3.0) - 1.0) * 100, 1)
        if p_prev > 0 and pat > 0:
            pat_3y_cagr = round(((pat / p_prev) ** (1.0 / 3.0) - 1.0) * 100, 1)

    cum_cfo = 0.0
    cum_pat = 0.0
    for y in range(as_of_year - 2, as_of_year + 1):
        if y in ym:
            idx = ym[y]
            if idx < len(stock_info["cfo"]):
                cum_cfo += stock_info["cfo"][idx]
            if idx < len(stock_info["pat"]):
                cum_pat += stock_info["pat"][idx]
    cfo_pat = round(cum_cfo / cum_pat, 2) if cum_pat > 0 else 0.0

    debt = stock_info["borrowings"][curr_i] if curr_i < len(stock_info["borrowings"]) else 0.0
    fa = stock_info["fixed_assets"][curr_i] if curr_i < len(stock_info["fixed_assets"]) else 1.0
    debt_ratio = round(debt / fa, 2) if fa > 0 else 0.0

    return {
        "eps": eps,
        "sales": sales,
        "pat": pat,
        "sales_3y_cagr": sales_3y_cagr,
        "pat_3y_cagr": pat_3y_cagr,
        "cfo_pat": cfo_pat,
        "debt_ratio": debt_ratio
    }


def run_comprehensive_backtest():
    print("\n" + "="*85)
    print(" 🚀 QUANTITATIVE INSTITUTIONAL BACKTEST: PREDICT VALUATION MODEL (INDIAN EQUITIES)")
    print("="*85)

    # 1. Fetch Benchmarks
    print("1. Fetching Benchmarks (NIFTY 50 and NIFTY Midcap 100)...")
    benchmarks_cache = {}
    for b in BENCHMARKS:
        df = fetch_benchmark_chart(b["cid"])
        benchmarks_cache[b["ticker"]] = {"name": b["name"], "df": df}
        print(f"   • {b['name']}: {len(df)} price dates loaded.")

    # 2. Fetch Universe Data
    print(f"\n2. Fetching financial history & 5-year price series for {len(UNIVERSE)} companies...")
    universe_cache = {}
    for idx, u in enumerate(UNIVERSE):
        ticker = u["ticker"]
        name = u["name"]
        print(f"   [{idx+1:02d}/{len(UNIVERSE)}] {ticker:<12} ({name})...", end="", flush=True)
        data = scrape_full_company(ticker)
        if data and not data["chart_df"].empty:
            data["name"] = name
            data["sector"] = u["sector"]
            universe_cache[ticker] = data
            print(f" ✅ Loaded ({len(data['chart_df'])} quotes, {len(data['year_map'])} FYs)")
        else:
            print(" ❌ Skipped (missing data/chart)")
        time.sleep(0.2)

    # 3. Define 4 Historical Test Windows
    WINDOWS = [
        {
            "id": "W1_2021_2023",
            "name": "Cycle 1: Dec 2021 -> Dec 2023 (Global Rate Hikes & Multi-Year De-rating)",
            "start_date": "2021-12-15",
            "end_date": "2023-12-15",
            "as_of_year": 2021,
            "horizon_years": 2.0
        },
        {
            "id": "W2_2022_2024",
            "name": "Cycle 2: Oct 2022 -> Oct 2024 (Capex, Defense, EMS & Retail Supercycle)",
            "start_date": "2022-10-31",
            "end_date": "2024-10-31",
            "as_of_year": 2022,
            "horizon_years": 2.0
        },
        {
            "id": "W3_2023_2025",
            "name": "Cycle 3: Oct 2023 -> Oct 2025 (Selectivity, Scale & Operating Leverage)",
            "start_date": "2023-10-31",
            "end_date": "2025-10-31",
            "as_of_year": 2023,
            "horizon_years": 2.0
        },
        {
            "id": "W4_2021_2026",
            "name": "Cycle 4: Dec 2021 -> Oct 2026 (Full 5-Year Structural Compounding Run)",
            "start_date": "2021-12-15",
            "end_date": "2026-10-16",
            "as_of_year": 2021,
            "horizon_years": 4.8
        }
    ]

    all_windows_output = []

    for win in WINDOWS:
        print("\n" + "#"*85)
        print(f" 📊 EVALUATING {win['name'].upper()}")
        print(f" Formation: {win['start_date']} | Exit: {win['end_date']} | Horizon: {win['horizon_years']:.1f} Years")
        print("#"*85)

        # Benchmark Returns
        nifty_p0, _ = get_price_data(benchmarks_cache["NIFTY"]["df"], win["start_date"])
        nifty_p1, _ = get_price_data(benchmarks_cache["NIFTY"]["df"], win["end_date"])
        nifty_ret = ((nifty_p1 - nifty_p0) / nifty_p0 * 100) if (nifty_p0 and nifty_p1) else 0.0

        mid_p0, _ = get_price_data(benchmarks_cache["NMIDCAP100"]["df"], win["start_date"])
        mid_p1, _ = get_price_data(benchmarks_cache["NMIDCAP100"]["df"], win["end_date"])
        mid_ret = ((mid_p1 - mid_p0) / mid_p0 * 100) if (mid_p0 and mid_p1) else 0.0

        print(f" Benchmarks: NIFTY 50 = {nifty_ret:+.1f}% | NIFTY Midcap 100 = {mid_ret:+.1f}%\n")

        records = []
        for ticker, sdata in universe_cache.items():
            chart_df = sdata["chart_df"]
            p0, dma200_0 = get_price_data(chart_df, win["start_date"])
            p1, _ = get_price_data(chart_df, win["end_date"])

            if not p0 or not p1 or p0 <= 0 or p1 <= 0:
                continue

            pit = reconstruct_pit(sdata, win["as_of_year"])
            if not pit or pit["eps"] <= 0:
                continue

            eps_0 = pit["eps"]
            pe_0 = p0 / eps_0
            sales_3y = pit["sales_3y_cagr"]
            pat_3y = pit["pat_3y_cagr"]
            cfo_pat = pit["cfo_pat"]
            debt_ratio = pit["debt_ratio"]
            sector = sdata["sector"]

            # GATE 1: Sector Vector Gatekeeper
            is_bank_nbfc = any(w in sector.lower() for w in ["bank", "nbfc", "lending", "credit"])
            
            # GATE 2: Forensic Accounting Gate
            passes_forensic = (cfo_pat >= 0.70) and (debt_ratio < 1.0)

            # GATE 3: Growth Hurdle Gate
            expected_cagr = max(sales_3y, pat_3y)
            if ticker in KNOWN_COMPANY_PROFILES:
                prof = KNOWN_COMPANY_PROFILES[ticker]
                growth_rate = prof["base_cagr"] / 100.0
                bull_rate = prof["bull_cagr"] / 100.0
                base_exit_g = prof["base_exit_g"] / 100.0
                bull_exit_g = prof["bull_exit_g"] / 100.0
                base_peg = prof.get("base_peg", 1.6)
                bull_peg = prof.get("bull_peg", 1.85)
                base_prob = prof["base_prob"] / 100.0
                bull_prob = (100 - prof["base_prob"]) / 100.0
            else:
                growth_rate = max(0.20, min(0.35, round(expected_cagr * 0.85 / 100.0, 2))) if expected_cagr >= 15 else 0.15
                bull_rate = min(0.45, growth_rate + 0.10)
                base_exit_g = max(0.18, round(growth_rate * 0.85, 2))
                bull_exit_g = max(0.24, round(bull_rate * 0.85, 2))
                base_peg = 1.60
                bull_peg = 1.85
                base_prob = 0.55 if cfo_pat >= 0.75 else 0.65
                bull_prob = 1.0 - base_prob

            passes_growth = (growth_rate >= 0.20) or (bull_rate >= 0.20)

            # GATE 4: Valuation & Compounding Engine
            eps_yr2_base = eps_0 * ((1.0 + growth_rate) ** 2)
            eps_yr2_bull = eps_0 * ((1.0 + bull_rate) ** 2)
            fwd_pe_yr2 = p0 / eps_yr2_base

            base_pe = max(15.0, round(base_peg * (base_exit_g * 100), 1))
            bull_pe = max(base_pe + 5.0, round(bull_peg * (bull_exit_g * 100), 1))

            target_base = eps_yr2_base * base_pe
            target_bull = eps_yr2_bull * bull_pe
            upside_base_pct = ((target_base - p0) / p0) * 100
            upside_bull_pct = ((target_bull - p0) / p0) * 100
            expected_target = (target_base * base_prob) + (target_bull * bull_prob)
            expected_return_pct = ((expected_target - p0) / p0) * 100

            passes_pe = fwd_pe_yr2 < 50.0
            passes_bull_upside = upside_bull_pct >= 50.0

            # Classification
            if is_bank_nbfc:
                verdict = "REJECT_BANK"
                approved = False
            elif not passes_forensic:
                verdict = "REJECT_FORENSIC"
                approved = False
            elif not passes_growth:
                verdict = "REJECT_GROWTH"
                approved = False
            elif not passes_pe or upside_base_pct < -20.0:
                verdict = "HIGH_VALUATION_TRAP"
                approved = False
            elif passes_bull_upside and passes_pe:
                verdict = "STRONG_BUY" if upside_base_pct >= 10.0 else "QUALIFIED_BUY"
                approved = True
            else:
                verdict = "WATCHLIST"
                approved = False

            # Realized Performance
            realized_return_pct = ((p1 - p0) / p0) * 100
            realized_cagr = (((p1 / p0) ** (1.0 / win["horizon_years"])) - 1.0) * 100
            hit_positive = realized_return_pct > 0.0
            hit_target = p1 >= expected_target

            # Maximum Path Drawdown
            sub_c = chart_df[(chart_df["Date"] >= win["start_date"]) & (chart_df["Date"] <= win["end_date"])]
            max_p = sub_c["Price"].max() if not sub_c.empty else p1
            min_p = sub_c["Price"].min() if not sub_c.empty else p0
            max_dd = ((min_p - p0) / p0 * 100) if (min_p < p0) else 0.0

            # Enhanced Model (Predict 2.0) Logic:
            # 1. Trend Filter: Price must be > DMA200 at entry
            trend_ok = (dma200_0 is not None) and (p0 > dma200_0)
            enhanced_approved = approved and trend_ok

            # 2. Risk Management: Profit Harvesting & Stop Loss
            enhanced_ret = realized_return_pct
            if enhanced_approved:
                # Early bull profit taking: if max price reached Bull Target, lock in 50%
                if max_p >= target_bull:
                    enhanced_ret = 0.5 * upside_bull_pct + 0.5 * realized_return_pct
                # Stop loss: cut loss if path drawdown exceeded -18%
                elif min_p < p0 * 0.82:
                    enhanced_ret = max(realized_return_pct, -18.0)

            records.append({
                "ticker": ticker,
                "name": sdata["name"],
                "sector": sector,
                "p0": p0,
                "p1": p1,
                "pe_0": round(pe_0, 1),
                "fwd_pe_yr2": round(fwd_pe_yr2, 1),
                "sales_3y": sales_3y,
                "cfo_pat": cfo_pat,
                "verdict": verdict,
                "approved": approved,
                "enhanced_approved": enhanced_approved,
                "expected_return_pct": round(expected_return_pct, 1),
                "realized_return_pct": round(realized_return_pct, 1),
                "realized_cagr": round(realized_cagr, 1),
                "hit_positive": hit_positive,
                "hit_target": hit_target,
                "max_dd": round(max_dd, 1),
                "enhanced_ret": round(enhanced_ret, 1)
            })

        df_res = pd.DataFrame(records)
        if df_res.empty:
            continue

        approved_b = df_res[df_res["approved"]]
        rejected_b = df_res[~df_res["approved"]]
        enhanced_b = df_res[df_res["enhanced_approved"]]

        app_ret = approved_b["realized_return_pct"].mean() if not approved_b.empty else 0.0
        rej_ret = rejected_b["realized_return_pct"].mean() if not rejected_b.empty else 0.0
        enh_ret = enhanced_b["enhanced_ret"].mean() if not enhanced_b.empty else 0.0

        app_win_rate = (approved_b["hit_positive"].mean() * 100) if not approved_b.empty else 0.0
        app_target_hit = (approved_b["hit_target"].mean() * 100) if not approved_b.empty else 0.0
        app_avg_dd = approved_b["max_dd"].mean() if not approved_b.empty else 0.0

        alpha_nifty = app_ret - nifty_ret
        alpha_midcap = app_ret - mid_ret

        print(f" 📈 RESULTS FOR {win['id']}:")
        print(f"   • Predict Approved Basket ({len(approved_b)} stocks): Realized Return = {app_ret:+.1f}% | Win Rate: {app_win_rate:.0f}% | Target Accuracy: {app_target_hit:.0f}%")
        print(f"   • Predict Enhanced 2.0 Basket ({len(enhanced_b)} stocks): Realized Return = {enh_ret:+.1f}%")
        print(f"   • Predict Rejected Basket ({len(rejected_b)} stocks): Realized Return = {rej_ret:+.1f}%")
        print(f"   • Alpha Generated: vs NIFTY 50 = {alpha_nifty:+.1f}% | vs Midcap 100 = {alpha_midcap:+.1f}%\n")

        print("   --- Top Approved Compounders (Realized Returns) ---")
        for _, r in approved_b.sort_values(by="realized_return_pct", ascending=False).head(5).iterrows():
            print(f"     🟢 {r['ticker']:<11} | Realized: {r['realized_return_pct']:+6.1f}% (CAGR: {r['realized_cagr']:+5.1f}%) | PE0: {r['pe_0']:5.1f}x -> Fwd PE: {r['fwd_pe_yr2']:4.1f}x")

        # High Valuation Traps Analysis
        traps = df_res[df_res["verdict"] == "HIGH_VALUATION_TRAP"]
        if not traps.empty:
            print("   --- High Valuation Traps Identified by Predict Model ---")
            for _, r in traps.head(5).iterrows():
                print(f"     🟠 {r['ticker']:<11} | Realized: {r['realized_return_pct']:+6.1f}% | PE0: {r['pe_0']:5.1f}x -> Fwd PE: {r['fwd_pe_yr2']:4.1f}x | Max DD: {r['max_dd']:5.1f}%")

        # Rejected stocks that exploded (Type II error)
        missed = rejected_b[rejected_b["realized_return_pct"] >= 50.0]
        if not missed.empty:
            print("   --- Missed Multibaggers (Type II Errors in Strict Screening) ---")
            for _, r in missed.head(4).iterrows():
                print(f"     ⚠️ {r['ticker']:<11} | Realized: {r['realized_return_pct']:+6.1f}% | Rejected Reason: {r['verdict']} | PE0: {r['pe_0']}x")

        all_windows_output.append({
            "window_id": win["id"],
            "window_name": win["name"],
            "start_date": win["start_date"],
            "end_date": win["end_date"],
            "horizon_years": win["horizon_years"],
            "nifty_ret": round(nifty_ret, 1),
            "midcap_ret": round(mid_ret, 1),
            "approved_count": len(approved_b),
            "rejected_count": len(rejected_b),
            "approved_ret": round(app_ret, 1),
            "rejected_ret": round(rej_ret, 1),
            "enhanced_ret": round(enh_ret, 1),
            "win_rate": round(app_win_rate, 1),
            "target_hit_rate": round(app_target_hit, 1),
            "avg_drawdown": round(app_avg_dd, 1),
            "alpha_nifty": round(alpha_nifty, 1),
            "alpha_midcap": round(alpha_midcap, 1),
            "records": records
        })

    # Save to JSON
    out_path = os.path.join(_SCRIPT_DIR, "backtest_results.json")
    with open(out_path, "w") as f:
        json.dump(all_windows_output, f, indent=2)
    print(f"\n💾 Backtest complete. Detailed results saved to: {out_path}")
    return all_windows_output


if __name__ == "__main__":
    run_comprehensive_backtest()
