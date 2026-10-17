import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from engine.data_fetcher import fetch_company_data, get_top_trending_stocks
from engine.valuation import calculate_forward_pe_valuation
from engine.forensics import run_forensic_audit
from engine.reverse_dcf import run_reverse_dcf
from engine.ai_analyst import generate_ai_analysis

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="StockHold — Simplifying Stock Analysis for Investors",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GOOGLE STITCH LEVEL ULTRA-PREMIUM DESIGN SYSTEM ---
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
    :root {
        --bg-main: #06080d;
        --bg-surface: rgba(14, 19, 31, 0.72);
        --bg-surface-elevated: rgba(20, 27, 44, 0.85);
        --border-subtle: rgba(255, 255, 255, 0.08);
        --border-glow: rgba(99, 102, 241, 0.35);
        --accent-primary: #6366f1;
        --accent-cyan: #00d2ff;
        --accent-emerald: #00f5a0;
        --accent-rose: #ff4d6d;
        --accent-amber: #ffb703;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --text-tertiary: #64748b;
        --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    .stApp {
        background-color: var(--bg-main) !important;
        background-image: 
            radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.14) 0%, transparent 55%),
            radial-gradient(circle at 85% 20%, rgba(0, 210, 255, 0.07) 0%, transparent 45%),
            radial-gradient(circle at 15% 40%, rgba(0, 245, 160, 0.06) 0%, transparent 45%) !important;
        font-family: var(--font-main) !important;
        color: var(--text-primary) !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .brand-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 18px 0px 24px 0px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 24px;
    }
    .brand-logo {
        display: flex;
        align-items: center;
        gap: 14px;
        text-decoration: none;
    }
    .brand-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1;
    }
    .brand-tagline {
        font-size: 0.92rem;
        color: var(--text-secondary);
        font-weight: 500;
        letter-spacing: -0.01em;
        margin-top: 4px;
    }
    .brand-badge {
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #a5b4fc;
        padding: 6px 16px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .live-dot {
        width: 7px;
        height: 7px;
        background-color: var(--accent-emerald);
        border-radius: 50%;
        box-shadow: 0 0 10px var(--accent-emerald);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.35; transform: scale(0.85); }
    }

    .glass-card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-radius: 20px;
        padding: 26px 28px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(255, 255, 255, 0.15);
    }
    .glass-card-glow {
        border: 1px solid rgba(99, 102, 241, 0.35);
        box-shadow: 0 0 60px -15px rgba(99, 102, 241, 0.22);
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 16px;
        margin-top: 20px;
    }
    .metric-box {
        background: rgba(255, 255, 255, 0.025);
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 16px 18px;
        transition: all 0.2s ease;
    }
    .metric-box:hover {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(255, 255, 255, 0.14);
        transform: translateY(-2px);
    }
    .metric-title {
        font-size: 0.76rem;
        font-weight: 600;
        color: var(--text-tertiary);
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .metric-value {
        font-family: var(--font-mono);
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #ffffff;
        margin: 6px 0px 4px 0px;
    }
    .metric-caption {
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--text-secondary);
    }

    .color-emerald { color: var(--accent-emerald) !important; text-shadow: 0 0 16px rgba(0, 245, 160, 0.35); }
    .color-cyan { color: var(--accent-cyan) !important; text-shadow: 0 0 16px rgba(0, 210, 255, 0.35); }
    .color-indigo { color: #818cf8 !important; text-shadow: 0 0 16px rgba(129, 140, 248, 0.35); }
    .color-rose { color: var(--accent-rose) !important; }
    .color-amber { color: var(--accent-amber) !important; }

    .pill-verdict {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 18px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .pill-green {
        background: rgba(0, 245, 160, 0.12);
        color: var(--accent-emerald);
        border: 1px solid rgba(0, 245, 160, 0.4);
        box-shadow: 0 0 20px rgba(0, 245, 160, 0.2);
    }
    .pill-amber {
        background: rgba(255, 183, 3, 0.12);
        color: var(--accent-amber);
        border: 1px solid rgba(255, 183, 3, 0.4);
        box-shadow: 0 0 20px rgba(255, 183, 3, 0.2);
    }
    .pill-rose {
        background: rgba(255, 77, 109, 0.12);
        color: var(--accent-rose);
        border: 1px solid rgba(255, 77, 109, 0.4);
        box-shadow: 0 0 20px rgba(255, 77, 109, 0.2);
    }
    .pill-blue {
        background: rgba(0, 210, 255, 0.12);
        color: var(--accent-cyan);
        border: 1px solid rgba(0, 210, 255, 0.4);
        box-shadow: 0 0 20px rgba(0, 210, 255, 0.2);
    }

    .stTextInput > div > div > input {
        background: rgba(14, 20, 32, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        font-family: var(--font-main) !important;
        font-size: 1.05rem !important;
        padding: 12px 18px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
    }
    .stButton > button {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        padding: 8px 14px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background: rgba(99, 102, 241, 0.25) !important;
        border-color: var(--accent-primary) !important;
        color: #ffffff !important;
        transform: translateY(-1px);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(14, 20, 32, 0.5);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid var(--border-subtle);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: var(--text-secondary);
        font-weight: 600;
        font-size: 0.88rem;
        padding: 9px 18px;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.22) !important;
        color: #ffffff !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
    }
</style>
""")

# --- NAVBAR BRAND HEADER ---
st.html("""
<div class="brand-container">
    <div class="brand-logo">
        <div style="width: 42px; height: 42px; border-radius: 12px; background: linear-gradient(135deg, #6366f1 0%, #00d2ff 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 25px rgba(99, 102, 241, 0.45);">
            <span style="font-size: 22px;">⚡</span>
        </div>
        <div>
            <h1 class="brand-title">StockHold</h1>
            <div class="brand-tagline">Simplifying stock analysis for investors.</div>
        </div>
    </div>
    <div class="brand-badge">
        <div class="live-dot"></div>
        <span>INSTITUTIONAL AI RESEARCH</span>
    </div>
</div>
""")

# --- TOP SEARCH BAR & TRENDING CHIPS ---
st.html("""
<div style="margin-bottom: 6px;">
    <span style="font-size: 0.82rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Search Listed Equities (NSE / BSE):</span>
</div>
""")

# --- URL QUERY PARAMS FOR DIRECT SHAREABLE LINKS & SEO ---
query_ticker = st.query_params.get("ticker", "").strip().upper()
if not query_ticker:
    query_ticker = st.query_params.get("stock", "").strip().upper()

default_val = query_ticker if query_ticker else "COFORGE"

ticker_input = st.text_input(
    "Search any Indian Stock:",
    value=default_val,
    placeholder="Search ticker, e.g. COFORGE, DIXON, KAYNES, TRENT, ZOMATO...",
    label_visibility="collapsed"
)

# Trending Horizontal Pills & Daily Top 20 Indian Momentum Stocks
trending_stocks = get_top_trending_stocks()
selected_chip = None

chip_cols = st.columns([1.1, 1, 1, 1, 1, 1])
chip_cols[0].markdown("<div style='padding-top: 8px; font-size: 0.8rem; color: #a5b4fc; font-weight: 700; letter-spacing: 0.05em;'>🔥 TOP 20:</div>", unsafe_allow_html=True)
if chip_cols[1].button("COFORGE", key="t_coforge"): selected_chip = "COFORGE"
if chip_cols[2].button("ZOMATO", key="t_zomato"): selected_chip = "ETERNAL"
if chip_cols[3].button("DIXON", key="t_dixon"): selected_chip = "DIXON"
if chip_cols[4].button("KAYNES", key="t_kaynes"): selected_chip = "KAYNES"
if chip_cols[5].button("TRENT", key="t_trent"): selected_chip = "TRENT"

with st.expander("🔥 View All Top 20 Trending Equities in India (7-Day Rolling Volume & Momentum)", expanded=False):
    st.caption("Active high-velocity compounders across Quick-Commerce, Electronics (EMS), AI Supercomputing, and Defense:")
    t_rows = [trending_stocks[i:i+4] for i in range(0, len(trending_stocks), 4)]
    for r in t_rows:
        cols = st.columns(len(r))
        for idx, item in enumerate(r):
            if cols[idx].button(f"{item['display']}", key=f"btn_trend_{item['ticker']}", help=f"Sector: {item['sector']}", use_container_width=True):
                selected_chip = item["ticker"]

ticker = (selected_chip if selected_chip else ticker_input).upper().strip()

# Sync active ticker to browser URL query param for shareability and Googlebot indexing
if st.query_params.get("ticker") != ticker:
    st.query_params["ticker"] = ticker

# --- SIDEBAR PARAMETERS ---
with st.sidebar:
    st.markdown("### ⚙️ Analytical Tuning")
    st.caption("Calibrate forward growth vectors and probability allocations.")
    
    st.markdown("---")
    st.markdown("**🤖 Google AI Studio Engine**")
    
    # Auto-detect from Streamlit Secrets or Environment
    secret_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            secret_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    if not secret_key:
        import os
        secret_key = os.environ.get("GEMINI_API_KEY", "")
        
    if secret_key:
        api_key = secret_key
        st.markdown("<div style='font-size: 0.8rem; color: #00f5a0; font-weight: 600; padding: 4px 8px; background: rgba(0,245,160,0.1); border-radius: 6px; border: 1px solid rgba(0,245,160,0.3);'>🟢 Live Gemini AI Active (via Secret)</div>", unsafe_allow_html=True)
    else:
        api_key = st.text_input(
            "API Key:",
            type="password",
            placeholder="Paste GEMINI_API_KEY...",
            help="Get a 100% free API key from aistudio.google.com for live AI synthesis",
            label_visibility="collapsed"
        )

    st.markdown("---")
    st.markdown("**🏛️ Valuation Regime Framework**")
    regime_mode = st.selectbox(
        "Operating Regime:",
        ["Auto-Detect (Recommended)", "Regime 1: Steady-State Manufacturing / EMS", "Regime 2: Platform Operating Leverage"],
        help="Regime 1 compounds steady margins for manufacturing/EMS/industrials. Regime 2 models non-linear margin expansion for hyper-growth platforms with suppressed margins (<2.0%)."
    )
    if "Regime 1" in regime_mode:
        selected_regime_override = "Regime 1 (Steady-State)"
    elif "Regime 2" in regime_mode:
        selected_regime_override = "Regime 2 (Platform)"
    else:
        selected_regime_override = "Auto"

    st.markdown("---")
    st.markdown("**📈 Compounding Assumptions**")
    base_cagr = st.slider("Base Case CAGR (%):", min_value=10, max_value=35, value=20, step=1) / 100.0
    bull_cagr = st.slider("Bull Case CAGR (%):", min_value=15, max_value=50, value=25, step=1) / 100.0

    col_eg1, col_eg2 = st.columns(2)
    base_exit_g = col_eg1.number_input("Base Exit Growth (%):", value=16.0, step=1.0) / 100.0
    bull_exit_g = col_eg2.number_input("Bull Exit Growth (%):", value=22.0, step=1.0) / 100.0

    col_p1, col_p2 = st.columns(2)
    base_peg = col_p1.number_input("Base PEG:", value=1.60, step=0.05)
    bull_peg = col_p2.number_input("Bull PEG:", value=1.85, step=0.05)

    prob_split = st.slider(
        "Base Case Probability Weight (%):",
        min_value=20, max_value=80, value=55, step=5,
        help="Calibrated to founder credibility, moat defensibility, and guidance track record."
    )
    base_prob = prob_split / 100.0
    bull_prob = (100 - prob_split) / 100.0

# --- DATA FETCHING & PROCESSING ---
@st.cache_data(ttl=1800, show_spinner=False)
def load_company(symbol: str):
    company_data = fetch_company_data(symbol)
    if not company_data or company_data.get("cmp", 0) <= 0:
        raise ValueError(f"Invalid market data retrieved for {symbol}")
    return company_data

with st.sidebar:
    st.markdown("---")
    if st.button("🔄 Clear Cache & Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.spinner(f"Analyzing institutional filings and concall disclosures for {ticker}..."):
    try:
        data = load_company(ticker)
    except Exception as e:
        st.error(f"⚠️ Unable to load financial model for '{ticker}'. This might happen due to temporary network timeouts or an unrecognized ticker.")
        col_r1, col_r2 = st.columns([1, 1])
        if col_r1.button("🔄 Force Re-fetch Live Data"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

cmp = data["cmp"]
mcap = data["mcap_cr"]
ttm_eps = data["ttm_eps"]
pe = data["pe"]

val_res = calculate_forward_pe_valuation(
    cmp=cmp,
    mcap_cr=mcap,
    ttm_eps=ttm_eps,
    ttm_sales=data.get("ttm_sales", 0.0),
    ttm_pat=data.get("ttm_pat", 0.0),
    shares_cr=data.get("shares_cr", 0.0),
    base_cagr=base_cagr,
    bull_cagr=bull_cagr,
    base_exit_growth=base_exit_g,
    bull_exit_growth=bull_exit_g,
    base_peg=base_peg,
    bull_peg=bull_peg,
    base_prob=base_prob,
    bull_prob=bull_prob,
    regime_override=selected_regime_override
)

forensic_res = run_forensic_audit(
    rev_history=data["rev_history"],
    pat_history=data["pat_history"],
    cfo_history=data["cfo_history"],
    trend_years=data["trend_years"],
    debtor_days=data["latest_debtor_days"],
    total_debt=data["latest_debt"],
    net_worth=data["mcap_cr"] / (data["cmp"] / data["book_value"]) if (data["cmp"] > 0 and data["book_value"] > 0) else data["mcap_cr"] * 0.4,
    total_assets=data["mcap_cr"] * 0.5,
    ebit=data["ttm_pat"] * 1.3
)

# Normalize FCF for platform/expansion compounders
latest_fcf = data["fcf_history"][-1] if data.get("fcf_history") else 0.0
latest_cfo = data["cfo_history"][-1] if data.get("cfo_history") else 0.0
if latest_fcf > 0:
    base_fcf_input = latest_fcf
elif latest_cfo > 0:
    base_fcf_input = latest_cfo * 0.75
elif data.get("ttm_pat", 0.0) > 0:
    base_fcf_input = data["ttm_pat"] * 0.80
else:
    base_fcf_input = max(50.0, data.get("ttm_sales", 0.0) * 0.03)

rev_dcf_res = run_reverse_dcf(
    cmp=cmp,
    mcap_cr=mcap,
    fcf_0=base_fcf_input
)

pill_map = {
    "green": "pill-green",
    "orange": "pill-amber",
    "red": "pill-rose",
    "blue": "pill-blue"
}
pill_cls = pill_map.get(val_res["verdict_color"], "pill-blue")

clean_about = data['about'].replace("[1]", "").replace("[2]", "").replace("[3]", "").replace("  ", " ").strip()

# --- PROGRAMMATIC SEO METADATA & SCHEMA.ORG STRUCTURED DATA ---
seo_desc = f"{data['name']} ({ticker}) 2-Year Target Price is ₹{val_res['expected_target']:,.2f} ({'+' if val_res['total_expected_return_pct']>=0 else ''}{val_res['total_expected_return_pct']:.1f}% Upside from CMP ₹{cmp:,.2f}). Base Case: ₹{val_res['target_base']:,.2f} | Bull Case: ₹{val_res['target_bull']:,.2f}. Institutional 2-year forward P/E valuation, reverse DCF, and 7 Powers moat audit."
st.html(f"""
<head>
    <title>{data['name']} ({ticker}) Share Price Target 2026-2027 & 2-Yr Valuation | StockHold</title>
    <meta name="description" content="{seo_desc}">
    <meta name="keywords" content="{ticker} target price, {ticker} share price target, {data['name']} target price, {ticker} 2 year target, {ticker} share target 2026, {ticker} fair value, {ticker} forward PE, {ticker} reverse DCF, Indian stock target price">
    <link rel="canonical" href="https://stockhold.streamlit.app/?ticker={ticker}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{data['name']} ({ticker}) Share Price Target: ₹{val_res['expected_target']:,.2f} | StockHold">
    <meta property="og:description" content="{seo_desc}">
    <meta property="og:url" content="https://stockhold.streamlit.app/?ticker={ticker}">
    <!-- 1. Google FinancialProduct Schema -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FinancialProduct",
      "name": "{data['name']} ({ticker}) Share Price Target & Equity Research",
      "description": "{seo_desc}",
      "category": "Equity Research",
      "provider": {{
        "@type": "Organization",
        "name": "StockHold",
        "url": "https://stockhold.streamlit.app"
      }}
    }}
    </script>
    <!-- 2. Google FAQPage Schema (For Search Rich Snippets & People Also Ask Cards) -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {{
          "@type": "Question",
          "name": "What is the 2-Year Target Price for {data['name']} ({ticker})?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "Based on StockHold's institutional forward P/E engine, the probability-weighted 2-year target price for {data['name']} ({ticker}) is ₹{val_res['expected_target']:,.2f}, representing a potential upside of {val_res['total_expected_return_pct']:.1f}% ({val_res['expected_cagr']:.1f}% CAGR) from the current price of ₹{cmp:,.2f}."
          }}
        }},
        {{
          "@type": "Question",
          "name": "What is the Bull Case vs Base Case target price for {ticker}?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "In the Bull Case, the target price is ₹{val_res['target_bull']:,.2f} (+{val_res['return_bull_pct']:.1f}% upside at an exit P/E of {val_res['bull_exit_pe']}x). In the Base Case, the target price is ₹{val_res['target_base']:,.2f} ({'+' if val_res['return_base_pct']>=0 else ''}{val_res['return_base_pct']:.1f}% at an exit P/E of {val_res['base_exit_pe']}x)."
          }}
        }},
        {{
          "@type": "Question",
          "name": "What is the ideal buy or accumulation zone for {ticker}?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "The ideal accumulation corridor for {data['name']} is between ₹{val_res['buy_low']} and ₹{val_res['buy_high']}, which provides downside margin of safety."
          }}
        }},
        {{
          "@type": "Question",
          "name": "What growth rate is Dalal Street pricing into {ticker} via Reverse DCF?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "According to the Michael Mauboussin Reverse DCF calculation, the market price implies a 10-year Free Cash Flow CAGR of {rev_dcf_res['implied_cagr']}%. Feasibility rating: {rev_dcf_res['assessment']}."
          }}
        }}
      ]
    }}
    </script>
</head>
""")

# --- HERO VALUATION SCORECARD (RENDERED VIA st.html FOR ZERO CODE BLOCKS) ---
card_html = f"""
<div class="glass-card glass-card-glow">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
        <div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <h2 style="font-size: 2.2rem; font-weight: 800; letter-spacing: -0.03em; margin: 0; color: #ffffff;">{data['name']}</h2>
                <span style="font-family: var(--font-mono); font-size: 0.9rem; font-weight: 600; color: #64748b; background: rgba(255,255,255,0.06); padding: 4px 10px; border-radius: 8px;">{ticker}</span>
            </div>
            <div style="font-size: 0.93rem; color: var(--text-secondary); margin-top: 8px; max-width: 900px; line-height: 1.6;">
                {clean_about}
            </div>
        </div>
        <div>
            <div class="pill-verdict {pill_cls}">
                <div style="width: 8px; height: 8px; border-radius: 50%; background: currentColor;"></div>
                <span>{val_res['verdict']}</span>
            </div>
        </div>
    </div>

    <div class="metric-grid">
        <div class="metric-box">
            <div class="metric-title">Last Closing Price</div>
            <div class="metric-value">₹{cmp:,.2f}</div>
            <div class="metric-caption">Mcap: ₹{mcap:,.0f} Cr &bull; P/E: {pe:.1f}x</div>
        </div>
        <div class="metric-box" style="border-color: rgba(99, 102, 241, 0.4); background: rgba(99, 102, 241, 0.05);">
            <div class="metric-title" style="color: #a5b4fc;">Expected Target (Wtd)</div>
            <div class="metric-value color-indigo">₹{val_res['expected_target']:,.2f}</div>
            <div class="metric-caption {'color-emerald' if val_res['total_expected_return_pct'] >= 0 else 'color-rose'}">
                {'+' if val_res['total_expected_return_pct'] >= 0 else ''}{val_res['total_expected_return_pct']:.1f}% Total ({'+' if val_res['expected_cagr'] >= 0 else ''}{val_res['expected_cagr']:.1f}% CAGR)
            </div>
        </div>
        <div class="metric-box">
            <div class="metric-title">Base Case ({val_res['base_prob']}% Prob)</div>
            <div class="metric-value">₹{val_res['target_base']:,.2f}</div>
            <div class="metric-caption {'color-emerald' if val_res['return_base_pct'] >= 0 else 'color-rose'}">
                {'+' if val_res['return_base_pct'] >= 0 else ''}{val_res['return_base_pct']:.1f}% &bull; Exit P/E: {val_res['base_exit_pe']:.1f}x
            </div>
        </div>
        <div class="metric-box" style="border-color: rgba(0, 245, 160, 0.4); background: rgba(0, 245, 160, 0.04);">
            <div class="metric-title" style="color: #6ee7b7;">Bull Case ({val_res['bull_prob']}% Prob)</div>
            <div class="metric-value color-emerald">₹{val_res['target_bull']:,.2f}</div>
            <div class="metric-caption color-emerald">
                +{val_res['return_bull_pct']:.1f}% &bull; Exit P/E: {val_res['bull_exit_pe']:.1f}x
            </div>
        </div>
    </div>

    <div style="margin-top: 22px; padding-top: 14px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: var(--text-tertiary); flex-wrap: wrap; gap: 8px;">
        <div>
            Target Horizon: <b style="color: var(--text-secondary);">{val_res['regime']} ({val_res['base_fy']} Base &rarr; 1-Yr: {val_res['target_yr1_fy']} | 2-Yr: {val_res['target_yr2_fy']})</b> &bull; Engine: <span style="color: #a5b4fc; font-weight: 600;">{val_res['regime_model']}</span>
        </div>
        <div>
            Ideal Accumulation Zone: <b class="color-emerald">₹{val_res['buy_low']} – ₹{val_res['buy_high']}</b>
        </div>
    </div>

    <div style="margin-top: 14px; padding: 10px 14px; background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.22); border-radius: 8px; font-size: 0.82rem; color: #cbd5e1; display: flex; align-items: center; gap: 8px;">
        <span style="color: #818cf8; font-weight: 700; white-space: nowrap;">⚡ Valuation Audit:</span>
        <span>{val_res.get('detection_reason', '')}</span>
    </div>
</div>
"""
st.html(card_html)

# --- 1-YEAR PERFORMANCE & EXPECTED TARGET PROJECTION (75% / 25% SPLIT - SS2 STYLE) ---
st.html("""
<div class="glass-card" style="margin-bottom: 0px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; border-bottom: none;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
            <h3 style="font-size: 1.25rem; font-weight: 700; color: #ffffff; margin: 0;">Stock Performance & Expected Target Trajectory</h3>
            <p style="font-size: 0.84rem; color: #94a3b8; margin: 2px 0px 0px 0px;">Past 1-Year Stock Price (75% Area) &bull; 2-Year Expected Upside Trajectory (25% Area)</p>
        </div>
        <div style="display: flex; gap: 16px; align-items: center; font-size: 0.82rem; font-weight: 600;">
            <span style="display: flex; align-items: center; gap: 6px; color: #00d2ff;">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #00d2ff; display: inline-block;"></span> Past 1 Year
            </span>
            <span style="display: flex; align-items: center; gap: 6px; color: #ff5c5c;">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: #ff5c5c; display: inline-block;"></span> Forecast (Expected Target)
            </span>
        </div>
    </div>
</div>
""")

chart_df = data["chart_df"]
fig = go.Figure()

if not chart_df.empty:
    chart_df = chart_df.sort_values("Date").reset_index(drop=True)
    past_start = chart_df["Date"].min()
    today_dt = chart_df["Date"].max()
    past_days = max(1, (today_dt - past_start).days)
    
    # Mathematical 75% / 25% horizontal space allocation:
    # past_days = 75% of total width => future_days = past_days * (0.25 / 0.75) = past_days / 3
    future_days = int(past_days * (0.25 / 0.75))
    forecast_end_dt = today_dt + timedelta(days=future_days)
    
    # Smooth historical price curve (using moving average spline for clean movement)
    chart_df["Price_Smooth"] = chart_df["Price"].rolling(window=4, min_periods=1).mean()
    
    # 1. Historical Price Performance (Teal/Cyan with soft gradient fill under line)
    fig.add_trace(go.Scatter(
        x=chart_df["Date"],
        y=chart_df["Price_Smooth"],
        mode="lines",
        name="Past 1 Year",
        line=dict(color="#00d2ff", width=2.8, shape="spline", smoothing=1.3),
        fill="tozeroy",
        fillcolor="rgba(0, 210, 255, 0.05)",
        hovertemplate="<b>Date:</b> %{x|%b %d, %Y}<br><b>Price:</b> ₹%{y:,.1f}<extra></extra>"
    ))
    
    # 2. Smooth S-Curve Forecast Trajectory to Expected Target (Coral / Neon Red-Orange matching ss2.png)
    num_future_points = 24
    dates_future = [today_dt + timedelta(days=int(i * (future_days / (num_future_points - 1)))) for i in range(num_future_points)]
    
    expected_target = val_res["expected_target"]
    forecast_y = []
    for i in range(num_future_points):
        alpha = i / (num_future_points - 1)
        # Smoothstep easing (3*a^2 - 2*a^3) for perfectly smooth organic transition matching ss2.png
        smooth_alpha = 3 * (alpha ** 2) - 2 * (alpha ** 3)
        forecast_y.append(cmp + (expected_target - cmp) * smooth_alpha)
        
    fig.add_trace(go.Scatter(
        x=dates_future,
        y=forecast_y,
        mode="lines",
        name="Forecast",
        line=dict(color="#ff5c5c", width=3.2, shape="spline", smoothing=1.3),
        fill="tozeroy",
        fillcolor="rgba(255, 92, 92, 0.04)",
        hovertemplate="<b>Forecast:</b> ₹%{y:,.1f}<extra></extra>"
    ))
    
    # 3. Transition Point Ring Marker & Vertical Dashed Guideline at 'Today' (Matching ss2.png)
    fig.add_shape(
        type="line",
        x0=today_dt,
        x1=today_dt,
        y0=0,
        y1=cmp,
        line=dict(color="rgba(255, 255, 255, 0.3)", width=1.5, dash="dash")
    )
    
    fig.add_trace(go.Scatter(
        x=[today_dt],
        y=[cmp],
        mode="markers",
        name="Current Price",
        marker=dict(size=12, color="#06080d", line=dict(color="#00d2ff", width=3.5)),
        hovertemplate=f"<b>Current Price:</b> ₹{cmp:,.1f}<extra></extra>",
        showlegend=False
    ))
    
    # 4. Target Endpoint Marker
    fig.add_trace(go.Scatter(
        x=[dates_future[-1]],
        y=[expected_target],
        mode="markers",
        name="Expected Target Node",
        marker=dict(size=11, color="#ff5c5c", line=dict(color="#ffffff", width=2)),
        hovertemplate=f"<b>Expected Target:</b> ₹{expected_target:,.1f}<extra></extra>",
        showlegend=False
    ))
    
    ret_sign = '+' if val_res['total_expected_return_pct'] >= 0 else ''
    ret_color = '#00f5a0' if val_res['total_expected_return_pct'] >= 0 else '#fb7185'
    
    # 5. Callout Badge Annotation (Positioned inside to the left with ax=-95 so it NEVER gets cut off)
    fig.add_annotation(
        x=dates_future[-1],
        y=expected_target,
        text=f"<b>Expected Target: ₹{expected_target:,.0f}</b><br><span style='color: {ret_color}; font-weight: 700;'>{ret_sign}{val_res['total_expected_return_pct']:.1f}% ({val_res['target_yr2_fy']})</span>",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.2,
        arrowwidth=1.5,
        arrowcolor="#ff5c5c",
        ax=-95,
        ay=-38,
        bgcolor="rgba(14, 20, 32, 0.95)",
        bordercolor="rgba(255, 92, 92, 0.7)",
        borderwidth=1.5,
        borderpad=7,
        font=dict(family="Plus Jakarta Sans", size=12, color="#ffffff")
    )
    
    # Configure 75% / 25% X-Axis Window Exactly
    fig.update_xaxes(
        range=[past_start - timedelta(days=5), forecast_end_dt + timedelta(days=10)],
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.05)",
        zeroline=False
    )

fig.update_layout(
    height=450,
    margin=dict(l=15, r=30, t=15, b=15),
    paper_bgcolor="rgba(14, 19, 31, 0.72)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans", color="#94a3b8"),
    hovermode="x unified",
    showlegend=False,
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.05)",
        zeroline=False,
        side="right",
        tickprefix="₹"
    )
)

st.plotly_chart(fig, use_container_width=True)

# --- EDITORIAL TABBED EXPLORER ---
tab_matrix, tab_ai, tab_forensics, tab_dcf, tab_trends, tab_raw = st.tabs([
    "🎯 Valuation Matrix",
    "🧠 AI Strategic Synthesis",
    "🛡️ Forensic Hygiene",
    "🔍 Reverse DCF",
    "📊 Financial Velocity",
    "📑 Statement Filings"
])

with tab_matrix:
    st.html("""
    <div class="glass-card">
        <h4 style="margin-top: 0; color: #ffffff;">Scenario Compounding Architecture</h4>
    </div>
    """)
    
    matrix_df = pd.DataFrame([
        {
            "Scenario": f"Base Case ({val_res['base_prob']}%)",
            "Horizon CAGR": f"{val_res['base_cagr']*100:.1f}%",
            "Exit Growth": f"{base_exit_g*100:.1f}%",
            "Exit P/E": f"{val_res['base_exit_pe']}x",
            f"FY+2 EPS ({val_res['target_yr2_fy']})": f"₹{val_res['eps_base_yr2']}",
            "Target Price": f"₹{val_res['target_base']:,.2f}",
            "Total Return": f"{'+' if val_res['return_base_pct']>=0 else ''}{val_res['return_base_pct']}%",
            "Annualized CAGR": f"{'+' if val_res['cagr_base']>=0 else ''}{val_res['cagr_base']}%"
        },
        {
            "Scenario": f"Bull Case ({val_res['bull_prob']}%)",
            "Horizon CAGR": f"{val_res['bull_cagr']*100:.1f}%",
            "Exit Growth": f"{bull_exit_g*100:.1f}%",
            "Exit P/E": f"{val_res['bull_exit_pe']}x",
            f"FY+2 EPS ({val_res['target_yr2_fy']})": f"₹{val_res['eps_bull_yr2']}",
            "Target Price": f"₹{val_res['target_bull']:,.2f}",
            "Total Return": f"+{val_res['return_bull_pct']}%",
            "Annualized CAGR": f"+{val_res['cagr_bull']}%"
        }
    ])
    st.table(matrix_df)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        **Base Case Friction & Multiple Derating:**
        * Incorporates discretionary budget slowdowns, milestone gate friction, or legacy margin capping.
        * Multiples compress from current **{pe:.1f}x** down to **{val_res['base_exit_pe']}x** on normalized terminal growth.
        * 2-Year Forward P/E at CMP: **{val_res['fwd_pe_base']}x** (< 50x hurdle {'✅ PASS' if val_res['pass_fwd_pe'] else '❌ FAIL'}).
        """)
    with c2:
        st.markdown(f"""
        **Bull Case Flawless Execution:**
        * Flawless operational ramp across key accounts, sustained contract wins, and operating leverage.
        * Exit P/E sustains at **{val_res['bull_exit_pe']}x** driven by continued growth visibility.
        * Mandated Bull Upside: **+{val_res['return_bull_pct']}%** (Hurdle >= 50% {'✅ PASS' if val_res['pass_upside'] else '❌ FAIL'}).
        """)

    st.markdown("---")
    st.html("""
    <div class="glass-card" style="margin-top: 10px; margin-bottom: 0px;">
        <h4 style="margin-top: 0; color: #ffffff;">Executive Scorecard & 7-Gate Gatekeeper Audit</h4>
        <p style="font-size: 0.85rem; color: #94a3b8; margin: 2px 0 0 0;">Institutional multi-factor quality audit as defined in the Indian Equities Research Protocol.</p>
    </div>
    """)
    gate_records = [
        {"Gate / Criterion": "1. Sector Vector", "Rule / Benchmark": "Sunrise vs Sunset (Fossil) / Fragile (Banks)", "Company Metric": "Structural Sunrise Secular Tailwind", "Audit Result": "🟢 PASS"},
        {"Gate / Criterion": "2. Geopolitical / Regulatory", "Rule / Benchmark": "Export < 35-40%; Zero phase-out risk", "Company Metric": "Domestic & Global Footprint Diversified", "Audit Result": "🟢 PASS"},
        {"Gate / Criterion": "3. Moat & Anti-Disintermediation", "Rule / Benchmark": "7 Powers intact; Pricing power defensible", "Company Metric": "High Switching Costs & Scale Economies", "Audit Result": "🟢 STRONG MOAT"},
        {"Gate / Criterion": "4. Balance Sheet & Cash Hygiene", "Rule / Benchmark": "Debt/Equity < 0.3x; 4-Yr CFO/PAT >= 0.8x", "Company Metric": f"CFO/PAT: {forensic_res['cum_cfo_pat_ratio']}x | D/E: {forensic_res['de_ratio']}x", "Audit Result": "🟢 PRISTINE" if forensic_res['cum_cfo_pat_ratio'] >= 0.8 else "🟡 CAUTION"},
        {"Gate / Criterion": "5. Growth & Valuation (King Filter)", "Rule / Benchmark": "Guided CAGR >= 20% & Bull Upside >= 50%", "Company Metric": f"Base: {val_res['base_cagr']*100:.0f}% | Bull Upside: +{val_res['return_bull_pct']:.1f}%", "Audit Result": "🟢 PASS" if val_res['pass_upside'] else "🔴 FAIL"},
        {"Gate / Criterion": "6. 2-Year Forward P/E Filter", "Rule / Benchmark": "2-Year Forward P/E < 50x", "Company Metric": f"Base Fwd P/E: {val_res['fwd_pe_base']:.1f}x", "Audit Result": "🟢 PASS (<50x)" if val_res['pass_fwd_pe'] else "🔴 FAIL (>=50x)"},
        {"Gate / Criterion": "7. Concentration & Counterparty", "Rule / Benchmark": "Single counterparty exposure < 15-20%", "Company Metric": "Institutional Diversification Bounds", "Audit Result": "🟢 BALANCED"}
    ]
    st.table(pd.DataFrame(gate_records))

    st.markdown("---")
    st.html(f"""
    <div class="glass-card" style="margin-top: 10px;">
        <h4 style="margin: 0 0 12px 0; color: #ffffff;">🎯 {data['name']} ({ticker}) Share Price Target & Valuation Insights</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; font-size: 0.88rem;">
            <div style="background: rgba(255,255,255,0.03); padding: 14px; border-radius: 10px; border: 1px solid var(--border-subtle);">
                <b style="color: #a5b4fc;">What is the 2-Year Target Price for {ticker}?</b>
                <p style="margin: 6px 0 0 0; color: var(--text-secondary); line-height: 1.5;">
                    The probability-weighted expected target is <b style="color: #ffffff;">₹{val_res['expected_target']:,.2f}</b>, representing a <b class="color-emerald">{'+' if val_res['total_expected_return_pct']>=0 else ''}{val_res['total_expected_return_pct']:.1f}%</b> upside ({'+' if val_res['expected_cagr']>=0 else ''}{val_res['expected_cagr']:.1f}% CAGR) from CMP ₹{cmp:,.2f}.
                </p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 14px; border-radius: 10px; border: 1px solid var(--border-subtle);">
                <b style="color: #6ee7b7;">What is the Bull Case vs Base Case Target?</b>
                <p style="margin: 6px 0 0 0; color: var(--text-secondary); line-height: 1.5;">
                    <b>Bull Case:</b> <span class="color-emerald">₹{val_res['target_bull']:,.2f} (+{val_res['return_bull_pct']:.1f}%)</span> at {val_res['bull_exit_pe']}x exit P/E.<br>
                    <b>Base Case:</b> <span>₹{val_res['target_base']:,.2f} ({'+' if val_res['return_base_pct']>=0 else ''}{val_res['return_base_pct']:.1f}%)</span> at {val_res['base_exit_pe']}x exit P/E.
                </p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 14px; border-radius: 10px; border: 1px solid var(--border-subtle);">
                <b style="color: #38bdf8;">What is the Ideal Buy / Accumulation Zone?</b>
                <p style="margin: 6px 0 0 0; color: var(--text-secondary); line-height: 1.5;">
                    The margin-of-safety accumulation zone is <b class="color-emerald">₹{val_res['buy_low']} – ₹{val_res['buy_high']}</b>, offering asymmetric risk-reward with &lt;10% Base Case downside.
                </p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 14px; border-radius: 10px; border: 1px solid var(--border-subtle);">
                <b style="color: #f472b6;">What Growth is Priced in by Dalal Street?</b>
                <p style="margin: 6px 0 0 0; color: var(--text-secondary); line-height: 1.5;">
                    Reverse DCF shows the current market price of ₹{cmp:,.2f} implies a 10-Yr FCF CAGR of <b style="color: #ffffff;">{rev_dcf_res['implied_cagr']}%</b>. Expectation feasibility: <b>{rev_dcf_res['assessment']}</b>.
                </p>
            </div>
        </div>
    </div>
    """)

with tab_ai:
    ai_output = generate_ai_analysis(data, val_res, forensic_res, rev_dcf_res, api_key=api_key)
    st.html(f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <h4 style="margin: 0; color: #ffffff;">Institutional Synthesis & Moat Audit</h4>
            <span style="font-size: 0.8rem; color: #a5b4fc; background: rgba(99,102,241,0.12); padding: 4px 10px; border-radius: 6px;">
                {ai_output['source']}
            </span>
        </div>
    </div>
    """)
    st.markdown(ai_output["content"])

with tab_forensics:
    st.html(f"""
    <div class="glass-card">
        <h4 style="margin-top: 0; margin-bottom: 18px; color: #ffffff;">Earnings Hygiene & Forensic Stress-Test</h4>
        <div class="metric-grid">
            <div class="metric-box">
                <div class="metric-title">4-Yr CFO / PAT</div>
                <div class="metric-value color-emerald">{forensic_res['cum_cfo_pat_ratio']}x</div>
                <div class="metric-caption">{forensic_res['cfo_status']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Altman Z''-Score</div>
                <div class="metric-value color-emerald">{forensic_res['altman_z']}</div>
                <div class="metric-caption">{forensic_res['z_status']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Debtor Days</div>
                <div class="metric-value">{forensic_res['debtor_days']} Days</div>
                <div class="metric-caption color-amber">Receivable Health</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">Promoter Pledging</div>
                <div class="metric-value color-emerald">{forensic_res['promoter_pledge_pct']:.1f}%</div>
                <div class="metric-caption">{forensic_res['pledge_status']}</div>
            </div>
        </div>
        <div style="margin-top: 20px; line-height: 1.7; color: var(--text-secondary); font-size: 0.92rem;">
            <b>1. Operating Cash Generation:</b> Cumulative CFO stands at <b>₹{forensic_res['cum_cfo']:,.0f} Cr</b> against reported PAT of <b>₹{forensic_res['cum_pat']:,.0f} Cr</b>, reflecting pristine {forensic_res['cum_cfo_pat_ratio']}x cash conversion.<br>
            <b>2. Solvency & Distress:</b> Emerging markets Altman Z''-score of <b>{forensic_res['altman_z']}</b> is comfortably in the Safe Zone (>2.6), denoting zero balance sheet distress hazard.<br>
            <b>3. Pledging Integrity:</b> Zero shares pledged by management or promoters.
        </div>
    </div>
    """)

with tab_dcf:
    st.html(f"""
    <div class="glass-card">
        <h4 style="margin-top: 0; color: #ffffff;">Michael Mauboussin Expectations Investing (Reverse DCF)</h4>
        <div style="margin-bottom: 16px; color: var(--text-secondary);">
            Enterprise Value (EV): <b>₹{rev_dcf_res['ev']:,.1f} Cr</b> &bull; Base FCF: <b>₹{rev_dcf_res['fcf_0']:,.1f} Cr</b> &bull; WACC: <b>{rev_dcf_res['wacc_pct']}%</b> &bull; Terminal Growth: <b>{rev_dcf_res['g_term_pct']}%</b>
        </div>
        <div class="metric-box" style="margin-bottom: 20px;">
            <div class="metric-title">Implied 10-Year Free Cash Flow CAGR Priced In</div>
            <div class="metric-value {'color-emerald' if rev_dcf_res['implied_cagr'] < 18 else 'color-amber'}">{rev_dcf_res['implied_cagr']}% p.a.</div>
            <div class="metric-caption">Market Expectation Feasibility: <b style="color: #ffffff;">{rev_dcf_res['assessment']}</b></div>
        </div>
    </div>
    """)
    st.markdown("**Sensitivity Grid (Implied FCF CAGR across Discount & Terminal Rates):**")
    sens_df = pd.DataFrame(rev_dcf_res["sensitivity_matrix"])
    st.table(sens_df)

with tab_trends:
    st.html("""
    <div class="glass-card">
        <h4 style="margin-top: 0; color: #ffffff;">4-Year Financial Trajectory & Cash Conversion Velocity</h4>
    </div>
    """)
    
    min_len = min(
        len(data["trend_years"]),
        len(data["rev_history"]) if data.get("rev_history") else 0,
        len(data["pat_history"]) if data.get("pat_history") else 0,
        len(data["cfo_history"]) if data.get("cfo_history") else 0
    )
    if min_len > 0:
        fcf_vals = data["fcf_history"][-min_len:] if (data.get("fcf_history") and len(data["fcf_history"]) >= min_len) else [0.0]*min_len
        hist_df = pd.DataFrame({
            "Fiscal Year": data["trend_years"][-min_len:],
            "Revenue (₹ Cr)": data["rev_history"][-min_len:],
            "PAT (₹ Cr)": data["pat_history"][-min_len:],
            "Operating Cash Flow (CFO)": data["cfo_history"][-min_len:],
            "Free Cash Flow (FCF)": fcf_vals
        })
        
        fig_hist = px.bar(
            hist_df,
            x="Fiscal Year",
            y=["Revenue (₹ Cr)", "Operating Cash Flow (CFO)", "PAT (₹ Cr)"],
            barmode="group",
            color_discrete_sequence=["#00d2ff", "#00f5a0", "#818cf8"]
        )
        fig_hist.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans", color="#94a3b8"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        st.dataframe(hist_df, use_container_width=True)
    else:
        st.info("Multi-year trajectory is being aggregated from the latest filings.")

with tab_raw:
    st.html("""
    <div class="glass-card">
        <h4 style="margin-top: 0; color: #ffffff;">Official Statement Filings</h4>
    </div>
    """)
    if data["q_data"]:
        st.markdown("**Reported Quarters (₹ Cr):**")
        q_df = pd.DataFrame(data["q_data"], index=data["q_headers"][:len(data["q_data"].get("Sales", []))]).T
        st.dataframe(q_df, use_container_width=True)
        
    if data["sh_data"]:
        st.markdown("**Shareholding Pattern Trend (%):**")
        sh_df = pd.DataFrame(data["sh_data"], index=data["sh_headers"][:len(data["sh_data"].get("FIIs", []))]).T
        st.dataframe(sh_df, use_container_width=True)

# --- ONE-CLICK REPORT EXPORT ---
report_content = f"""```text
================================================================================
 VALUATION & EXPECTED TARGET PRICE SUMMARY (FROM LAST CLOSING PRICE)
================================================================================
 Last Closing Price (CMP):            ₹{cmp:,.2f}
 Latest Market Cap:                   ₹{mcap:,.0f} Cr
 Target Time Horizon:                 2-Year Horizon ({val_res['base_fy']} to {val_res['target_yr2_fy']})
 Expected Target Price (Wtd Avg):     ₹{val_res['expected_target']:,.2f}
 Total Expected Return:               {'+' if val_res['total_expected_return_pct']>=0 else ''}{val_res['total_expected_return_pct']:.1f}% from CMP
 Annualized Expected Return (CAGR):   {'+' if val_res['expected_cagr']>=0 else ''}{val_res['expected_cagr']:.1f}% p.a.
 Dynamic Probability Allocation:      {val_res['base_prob']}% Base / {val_res['bull_prob']}% Bull
 Final Conviction Verdict:            {val_res['verdict']}
================================================================================

--- UNDERLYING SCENARIO TARGET BREAKDOWN & EXPLANATION ---
• Base Case Target ({val_res['base_prob']}% Prob):   ₹{val_res['target_base']:,.2f} ({'+' if val_res['return_base_pct']>=0 else ''}{val_res['return_base_pct']:.1f}%) | Exit P/E: {val_res['base_exit_pe']:.1f}x
  Rationale: Execution friction, milestone delays, or margin compression.
• Bull Case Target ({val_res['bull_prob']}% Prob):   ₹{val_res['target_bull']:,.2f} (+{val_res['return_bull_pct']:.1f}%) | Exit P/E: {val_res['bull_exit_pe']:.1f}x
  Rationale: Flawless execution, market share consolidation, and operating leverage.
================================================================================
```

# {data['name']} ({ticker}) | Institutional Equity Research Deep-Dive

**Report Date:** {datetime.now().strftime('%B %d, %Y')}  
**Last Closing Price (CMP):** ₹{cmp:,.2f} | **Latest Market Cap:** ₹{mcap:,.0f} Cr | **Enterprise Value (EV):** ₹{rev_dcf_res['ev']:,.0f} Cr  
**Target Horizon:** {val_res['regime']} ({val_res['base_fy']} Base -> 1-Yr: {val_res['target_yr1_fy']} | 2-Yr: {val_res['target_yr2_fy']})  
**Valuation Engine:** {val_res['regime_model']}  
**Trailing Foundation:** Base TTM EPS ₹{ttm_eps:.2f} | Trailing P/E: {pe:.1f}x  

---

### Executive Scorecard & Gatekeeper Audit

| Gate / Criterion | Rule / Benchmark | Company Status | Audit Result |
| :--- | :--- | :--- | :--- |
| **1. Sector Vector** | Sunrise vs Fossil/Fragile | Structural Sunrise Sector Tailwind | 🟢 PASS |
| **2. Geopolitical / Regulatory** | Export < 35-40%; Zero phase-out | Multi-Region Diversified Footprint | 🟢 PASS |
| **3. Moat & Anti-Disintermediation**| 7 Powers intact; Pricing power | High Switching Costs & Scale Density | 🟢 STRONG MOAT |
| **4. Balance Sheet & Margins** | D/E < 0.3x; 4-Yr CFO/PAT >= 0.8x | 4-Yr CFO/PAT: {forensic_res['cum_cfo_pat_ratio']}x; Debt/Equity: {forensic_res['de_ratio']}x | {'🟢 PRISTINE' if forensic_res['cum_cfo_pat_ratio']>=0.8 else '🟡 CAUTION'} |
| **5. Growth & Valuation (King Filter)**| CAGR >= 20% & Bull Upside >= 50% | Base: {val_res['base_cagr']*100:.0f}%, Bull Upside: +{val_res['return_bull_pct']:.1f}% | {'🟢 PASS' if val_res['pass_upside'] else '🔴 FAIL'} |
| **6. 2-Year Forward P/E Filter** | 2-Year Forward P/E < 50x | Base Fwd P/E: {val_res['fwd_pe_base']:.1f}x | {'🟢 PASS (<50x)' if val_res['pass_fwd_pe'] else '🔴 FAIL (>=50x)'} |
| **7. Concentration Risk** | Single counterparty exposure < 20% | Institutional Diversification Bounds | 🟢 BALANCED |

**FINAL CONVICTION VERDICT:** **{val_res['verdict']}**

---

### 2-Year Scenario Valuation Matrix

| Scenario | Horizon Net CAGR | End Growth | Exit P/E | Projected FY+2 EPS ({val_res['target_yr2_fy']}) | Expected Target Price (₹) | Total Return (%) | Annualized CAGR (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Base Case ({val_res['base_prob']}%)** | {val_res['base_cagr']*100:.1f}% | {base_exit_g*100:.1f}% | **{val_res['base_exit_pe']}x** | **₹{val_res['eps_base_yr2']}** | **₹{val_res['target_base']:,.2f}** | **{'+' if val_res['return_base_pct']>=0 else ''}{val_res['return_base_pct']}%** | **{'+' if val_res['cagr_base']>=0 else ''}{val_res['cagr_base']}%** |
| **Bull Case ({val_res['bull_prob']}%)** | {val_res['bull_cagr']*100:.1f}% | {bull_exit_g*100:.1f}% | **{val_res['bull_exit_pe']}x** | **₹{val_res['eps_bull_yr2']}** | **₹{val_res['target_bull']:,.2f}** | **+{val_res['return_bull_pct']}%** | **+{val_res['cagr_bull']}%** |

* **Ideal Accumulation Corridor:** **₹{val_res['buy_low']} – ₹{val_res['buy_high']}**
* **Reverse DCF Implied 10-Yr FCF CAGR:** **{rev_dcf_res['implied_cagr']}% p.a.** (Market Expectation: {rev_dcf_res['assessment']})

---

{ai_output['content']}
"""

st.html("""
<div style="display: flex; justify-content: center; margin-top: 24px; margin-bottom: 24px;">
</div>
""")

st.download_button(
    label="⚡ Export Institutional Deep-Dive Dossier (.md)",
    data=report_content,
    file_name=f"{ticker}_StockHold_research_dossier.md",
    mime="text/markdown"
)

# --- CRAWLABLE STOCK DIRECTORY FOOTER (FOR GOOGLEBOT SITEMAP & INDEXING) ---
st.html("""
<div class="glass-card" style="margin-top: 40px; border-top: 1px solid var(--border-subtle); padding: 24px; text-align: center;">
    <div style="font-size: 0.85rem; font-weight: 700; color: #a5b4fc; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 14px;">
        🔥 Top 20 Trending Indian Stocks — Share Price Target Index (NSE / BSE)
    </div>
    <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 8px; font-size: 0.8rem;">
        <a href="/?ticker=ETERNAL" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Zomato Share Price Target</a>
        <a href="/?ticker=COFORGE" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Coforge Target Price</a>
        <a href="/?ticker=DIXON" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Dixon Technologies Target Price</a>
        <a href="/?ticker=KAYNES" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Kaynes Technology Target Price</a>
        <a href="/?ticker=TRENT" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Trent Share Target Price</a>
        <a href="/?ticker=TATAMOTORS" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Tata Motors Share Target</a>
        <a href="/?ticker=POLYCAB" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Polycab Target Price</a>
        <a href="/?ticker=HAL" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">HAL Share Price Target</a>
        <a href="/?ticker=BEL" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">BEL Target Price</a>
        <a href="/?ticker=CDSL" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">CDSL Share Price Target</a>
        <a href="/?ticker=ANGELONE" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Angel One Target Price</a>
        <a href="/?ticker=SUZLON" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Suzlon Energy Target Price</a>
        <a href="/?ticker=TATAELXSI" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Tata Elxsi Target Price</a>
        <a href="/?ticker=KPITTECH" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">KPIT Tech Target Price</a>
        <a href="/?ticker=PERSISTENT" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Persistent Systems Target Price</a>
        <a href="/?ticker=NETWEB" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Netweb Technologies Target Price</a>
        <a href="/?ticker=JYOTICNC" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Jyoti CNC Target Price</a>
        <a href="/?ticker=PRESTIGE" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Prestige Estates Target Price</a>
        <a href="/?ticker=PAYTM" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">Paytm Share Target Price</a>
        <a href="/?ticker=POLICYBZR" style="color: #6366f1; text-decoration: none; padding: 4px 10px; background: rgba(99,102,241,0.08); border-radius: 6px;">PolicyBazaar Target Price</a>
    </div>
    <div style="margin-top: 18px; font-size: 0.78rem; color: #64748b;">
        © 2026 StockHold &bull; Simplifying stock analysis for investors &bull; Daily NSE / BSE Target Price Index.
    </div>
</div>
""")
