# Indian Stock Analysis Protocol: High-Growth & Anti-Fragility Framework

This protocol defines the institutional research framework to evaluate high-growth (30%+ CAGR) compounders in structural sunrise sectors while eliminating fragile businesses, sunset industries, regulatory traps, middleman aggregators, and valuation bubbles.


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
| **7. Stage 2 Trend Gate** | Technical Timing | **Pass**: $\text{CMP} > \text{200-DMA}$, $\text{50-DMA} > \text{200-DMA}$, $\text{RS} \ge 70$. **Reject**: Stage 4 downtrends below 200-DMA. |
| **8. EARS & Torpedo** | Quarterly Momentum | $\text{YoY PAT Growth}_{Q_0} > \text{YoY PAT Growth}_{Q_{-1}}$, $\text{CFO}/\text{EBITDA} \ge 0.7\text{x}$; automated exit on $>15\%$ miss. |
| **9. Normalized Turnaround** | Suppressed Base Bridge | For thin-margin turnarounds (Trent/Zomato), bridge Normalized PAT at 5–8% benchmark NPM (Fwd P/E $< 45\times$). |
| **10. Cash Harvesting** | Realized Profit Lock | Harvest 50% cash upon early Bull Target hit (12–18m); dynamic trailing stop at $\max(\text{Entry}\times 0.85, \text{Peak}\times 0.82, \text{50-WMA})$. |

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
* Assess durability against Hamilton Helmer's 7 Powers (see [valuation_models.md](./valuation_models.md)).

### Step 4: Balance Sheet Hygiene & Forensic Audit
* Check for Dalal Street accounting red flags (see [forensic_checklist.md](./forensic_checklist.md)):
  * Cumulative 3-Yr CFO/PAT $\ge 0.8\times$.
  * Promoter pledging $< 10\%$ (ideally 0%).
  * No excessive CWIP parking or high contingent liabilities relative to net worth.
  * **Management Commentary Check**: When identifying red flags (e.g., debtor days expansion, CFO/PAT divergence), always check and report recent management explanations from concalls/filings (e.g., milestone billing, mix shifts, government collection cycles).
* *Optional quantitative run*:
  ```bash
  python3 predict/scripts/forensic_audit.py <TICKER> --years FY22 FY23 FY24 FY25 --cfo <CFOs> --pat <PATs> --rev <REVs> --rec <RECs>
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
python3 predict/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --growth <BASE_CAGR> --bull-growth <BULL_CAGR> --base-exit-growth <BASE_G_EXIT> --bull-exit-growth <BULL_G_EXIT>
```

**B. For Platform / Early-Profitability Compounders with Non-Linear Operating Leverage** (Quick Commerce, Tech, SaaS, Marketplaces where current Net Margin is thin $<3.0\%$):
*Do NOT use linear EPS compounding. Programmatic guard strictly enforces the Margin Expansion Model or direct line-item consensus:*
```bash
# Via Margin Expansion (Regime 2 Master):
python3 predict/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --rev-cagr <REV_CAGR> --current-margin <NPM_0> --target-margin-yr2 <NPM_2>

# OR via direct consensus / line-item FY+2 EPS:
python3 predict/scripts/forward_growth_pe.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --eps <TTM_EPS> --target-eps-yr2 <CONSENSUS_EPS_YR2>
```

**C. Regime 2 Normalized Margin Bridge for Turnarounds & Suppressed Earnings Compounders** (Turnaround retail like Trent, Capex ramps like Kaynes/Dixon):
*When trailing base EPS is distorted by rapid dark store/retail footprint expansion, plant commissioning, or post-crisis turnaround:*
* Compute **Normalized FY+2 PAT**:
  $$\text{Normalized FY+2 PAT} = \text{Target FY+2 Revenue} \times \text{Steady-State Benchmark NPM (5% to 8\%)}$$
  $$\text{Normalized 2-Year Forward P/E} = \frac{\text{Market Cap}}{\text{Normalized FY+2 PAT}}$$
* If Normalized 2-Year Forward P/E $< 45\times$ and Revenue CAGR $\ge 30\%$, it passes the valuation gate, eliminating Type II missed multibagger rejections.

**D. Empirical Growth Derivation Bridge (Zero Unanchored Numbers)**:
* Every CAGR assumed must be bridged against:
  1. 3-Year Historical Revenue CAGR
  2. Last Reported FY / TTM YoY Growth Rate
  3. Segment-Level Mix Shifts (e.g., core services vs new product ramps)
  4. Official Management Guidance from recent concalls.
* Base Case CAGR must reflect conservative normalization or category maturation; Bull Case CAGR must reflect sustained historical velocity and full guidance execution.

**E. Contracted Mega-Cap Duopoly Cash Invariant (The Bharti Airtel Invariant)**:
* For contracted infrastructure/telecom duopolies ($\text{Mcap} \ge ₹50,000\text{ Cr}$) with massive cash generation ($\text{CFO/PAT} \ge 2.5\times$ or $\text{EBITDA Margin} \ge 40\%$):
  1. **Depreciation Neutralization**: Evaluate on **EV/EBITDA ($< 15\times$)** or **Cash Forward P/E** ($\frac{\text{CMP}}{\text{Cash EPS}_{t+2}} < 30\times$, where $\text{Cash EPS} = \text{EPS} + \text{Depreciation per share}$) to prevent false negatives from accounting amortizations.
  2. **Calibrated Bull Upside Hurdle**: Lowered from $\ge 50\%$ to **$\ge 40\%$** (or Expected CAGR $\ge 18\%$).

**F. Cyclical Commodity Margin Peak & Global Dumping Guard (The Chemical Trap Guard)**:
* For intermediate chemical, metal, and commodity processors:
  1. **Peak Margin Normalization**: If $\text{TTM OPM} > 1.25 \times \text{5-Year Median OPM}$, projections must NOT compound from peak EPS; anchor base to **Normalized Median OPM EPS**.
  2. **Dumping & Destocking Gate**: If Gross Margin contracts by $>300\text{ bps}$ YoY for 2 consecutive quarters ($\Delta \text{GM} < -300\text{ bps}$), mark as `CYCLICAL DE-STOCKING TRAP` and disqualify entry.

*Key Parameters (apply when appropriate)*:
* `--haircut <0.85>`: Apply a 15–20% haircut if management has a history of missing guidance.
* `--dilution <0.03>`: Factor in 3–5% annual share dilution if capex is funded via recurring QIPs/ESOPs.

*Hurdle Criteria*:
* **Growth Filter**: Net projected CAGR must be $\ge 20\%$ (or $\ge 16\%$ for contracted mega-cap duopolies).
* **Valuation Filter**: **2-Year Forward P/E must be $< 50$** ($\frac{\text{CMP}}{\text{EPS}_{t+2}} < 50$, or Cash P/E $< 30\times$).
* **Upside Mandate**: **Mandatory $\ge 50\%$ upside from CMP** over 2 years in Bull Case ($\ge 40\%$ for contracted mega-cap duopolies).


### Step 6: Minervini / CANSLIM Stage 2 Trend Confirmation Gate
* A fundamentally approved stock must **never be entered in a Stage 4 downtrend**.
* **Technical Confirmation Criteria**:
  1. **Price Trend**: $\text{CMP} > \text{200-DMA}$.
  2. **Trend Momentum**: $\text{50-DMA} > \text{200-DMA}$ with 200-DMA sloping upward or flattening.
  3. **Relative Strength (RS)**: Outperforming NIFTY 500 over 6–12 months ($\text{RS Rating} \ge 70$).
* If CMP is below 200-DMA, flag as `STAGE 4 CAUTION / WAIT FOR PULLBACK` to prevent catching falling knives.

### Step 7: Quarterly Earnings Revision & Acceleration Score (EARS)
* Do not rely solely on annual statements (4-month publishing lag). Audit the last 2 reported quarters:
  1. **Acceleration Invariant**: $\text{YoY PAT Growth}_{Q_0} > \text{YoY PAT Growth}_{Q_{-1}}$.
  2. **Cash Reality Check**: Quarterly $\frac{\text{CFO}}{\text{Operating Profit}} \ge 0.70$.
  3. **March-Quarter Seasonality Normalization Protocol**:
     * For businesses with lumpy Q4 billing cycles (e.g., Defense PSUs like HAL/BEL, EPC, Capital Goods, and IT solutions where 40–55% of annual PAT is booked in March), sequential QoQ ($Q_0 \text{ vs } Q_{-1}$) causes false panic (e.g., June Q1 dropping 60% sequentially vs March Q4).
     * **Same-Quarter Year-over-Year Matching**: Growth is always measured relative to the same quarter of the prior year:
       $$\text{YoY Growth}_{Q_0} = \frac{\text{PAT}_{Q_0} - \text{PAT}_{Q_{-4}}}{\text{PAT}_{Q_{-4}}}, \quad \text{YoY Growth}_{Q_{-1}} = \frac{\text{PAT}_{Q_{-1}} - \text{PAT}_{Q_{-5}}}{\text{PAT}_{Q_{-5}}}$$
       $$\text{Acceleration Confirmed} \iff \text{YoY Growth}_{Q_0} > \text{YoY Growth}_{Q_{-1}}$$
     * **Rolling 4-Quarter TTM Base**: TTM PAT is computed over the last 4 quarters ($\sum_{k=0}^{3} \text{PAT}_{t-k}$), ensuring every evaluation base contains exactly one March quarter, removing all seasonal bias.
     * **Pre-Q4 Execution Indicators**: In Q1–Q3, evaluate Book-to-Bill ratio ($\ge 1.2\times$), order backlog growth, and unearned revenue/customer advances rather than expecting linear quarterly PAT distribution.
  4. **Earnings Torpedo Rule**: If a company reports a quarterly PAT miss of $>15\%$ against consensus (measured against seasonally adjusted street consensus for that quarter), automatically trigger an **immediate 50% position trim or exit** to prevent catastrophic capital destruction (avoids traps like Tanla).

### Step 8: Dynamic Cash Harvesting & Trailing Stop Protocol (The Cash Earning Engine)
* Convert paper valuations into realized cash profits:
  1. **Tranche 1 Profit Take (50% Realized Cash)**: When the market price reaches the **Bull Case Target Price** within 12–18 months, immediately sell **50% of the position** and transfer proceeds into cash / liquid treasuries.
  2. **Dynamic Trailing Stop-Loss Protection**: Protect remaining capital with a dynamic stop-loss:
     $$\text{Stop Price} = \max(\text{Entry Price} \times 0.85, \; \text{Peak Price} \times 0.82, \; \text{50-Week EMA})$$
     If closed below on a weekly basis, liquidate remaining shares to lock in profits and protect downside.

*Optional Reverse DCF Engine* (Expectations Investing):
```bash
python3 predict/scripts/reverse_dcf.py <TICKER> --cmp <CMP> --mcap <MCAP_CR> --fcf <FCF0_CR>
```

---

## 4. Output Contract

Always generate the final research report following the layout in [report_template.md](./report_template.md).

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
 Technical Trend Gate (Stage 2):      STAGE 2 CONFIRMED / STAGE 4 CAUTION (CMP vs 200-DMA)
 Quarterly EARS Rating:               POSITIVE ACCELERATION / NEUTRAL / TORPEDO ALERT
 Cash Harvesting Target (50% Trim):   ₹[BULL_PRICE] (+[XX.X]%)
 Dynamic Trailing Stop-Loss:          ₹[STOP_PRICE] (-15% Entry / -18% Peak)
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
