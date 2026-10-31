import os
import sys

# Ensure stockhold directory, repo root, and predict/scripts are in sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CURRENT_DIR)
for _p in [_CURRENT_DIR, _ROOT_DIR, os.path.join(_ROOT_DIR, "predict", "scripts")]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Clear stale cached engine modules from in-memory sys.modules on hot-reloads
for _mod in list(sys.modules.keys()):
    if _mod == "engine" or _mod.startswith("engine."):
        sys.modules.pop(_mod, None)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

import inspect

import streamlit.components.v1 as components

try:
    from engine.data_fetcher import fetch_company_data, get_top_trending_stocks
    from engine.valuation import calculate_forward_pe_valuation, calibrate_stock_parameters, prepare_valuation_params
    from engine.forensics import run_forensic_audit, forensic_inputs_from_data
    from engine.reverse_dcf import run_reverse_dcf
    from engine.ai_analyst import generate_ai_analysis
    from engine.stock_universe import get_indexed_stock_options, extract_ticker_from_string
    from engine.html_reporter import (
        generate_html_for_stock,
        find_existing_html_report,
        derive_action_commentary,
        build_institutional_markdown_dossier
    )
except ImportError:
    # Direct fallback if sys.path resolves differently
    import importlib
    for _mod in list(sys.modules.keys()):
        if _mod == "engine" or _mod.startswith("engine."):
            sys.modules.pop(_mod, None)
    from stockhold.engine.data_fetcher import fetch_company_data, get_top_trending_stocks
    from stockhold.engine.valuation import calculate_forward_pe_valuation, calibrate_stock_parameters, prepare_valuation_params
    try:
        from stockhold.engine.forensics import run_forensic_audit, forensic_inputs_from_data
    except ImportError:
        import stockhold.engine.forensics as _f_mod
        importlib.reload(_f_mod)
        run_forensic_audit = _f_mod.run_forensic_audit
        forensic_inputs_from_data = getattr(_f_mod, "forensic_inputs_from_data", None)
    from stockhold.engine.reverse_dcf import run_reverse_dcf
    from stockhold.engine.ai_analyst import generate_ai_analysis
    from stockhold.engine.stock_universe import get_indexed_stock_options, extract_ticker_from_string
    from stockhold.engine.html_reporter import (
        generate_html_for_stock,
        find_existing_html_report,
        derive_action_commentary,
        build_institutional_markdown_dossier
    )

if "forensic_inputs_from_data" not in locals() or forensic_inputs_from_data is None:
    def forensic_inputs_from_data(data: dict) -> dict:
        eq_cap = data.get("equity_capital")
        reserves = data.get("reserves")
        if eq_cap is not None and reserves is not None:
            net_worth = eq_cap + reserves
        elif data.get("cmp", 0) > 0 and data.get("book_value", 0) > 0:
            net_worth = data["mcap_cr"] / (data["cmp"] / data["book_value"])
        else:
            net_worth = 0.0
        other_a, other_l = data.get("other_assets"), data.get("other_liabilities")
        total_assets = data.get("total_assets") or 0.0
        return {
            "rev_history": data.get("rev_history", []),
            "pat_history": data.get("pat_history", []),
            "cfo_history": data.get("cfo_history", []),
            "trend_years": data.get("trend_years", []),
            "debtor_days": data.get("latest_debtor_days", 60.0),
            "total_debt": data.get("latest_debt", 0.0),
            "net_worth": net_worth,
            "total_assets": total_assets,
            "ebit": data.get("ebit"),
            "working_capital": (other_a - other_l) if (other_a is not None and other_l is not None) else None,
            "retained_earnings": reserves,
            "total_liabilities": (total_assets - net_worth) if total_assets > 0 and net_worth > 0 else None,
        }

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

    div[data-baseweb="select"] > div {
        background: rgba(14, 20, 32, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
    }
    div[data-baseweb="select"] * {
        color: #ffffff !important;
        font-family: var(--font-main) !important;
    }
    div[data-baseweb="popover"] ul {
        background: #0b0f19 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
    }
    div[data-baseweb="popover"] li {
        color: #e2e8f0 !important;
    }
    div[data-baseweb="popover"] li:hover {
        background: rgba(99, 102, 241, 0.25) !important;
        color: #ffffff !important;
    }
</style>
""")

# --- CRAWLABLE STOCK DIRECTORY FOOTER (FOR GOOGLEBOT SITEMAP & INDEXING) ---
def render_footer():
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

# --- URL QUERY PARAMS FOR DIRECT SHAREABLE LINKS & SEO ---
query_ticker = st.query_params.get("ticker", "").strip().upper()
if not query_ticker:
    query_ticker = st.query_params.get("stock", "").strip().upper()

# =========================================================================
# STATE 1: HOMEPAGE (Rendered when no ticker parameter is present in URL)
# =========================================================================
if not query_ticker:
    st.html("""
    <div style="text-align: center; padding: 44px 16px 20px 16px; max-width: 820px; margin: 0 auto;">
        <div style="display: inline-flex; align-items: center; justify-content: center; width: 62px; height: 62px; border-radius: 18px; background: linear-gradient(135deg, #6366f1 0%, #00d2ff 100%); box-shadow: 0 0 32px rgba(99, 102, 241, 0.45); font-size: 30px; margin-bottom: 18px;">
            ⚡
        </div>
        <h1 style="font-size: 3.1rem; font-weight: 800; letter-spacing: -0.04em; background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; line-height: 1.1;">
            StockHold
        </h1>
        <p style="font-size: 1.15rem; color: #94a3b8; font-weight: 500; margin-top: 10px; margin-bottom: 24px; line-height: 1.5;">
            Simplifying stock analysis for investors.<br>
            <span style="font-size: 0.92rem; color: #64748b;">Institutional forward valuation models, forensic cash-flow checks, and 7 Powers moat audits.</span>
        </p>
    </div>
    """)

    # Autocomplete Search Bar
    scol1, scol2, scol3 = st.columns([1, 4, 1])
    with scol2:
        st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #a5b4fc; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;'>🔍 Search Any Indian Stock (NSE / BSE):</div>", unsafe_allow_html=True)
        stock_options = get_indexed_stock_options()
        selected_home = st.selectbox(
            "Search any Indian Stock:",
            options=stock_options,
            index=None,
            placeholder="Type company name or ticker (e.g. Coforge, Dixon, Trent, Zomato, Tata Motors, Kaynes)...",
            label_visibility="collapsed",
            key="home_select_stock"
        )
        if selected_home:
            chosen = extract_ticker_from_string(selected_home)
            if chosen:
                st.query_params["ticker"] = chosen
                st.rerun()

        with st.expander("⚡ Or search by custom NSE / BSE ticker directly", expanded=False):
            cin1, cin2 = st.columns([3, 1])
            custom_t = cin1.text_input("Custom Ticker", placeholder="e.g. MOTHERSON, HAL, BEL, IXIGO...", label_visibility="collapsed", key="hp_custom_ticker")
            if cin2.button("Analyze Stock", key="btn_hp_custom", use_container_width=True):
                if custom_t.strip():
                    st.query_params["ticker"] = custom_t.strip().upper()
                    st.rerun()

    # Featured Institutional Research Dossiers
    st.html("""
    <div style="max-width: 980px; margin: 38px auto 14px auto;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 0.88rem; font-weight: 700; color: #f8fafc; text-transform: uppercase; letter-spacing: 0.06em;">
                📑 Featured Institutional Research Dossiers:
            </div>
            <div style="font-size: 0.76rem; color: #00f5a0; font-family: var(--font-mono); font-weight: 600;">
                ✓ 100% DETERMINISTIC QUANTITATIVE MODELS
            </div>
        </div>
    </div>
    """)

    feat_cols = st.columns(4)
    with feat_cols[0]:
        st.html("""
        <div class="glass-card" style="padding: 18px 16px; margin-bottom: 8px; border-left: 3px solid #6366f1;">
            <div style="font-size: 0.72rem; color: #a5b4fc; font-weight: 700; font-family: var(--font-mono);">NSE: KPITTECH</div>
            <div style="font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-top: 4px;">KPIT Tech</div>
            <div style="font-size: 0.78rem; color: #94a3b8; margin: 4px 0 10px 0;">Autonomous Driving & SDV</div>
            <div style="font-size: 0.88rem; color: #00f5a0; font-weight: 700; font-family: var(--font-mono);">+108.3% Upside</div>
        </div>
        """)
        if st.button("Open Report →", key="btn_hp_kpittech", use_container_width=True):
            st.query_params["ticker"] = "KPITTECH"
            st.rerun()

    with feat_cols[1]:
        st.html("""
        <div class="glass-card" style="padding: 18px 16px; margin-bottom: 8px; border-left: 3px solid #00f5a0;">
            <div style="font-size: 0.72rem; color: #6ee7b7; font-weight: 700; font-family: var(--font-mono);">BSE: ADVAIT</div>
            <div style="font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-top: 4px;">Advait Energy</div>
            <div style="font-size: 0.78rem; color: #94a3b8; margin: 4px 0 10px 0;">Green Hydrogen & Power EPC</div>
            <div style="font-size: 0.88rem; color: #00f5a0; font-weight: 700; font-family: var(--font-mono);">+168.0% Upside</div>
        </div>
        """)
        if st.button("Open Report →", key="btn_hp_advait", use_container_width=True):
            st.query_params["ticker"] = "ADVAIT"
            st.rerun()

    with feat_cols[2]:
        st.html("""
        <div class="glass-card" style="padding: 18px 16px; margin-bottom: 8px; border-left: 3px solid #00d2ff;">
            <div style="font-size: 0.72rem; color: #38bdf8; font-weight: 700; font-family: var(--font-mono);">NSE: TECHNOE</div>
            <div style="font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-top: 4px;">Techno Electric</div>
            <div style="font-size: 0.78rem; color: #94a3b8; margin: 4px 0 10px 0;">Data Centers & Smart Grid</div>
            <div style="font-size: 0.88rem; color: #00f5a0; font-weight: 700; font-family: var(--font-mono);">+55.2% Upside</div>
        </div>
        """)
        if st.button("Open Report →", key="btn_hp_technoe", use_container_width=True):
            st.query_params["ticker"] = "TECHNOE"
            st.rerun()

    with feat_cols[3]:
        st.html("""
        <div class="glass-card" style="padding: 18px 16px; margin-bottom: 8px; border-left: 3px solid #818cf8;">
            <div style="font-size: 0.72rem; color: #a5b4fc; font-weight: 700; font-family: var(--font-mono);">NSE: HDFCBANK</div>
            <div style="font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-top: 4px;">HDFC Bank</div>
            <div style="font-size: 0.78rem; color: #94a3b8; margin: 4px 0 10px 0;">Banking Franchise & Forensics</div>
            <div style="font-size: 0.88rem; color: #a5b4fc; font-weight: 700; font-family: var(--font-mono);">Core Valuation</div>
        </div>
        """)
        if st.button("Open Report →", key="btn_hp_hdfcbank", use_container_width=True):
            st.query_params["ticker"] = "HDFCBANK"
            st.rerun()

    # Trending Momentum Pills on Homepage
    st.html("""
    <div style="max-width: 980px; margin: 28px auto 12px auto;">
        <div style="font-size: 0.82rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em;">
            🔥 Trending Momentum Equities (1-Click Analysis):
        </div>
    </div>
    """)
    hp_pills = st.columns(6)
    if hp_pills[0].button("⚡ COFORGE", key="hp_btn_coforge", use_container_width=True):
        st.query_params["ticker"] = "COFORGE"; st.rerun()
    if hp_pills[1].button("⚡ ZOMATO", key="hp_btn_zomato", use_container_width=True):
        st.query_params["ticker"] = "ETERNAL"; st.rerun()
    if hp_pills[2].button("⚡ DIXON", key="hp_btn_dixon", use_container_width=True):
        st.query_params["ticker"] = "DIXON"; st.rerun()
    if hp_pills[3].button("⚡ KAYNES", key="hp_btn_kaynes", use_container_width=True):
        st.query_params["ticker"] = "KAYNES"; st.rerun()
    if hp_pills[4].button("⚡ TRENT", key="hp_btn_trent", use_container_width=True):
        st.query_params["ticker"] = "TRENT"; st.rerun()
    if hp_pills[5].button("⚡ TATA MOTORS", key="hp_btn_tatamotors", use_container_width=True):
        st.query_params["ticker"] = "TATAMOTORS"; st.rerun()

    render_footer()
    st.stop()


# =========================================================================
# STATE 2: STOCK PAGE (When ?ticker=XYZ is provided in URL)
# =========================================================================
ticker = query_ticker
if not ticker:
    st.stop()
    sys.exit(0)

# Strict single-scrollbar viewport lock & mobile-responsive CSS
st.html("""
<style>
/* 1. Natural Smooth Scrolling Container */
.main .block-container {
    padding: 8px 16px 40px 16px !important;
    max-width: 100% !important;
}

/* 2. Seamless report container and iframe styling */
div[data-testid="stElementContainer"]:has(iframe),
div[data-testid="stCustomComponentV1"] {
    width: 100% !important;
    border-radius: 12px;
}

iframe {
    width: 100% !important;
    border: none !important;
    border-radius: 12px;
    overflow: auto !important;
}

/* 3. Mobile Responsiveness: Keep top navbar clean and unstacked on mobile */
@media (max-width: 768px) {
    .main .block-container {
        padding: 6px 10px 32px 10px !important;
    }
    div[data-testid="stHorizontalBlock"]:first-of-type {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 8px !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:first-child {
        width: 36% !important;
        min-width: 100px !important;
        flex: 0 0 auto !important;
    }
    div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:last-child {
        width: 64% !important;
        flex: 1 1 auto !important;
    }
}
</style>

<script>
// Auto-resize embedded report iframes to their true DOM scrollHeight
window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'stockhold:setFrameHeight' && e.data.height) {
        const targetH = Math.max(8500, e.data.height + 60);
        const iframes = document.querySelectorAll('iframe');
        iframes.forEach(function(iframe) {
            iframe.style.height = targetH + 'px';
            iframe.height = targetH;
            const parent = iframe.closest('div[data-testid="stCustomComponentV1"]');
            if (parent) {
                parent.style.height = targetH + 'px';
                parent.style.maxHeight = 'none';
            }
            const elContainer = iframe.closest('div[data-testid="stElementContainer"]');
            if (elContainer) {
                elContainer.style.height = targetH + 'px';
                elContainer.style.maxHeight = 'none';
            }
        });
    }
});
</script>
""")

# Top Compact Navbar: StockHold Logo on Left, Search on Right, ZERO Trending Stocks
nav_left, nav_right = st.columns([1.6, 1.4])
with nav_left:
    st.html("""
    <a href="/" target="_top" style="text-decoration: none; display: flex; align-items: center; gap: 12px; padding: 4px 0 10px 0;">
        <div style="width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #6366f1 0%, #00d2ff 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 16px rgba(99, 102, 241, 0.45); font-size: 19px;">⚡</div>
        <div>
            <span style="font-size: 1.45rem; font-weight: 800; letter-spacing: -0.03em; background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">StockHold</span>
            <span style="font-size: 0.76rem; color: #64748b; margin-left: 10px; font-weight: 600;">← HOME</span>
        </div>
    </a>
    """)

with nav_right:
    stock_opts = get_indexed_stock_options()
    curr_idx = None
    for idx, opt in enumerate(stock_opts):
        if opt.startswith(f"{ticker} —") or opt.startswith(f"{ticker} "):
            curr_idx = idx
            break
    
    nav_sel = st.selectbox(
        "Search another Indian Stock:",
        options=stock_opts,
        index=curr_idx,
        placeholder="🔍 Search another stock (e.g. DIXON, TRENT, KPIT)...",
        label_visibility="collapsed",
        key=f"nav_stock_search_{ticker}"
    )
    if nav_sel:
        chosen = extract_ticker_from_string(nav_sel)
        if chosen and chosen != ticker:
            st.query_params["ticker"] = chosen
            st.rerun()

# --- DATA FETCHING & PROCESSING (MARKET-HOURS AWARE CACHING) ---
def get_market_cache_bucket() -> tuple:
    """
    Returns (cache_bucket, is_market_open) based on Indian Standard Time (IST).
    - Market Open (Mon-Fri 09:15-15:30 IST): 60-second cache bucket for live prices.
    - Market Closed / Weekends: 1800-second (30-minute) cache bucket to conserve resources.
    """
    import datetime, zoneinfo
    try:
        now_ist = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
    except Exception:
        now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

    is_market_open = (
        now_ist.weekday() < 5 and (
            (now_ist.hour == 9 and now_ist.minute >= 15) or
            (10 <= now_ist.hour < 15) or
            (now_ist.hour == 15 and now_ist.minute <= 30)
        )
    )
    ts = int(now_ist.timestamp())
    bucket = ts // 60 if is_market_open else ts // 1800
    return bucket, is_market_open


@st.cache_data(ttl=1800, max_entries=100, show_spinner=False)
def load_company(symbol: str, cache_bucket: int):
    company_data = fetch_company_data(symbol)
    if not company_data or company_data.get("cmp", 0) <= 0:
        raise ValueError(f"Invalid market data retrieved for {symbol}")
    return company_data

cache_bucket, is_market_open = get_market_cache_bucket()

with st.spinner(f"Analyzing institutional filings and concall disclosures for {ticker}..."):
    try:
        data = load_company(ticker, cache_bucket)
    except Exception as e:
        st.error(f"⚠️ Unable to load financial model for '{ticker}'. This might happen due to temporary network timeouts or an unrecognized ticker.")
        col_r1, col_r2 = st.columns([1, 1])
        if col_r1.button("🔄 Force Re-fetch Live Data"):
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.stop()

if "data" not in locals() or not data:
    st.stop()
    sys.exit(0)

# Dynamically calibrate model parameters to the company's specific growth momentum & cash conversion
data["registry_ticker"] = str(ticker).upper().replace(" ", "").replace("-", "")
calibrated = calibrate_stock_parameters(data)

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

    # Underwriting Foundation Callout: Management Guidance vs First-Principles
    is_guidance_active = bool(calibrated.get("is_guidance_anchored"))
    g_rev = calibrated.get("guided_rev_cagr")
    g_rel = calibrated.get("guidance_reliability", 0.75)
    g_as_of = calibrated.get("guidance_as_of", "")
    g_quote = calibrated.get("guidance_quote", "")

    if is_guidance_active and g_rev is not None:
        quote_snippet = f'<div style="font-size: 0.73rem; color: #94a3b8; font-style: italic; margin-top: 6px; border-left: 2px solid #00f5a0; padding-left: 6px;">"{g_quote[:180]}..." — Concall ({g_as_of})</div>' if g_quote else ""
        badge_html = f"""
        <div style="background: rgba(0, 245, 160, 0.08); border: 1px solid rgba(0, 245, 160, 0.35); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <span style="background: rgba(0, 245, 160, 0.2); color: #00f5a0; border: 1px solid rgba(0, 245, 160, 0.5); padding: 2px 7px; border-radius: 9999px; font-weight: 700; font-size: 0.72rem;">🟢 MANAGEMENT GUIDANCE ACTIVE</span>
                <span style="font-size: 0.72rem; color: #94a3b8; font-family: monospace;">{g_as_of}</span>
            </div>
            <div style="font-size: 0.8rem; color: #f1f5f9; line-height: 1.4;">
                Forward model anchored to disclosed guidance of <b>+{g_rev:.1f}% Revenue CAGR</b> discounted by historical delivery score (<b>{g_rel:.2f}x</b>).
            </div>
            {quote_snippet}
        </div>
        """
    else:
        sales_3y = data.get("sales_growth_3yr")
        profit_3y = data.get("profit_growth_3yr")
        badge_html = f"""
        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(71, 85, 105, 0.4); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="margin-bottom: 6px;">
                <span style="background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); padding: 2px 7px; border-radius: 9999px; font-weight: 700; font-size: 0.72rem;">⚪ FIRST-PRINCIPLES DERIVATION</span>
            </div>
            <div style="font-size: 0.8rem; color: #cbd5e1; line-height: 1.4;">
                No quantitative revenue targets in latest concalls. Deterministically derived from audited <b>Sales 3Y ({sales_3y if sales_3y is not None else 'N/A'}%)</b>, <b>PAT 3Y ({profit_3y if profit_3y is not None else 'N/A'}%)</b> & <b>ROCE ({calibrated.get('roce', 'N/A')}%)</b>.
            </div>
        </div>
        """
    st.markdown(badge_html, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.25); border-radius: 8px; padding: 10px; margin-bottom: 12px; font-size: 0.8rem; line-height: 1.4;">
        <b style="color: #a5b4fc;">✨ Dynamic Calibration ({data['ticker']}):</b><br>
        <span style="color: #94a3b8;">{calibrated['rationale']}</span><br>
        <span style="color: #cbd5e1;">• 3-Yr Sales CAGR: <b>{data.get('sales_growth_3yr') if data.get('sales_growth_3yr') is not None else 'N/A'}%</b></span><br>
        <span style="color: #cbd5e1;">• 3-Yr Profit CAGR: <b>{data.get('profit_growth_3yr') if data.get('profit_growth_3yr') is not None else 'N/A'}%</b></span>
    </div>
    """, unsafe_allow_html=True)
    
    base_cagr = st.slider(
        "Growth Anchor CAGR (%) (central estimate; sets bear growth & weight):",
        min_value=-10.0,
        max_value=60.0,
        value=float(max(-10.0, min(60.0, float(calibrated["base_cagr"])))),
        step=0.5,
        key=f"base_cagr_{ticker}"
    ) / 100.0

    bull_cagr = st.slider(
        "Bull Case CAGR (%):",
        min_value=-10.0,
        max_value=80.0,
        value=float(max(-10.0, min(80.0, float(calibrated["bull_cagr"])))),
        step=0.5,
        key=f"bull_cagr_{ticker}"
    ) / 100.0

    col_eg1, col_eg2 = st.columns(2)
    base_exit_g = col_eg1.number_input("Anchor Exit Growth (%) (sets bear exit P/E):", value=float(calibrated["base_exit_g"]), step=1.0, key=f"base_eg_{ticker}") / 100.0
    bull_exit_g = col_eg2.number_input("Bull Exit Growth (%):", value=float(calibrated["bull_exit_g"]), step=1.0, key=f"bull_eg_{ticker}") / 100.0

    col_p1, col_p2 = st.columns(2)
    base_peg = col_p1.number_input("Anchor PEG (sets bear exit P/E):", value=float(calibrated.get("base_peg", 1.60)), step=0.05, key=f"base_peg_{ticker}")
    bull_peg = col_p2.number_input("Bull PEG:", value=float(calibrated.get("bull_peg", 1.85)), step=0.05, key=f"bull_peg_{ticker}")

    bear_split = st.slider(
        "Bear Case Probability Weight (%):",
        min_value=0,
        max_value=80,
        value=int(max(0, min(80, int(calibrated.get("bear_prob", 30))))),
        step=5,
        help="Probability that growth stalls and the multiple de-rates; Bull gets the rest. Default: the weight that makes probability-weighted growth equal the growth anchor, raised for fragility and weak momentum.",
        key=f"bear_prob_{ticker}"
    )
    bear_prob = bear_split / 100.0

    st.markdown("---")
    force_recompile = st.checkbox(
        "⚡ Force Live HTML Re-compile",
        value=False,
        help="Recompile the HTML dashboard on-the-fly incorporating your custom slider overrides instead of loading the pre-compiled report from predict/reports/."
    )
    if st.button("🔄 Clear Cache & Reset Defaults", use_container_width=True):
        st.cache_data.clear()
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


cmp = data["cmp"]
mcap = data["mcap_cr"]
ttm_eps = data["ttm_eps"]
pe = data["pe"]

val_params = prepare_valuation_params(
    data=data,
    calibrated=calibrated,
    base_cagr_override=base_cagr,
    bull_cagr_override=bull_cagr,
    base_exit_growth_override=base_exit_g,
    bull_exit_growth_override=bull_exit_g,
    base_peg_override=base_peg,
    bull_peg_override=bull_peg,
    bear_prob_override=bear_prob,
    regime_override=selected_regime_override,
)

# Defensive signature check to guarantee zero runtime TypeError on hot-reloads
sig = inspect.signature(calculate_forward_pe_valuation)
has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
if not has_var_kw:
    val_params = {k: v for k, v in val_params.items() if k in sig.parameters}

val_res = calculate_forward_pe_valuation(**val_params)

# Guarantee fallback defaults if older cached version returned
if "base_reason" not in val_res:
    val_res["base_reason"] = calibrated.get("base_reason", "Execution friction, delayed milestone delivery, or moderate volume ramp")
if "bull_reason" not in val_res:
    val_res["bull_reason"] = calibrated.get("bull_reason", "Flawless execution, market share consolidation, and strong operational leverage")

# Explicitly sync guidance metadata from calibrated
for _gk in ["guided_rev_cagr", "guidance_status", "guidance_reliability", "guidance_quote", "guidance_as_of", "is_guidance_anchored", "ss_margin"]:
    if calibrated.get(_gk) is not None:
        val_res[_gk] = calibrated[_gk]

forensic_res = run_forensic_audit(**forensic_inputs_from_data(data))

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

# Check if curated institutional report already exists (with automatic price drift validation)
existing_html, existing_path = find_existing_html_report(ticker, current_cmp=cmp) if not force_recompile else (None, None)

if existing_html:
    html_report_str = existing_html
    report_meta = {
        "is_curated": True,
        "source_path": existing_path,
        "ticker": ticker,
        "title": Path(existing_path).stem.replace("_", " ").title()
    }
    md_path = Path(existing_path).with_suffix(".md")
    md_dossier = md_path.read_text(encoding="utf-8") if md_path.is_file() else ""
    is_curated = True
    report_source_path = existing_path
    ai_output = {
        "source": "Published Institutional Coverage Desk",
        "content": "Institutional equity research dossier from coverage universe"
    }
    m_comm = re.search(r'Why (?:Buy|Avoid|Watchlist|Accumulate)[^<]*</span>\s*</div>\s*<p[^>]*>(.*?)</p>', existing_html, re.DOTALL | re.IGNORECASE)
    action_commentary = m_comm.group(1).strip() if m_comm else derive_action_commentary(ticker, data, val_res, forensic_res)
else:
    @st.cache_data(ttl=86400, show_spinner=False)
    def _get_cached_ai_synthesis(
        t_sym: str, cmp_val: float, mcap_val: float, eps_val: float, pe_val: float,
        bear_t: float, bull_t: float, cfo_pat: float, d_days: int, alt_z: float,
        imp_cagr: float, api_k: str
    ) -> dict:
        return generate_ai_analysis(data, val_res, forensic_res, rev_dcf_res, api_key=api_k)

    # Dynamic AI synthesis & action commentary derivation
    with st.spinner(f"⚡ Synthesizing institutional research dossier & 7 Powers audit for {ticker}..."):
        ai_output = _get_cached_ai_synthesis(
            ticker,
            round(cmp, 1),
            round(mcap, 0),
            round(ttm_eps, 2),
            round(pe, 1),
            round(val_res.get("target_bear", 0.0), 1),
            round(val_res.get("target_bull", 0.0), 1),
            round(forensic_res.get("cum_cfo_pat_ratio", 0.0), 2),
            int(forensic_res.get("debtor_days") or 0),
            round(forensic_res.get("altman_z") or 0.0, 2),
            round(rev_dcf_res.get("implied_cagr", 0.0), 1),
            api_key
        )
        action_commentary = derive_action_commentary(ticker, data, val_res, forensic_res)

        # Generate institutional HTML report for stock
        html_report_str, report_meta, md_dossier, is_curated, report_source_path = generate_html_for_stock(
            data, val_res, forensic_res, rev_dcf_res, ai_output, force_regenerate=force_recompile
        )

# --- INSTITUTIONAL SURFACE: guard badge + kill-switches (judging strip) ---
try:
    from engine.safety_guard import FinancialSafetyGuard
except ImportError:
    from safety_guard import FinancialSafetyGuard

_ai_text = (ai_output.get("content", "") if isinstance(ai_output, dict) else str(ai_output or ""))
_guard = FinancialSafetyGuard.audit_synthesis(val_res, _ai_text)
_guard_ok = bool(_guard.get("passes_guard"))
_altman_missing = forensic_res.get("altman_z") is None
_sparse = bool(calibrated.get("sparse_anchor"))
_kill_lines = [ln.strip() for ln in _ai_text.splitlines() if "kill switch" in ln.lower() or "kill-switch" in ln.lower()][:3]
if not _kill_lines:
    stop_px = val_res.get('trailing_stop_loss') or round(data["cmp"] * 0.85, 1)
    debtor_d = forensic_res.get("debtor_days")
    _kill_lines = [
        f"Kill Switch #1: Close below ₹{stop_px:,.2f} triggers automated trailing stop exit (15% capital preservation).",
        f"Kill Switch #2: Exit immediately if YoY sales growth prints below 12.0% for two consecutive quarters.",
        f"Kill Switch #3: Exit if debtor days expand >25 days (above today's {debtor_d}d) without cash conversion."
    ]
_badge = ("GUARD PASS — targets match deterministic math" if _guard_ok
          else "GUARD FLAG — " + "; ".join(_guard.get("violations", [])[:2]))
_badge_color = "#00f5a0" if _guard_ok else "#ffb703"

_is_guided = bool(calibrated.get("is_guidance_anchored"))
_g_cagr = calibrated.get("guided_rev_cagr")
_guidance_chip = (
    f"<span style='font-size: 0.78rem; font-weight: 700; color: #00f5a0;'>| 🟢 Guidance Anchored (+{_g_cagr:.1f}%)</span>"
    if _is_guided and _g_cagr is not None
    else "<span style='font-size: 0.78rem; font-weight: 700; color: #94a3b8;'>| ⚪ First-Principles Derivation</span>"
)

st.html(f"""
<div class="glass-card" style="padding: 14px 16px; margin: 6px 0 12px 0;">
  <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
    <span style="font-size: 0.78rem; font-weight: 700; color: {_badge_color};">{_badge}</span>
    <span style="font-size: 0.78rem; color: #94a3b8;">| {val_res.get('verdict', '')}</span>
    {_guidance_chip}
    <span style="font-size: 0.78rem; color: #94a3b8;">| {ai_output.get('source', 'Institutional Valuation Desk') if isinstance(ai_output, dict) else 'Algorithmic Desk'}</span>
    {"<span style='font-size: 0.78rem; font-weight: 700; color: #ffb703;'>| Altman UNAVAILABLE — fragile-tier penalty applied</span>" if _altman_missing else ""}
    {"<span style='font-size: 0.78rem; font-weight: 700; color: #ffb703;'>| SPARSE INPUTS — " + calibrated.get('rationale', '').split(']')[0].replace('[SPARSE INPUTS: ', '') + "</span>" if _sparse else ""}
  </div>
  <div style="font-size: 0.86rem; color: #e2e8f0; margin-top: 8px;">{action_commentary}</div>
  <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 6px;">{" · ".join(_kill_lines)}</div>
</div>
""")

report_content = md_dossier if md_dossier else build_institutional_markdown_dossier(data, val_res, forensic_res, rev_dcf_res, ai_output)

# --- SIDEBAR RESEARCH DOSSIER EXPORT TOOLS ---
with st.sidebar:
    st.markdown("---")
    st.markdown("**📥 Export Research**")
    st.download_button(
        label="⚡ Download HTML Report (.html)",
        data=html_report_str,
        file_name=f"{ticker.lower()}_research_report.html",
        mime="text/html",
        use_container_width=True,
        key="dl_side_html"
    )
    st.download_button(
        label="📄 Export Dossier (.md)",
        data=report_content,
        file_name=f"{ticker}_StockHold_research_dossier.md",
        mime="text/markdown",
        use_container_width=True,
        key="dl_side_md"
    )
    if is_curated:
        st.caption("✓ Published institutional dossier (`predict/reports/`)")
    else:
        st.caption("⚡ Dynamic algorithmic compilation (Live filings)")


# --- PROGRAMMATIC SEO METADATA & SCHEMA.ORG STRUCTURED DATA ---
seo_desc = f"{data['name']} ({ticker}) 2-Year Target Price is ₹{val_res['expected_target']:,.2f} ({'+' if val_res['total_expected_return_pct']>=0 else ''}{val_res['total_expected_return_pct']:.1f}% Upside from CMP ₹{cmp:,.2f}). Bear Case: ₹{val_res['target_bear']:,.2f} | Bull Case: ₹{val_res['target_bull']:,.2f}. Institutional 2-year forward P/E valuation, reverse DCF, and 7 Powers moat audit."
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
          "name": "What is the Bull Case vs Bear Case target price for {ticker}?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "In the Bull Case, the target price is ₹{val_res['target_bull']:,.2f} (+{val_res['return_bull_pct']:.1f}% upside at an exit P/E of {val_res['bull_exit_pe']}x). In the Bear Case, the target price is ₹{val_res['target_bear']:,.2f} ({'+' if val_res['return_bear_pct']>=0 else ''}{val_res['return_bear_pct']:.1f}% at an exit P/E of {val_res['bear_exit_pe']}x)."
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

# --- EMBEDDED INSTITUTIONAL HTML RESEARCH REPORT ---
# Dynamic calculation based on rendered elements + generous safety floor + scrolling=True
section_count = html_report_str.count('<section class="report-section') or html_report_str.count("<section") or 5
table_count = html_report_str.count("<table") or 4
chart_count = html_report_str.count("<canvas") or 1
calculated_px = 3500 + (section_count * 1150) + (table_count * 380) + (chart_count * 400)
report_height = max(8800, min(16000, calculated_px))
components.html(html_report_str, height=report_height, scrolling=True)

# --- CRAWLABLE STOCK DIRECTORY FOOTER (FOR GOOGLEBOT SITEMAP & INDEXING) ---
render_footer()
