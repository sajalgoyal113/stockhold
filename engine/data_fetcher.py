import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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
    "M&M": "M&M"
}

def resolve_screener_ticker(query: str) -> str:
    cleaned = query.upper().strip()
    if cleaned in COMMON_ALIASES:
        return COMMON_ALIASES[cleaned]
    # Check if direct request works
    try:
        r = requests.get(f"https://www.screener.in/company/{cleaned}/", headers=HEADERS, timeout=5)
        if r.status_code == 200:
            return cleaned
    except Exception:
        pass
    # Try Screener Search API
    try:
        sr = requests.get(f"https://www.screener.in/api/company/search/?q={query}", headers=HEADERS, timeout=6)
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

def fetch_company_data(ticker: str):
    ticker = resolve_screener_ticker(ticker)
    
    # Try consolidated first, fallback to standalone
    urls = [
        f"https://www.screener.in/company/{ticker}/consolidated/",
        f"https://www.screener.in/company/{ticker}/"
    ]
    
    html = None
    final_url = None
    for u in urls:
        try:
            r = requests.get(u, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                html = r.text
                final_url = u
                break
        except Exception:
            continue
            
    if not html:
        raise ValueError(f"Could not fetch data for ticker: {ticker} from Screener.in")

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
            
        # Shares count
        if cmp > 0 and mcap_cr > 0:
            shares_cr = mcap_cr / cmp
            # TTM EPS based on current diluted share count:
            ttm_eps = ttm_pat / shares_cr if shares_cr > 0 else ttm_eps_sum
        else:
            shares_cr = 0.0
            ttm_eps = ttm_eps_sum
    else:
        # Fallback to P&L TTM
        shares_cr = (mcap_cr / cmp) if cmp > 0 else 0.0
        ttm_eps = clean_num(pl_data.get("EPS in Rs", ["0"])[-1]) if "EPS in Rs" in pl_data else 0.0
        ttm_pat = clean_num(pl_data.get("Net Profit", ["0"])[-1]) if "Net Profit" in pl_data else 0.0
        ttm_sales = clean_num(pl_data.get("Sales", ["0"])[-1]) if "Sales" in pl_data else 0.0

    if ttm_eps <= 0 and pe > 0 and cmp > 0:
        ttm_eps = cmp / pe

    # 6. Extract 4-Year Trend Metrics for Forensics
    trend_years = pl_headers[-5:-1] if pl_headers and len(pl_headers) >= 5 else (pl_headers or ["FY23", "FY24", "FY25", "FY26"])
    # Clean year names
    trend_years = [y.replace("Mar ", "FY") for y in trend_years if any(c.isdigit() for c in y)][-4:]
    if len(trend_years) < 4:
        trend_years = ["FY23", "FY24", "FY25", "FY26"]

    rev_history = [clean_num(v) for v in pl_data.get("Sales", [])[-4:]]
    pat_history = [clean_num(v) for v in pl_data.get("Net Profit", [])[-4:]]
    cfo_history = [clean_num(v) for v in cf_data.get("Cash from Operating Activity", [])[-4:]]
    fcf_history = [clean_num(v) for v in cf_data.get("Free Cash Flow", [])[-4:]]
    
    # Borrowings and Cash from Balance sheet
    borrowings_arr = [clean_num(v) for v in bs_data.get("Borrowings", [])]
    latest_debt = borrowings_arr[-1] if borrowings_arr else 0.0
    
    # Debtor days
    debtor_days_arr = [clean_num(v) for v in rat_data.get("Debtor Days", [])]
    latest_debtor_days = debtor_days_arr[-1] if debtor_days_arr else 60.0
    
    # 7. Price Chart History (from Screener Chart API)
    chart_df = pd.DataFrame()
    if company_id:
        try:
            chart_url = f"https://www.screener.in/api/company/{company_id}/chart/?q=Price-DMA50-DMA200-Volume&days=365"
            cr = requests.get(chart_url, headers=HEADERS, timeout=8)
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

    return {
        "ticker": ticker,
        "name": name,
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
        "chart_df": chart_df
    }
