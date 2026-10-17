---
name: indian-stock-analysis
description: >-
  Conducts institutional-grade equity research and forensic valuation on Indian stocks (NSE/BSE).
  Evaluates 30%+ CAGR compounders in sunrise sectors using a 2-year forward P/E < 50 hurdle rate,
  anti-fragility audit, and deterministic quantitative Python engines.
---

# Indian Stock Analysis Protocol: High-Growth & Anti-Fragility Framework

This skill executes an institutional research protocol to evaluate high-growth (30%+ CAGR) compounders in structural sunrise sectors while eliminating fragile businesses, sunset industries, regulatory traps, middleman aggregators, and valuation bubbles.

---

## 1. Quick Decision Matrix

| Gate | Focus | Benchmark / Rule |
| :--- | :--- | :--- |
| **1. Sector Vector** | Secular tailwind | **Pass**: Clean Energy, BESS, Semis, EMS, CDMO/Hospitals. **Avoid**: Banks/NBFCs (8x–10x leverage fragility), Oil (sunset). |
| **2. Vulnerability** | External shocks | US export concentration $< 35-40\%$; zero material phase-out risk (e.g. lead-acid vs lithium); no subsidy dependence. |
| **3. Moat Test** | Anti-disintermediation | Upstream suppliers and downstream clients cannot bypass company; pricing power intact; defensible entry barrier. |
| **4. Forensic Quality** | Earnings hygiene | Cumulative 3-Yr CFO/PAT $\ge 0.8\times$; Net Debt/Equity $< 0.3\times$ (or Net Cash); receivables growth $\le$ revenue growth. |
| **5. Growth & Valuation** | The King Filter | Guided 2–3 yr CAGR $\ge 20\%$; Rolling TTM base EPS; **2-Year Forward P/E $< 50$**; **Mandated $\ge 50\%$ 2-Year Upside in Bull Case**. |
| **6. Client Concentration** | Counterparty Risk | Always disclose Top 5 and Top 10 clients and % revenue concentration; single client ideally $< 15\text{--}20\%$. |

---

## 2. AI Data Retrieval Protocol

Before performing calculations, gather accurate live and historical metrics:

1. **Company Financials & Rolling TTM EPS**:
   * Inspect **Screener.in**: `https://www.screener.in/company/<TICKER>/consolidated/` (or standalone if no subsidiaries).
   * **Rolling TTM Rule**: Do NOT use prior fiscal year annual numbers if fresh quarters (Q1/Q2/Q3) have been reported. Sum the last 4 reported quarters:
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
  * Cumulative 3-Yr CFO/PAT $\ge 0.8\times$.
  * Promoter pledging $< 10\%$ (ideally 0%).
  * No excessive CWIP parking or high contingent liabilities relative to net worth.
  * **Management Commentary Check**: When identifying red flags (e.g., debtor days expansion, CFO/PAT divergence), always check and report recent management explanations from concalls/filings (e.g., milestone billing, mix shifts, government collection cycles).
* *Optional quantitative run*:
  ```bash
  python3 .agents/skills/indian-stock-analysis/scripts/forensic_audit.py <TICKER> --years FY22 FY23 FY24 FY25 --cfo <CFOs> --pat <PATs> --rev <REVs> --rec <RECs>
  ```

### Step 5: Growth & 2-Year Forward P/E Engine (The King Filter)
Execute the forward compounding engine using the true Rolling TTM EPS base:

**Dynamic Base & Bull P/E Multiples**:
* Do NOT fix or hardcode Base and Bull P/E multiples (e.g. 35x or 50x).
* **Bull Case**: Modeled assuming execution goes as planned or better. The exit P/E multiple is determined by the accelerated/sustained growth rate expected at the end of the evaluation period.
* **Base Case**: Modeled assuming some milestones or targets are missed or delayed. The exit P/E multiple is determined by the more modest/delayed growth rate expected at the end of the evaluation period.
* **Omit Bear Case**: The Bear case scenario is eliminated; evaluation focuses on Base Case vs Bull Case asymmetry.
* **Explicit Growth Rate Rationale**: Clearly specify the operational rationale for the growth rates assumed in both scenarios (volume expansion, capacity ramps, pricing power, margin leverage, or friction points).

**A. For Steady-State / Normalized Margin Compounders** (EMS, CDMO, Industrials):
```bash
python3 .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --growth <BASE_CAGR> --bull-growth <BULL_CAGR> --base-exit-growth <BASE_G_EXIT> --bull-exit-growth <BULL_G_EXIT>
```

**B. For Platform / Early-Profitability Compounders with Non-Linear Operating Leverage** (Quick Commerce, Tech, SaaS where current Net Margin is suppressed $<1.5\%$):
*Do NOT use additive top-line growth. Use the Margin Expansion Model or direct consensus FY+2 EPS:*
```bash
# Via Margin Expansion:
python3 .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --rev-cagr <REV_CAGR> --current-margin <NPM_0> --target-margin-yr2 <NPM_2>

# OR via direct consensus FY+2 EPS:
python3 .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --target-eps-yr2 <CONSENSUS_EPS_YR2>
```

*Key Parameters (apply when appropriate)*:
* `--haircut <0.85>`: Apply a 15–20% haircut if management has a history of missing guidance.
* `--dilution <0.03>`: Factor in 3–5% annual share dilution if capex is funded via recurring QIPs/ESOPs.

*Hurdle Criteria*:
* **Growth Filter**: Net projected CAGR must be $\ge 20\%$.
* **Valuation Filter**: **2-Year Forward P/E must be $< 50$** ($\frac{\text{CMP}}{\text{EPS}_{t+2}} < 50$).
* **Upside Mandate**: **Mandatory $\ge 50\%$ upside from CMP** over 2 years in the Bull Case scenario.

*Optional Reverse DCF Engine* (Expectations Investing):
```bash
python3 .agents/skills/indian-stock-analysis/scripts/reverse_dcf.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --fcf <FCF0_CR>
```

---

## 4. Output Contract

Always generate the final research report following the layout in [references/report_template.md](./references/report_template.md).

**Mandatory Top Card Format**:
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
 Dynamic Probability Allocation:      [XX]% Base / [YY]% Bull (Calibrated to execution risk & moat defensibility)
 Final Conviction Verdict:            STRONG BUY / QUALIFIED BUY / WATCHLIST / REJECT
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

Before concluding the analysis, verify:
1. **Trailing EPS Consistency**: $\text{CMP} / \text{TTM EPS} = \text{TTM P/E}$ matches market quotes.
2. **Units Consistency**: All financial statement values in scripts are in ₹ Crores, and share prices are in ₹ per share.
3. **Forward Fiscal Year Mapping (H1 vs H2 Roll-Forward)**:
   - Identify active quarter from current date:
     - **H1 (Q1/Q2: April 1 – Sept 30)**:
       - 1-Year Target = Current running FY (**FY$_t$**), compounded by 1 year ($(1+g)^1$) from FY$_{t-1}$ base.
       - 2-Year Target = Next FY (**FY$_{t+1}$**), compounded by 2 years ($(1+g)^2$).
     - **H2 (Q3/Q4: Oct 1 – March 31)**: Multiples roll forward:
       - 1-Year Target = Next FY (**FY$_{t+1}$**), compounded by 2 years ($(1+g)^2$) from FY$_{t-1}$ base.
       - 2-Year Target = Two FYs ahead (**FY$_{t+2}$**), compounded by 3 years ($(1+g)^3$) from FY$_{t-1}$ base.
   - Example (Oct 11, 2026 $\to$ Q3 FY27): 1-Year Target is **FY28** ($(1+g)^2$) and 2-Year Target is **FY29** ($(1+g)^3$).
4. **Compounding Math Integrity**: In H1, $\text{Yr 2 EPS} = \text{Base EPS} \times (1 + g)^2$. In H2, $\text{Yr 2 EPS (FY}_{t+2}\text{)} = \text{Base EPS} \times (1 + g)^3$. Avoid undercounting or overcounting compounding years.
