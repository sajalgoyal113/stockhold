# Forensic Accounting Checklist for Indian Listed Companies (Dalal Street Field Manual)

This reference guide details forensic red flags, accounting manipulations, and governance risks specific to Indian equity markets (NSE / BSE / MCA / SEBI regulations).

---

## 1. Cash Flow vs Accounting Profit Divergence
* **CFO / PAT Conversion Ratio**:
  * Measure across a 3-year and 5-year rolling cycle: $\frac{\sum \text{CFO}}{\sum \text{PAT}}$.
  * **Pristine**: $\ge 1.0\times$ (Depreciation shields cash; business collects cash faster than accounting profit).
  * **Acceptable**: $0.8\times - 1.0\times$.
  * **Amber / Yellow Flag**: $0.5\times - 0.8\times$ (Profits trapped in working capital or unbilled revenue).
  * **Critical Red Flag**: $< 0.5\times$ or negative CFO with positive PAT. High probability of fabricated revenue, uncollected credit sales, or non-cash paper gains.
  * **Zero-Debt Long-Cycle Working Capital Exemption**: In capital goods, defense systems, aerospace, and heavy manufacturing with 24-48 month build cycles, physical inventory and work-in-progress (WIP) absorb cash prior to milestone clearance. If the franchise is **virtually debt-free ($\text{Debt/Equity} \le 0.05\text{x}$ or Net Cash)** and cumulative 4-year operating cash flow is positive, there is zero risk of credit default or insolvency. The 4-year cumulative $\text{CFO/PAT}$ hurdle is calibrated to $\ge 0.30\times$. If $\text{Debt/Equity} > 0.05\text{x}$, the standard $\ge 0.60\times$ hurdle remains non-negotiable.

---

## 2. Working Capital & Revenue Quality
* **Receivables vs Revenue Velocity**:
  * Compare $\text{YoY Receivables Growth}$ against $\text{YoY Revenue Growth}$.
  * If trade receivables grow at $2\times$ the rate of revenue over 2+ consecutive quarters, audit for:
    * Channel stuffing near quarter-end.
    * Extended credit terms granted to distributors to inflate volume.
    * "Bill and hold" arrangements or unbilled revenue booked under other current assets.
* **Cash Conversion Cycle (CCC = DIO + DSO - DPO)**:
  * Persistent expansion in CCC indicates weakening bargaining power against either suppliers or customers.
* **Bad Debt Provisioning**:
  * Check Note on "Expected Credit Loss (ECL)" under Ind AS 109. If aging receivables (>180 days) are rising while ECL provisions are dropping, earnings are artificially inflated.

---

## 3. Capitalization & Asset Side Shenanigans
* **Capital Work in Progress (CWIP) as a Parking Lot**:
  * Continuous high CWIP as a % of Gross Block that does not commercialize into Gross Block over 2-3 years.
  * Companies often park operating expenses (interest, employee salaries, administrative overheads) into CWIP to prevent them from hitting the P&L, artificially inflating EBITDA.
* **Intangibles under Development**:
  * Capitalization of software development costs, platform development, or brand expenses instead of expensing via SG&A.
* **Frequent Asset Revaluations or Goodwill Impairment Avoidance**:
  * Carrying acquired subsidiaries or intangibles at book value without impairment testing despite falling subsidiary cash flows.

---

## 4. Governance, Promoter Behavior & Capital Allocation
* **Promoter Pledging**:
  * Check Trendlyne / BSE corporate shareholding filings.
  * High pledging creates a reflexive trap: sharp market drawdowns trigger margin calls from NBFCs/mutual funds, forcing emergency distress selling.
  * $0\%$: Pristine.
  * $<10\%$: Monitor.
  * $10\% - 25\%$: Elevated structural risk.
  * $>25\%$: High governance hazard.
* **Related Party Transactions (RPTs)**:
  * Scrutinize the annual report RPT note:
    * Sales/purchases from private promoter-owned LLPs or private limited companies.
    * Loans/advances given to related parties.
    * Brand royalty or management consulting fees paid to promoter family trusts.
* **Auditor Red Flags**:
  * Sudden resignation of statutory auditors midway through the fiscal year (citing "pre-occupation" or lack of management disclosures).
  * Surging non-audit fees relative to statutory audit fees.
  * Churn from Tier-1 audit firms (Big 4 / Walker Chandiok / BSR / SR Batliboi) to unknown sole proprietorships.
* **Contingent Liabilities**:
  * Compare contingent liabilities (tax demands under appeal, corporate guarantees given to sister concerns) against Net Worth. If $>20\%$ of Net Worth, a sudden adverse court/tribunal ruling can impair equity value.
