import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Persistent HTTP session with connection pooling & keep-alive
_HTTP_SESSION = requests.Session()
_HTTP_SESSION.headers.update(HEADERS)

def clean_num(val_str):
    if not val_str:
        return 0.0
    cleaned = re.sub(r"[^\d.-]", "", val_str)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

COMMON_ALIASES = {
    "ZOMATO": "ETERNAL",
    "ONE97": "PAYTM",
    "POLICYBAZAAR": "POLICYBZR",
    "TATAMOTORS": "TMCV",
    "L&T": "LT",
    "M&M": "M&M",
    "CYIENT DLM": "CYIENTDLM",
    "CYIENT-DLM": "CYIENTDLM",
    "CYIENT_DLM": "CYIENTDLM",
    "IXIGO": "IXIGO",
    "LE TRAVENUES": "IXIGO",
    "LE TRAVENUES TECHNOLOGY": "IXIGO",
    "URBAN COMPANY": "URBANCO",
    "URBANCOMPANY": "URBANCO",
    "URBAN": "URBANCO",
    "AMARAJABAT": "ARE&M",
    "AMARA RAJA": "ARE&M",
    "AMARA RAJA ENERGY": "ARE&M",
    "ASSOCHALC": "ASALCBR",
    "C.E. INFO SYSTEMS": "MAPMYINDIA",
    "CE INFO SYSTEMS": "MAPMYINDIA",
    "CEINFOSYST": "MAPMYINDIA",
    "CEINFOSYSTEMS": "MAPMYINDIA"
}

TOP_TRENDING_STOCKS = [
    {"ticker": "ETERNAL", "display": "ZOMATO", "sector": "Quick-Commerce"},
    {"ticker": "CYIENTDLM", "display": "CYIENT DLM", "sector": "Aerospace EMS"},
    {"ticker": "COFORGE", "display": "COFORGE", "sector": "Enterprise IT"},
    {"ticker": "DIXON", "display": "DIXON TECH", "sector": "EMS & Mobile PLI"},
    {"ticker": "KAYNES", "display": "KAYNES TECH", "sector": "OSAT & Defense EMS"},
    {"ticker": "TRENT", "display": "TRENT", "sector": "Zudio Retail"},
    {"ticker": "TATAMOTORS", "display": "TATA MOTORS", "sector": "Automotive / JLR"},
    {"ticker": "POLYCAB", "display": "POLYCAB", "sector": "Cables & Infra"},
    {"ticker": "HAL", "display": "HAL", "sector": "Defense Aviation"},
    {"ticker": "BEL", "display": "BEL", "sector": "Defense Electronics"},
    {"ticker": "CDSL", "display": "CDSL", "sector": "Capital Markets"},
    {"ticker": "IXIGO", "display": "IXIGO", "sector": "Travel Tech"},
    {"ticker": "ANGELONE", "display": "ANGEL ONE", "sector": "Fintech Brokerage"},
    {"ticker": "SUZLON", "display": "SUZLON", "sector": "Wind Energy Turnaround"},
    {"ticker": "TATAELXSI", "display": "TATA ELXSI", "sector": "Automotive Software"},
    {"ticker": "KPITTECH", "display": "KPIT TECH", "sector": "Mobility Software"},
    {"ticker": "PERSISTENT", "display": "PERSISTENT", "sector": "Digital Engineering"},
    {"ticker": "NETWEB", "display": "NETWEB TECH", "sector": "AI Supercomputing"},
    {"ticker": "JYOTICNC", "display": "JYOTI CNC", "sector": "Aerospace Machining"},
    {"ticker": "PRESTIGE", "display": "PRESTIGE", "sector": "Real Estate Growth"},
    {"ticker": "PAYTM", "display": "PAYTM", "sector": "Merchant Payments"},
    {"ticker": "POLICYBZR", "display": "POLICYBAZAAR", "sector": "Insurtech Platform"}
]

def get_top_trending_stocks():
    return TOP_TRENDING_STOCKS

def resolve_screener_ticker(query: str) -> str:
    cleaned = query.upper().strip()
    if cleaned in COMMON_ALIASES:
        return COMMON_ALIASES[cleaned]
    # Screener Search API (fast resolution for renamed / BSE tickers)
    try:
        sr = _HTTP_SESSION.get(f"https://www.screener.in/api/company/search/?q={query}", timeout=4)
        if sr.status_code == 200:
            results = sr.json()
            if results and len(results) > 0:
                url = results[0].get("url", "")
                m = re.search(r"/company/([^/]+)/", url)
                if m:
                    return m.group(1).upper()
    except Exception:
        pass
    return cleaned

_DATA_FETCHER_CACHE = {}
_DATA_FETCHER_CACHE_TS = {}
CACHE_TTL_SECONDS = 6 * 3600


def _cache_get(key: str):
    rec = _DATA_FETCHER_CACHE.get(key)
    if rec is None:
        return None
    ts = _DATA_FETCHER_CACHE_TS.get(key, 0.0)
    import time as _t
    if _t.time() - ts > CACHE_TTL_SECONDS:
        _DATA_FETCHER_CACHE.pop(key, None)
        _DATA_FETCHER_CACHE_TS.pop(key, None)
        return None
    return rec


def _cache_put(key: str, rec: dict):
    import time as _t
    _DATA_FETCHER_CACHE[key] = rec
    _DATA_FETCHER_CACHE_TS[key] = _t.time()


def fetch_company_data(ticker: str):
    orig_ticker = (ticker or "").strip().upper()
    if not orig_ticker:
        raise ValueError("Empty ticker symbol provided")

    # 1. Instant cache check (0ms in-memory return)
    hit = _cache_get(orig_ticker)
    if hit is not None:
        return hit
    resolved_alias = COMMON_ALIASES.get(orig_ticker)
    if resolved_alias:
        hit = _cache_get(resolved_alias)
        if hit is not None:
            return hit

    ticker = resolved_alias if resolved_alias else orig_ticker

    # 2. Fast single-flight fetch: Try consolidated first (prefers 1 request in 95% of cases)
    html = None
    final_url = None
    
    candidate_urls = [
        f"https://www.screener.in/company/{ticker}/consolidated/",
        f"https://www.screener.in/company/{ticker}/"
    ]

    for u in candidate_urls:
        try:
            r = _HTTP_SESSION.get(u, timeout=6)
            if r.status_code == 200:
                soup_check = BeautifulSoup(r.text, "html.parser")
                for li in soup_check.find_all("li", class_="flex"):
                    name_span = li.find("span", class_="name")
                    val_span = li.find("span", class_="value")
                    if name_span and val_span and "Current Price" in name_span.text:
                        p_val = clean_num(val_span.text)
                        if p_val > 0:
                            html = r.text
                            final_url = u
                            break
            if html:
                break
        except Exception:
            continue

    # 3. If direct candidate URLs failed, try resolving ticker via Screener Search API
    if not html:
        resolved_search = resolve_screener_ticker(orig_ticker)
        if resolved_search and resolved_search != ticker:
            ticker = resolved_search
            for u in [f"https://www.screener.in/company/{ticker}/consolidated/", f"https://www.screener.in/company/{ticker}/"]:
                try:
                    r = _HTTP_SESSION.get(u, timeout=6)
                    if r.status_code == 200:
                        soup_check = BeautifulSoup(r.text, "html.parser")
                        for li in soup_check.find_all("li", class_="flex"):
                            name_span = li.find("span", class_="name")
                            val_span = li.find("span", class_="value")
                            if name_span and val_span and "Current Price" in name_span.text:
                                if clean_num(val_span.text) > 0:
                                    html = r.text
                                    final_url = u
                                    break
                        if html:
                            break
                except Exception:
                    continue

    if not html:
        # Check local fundamentals database snapshot if live network is throttled or offline
        try:
            import json, os
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            candidate_paths = [
                os.path.join(os.path.dirname(cur_dir), "data", "portfolio_fundamentals.json"),
                os.path.join(os.path.dirname(os.path.dirname(cur_dir)), "predict", "data", "portfolio_fundamentals.json")
            ]
            for db_path in candidate_paths:
                if os.path.exists(db_path):
                    with open(db_path, "r") as f:
                        local_db = json.load(f)
                    for cand_key in [ticker, orig_ticker]:
                        if cand_key in local_db:
                            rec = local_db[cand_key].copy()
                            rec["is_live"] = False
                            rec["source_label"] = "Offline Fallback Snapshot (portfolio_fundamentals.json)"
                            if "eps" in rec:
                                rec["ttm_eps"] = float(rec["eps"])
                            rec["snapshot_as_of"] = local_db.get("_as_of", rec.get("snapshot_as_of", "unknown"))
                            _cache_put(ticker, rec)
                            _cache_put(orig_ticker, rec)
                            print(f"⚠️  [OFFLINE/CACHE FALLBACK] Loaded fundamentals snapshot for {cand_key} from local portfolio database. (CMP may be stale - mandatory live quote cross-check required!)")
                            return rec
        except Exception:
            pass
        raise ValueError(f"Could not fetch valid financial data for ticker: {ticker} from Screener.in")

    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Company Name & Info
    h1 = soup.find("h1")
    name = h1.text.strip() if h1 else ticker
    
    about_div = soup.find("div", class_="about")
    about_text = about_div.text.strip() if about_div else ""
    # clean about text
    about_text = re.sub(r"\s+", " ", about_text)
    
    # 2. Company ID for Chart API
    m_cid = re.search(r"data-company-id=\"(\d+)\"", html)
    company_id = m_cid.group(1) if m_cid else None
    
    # 3. Top Ratios
    top_ratios = {}
    ratio_lis = soup.find_all("li", class_="flex")
    for li in ratio_lis:
        name_span = li.find("span", class_="name")
        val_span = li.find("span", class_="value")
        if name_span and val_span:
            k = name_span.text.strip()
            v = val_span.text.strip().replace("\n", " ")
            v = re.sub(r"\s+", " ", v)
            top_ratios[k] = v

    # Extract numerical primary metrics
    mcap_cr = clean_num(top_ratios.get("Market Cap", "0"))
    cmp = clean_num(top_ratios.get("Current Price", "0"))
    pe = clean_num(top_ratios.get("Stock P/E", "0"))
    book_value = clean_num(top_ratios.get("Book Value", "0"))
    roce = clean_num(top_ratios.get("ROCE", "0"))
    roe = clean_num(top_ratios.get("ROE", "0"))
    face_value = clean_num(top_ratios.get("Face Value", "0"))
    
    # 4. Helper to parse tables
    def parse_section_table(sec_id):
        sec = soup.find("section", id=sec_id)
        if not sec:
            return None, {}
        headers = [th.text.strip() for th in sec.find_all("th") if th.text.strip()]
        data_rows = {}
        for tr in sec.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            row_title = tds[0].text.strip()
            # clean title
            row_title = re.sub(r"\s+", " ", row_title).replace("+", "").strip()
            values = [td.text.strip().replace(",", "") for td in tds[1:]]
            if row_title and values:
                data_rows[row_title] = values
        return headers, data_rows

    q_headers, q_data = parse_section_table("quarters")
    pl_headers, pl_data = parse_section_table("profit-loss")
    bs_headers, bs_data = parse_section_table("balance-sheet")
    cf_headers, cf_data = parse_section_table("cash-flow")
    rat_headers, rat_data = parse_section_table("ratios")
    sh_headers, sh_data = parse_section_table("shareholding")

    # 4b. Helper to parse Compounded Growth & ROE ranges tables
    growth_ranges = {}
    for r_table in soup.find_all("table", class_="ranges-table"):
        th = r_table.find("th")
        if not th:
            continue
        title = th.text.strip().lower()
        for tr in r_table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                k = tds[0].text.strip().lower()
                val = clean_num(tds[1].text)
                if "sales growth" in title:
                    if "3 years" in k: growth_ranges["sales_growth_3yr"] = val
                    elif "5 years" in k: growth_ranges["sales_growth_5yr"] = val
                    elif "ttm" in k: growth_ranges["sales_growth_ttm"] = val
                elif "profit growth" in title:
                    if "3 years" in k: growth_ranges["profit_growth_3yr"] = val
                    elif "5 years" in k: growth_ranges["profit_growth_5yr"] = val
                    elif "ttm" in k: growth_ranges["profit_growth_ttm"] = val
                elif "return on equity" in title:
                    if "3 years" in k: growth_ranges["roe_3yr"] = val
                    elif "last year" in k: growth_ranges["roe_last_yr"] = val

    # 5. Compute Rolling TTM EPS and PAT from last 4 reported quarters
    ttm_pat = 0.0
    ttm_sales = 0.0
    ttm_eps = 0.0
    last_4_quarters = []
    
    if q_headers and "Net Profit" in q_data:
        # get valid quarter columns (exclude 'Raw PDF' or empty)
        quarters = [q for q in q_headers if any(char.isdigit() for char in q)]
        net_profits = [clean_num(p) for p in q_data.get("Net Profit", [])]
        sales_arr = [clean_num(s) for s in q_data.get("Sales", [])]
        eps_arr = [clean_num(e) for e in q_data.get("EPS in Rs", [])]
        
        # take the last 4 quarters
        if len(net_profits) >= 4:
            last_4_pat = net_profits[-4:]
            last_4_sales = sales_arr[-4:]
            last_4_eps = eps_arr[-4:] if len(eps_arr) >= 4 else []
            last_4_quarters = quarters[-4:]
            
            ttm_pat = sum(last_4_pat)
            ttm_sales = sum(last_4_sales)
            ttm_eps_sum = sum(last_4_eps) if last_4_eps else 0.0
        else:
            ttm_pat = sum(net_profits)
            ttm_sales = sum(sales_arr)
            ttm_eps_sum = sum(eps_arr)
            last_4_quarters = quarters
            last_4_eps = eps_arr
            
        # Shares count
        if cmp > 0 and mcap_cr > 0:
            shares_cr = mcap_cr / cmp
        else:
            shares_cr = 0.0

        # Exact Rolling TTM EPS from last 4 reported quarters as mandated by GEMINI.md Rule 1
        if len(last_4_eps) == 4 and ttm_eps_sum > 0:
            ttm_eps = round(ttm_eps_sum, 2)
        elif shares_cr > 0 and ttm_pat > 0:
            ttm_eps = round(ttm_pat / shares_cr, 2)
        else:
            ttm_eps = round(ttm_eps_sum, 2)
    else:
        # Fallback to P&L TTM
        shares_cr = (mcap_cr / cmp) if cmp > 0 else 0.0
        ttm_eps = clean_num(pl_data.get("EPS in Rs", ["0"])[-1]) if "EPS in Rs" in pl_data else 0.0
        ttm_pat = clean_num(pl_data.get("Net Profit", ["0"])[-1]) if "Net Profit" in pl_data else 0.0
        ttm_sales = clean_num(pl_data.get("Sales", ["0"])[-1]) if "Sales" in pl_data else 0.0

    if ttm_eps <= 0 and pe > 0 and cmp > 0:
        ttm_eps = round(cmp / pe, 2)
    elif pe <= 0 and ttm_eps > 0 and cmp > 0:
        pe = round(cmp / ttm_eps, 1)

    # 6. Extract 4-Year Trend Metrics for Forensics
    # The P&L table has a TTM column (Screener may append "Compounded Growth" header columns
    # after it); cash-flow has annual columns only. Use the last 4 FULL fiscal years before TTM
    # from both so CFO/PAT compares the same periods.
    ttm_idx = next((i for i, h in enumerate(pl_headers or []) if str(h).strip().upper() == "TTM"), None)
    pl_slice = slice(ttm_idx - 4, ttm_idx) if ttm_idx is not None and ttm_idx >= 4 else slice(-4, None)
    trend_years = [str(y).split("\n")[0].strip().replace("Mar ", "FY") for y in (pl_headers or [])[pl_slice]]
    trend_years = [y for y in trend_years if any(c.isdigit() for c in y)]
    if len(trend_years) < 4:
        trend_years = ["FY23", "FY24", "FY25", "FY26"]
    rev_history = [clean_num(v) for v in pl_data.get("Sales", [])[pl_slice]]
    pat_history = [clean_num(v) for v in pl_data.get("Net Profit", [])[pl_slice]]
    cfo_history = [clean_num(v) for v in cf_data.get("Cash from Operating Activity", [])[-4:]]
    fcf_history = [clean_num(v) for v in cf_data.get("Free Cash Flow", [])[-4:]]
    
    # Borrowings from Balance sheet (GROSS debt: Screener does not split out cash)
    borrowings_arr = [clean_num(v) for v in bs_data.get("Borrowings", [])]
    latest_debt = borrowings_arr[-1] if borrowings_arr else 0.0

    # Real balance-sheet / P&L inputs for the Altman Z'' score (None when unavailable)
    def _last(rows, key):
        vals = rows.get(key) or []
        return clean_num(vals[-1]) if vals else None
    bs_total_assets = _last(bs_data, "Total Assets")
    bs_equity_capital = _last(bs_data, "Equity Capital")
    bs_reserves = _last(bs_data, "Reserves")
    bs_other_assets = _last(bs_data, "Other Assets")
    bs_other_liabilities = _last(bs_data, "Other Liabilities")
    last_fy = (lambda key: (clean_num(pl_data[key][pl_slice][-1]) if pl_data.get(key) and pl_data[key][pl_slice] else None))
    pbt_fy = last_fy("Profit before tax")
    interest_fy = last_fy("Interest")
    ebit_fy = (pbt_fy + (interest_fy or 0.0)) if pbt_fy is not None else None
    
    # Debtor days
    debtor_days_arr = [clean_num(v) for v in rat_data.get("Debtor Days", [])]
    latest_debtor_days = debtor_days_arr[-1] if debtor_days_arr else 60.0
    
    # 6b. Concall documents (transcript / PPT links, newest first) for guidance extraction
    concalls = []
    try:
        con_div = soup.find("div", class_="concalls")
        for li in (con_div.find_all("li") if con_div else []):
            date_div = li.find("div")
            item = {"date": date_div.text.strip() if date_div else ""}
            for a in li.find_all("a"):
                label = a.text.strip().lower()
                if label.startswith("transcript"):
                    item["transcript"] = a.get("href")
                elif label == "ppt":
                    item["ppt"] = a.get("href")
            concalls.append(item)
    except Exception:
        concalls = []

    # 6c. Peer net margins (Screener peers table: NP Qtr / Sales Qtr), the company itself excluded.
    # Used as a steady-state margin reference for companies with no profitable history.
    peer_npms, peer_names = [], []
    m_wid = re.search(r"data-warehouse-id=\"(\d+)\"", html)
    if m_wid:
        try:
            pr = _HTTP_SESSION.get(f"https://www.screener.in/api/company/{m_wid.group(1)}/peers/", timeout=4)
            if pr.status_code == 200:
                psoup = BeautifulSoup(pr.text, "html.parser")
                prow = psoup.find_all("tr")
                heads = [re.sub(r"\s+", " ", th.text).strip().lower() for th in (prow[0].find_all("th") if prow else [])]
                i_np = next((i for i, h in enumerate(heads) if h.startswith("np qtr")), None)
                i_sq = next((i for i, h in enumerate(heads) if h.startswith("sales qtr")), None)
                i_mc = next((i for i, h in enumerate(heads) if h.startswith("mar cap")), None)
                for tr in prow[1:]:
                    tds = [td.text.strip() for td in tr.find_all("td")]
                    if i_np is None or i_sq is None or len(tds) <= max(i_np, i_sq):
                        continue
                    if i_mc is not None and mcap_cr > 0 and abs(clean_num(tds[i_mc]) - mcap_cr) / mcap_cr < 0.02:
                        continue  # the company itself
                    npq, sq = clean_num(tds[i_np]), clean_num(tds[i_sq])
                    if sq > 0 and tds[i_np]:
                        peer_npms.append(round(npq / sq, 4))
                        peer_names.append(tds[1] if len(tds) > 1 else "")
        except Exception:
            pass

    # 7. Price Chart History (from Screener Chart API)
    chart_df = pd.DataFrame()
    if company_id:
        try:
            chart_url = f"https://www.screener.in/api/company/{company_id}/chart/?q=Price-DMA50-DMA200-Volume&days=365"
            cr = _HTTP_SESSION.get(chart_url, timeout=4)
            if cr.status_code == 200:
                cdata = cr.json()
                datasets = cdata.get("datasets", [])
                if datasets:
                    price_points = datasets[0].get("values", [])
                    if price_points:
                        dates = [p[0] for p in price_points]
                        prices = [clean_num(p[1]) for p in price_points]
                        chart_df = pd.DataFrame({"Date": pd.to_datetime(dates), "Price": prices})
                        if len(datasets) > 1 and datasets[1].get("metric") == "DMA50":
                            chart_df["DMA50"] = [clean_num(p[1]) for p in datasets[1].get("values", [])]
                        if len(datasets) > 2 and datasets[2].get("metric") == "DMA200":
                            chart_df["DMA200"] = [clean_num(p[1]) for p in datasets[2].get("values", [])]
        except Exception:
            pass

    res = {
        "ticker": ticker,
        "name": name,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "chart_window_days": 365,
        "is_live": True,
        "source_label": "Screener Consolidated" if "/consolidated/" in final_url else "Screener Standalone",
        "about": about_text,
        "cmp": cmp,
        "mcap_cr": mcap_cr,
        "pe": pe,
        "book_value": book_value,
        "roce": roce,
        "roe": roe,
        "face_value": face_value,
        "shares_cr": shares_cr,
        "ttm_pat": ttm_pat,
        "ttm_sales": ttm_sales,
        "ttm_eps": round(ttm_eps, 2),
        "ttm_eps_sum": round(ttm_eps_sum, 2) if (ttm_eps_sum is not None) else None,
        "last_4_quarters": last_4_quarters,
        "q_headers": q_headers,
        "q_data": q_data,
        "pl_headers": pl_headers,
        "pl_data": pl_data,
        "bs_headers": bs_headers,
        "bs_data": bs_data,
        "cf_headers": cf_headers,
        "cf_data": cf_data,
        "rat_headers": rat_headers,
        "rat_data": rat_data,
        "sh_headers": sh_headers,
        "sh_data": sh_data,
        "trend_years": trend_years,
        "rev_history": rev_history,
        "pat_history": pat_history,
        "cfo_history": cfo_history,
        "fcf_history": fcf_history,
        "latest_debt": latest_debt,
        "latest_debtor_days": latest_debtor_days,
        "total_assets": bs_total_assets,
        "equity_capital": bs_equity_capital,
        "reserves": bs_reserves,
        "other_assets": bs_other_assets,
        "other_liabilities": bs_other_liabilities,
        "ebit": ebit_fy,
        "concalls": concalls,
        "peer_npms": peer_npms,
        "peer_names": peer_names,
        "chart_df": chart_df,
        "sales_growth_3yr": growth_ranges.get("sales_growth_3yr"),
        "sales_growth_5yr": growth_ranges.get("sales_growth_5yr"),
        "sales_growth_ttm": growth_ranges.get("sales_growth_ttm"),
        "profit_growth_3yr": growth_ranges.get("profit_growth_3yr"),
        "profit_growth_5yr": growth_ranges.get("profit_growth_5yr"),
        "roe_3yr": growth_ranges.get("roe_3yr")
    }
    _cache_put(ticker, res)
    if orig_ticker and orig_ticker != ticker:
        _cache_put(orig_ticker, res)
    return res
