# Equity Research Directives (Indian Equities)

When analyzing, valuing, or reviewing any Indian listed company (NSE/BSE), activate the `indian-stock-analysis` skill (`.agents/skills/indian-stock-analysis/SKILL.md`).

## Core Invariants
1. **Trailing EPS Base**: Never use stale annual report numbers when fresh quarterly results exist; compute Rolling TTM EPS from the last 4 reported quarters.
2. **Growth & Valuation Hurdle**: Target companies in sunrise sectors with $\ge 20\%$ guided CAGR where **2-Year Forward P/E $< 50$** and a mandated minimum **$\ge 50\%$ upside from current market price within 2 years in the Bull Case scenario**. Avoid banks/NBFCs and sunset fossil fuels.
3. **Executive Summary Card**: Always begin analysis reports with the Valuation & Expected Target Price Summary Card as defined in the skill's report template (`.agents/skills/indian-stock-analysis/references/report_template.md`). The top summary card MUST prominently display the **Probability-Weighted Expected Value** (Expected Target Price, Total Expected Return %, Annualized CAGR, Latest Market Cap, and Dynamic Probability Allocation). The underlying Base Case and Bull Case target prices, exit P/E multiples, compounding speeds, and operational rationales are detailed in the explanations below.
4. **Client Concentration & Transparency**: Always detail the company's top clients and revenue concentration (Top 5 / Top 10 breakdown and single-client exposure).
5. **Order Book & Project Visibility**: If the company maintains an order book or program pipeline (auto components, EMS, defense, EPC, capital goods), detail the order book size, top upcoming vehicle/product projects, awarding clients, and multi-year revenue visibility (% of forward revenue covered).
6. **Target Horizon & Forward Financial Year Mapping (H1 vs H2 Roll-Forward)**:
   - Identify the active quarter based on the current date:
     - **H1 (Q1/Q2: April 1 – Sept 30)**:
       - **1-Year Target**: Current running fiscal year (**FY$_t$**), compounded by 1 year ($(1+g)^1$) from the last reported annual base (FY$_{t-1}$).
       - **2-Year Target**: Next fiscal year (**FY$_{t+1}$**), compounded by 2 years ($(1+g)^2$).
     - **H2 (Q3/Q4: Oct 1 – March 31)**: Multiples roll forward as H1 concludes:
       - **1-Year Target**: Next fiscal year (**FY$_{t+1}$**), compounded by 2 years ($(1+g)^2$) from the FY$_{t-1}$ base.
       - **2-Year Target**: Two fiscal years ahead (**FY$_{t+2}$**), compounded by 3 years ($(1+g)^3$) from the FY$_{t-1}$ base.
   - Example (Oct 11, 2026 $\to$ Q3 FY27):
     - Running year is FY27. Because it is H2, 1-Year target rolls to **FY28** ($(1+g)^2$) and 2-Year target rolls to **FY29** ($(1+g)^3$).
   - **Omit Bear Case Scenario**: Remove the Bear case scenario entirely. Only provide **Base Case** and **Bull Case** scenarios.
   - **Dynamic Base & Bull P/E Multiples**: Never use fixed/arbitrary exit P/E multiples (like hardcoded 35x or 50x). Exit P/E ratios must be determined dynamically based on the expected ongoing growth rate at the end of the evaluation period:
     - **Bull Case**: Flawless execution or better; the exit P/E is determined by the accelerated/sustained growth rate expected at the end of the evaluation period.
     - **Base Case**: Some targets are missed or delayed; the exit P/E is determined by the more modest/delayed growth rate expected at the end of the evaluation period.
   - **Explicit Growth Rate Rationale**: Always state a clear, fundamental operational reason for the growth rate assumed to forecast target prices in each scenario (volume runway, capacity additions, pricing power, margin expansion, or competitive friction).
   - **Dynamic Probability Weighting (Execution Credibility & Moat Calibration)**: The probability split between Base Case and Bull Case must NEVER be fixed (e.g. hardcoded 60/40). It must be dynamically calibrated based on **Founder/CEO execution credibility**, guidance track record, and competitive intensity:
     - *Elite Founder-Led / High-Credibility Execution (Consistently meets/beats guidance, e.g. Deepinder Goyal at Eternal, Dixon, Trent)*: Bull Case receives higher weightage $\implies$ **50% Base / 50% Bull** or **45% Base / 55% Bull**.
     - *Mature, Contracted Monopolies / Oligopolies with high stability*: e.g., **55% Base / 45% Bull**.
     - *Early-Stage / Fierce Multi-Player Price Wars with unproven margin delivery*: e.g., **65% Base / 35% Bull**.
     - *High Regulatory Vulnerability or History of Missed Guidance (e.g. sovereign supplier traps like ixigo)*: Base Case dominates $\implies$ **75% Base / 25% Bull**.
   - **Structured & Intuitive Report Presentation**: Reports must be visually structured, scannable, and clean—utilizing concise executive cards, clear comparative tables, bulleted thematic drivers, and explicit actionable price trigger ranges (Accumulate / Hold / Trim).
7. **Management Commentary on Forensic & Working Capital Anomalies**:
   - Whenever identifying red flags or friction points (e.g., expanding debtor days, CFO/PAT divergence, margin compression, write-offs, or slowing top-line growth), always investigate and explicitly incorporate **what management has stated in recent earnings calls, annual reports, or filings** regarding these specific anomalies (e.g., segment mix shifts, milestone-based billing, government payment cycles, or collection remediation).
