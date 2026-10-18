# 📈 Predict — Quantitative Stock Analysis & Forensic Valuation

`predict` is the quantitative research and modeling engine of the Finance repository. It implements deterministic forward P/E compounding, 4-year forensic accounting audits, expectations investing (reverse DCF), and batch portfolio valuation.

---

## 📁 Directory Structure

```text
predict/
├── scripts/                      # Deterministic Python calculation engines
│   ├── forward_growth_pe.py      # Master forward growth & dynamic exit P/E engine
│   ├── forensic_audit.py         # 4-year cumulative CFO/PAT & Altman Z''-score
│   ├── reverse_dcf.py            # Michael Mauboussin reverse DCF implied CAGR
│   └── evaluate_portfolio.py     # Batch portfolio & watchlist valuation CLI
│
├── references/                   # Institutional templates and audit frameworks
│   ├── analysis_protocol.md      # 5-step institutional stock analysis protocol
│   ├── report_template.md        # Institutional equity research report template
│   ├── forensic_checklist.md     # 10-point forensic accounting & hygiene checklist
│   └── valuation_models.md       # Hamilton Helmer 7 Powers & valuation frameworks (incl. platform compounders)
│
└── reports/                      # Generated institutional equity research reports
    └── portfolio_research_report.md  # 25-stock portfolio deep-dive & scenario matrices
```

---

## 🚀 How to Run Quantitative Analyses

All scripts run via the project Python virtual environment:
```bash
source /Users/sajal.goyal@zomato.com/Documents/Git/venv/bin/activate
```

### 1. Single Stock Forward Valuation Engine (Steady-State Margins)
```bash
python3 predict/scripts/forward_growth_pe.py <TICKER> \
  --cmp <CMP> \
  --mcap <MCAP_CR> \
  --eps <TTM_EPS> \
  --growth <BASE_CAGR> \
  --bull-growth <BULL_CAGR> \
  --base-exit-growth <BASE_EXIT_G> \
  --bull-exit-growth <BULL_EXIT_G>
```
*Example (Persistent Systems):*
```bash
python3 predict/scripts/forward_growth_pe.py PERSISTENT \
  --cmp 5741.00 --mcap 90564.28 --pe 48.43 \
  --growth 0.18 --bull-growth 0.24 \
  --base-exit-growth 0.16 --bull-exit-growth 0.22
```

### 2. Platform / Margin Expansion Compounders (Regime 2)
For hyper-growth companies with temporarily suppressed operating margins ($<1.5\%$):
```bash
python3 predict/scripts/forward_growth_pe.py <TICKER> \
  --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> \
  --rev-cagr <REV_CAGR> \
  --current-margin <CURRENT_NPM> \
  --target-margin-yr2 <TARGET_NPM>
```

### 3. Forensic Accounting Audit
```bash
python3 predict/scripts/forensic_audit.py <TICKER> \
  --years FY22 FY23 FY24 FY25 \
  --cfo <CFOs> --pat <PATs> --rev <REVs> --rec <RECs>
```

### 4. Expectations Investing (Reverse DCF)
```bash
python3 predict/scripts/reverse_dcf.py <TICKER> \
  --cmp <CMP> --mcap <MCAP_CR> --fcf <FCF0_CR>
```

### 5. Batch Portfolio Valuation
```bash
python3 predict/scripts/evaluate_portfolio.py --json <PATH_TO_PORTFOLIO_JSON>
```

---

## 📋 Core Research Directives & Invariants
- **Calendar Roll-Forward**: H1 (Apr 1 – Sep 30: FY$_t$ / FY$_{t+1}$) vs H2 (Oct 1 – Mar 31: FY$_{t+1}$ / FY$_{t+2}$).
- **The King Filter**: Guided CAGR $\ge 20\%$, 2-Year Forward P/E $< 50\times$, and mandated $\ge 50\%$ upside in Bull Case.
- **Dynamic Multiples**: Exit P/E derived dynamically from end-period growth rate (no arbitrary fixed multiples).
- **Execution Credibility Weighting**: Probability distribution between Base and Bull calibrated to founder track record.
