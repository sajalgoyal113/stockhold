# Institutional Equity Research & Valuation Platform (Indian Equities)

An institutional research ecosystem and quantitative valuation workspace for Indian listed equities (NSE/BSE). Built to analyze high-growth ($\ge 20\text{--}30\%$ CAGR) compounders in sunrise sectors while eliminating fragile balance sheets, sunset industries, regulatory traps, and valuation bubbles.

---

## 🏛️ Repository Architecture

The repository is organized into two distinct functional workspaces:

```text
Finance/
├── predict/                       # Quantitative Analysis, Modeling & Research Reports (MASTER SOURCE OF TRUTH)
│   ├── scripts/                  # Deterministic valuation & audit engines
│   │   ├── forward_growth_pe.py  # Master forward growth & dynamic P/E compounding engine
│   │   ├── forensic_audit.py     # 4-year cumulative cash flow & Dalal Street red-flag audit
│   │   ├── reverse_dcf.py        # Implied 10-year FCF CAGR root-finder & sensitivity
│   │   └── evaluate_portfolio.py # Batch portfolio & watchlist valuation analyzer
│   ├── references/               # Valuation models, templates, protocols & checklists
│   │   ├── analysis_protocol.md  # 5-step institutional stock analysis protocol
│   │   ├── report_template.md    # Institutional equity research report template
│   │   ├── forensic_checklist.md # 10-point forensic accounting checklist
│   │   └── valuation_models.md   # Hamilton Helmer 7 Powers & valuation frameworks (incl. platform compounders)
│   ├── reports/                  # Generated institutional research reports & portfolio audits
│   │   └── portfolio_research_report.md  # 25-stock portfolio deep dive
│   └── README.md                 # Predict tools & modeling guide
│
├── stockhold/                     # Interactive Web Application & Visual Dashboard
│   ├── app.py                    # Streamlit frontend & Google Stitch design system
│   ├── engine/                   # App engine modules (delegates directly to predict/)
│   │   ├── data_fetcher.py       # Screener.in consolidated scraper & historical quotes
│   │   ├── valuation.py          # Forward growth & dynamic exit P/E compounding logic
│   │   ├── forensics.py          # CFO/PAT reality check & Altman Z''-score
│   │   ├── reverse_dcf.py        # Expectations investing (reverse DCF implied CAGR)
│   │   └── ai_analyst.py         # Google Gemini AI synthesis & 7 Powers audit
│   ├── run_app.sh                # Streamlit launcher script
│   ├── requirements.txt          # Web app dependencies
│   └── README.md                 # StockHold application documentation
│
├── run_app.sh                     # One-click launcher for the StockHold web application
├── requirements.txt               # Repository-wide Python dependencies
└── GEMINI.md                      # Master behavioral rules, invariants & source of truth
```

---

## ⚡ Core Institutional Framework & Invariants

1. **Master Source of Truth (`predict/`)**:
   - `predict/` is the authoritative workspace for all equity research models, terminal P/E derivations, forensic checks, and reverse DCF calculations.
   - The web application in `stockhold/` delegates directly to `predict/scripts/` to ensure **100% mathematical synchronization**.

2. **Rolling TTM Base EPS Foundation**:
   - Never uses stale annual numbers when fresh quarterly results exist; computes Rolling TTM EPS dynamically from the last 4 reported quarters:
     $$\text{TTM PAT} = \sum_{i=1}^{4} \text{PAT}_{\text{last 4 quarters}}, \quad \text{TTM EPS} = \frac{\text{TTM PAT}}{\text{Shares Outstanding}}$$

3. **Calendar Roll-Forward Regime (H1 vs H2 Rule)**:
   - **H1 (Q1/Q2: April 1 – Sept 30)**:
     - 1-Year Target: Current running fiscal year (**FY$_t$**), compounded by 1 year ($(1+g)^1$) from the FY$_{t-1}$ base.
     - 2-Year Target: Next fiscal year (**FY$_{t+1}$**), compounded by 2 years ($(1+g)^2$).
   - **H2 (Q3/Q4: Oct 1 – March 31)**: Multiples roll forward as H1 concludes:
     - 1-Year Target: Next fiscal year (**FY$_{t+1}$**), compounded by 2 years ($(1+g)^2$) from the FY$_{t-1}$ base.
     - 2-Year Target: Two fiscal years ahead (**FY$_{t+2}$**), compounded by 3 years ($(1+g)^3$) from the FY$_{t-1}$ base.

4. **Asymmetric Scenario Valuation (Base vs Bull)**:
   - Omit Bear Case scenario; focus strictly on execution variance and upside asymmetry.
   - **Dynamic Exit P/E Multiples**: Exit multiples are derived from the expected terminal growth rate at the end of the evaluation period.
   - **Dynamic Probability Weighting**: Probability allocations are dynamically calibrated to **Founder/CEO execution credibility**, cash flow conversion hygiene, and moat durability (50/50 for elite founders down to 75/25 for sovereign-dependent traps).

5. **Strict Hurdle Rates**:
   - Projected Net CAGR $\ge 20\%$.
   - **2-Year Forward P/E $< 50$**.
   - **Mandatory $\ge 50\%$ Upside from CMP** within 2 years in the Bull Case scenario.

6. **Forensic Hygiene & Reality Checks**:
   - Cumulative 3-Year CFO/PAT $\ge 0.8\times$.
   - Altman Z''-Score for Emerging Markets ($Z'' > 2.6$ Safe Zone).
   - Receivables growth $\le$ Revenue growth.
   - Investigation of management commentary from concalls on working capital anomalies.

---

## 🚀 Getting Started

### 1. Launch the StockHold Web Application
```bash
# Clone the repository
git clone https://github.com/sajalgoyal113/stockhold.git
cd stockhold

# Install dependencies
pip install -r requirements.txt

# Run the app
./run_app.sh
```
Open your browser at `http://localhost:8501`.

### 2. Run Quantitative Valuation CLI Engines
```bash
# Run 2-Year Forward Growth & Dynamic Exit P/E Engine
python3 predict/scripts/forward_growth_pe.py DIXON --cmp 14500 --eps 120 --growth 0.30 --bull-growth 0.40

# Run Forensic Accounting & Earnings Quality Audit
python3 predict/scripts/forensic_audit.py TRENT --years FY22 FY23 FY24 FY25 --cfo 350 520 840 1250 --pat 110 390 1020 1480 --rev 4500 8200 12600 16500 --rec 25 40 65 90

# Run Expectations Investing & Reverse DCF
python3 predict/scripts/reverse_dcf.py ETERNAL --cmp 280 --mcap 265000 --fcf 2500

# Run Batch Portfolio Valuation
python3 predict/scripts/evaluate_portfolio.py
```

---

## 📄 License
MIT License. Designed for institutional equity analysts and disciplined compounder investors.
