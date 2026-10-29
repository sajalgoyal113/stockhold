#!/usr/bin/env python3
"""
predict/scripts/fetch_smallcap_backtest_data.py

Fetches historical financials and price trajectory for 25 Nifty Smallcap 250 constituents
from Screener.in and caches them locally to predict/data/smallcap250_backtest_cache.json.
"""

import os
import sys
import re
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
CACHE_FILE = os.path.join(_DATA_DIR, "smallcap250_backtest_cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

UNIVERSE = [
    # 1. Capital Goods & Defense
    {"ticker": "ACE", "name": "Action Construction Equipment", "sector": "Capital Goods (Cranes & Material Handling)", "disqualify_sector": False},
    {"ticker": "ZENTEC", "name": "Zen Technologies", "sector": "Defense Simulators & Anti-Drone Systems", "disqualify_sector": False},
    {"ticker": "TITAGARH", "name": "Titagarh Rail Systems", "sector": "Railway Wagons & Passenger Coaches", "disqualify_sector": False},
    {"ticker": "KSB", "name": "KSB Ltd", "sector": "Industrial Pumps & Nuclear Valves", "disqualify_sector": False},
    {"ticker": "TDPOWERSYS", "name": "TD Power Systems", "sector": "AC Generators & Steam Turbines", "disqualify_sector": False},
    {"ticker": "CARBORUNIV", "name": "Carborundum Universal", "sector": "Abrasives, Industrial Ceramics & Refractories", "disqualify_sector": False},

    # 2. Chemicals & Materials
    {"ticker": "NAVINFLUOR", "name": "Navin Fluorine International", "sector": "Specialty Fluorochemicals & CDMO", "disqualify_sector": False},
    {"ticker": "ANURAS", "name": "Anupam Rasayan India", "sector": "Agro & Pharma Custom Synthesis (CSM)", "disqualify_sector": False},
    {"ticker": "HSCL", "name": "Himadri Speciality Chemical", "sector": "Advanced Carbon & EV Battery Anodes", "disqualify_sector": False},
    {"ticker": "PRIVISCL", "name": "Privi Speciality Chemicals", "sector": "Aroma Chemicals & Pinene Derivatives", "disqualify_sector": False},

    # 3. Healthcare & Pharma
    {"ticker": "RAINBOW", "name": "Rainbow Children's Medicare", "sector": "Pediatric & Perinatal Super-Specialty Hospitals", "disqualify_sector": False},
    {"ticker": "PPLPHARMA", "name": "Piramal Pharma", "sector": "Global CDMO & Critical Care Inhalation", "disqualify_sector": False},

    # 4. Consumer, Retail & Hospitality
    {"ticker": "CROMPTON", "name": "Crompton Greaves Consumer", "sector": "Consumer Electricals & Appliances", "disqualify_sector": False},
    {"ticker": "BATAINDIA", "name": "Bata India", "sector": "Footwear Retail", "disqualify_sector": False},
    {"ticker": "AVANTIFEED", "name": "Avanti Feeds", "sector": "Aquaculture Feed & Shrimp Processing", "disqualify_sector": False},
    {"ticker": "LEMONTREE", "name": "Lemon Tree Hotels", "sector": "Mid-Scale Hospitality & Tourism", "disqualify_sector": False},

    # 5. Technology & Telecom
    {"ticker": "ZENSARTECH", "name": "Zensar Technologies", "sector": "IT Consulting & Digital Engineering", "disqualify_sector": False},
    {"ticker": "RAILTEL", "name": "RailTel Corporation of India", "sector": "Telecom & Rail Data Center Infrastructure", "disqualify_sector": False},
    {"ticker": "HFCL", "name": "HFCL Ltd", "sector": "Telecom Equipment & Optical Fiber", "disqualify_sector": False},

    # 6. Auto Components
    {"ticker": "APOLLOTYRE", "name": "Apollo Tyres", "sector": "Commercial & Passenger Vehicle Tyres", "disqualify_sector": False},
    {"ticker": "SONACOMS", "name": "Sona BLW Precision Forgings", "sector": "EV Driveline & Differential Assemblies", "disqualify_sector": False},

    # 7. Realty & Diversified
    {"ticker": "ABREL", "name": "Aditya Birla Real Estate (Century)", "sector": "Luxury Real Estate & Pulp/Paper", "disqualify_sector": False},

    # 8. Financial Services (Sector Disqualification Tests)
    {"ticker": "CDSL", "name": "Central Depository Services", "sector": "Capital Markets Depository Monopoly", "disqualify_sector": False},
    {"ticker": "MANAPPURAM", "name": "Manappuram Finance", "sector": "NBFC (Gold Loans & Microfinance)", "disqualify_sector": True},
    {"ticker": "CUB", "name": "City Union Bank", "sector": "Banking & SME Lending", "disqualify_sector": True},
]

def clean_num(val_str):
    if not val_str:
        return 0.0
    cleaned = re.sub(r"[^\d.-]", "", str(val_str))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def fetch_screener_cid(ticker: str) -> str:
    url = f"https://www.screener.in/company/{ticker}/"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    m = re.search(r'data-company-id=\"(\d+)\"', r.text) or re.search(r'companyId:\s*(\d+)', r.text) or re.search(r'/api/company/(\d+)/', r.text)
    return m.group(1) if m else None

def fetch_financials(ticker: str) -> dict:
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

    # Borrowings and Equity
    debt_vals = get_row("balance-sheet", "borrowings")
    equity_vals = get_row("balance-sheet", "equity capital")
    reserves_vals = get_row("balance-sheet", "reserves")

    return {
        "sales": get_row("profit-loss", "sales"),
        "pat": get_row("profit-loss", "net profit"),
        "eps": get_row("profit-loss", "eps"),
        "cfo": get_row("cash-flow", "operating activity"),
        "borrowings": debt_vals,
        "reserves": reserves_vals,
        "equity": equity_vals,
        "year_map": year_map
    }

def fetch_chart(cid: str) -> pd.DataFrame:
    try:
        url = f"https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200&days=1825"
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

def main():
    print("=" * 80)
    print(" FETCHING HISTORICAL DATA FOR 25 NIFTY SMALLCAP 250 STOCKS")
    print("=" * 80)

    cached_data = {}
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cached_data = json.load(f)
            print(f"Loaded existing cache with {len(cached_data)} stocks.")
        except Exception:
            cached_data = {}

    for idx, item in enumerate(UNIVERSE, 1):
        ticker = item["ticker"]
        print(f"[{idx:02d}/25] Fetching {ticker:<12} ({item['name']})...", end="", flush=True)
        
        cid = fetch_screener_cid(ticker)
        time.sleep(1.0)
        if not cid:
            print(" ❌ Failed to get CID")
            continue
        
        df_chart = fetch_chart(cid)
        time.sleep(1.0)
        if df_chart.empty:
            print(" ❌ Failed to get chart")
            continue
        
        fin = fetch_financials(ticker)
        time.sleep(1.0)
        if not fin or not fin.get("year_map"):
            print(" ❌ Failed to get financials")
            continue

        # Convert chart to serializable records
        chart_records = df_chart.to_dict(orient="records")
        for rec in chart_records:
            if isinstance(rec.get("Date"), pd.Timestamp):
                rec["Date"] = rec["Date"].strftime("%Y-%m-%d")

        cached_data[ticker] = {
            "name": item["name"],
            "sector": item["sector"],
            "disqualify_sector": item["disqualify_sector"],
            "cid": cid,
            "financials": fin,
            "chart": chart_records
        }
        print(" ✅ Cached successfully")

    with open(CACHE_FILE, "w") as f:
        json.dump(cached_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f" ALL DATA CACHED SUCCESSFULLY: {len(cached_data)} stocks in {CACHE_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
