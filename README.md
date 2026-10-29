# Institutional Equity Research & Valuation Platform (Indian Equities)

An institutional research ecosystem and quantitative valuation workspace for Indian listed equities (NSE/BSE). Built to analyze high-growth ($\ge 20\text{--}30\%$ CAGR) compounders in sunrise sectors while eliminating fragile balance sheets, sunset industries, regulatory traps, and valuation bubbles.

---

## 🏛️ Repository Architecture

The repository is organized into two distinct functional workspaces with root deployment entrypoints for Streamlit Community Cloud:

```text
Finance/
├── app.py                         # Root Streamlit entrypoint (points to stockhold/app.py)
├── requirements.txt               # Root Python dependencies for Streamlit Cloud
├── run_app.sh                     # Root launcher delegating to stockhold/run_app.sh
├── README.md                      # Repository documentation & guide
├── GEMINI.md                      # Behavioral rules, facts & repo source of truth
│
├── predict/                       # Quantitative Analysis, Modeling & Research Reports (MASTER SOURCE OF TRUTH)
│   ├── scripts/                  # Deterministic valuation & audit engines
│   │   ├── forward_growth_pe.py  # Master forward growth & dynamic P/E compounding engine
│   │   ├── forensic_audit.py     # 4-year cumulative cash flow & Dalal Street red-flag audit
│   │   ├── reverse_dcf.py        # Implied 10-year FCF CAGR root-finder & sensitivity
│   │   ├── evaluate_portfolio.py # Batch portfolio & watchlist valuation analyzer
│   │   ├── generate_html_report.py # Institutional interactive HTML report & portal generator
│   │   ├── decision.py           # Deterministic buy-or-not brief with empirical base rates
│   │   └── run_cli.py            # Master CLI runner for equity research
│   ├── references/               # Valuation models, templates, protocols & checklists
│   │   ├── analysis_protocol.md  # 5-step institutional stock analysis protocol
│   │   ├── report_template.md    # Institutional equity research report template
│   │   ├── forensic_checklist.md # 10-point forensic accounting checklist
│   │   └── valuation_models.md   # Hamilton Helmer 7 Powers & valuation frameworks
│   └── reports/                  # Generated institutional research reports & coverage portal (index.html)
│
└── stockhold/                     # Interactive Web Application & Visual Dashboard
    ├── app.py                    # Streamlit frontend & Google Stitch design system
    ├── engine/                   # Synchronized 100% byte-identical with predict/scripts/
    │   ├── valuation.py          # Forward growth & dynamic exit P/E compounding logic
    │   ├── forensics.py          # CFO/PAT reality check & Altman Z''-score
    │   ├── reverse_dcf.py        # Expectations investing (reverse DCF implied CAGR)
    │   ├── data_fetcher.py       # Screener.in consolidated scraper & historical quotes
    │   ├── html_reporter.py      # Institutional interactive HTML report generator
    │   └── decision.py           # Buy-or-not decision brief with base rates
    ├── run_app.sh                # Streamlit launcher script
    ├── requirements.txt          # Web app dependencies
    └── README.md                 # StockHold application documentation
```

---

## ⚡ Core Institutional Framework & Invariants

1. **Master Source of Truth (`predict/`)**:
   - `predict/` is the sole authoritative workspace for all equity research models, terminal P/E derivations, forensic checks, and reverse DCF calculations.
   - The web application in `stockhold/` delegates directly to `predict/scripts/` to ensure **100% mathematical synchronization**.

2. **Rolling TTM Base EPS Foundation**:
   - Never uses stale annual numbers when fresh quarterly results exist; computes Rolling TTM EPS dynamically from the last 4 reported quarters.

3. **Calendar Roll-Forward Regime (H1 vs H2 Rule)**:
   - **H1 (Q1/Q2: April 1 – Sept 30)**: 1-Yr Target: FY$_t$ (1 yr), 2-Yr Target: FY$_{t+1}$ (2 yrs).
   - **H2 (Q3/Q4: Oct 1 – March 31)**: 1-Yr Target: FY$_{t+1}$ (2 yrs), 2-Yr Target: FY$_{t+2}$ (3 yrs).

4. **Five Algorithmic Flaw Corrections**:
   - Asymmetric Re-Rating Gate (relaxing growth hurdle to 14.0% for deep value compounders).
   - Normalized Mid-Cycle Margin Bridge (anchoring trough bases to median historical margins).
   - Dynamic Debt Serviceability Gate (permitting D/E $\le 0.85\times$ with strong cash conversion).
   - Moat Proximity Buffer (13% pullback buffer below 200-DMA for pristine balance sheets).
   - 3-Tranche Moonbag Execution Protocol (30% @ $1.0\times$, 30% @ $1.8\times$, 40% Moonbag runner).

---

## 🚀 Quickstart & Usage

### 1. Launch the StockHold Web Application
```bash
./run_app.sh
```
Open **`http://localhost:8501`** in your browser, or visit the live cloud deployment: **`https://stockhold.streamlit.app`**.

### 2. Run Quantitative Valuation CLI
```bash
# Instant deterministic buy-or-not brief
python3 predict/scripts/run_cli.py PERSISTENT --decision

# Full institutional valuation and HTML compilation
python3 predict/scripts/run_cli.py DIXON --html
```
