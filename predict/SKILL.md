---
name: indian-stock-analysis
description: >-
  Conducts institutional equity research, forensic accounting audit, and deterministic forward
  growth valuation for Indian listed companies (NSE/BSE). Evaluates 20%+ CAGR compounders in sunrise sectors,
  applies 2-year forward P/E <= 80x hurdle, 50%+ bull upside mandate, Stage 2 trend confirmation,
  CFO/PAT conversion reality, Altman Z''-score, reverse DCF, and automatically compiles interactive HTML research dossiers.
---

# Indian Stock Analysis Protocol: High-Growth & Anti-Fragility Framework

This skill executes an institutional research protocol to evaluate high-growth ($\ge 20\%$ CAGR) compounders in structural sunrise sectors while eliminating fragile businesses, sunset industries, regulatory traps, middleman aggregators, and valuation bubbles.

---

## 1. Quick Decision Matrix (The 10 Institutional Gates)

| Gate | Focus | Benchmark / Directives |
| :--- | :--- | :--- |
| **1. Sector Vector** | Secular tailwind | **Pass**: Clean Energy, BESS, Semis, EMS, Defense Electronics, CDMO, Quick-Commerce/Tech. **Avoid**: Banks/NBFCs (high leverage fragility), Oil/Fossil Fuels (sunset). |
| **2. Geopolitical / Tariff Stress** | External shocks | US/EU export concentration $< 35-40\%$; stress-test against protectionist tariffs and Chinese dumping. Zero material phase-out risk. |
| **3. Moat & Anti-Disintermediation** | Hamilton Helmer 7 Powers | Upstream suppliers and downstream clients cannot bypass company; pricing power intact; defensible structural entry barriers. |
| **4. Forensic Quality & Earnings Hygiene** | Cash conversion reality | Cumulative 4-Yr $\text{CFO/PAT} \ge 0.8\times$; Net Debt/Equity $< 0.3\times$; receivables growth $\le$ revenue growth; Altman Z''-score $> 2.60$. |
| **5. Growth & Valuation (The King Filter)** | Asymmetric risk-reward | Guided 2–3 yr CAGR $\ge 20\%$; Rolling TTM base EPS; **2-Year Forward P/E $\le 80\times$**; **Mandated $\ge 50\%$ 2-Year Upside in Bull Case**. |
| **6. Client & Project Concentration** | Counterparty risk | Detail Top 5 and Top 10 clients and % revenue concentration; single-client exposure ideally $< 20\%$. Order book visibility for capex/EMS/defense. |
| **7. Minervini Stage 2 Confirmation** | Technical momentum | CMP $>$ 200-DMA; 50-DMA $>$ 200-DMA; Relative Strength vs Nifty $500 \ge 70$. Mark as Stage 4 caution if below 200-DMA. |
| **8. EARS & Torpedo Stop** | Empirical revision velocity | Same-Quarter YoY PAT Acceleration ($\text{YoY PAT Growth}_{Q_0} > \text{YoY PAT Growth}_{Q_{-1}}$) with March seasonality normalization. Automatic 50% trim on $>15\%$ quarterly miss. |
| **9. Capital Harvesting Protocol** | Converting paper to cash | Immediate 50% position trim upon hitting Bull Case Target Price within 12-18 months. Automated trailing stop-loss: $\max(\text{Entry}\times 0.85, \text{Peak}\times 0.82, \text{50-W EMA})$. |
| **10. Regime Selection** | Operating leverage | **Regime 1**: Steady-state margin compounders ($\text{NPM} \ge 4\%$). **Regime 2**: Margin expansion / platform compounders ($\text{NPM} < 3\%$ expanding towards $5\text{--}8\%$). |

---

## 2. AI Data Retrieval Protocol

Before performing calculations, gather verified live consolidated quotes directly from Screener:

1. **Company Financials & Rolling TTM EPS**:
   * Inspect **Screener.in**: `https://www.screener.in/company/<TICKER>/consolidated/` (or standalone if no subsidiaries).
   * **Rolling TTM Rule**: Do NOT use prior fiscal year annual numbers if fresh quarters have been reported. Sum the last 4 reported quarters:
     $$\text{TTM PAT} = \sum_{i=1}^{4} \text{PAT}_{\text{last 4 quarters}}, \quad \text{TTM EPS} = \frac{\text{TTM PAT}}{\text{Shares Outstanding}}$$
   * Cross-verify live CMP and TTM P/E ($\frac{\text{CMP}}{\text{TTM EPS}}$).
2. **Management Guidance & Transcripts**:
   * Review latest earnings call transcripts (available on Screener.in "Documents", Trendlyne, or BSE filings).
   * Extract explicit guidance: 2–3 year revenue/PAT CAGR, order book size, capex timeline, and working capital cycle.

---

## 3. Step-by-Step Execution Protocol

### Step 1: Sector Vector Gatekeeper
* Disqualify immediately if the company operates in **Banks/NBFCs** (high-leverage fragility), **Oil & Gas / Fossil Fuels** (secular terminal decline), or **Pure Commoditized Cyclicals** lacking pricing power.

### Step 2: Domain, Geopolitical & Tariff Stress-Test
* Audit export exposure to US/Europe. If $>35-40\%$, stress-test against protectionist tariffs and anti-dumping duties.
* Check for technological phase-out risks (e.g. ICE components, lead-acid displacement, single-use plastics).

### Step 3: Moat & Anti-Disintermediation Audit
* Test if the company is an asset-light middleman aggregator where upstream suppliers and downstream enterprise clients can connect directly.
* Assess durability against Hamilton Helmer's 7 Powers (see [references/valuation_models.md](./references/valuation_models.md)).

### Step 4: Balance Sheet Hygiene & Forensic Audit
* Check for Dalal Street accounting red flags (see [references/forensic_checklist.md](./references/forensic_checklist.md)):
  * Cumulative 4-Yr CFO/PAT $\ge 0.8\times$.
  * Promoter pledging $< 10\%$ (ideally 0%).
  * No excessive CWIP parking or high contingent liabilities relative to net worth.
  * **Management Commentary Check**: When identifying anomalies (e.g., debtor days expansion, CFO/PAT divergence), always incorporate recent management explanations from concalls/filings.
* *Quantitative forensic execution*:
  ```bash
  python3 predict/scripts/forensic_audit.py <TICKER> --years FY23 FY24 FY25 FY26 --cfo <CFOs> --pat <PATs> --rev <REVs> --rec <RECs>
  ```

### Step 5: Growth & 2-Year Forward P/E Engine (The King Filter)
Execute the forward compounding engine using verified Screener quotes and empirical first-principles calibration:

**Calendar Roll-Forward Mapping (H1 vs H2)**:
* **H1 (Apr 1 – Sep 30)**: 1-Yr Target rolls to current FY ($FY_t$, 1-yr comp); 2-Yr Target rolls to next FY ($FY_{t+1}$, 2-yr comp).
* **H2 (Oct 1 – Mar 31)**: 1-Yr Target rolls to $FY_{t+1}$ (2-yr comp); 2-Yr Target rolls to $FY_{t+2}$ (3-yr comp).

**Dynamic Base & Bull P/E Multiples**:
* Do NOT fix or hardcode exit P/Es (e.g. 35x or 50x).
* Exit multiples must be dynamically derived based on expected ongoing growth rate at the end of the evaluation period.

**A. For Steady-State Margin Compounders (Regime 1)**:
```bash
python3 predict/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --growth <BASE_CAGR> --bull-growth <BULL_CAGR> --base-exit-growth <BASE_G_EXIT> --bull-exit-growth <BULL_G_EXIT>
```

**B. For Platform / Early-Profitability Compounders with Non-Linear Operating Leverage (Regime 2)**:
```bash
python3 predict/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --rev-cagr <REV_CAGR> --current-margin <NPM_0> --target-margin-yr2 <NPM_2>
```

**C. Expectations Investing (Reverse DCF Implied 10-Yr FCF CAGR)**:
```bash
python3 predict/scripts/reverse_dcf.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --fcf <FCF0_CR>
```

### Step 6: Interactive HTML Research Dossier Compilation (Mandatory Deliverable)
Per GEMINI.md Rule 9, standalone markdown files are never the end deliverable. Always compile research into an institutional HTML dashboard and update the coverage portal:
```bash
# Convert research markdown to interactive HTML dashboard
python3 predict/scripts/generate_html_report.py predict/reports/<ticker>_research_report.md

# Re-index Research Coverage Portal
python3 predict/scripts/generate_html_report.py --all
```

---

## 4. Output Contract

Always include the Probability-Weighted Valuation Summary Card and a high-contrast 1-2 line investment commentary (Why Buy or Avoid) in the Hero Banner and Research Portal Card:

```text
================================================================================
 VALUATION & EXPECTED TARGET PRICE SUMMARY (FROM LAST CLOSING PRICE)
================================================================================
 Last Closing Price (CMP):            ₹[CMP]
 Latest Market Cap:                   ₹[MCAP] Cr
 Target Time Horizon:                 2-Year Horizon ([FY_START] to [FY_TARGET])
 Expected Target Price (Wtd Avg):     ₹[EXPECTED_PRICE]
 Total Expected Return:               [+/- XX.X]% from CMP
 Annualized Expected Return (CAGR):   [+/- XX.X]% p.a.
 Dynamic Probability Allocation:      [XX]% Base / [YY]% Bull (Calibrated to execution credibility & moat)
 Technical Trend Gate (Stage 2):      [STAGE 2 CONFIRMED / STAGE 4 CAUTION]
 Quarterly EARS Rating:               [POSITIVE ACCELERATION / MODERATING / TORPEDO]
 Cash Harvesting Target (50% Trim):   ₹[BULL_PRICE] (+[XX.X]%)
 Dynamic Trailing Stop-Loss:          ₹[STOP_PRICE] (-15.0% Capital Protection)
 Final Conviction Verdict:            STRONG HIGH-GROWTH BUY / QUALIFIED BUY / REJECT
================================================================================

--- UNDERLYING SCENARIO TARGET BREAKDOWN & EXPLANATION ---
• Base Case Target ([XX]% Prob):   ₹[BASE_PRICE] ([+/- XX.X]%) | Exit P/E: [XX.X]x on [XX.X]% end-growth
  Rationale: [Clear operational reason / delayed milestone thesis]
• Bull Case Target ([YY]% Prob):   ₹[BULL_PRICE] (+[XX.X]%) | Exit P/E: [XX.X]x on [XX.X]% end-growth
  Rationale: [Clear operational reason / flawless execution thesis]
================================================================================
```

---

## 5. Verification & Sanity Checks

1. **Trailing EPS Consistency**: $\text{CMP} / \text{TTM EPS} = \text{TTM P/E}$ matches market quotes.
2. **Units Consistency**: All financial statement values in ₹ Crores; share prices in ₹ per share.
3. **Calendar Compounding Powers**: Ensure compounding years match H1 ($(1+g)^1, (1+g)^2$) vs H2 ($(1+g)^2, (1+g)^3$).
4. **Hurdle Verification**: 2-Year Forward P/E must be $\le 80\times$ and Bull Case Upside must be $\ge 50\%$ from CMP ($\ge 40\%$ for mega-cap duopolies).
