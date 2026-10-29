#!/usr/bin/env python3
"""predict/scripts/fetch_smallcap_set2_data.py.

Fetches historical financials and 5-year daily chart data from Screener.in
for a fresh, distinct sample of 30 NIFTY Smallcap 250 constituents.
Caches output into predict/data/smallcap250_set2_cache.json.
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
CACHE_FILE = os.path.join(_DATA_DIR, "smallcap250_set2_cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

UNIVERSE_SET_2 = [
    # 1. Defense, Shipbuilding & Electronics
    {"ticker": "MAZDOCK", "name": "Mazagon Dock Shipbuilders", "sector": "Defense Shipbuilding (Submarines & Warships)", "disqualify_sector": False},
    {"ticker": "COCHINSHIP", "name": "Cochin Shipyard", "sector": "Shipbuilding, Aircraft Carriers & Ship Repair", "disqualify_sector": False},
    {"ticker": "GRSE", "name": "Garden Reach Shipbuilders & Engineers", "sector": "Warship Design & Defense Marine Engineering", "disqualify_sector": False},
    {"ticker": "DATAPATTNS", "name": "Data Patterns (India)", "sector": "Defense Radars, EW & Aerospace Electronics", "disqualify_sector": False},
    {"ticker": "KAYNES", "name": "Kaynes Technology India", "sector": "Integrated EMS, IoT & Semiconductor Packaging", "disqualify_sector": False},

    # 2. Telecom & High-Tech Software
    {"ticker": "TEJASNET", "name": "Tejas Networks", "sector": "Optical Networking & 5G Telecom RAN Equipment", "disqualify_sector": False},
    {"ticker": "KPITTECH", "name": "KPIT Technologies", "sector": "Automotive Software, SDV & Autonomous Architectures", "disqualify_sector": False},
    {"ticker": "NEWGEN", "name": "Newgen Software Technologies", "sector": "Low-Code Digital Automation & Enterprise ECM", "disqualify_sector": False},

    # 3. Capital Goods, Industrial Machinery & Power
    {"ticker": "APARINDS", "name": "Apar Industries", "sector": "Specialty Conductors, Transformer Oils & Power Cables", "disqualify_sector": False},
    {"ticker": "ELECON", "name": "Elecon Engineering", "sector": "Industrial Gearboxes & Material Handling Systems", "disqualify_sector": False},
    {"ticker": "BBL", "name": "Bharat Bijlee", "sector": "Industrial Electric Motors, Transformers & Automation", "disqualify_sector": False},
    {"ticker": "PRAJIND", "name": "Praj Industries", "sector": "Bio-Energy, 1G/2G Ethanol & Brewery Engineering", "disqualify_sector": False},
    {"ticker": "SUZLON", "name": "Suzlon Energy", "sector": "Wind Turbine Generators & Renewable O&M Services", "disqualify_sector": False},

    # 4. Circular Economy & Recycling
    {"ticker": "GRAVITA", "name": "Gravita India", "sector": "Lead, Aluminum & Plastic Recycling Metallurgy", "disqualify_sector": False},

    # 5. Infrastructure, Engineering & Transport
    {"ticker": "RITES", "name": "RITES Ltd", "sector": "Transport Infrastructure Consultancy & Rolling Stock Exports", "disqualify_sector": False},
    {"ticker": "ENGINERSIN", "name": "Engineers India", "sector": "Hydrocarbon, Petrochemicals & Green Hydrogen EPC", "disqualify_sector": False},
    {"ticker": "IRB", "name": "IRB Infrastructure Developers", "sector": "BOT & TOT Toll Highway Concessions & Real Estate", "disqualify_sector": False},
    {"ticker": "TARC", "name": "TARC Ltd", "sector": "Luxury Residential Real Estate Development (Delhi-NCR)", "disqualify_sector": False},

    # 6. Specialty Chemicals & Commoditization Stresses
    {"ticker": "DEEPAKNTR", "name": "Deepak Nitrite", "sector": "Phenol, Acetone & Downstream Intermediates", "disqualify_sector": False},
    {"ticker": "AARTIIND", "name": "Aarti Industries", "sector": "Benzene Chemistry & Specialty Intermediates", "disqualify_sector": False},
    {"ticker": "FINEORG", "name": "Fine Organic Industries", "sector": "Green Oleochemical Additives for Food & Polymers", "disqualify_sector": False},

    # 7. Consumer, Healthcare & Building Materials
    {"ticker": "JYOTHYLAB", "name": "Jyothy Labs", "sector": "Fabric Whitener, Detergents & Home Care FMCG", "disqualify_sector": False},
    {"ticker": "CAMPUS", "name": "Campus Activewear", "sector": "Athleisure & Sports Footwear Retail", "disqualify_sector": False},
    {"ticker": "CENTURYPLY", "name": "Century Plyboards (India)", "sector": "Plywood, Laminates & MDF Building Materials", "disqualify_sector": False},
    {"ticker": "CEATLTD", "name": "CEAT Ltd", "sector": "Automotive Tyres & Radial Rubber Manufacturing", "disqualify_sector": False},
    {"ticker": "MEDPLUS", "name": "MedPlus Health Services", "sector": "Omnichannel Pharmacy Retail Chain & Diagnostics", "disqualify_sector": False},
    {"ticker": "JBCHEPHARM", "name": "JB Chemicals & Pharmaceuticals", "sector": "Branded Formulations & Global CMO APIs", "disqualify_sector": False},
    {"ticker": "ERIS", "name": "Eris Lifesciences", "sector": "Chronic Cardio-Metabolic Branded Formulations", "disqualify_sector": False},

    # 8. Financial Services (Sector Disqualification Tests)
    {"ticker": "IIFL", "name": "IIFL Finance", "sector": "NBFC (Gold Loans, Microfinance & Mortgages)", "disqualify_sector": True},
    {"ticker": "IDFCFIRSTB", "name": "IDFC First Bank", "sector": "Banking, CASA Deposits & Consumer Credit", "disqualify_sector": True},
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
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        m = (re.search(r'data-company-id=\"(\d+)\"', r.text) or
             re.search(r'companyId:\s*(\d+)', r.text) or
             re.search(r'/api/company/(\d+)/', r.text))
        return m.group(1) if m else None
    except Exception:
        return None


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
                soup_test = BeautifulSoup(r.text, "html.parser")
                pl_test = soup_test.find("section", id="profit-loss")
                if pl_test and pl_test.find("table") and pl_test.find("table").find("thead"):
                    ths = pl_test.find("table").find("thead").find_all("th")
                    if len(ths) > 3:
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

    # Borrowings, Equity, Reserves
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
    print("=" * 90)
    print(" FETCHING POINT-IN-TIME DATA FOR 30 FRESH NIFTY SMALLCAP 250 STOCKS (SET 2)")
    print("=" * 90)

    cached_data = {}
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cached_data = json.load(f)
            print(f"Loaded existing cache with {len(cached_data)} stocks.")
        except Exception:
            cached_data = {}

    for idx, item in enumerate(UNIVERSE_SET_2, 1):
        ticker = item["ticker"]
        if ticker in cached_data and cached_data[ticker].get("financials", {}).get("year_map"):
            print(f"[{idx:02d}/30] {ticker:<12} already cached. Skipping.")
            continue

        print(f"[{idx:02d}/30] Fetching {ticker:<12} ({item['name'][:30]})...", end="", flush=True)

        cid = fetch_screener_cid(ticker)
        time.sleep(0.8)
        if not cid:
            print(" ❌ Failed to get CID")
            continue

        df_chart = fetch_chart(cid)
        time.sleep(0.8)
        if df_chart.empty:
            print(" ❌ Failed to get chart")
            continue

        fin = fetch_financials(ticker)
        time.sleep(0.8)
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

    print("\n" + "=" * 90)
    print(f" ALL DATA CACHED SUCCESSFULLY: {len(cached_data)} stocks in {CACHE_FILE}")
    print("=" * 90)


if __name__ == "__main__":
    main()
