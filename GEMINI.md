# Equity Research Directives (Indian Equities)

When analyzing, valuing, or reviewing any Indian listed company (NSE/BSE), always use the quantitative engines, models, checklists, and institutional research frameworks in `predict/`.

---

## 1. Repository Architecture & Separation of Concerns

The repository is strictly organized into two distinct functional workspaces:

```text
Finance/
├── stockhold/                     # Interactive Web Application & Visual Dashboard
│   ├── app.py                    # Streamlit frontend & Google Stitch design system
│   ├── engine/                   # App engine modules
│   │   ├── data_fetcher.py       # Screener.in consolidated scraper & historical quotes
│   │   ├── valuation.py          # Forward growth & dynamic exit P/E compounding logic
│   │   ├── forensics.py          # CFO/PAT reality check & Altman Z''-score
│   │   ├── reverse_dcf.py        # Expectations investing (reverse DCF implied CAGR)
│   │   └── ai_analyst.py         # Google Gemini AI synthesis & 7 Powers audit
│   ├── run_app.sh                # Streamlit launcher script
│   ├── requirements.txt          # Web app dependencies
│   └── README.md                 # StockHold application documentation
│
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
└── GEMINI.md                      # Behavioral rules, facts & repo source of truth
```

---

## 2. Core Operational Directives & Workspace Rules

1. **Always Refer to `predict/` to Analyse Any Stock**:
   - The `predict/` folder is the sole authoritative workspace and master source of truth for all stock analysis, forward growth modeling, terminal P/E exit derivations, forensic accounting audits, reverse DCF computations, and institutional equity research reports.
   - When evaluating any company or portfolio, always run calculation engines from `predict/scripts/`, verify checklists in `predict/references/`, and save analysis outputs to `predict/reports/`.

2. **Only Refer to `stockhold/` When Asked About the Web App**:
   - Refer to `stockhold/` **strictly and only** when the user asks questions or requests modifications regarding the Streamlit web application, user interface, Google Stitch styling, interactive charts, or web deployment.
   - **Never treat `stockhold/` as the source of truth for stock analysis.**
   - The web app's underlying methods of computing, projecting, and analysing stocks must remain **100% identical and synchronized** with the logic in `predict/`.

3. **Consolidation in `predict/` & Zero Auto-Memory**:
   - All analytical scripts (`forward_growth_pe.py`, `forensic_audit.py`, `reverse_dcf.py`, `evaluate_portfolio.py`) and reference documentation (`report_template.md`, `forensic_checklist.md`, `valuation_models.md`) are consolidated directly inside `predict/` so that all files are visible, editable, and version-controlled.
   - **Do NOT store stock analysis facts, learned preferences, or corrections in the auto-memory system.** All new stock-related insights, model updates, company notes, and portfolio evaluations must be recorded directly in `predict/` (for models/reports) or in `GEMINI.md` (for behavioral directives and rules).

4. **Python Runtime Environment**:
   - The primary execution environment is `/Users/sajal.goyal@zomato.com/Documents/Git/venv` (Python 3.13) or local `stockhold/venv`.

5. **Deterministic Math Invariant**:
   - Financial ratios, exit multiples, compounded EPS, and implied growth rates must ALWAYS be calculated deterministically via Python engines (`predict/scripts/`). Never hallucinate numerical projections.

6. **Zero Manual Quote Entry & Live Consolidated Verification**:
   - Never manually pass or hardcode stock prices (CMP), Market Cap, or TTM EPS from memory or unverified notes.
   - All engines in `predict/scripts/` (`forward_growth_pe.py`, `reverse_dcf.py`) must automatically fetch verified live consolidated quotes directly from Screener (`data_fetcher.py`) by default.
   - If a manual `--cmp` is explicitly passed for limit-order or entry-price stress-testing, the engine automatically checks for price drift against the live market price and triggers a prominent `[PRICE DRIFT WARNING]` if the deviation exceeds 5%.

7. **Strict Root Directory Invariant & Cloud Deployment Entrypoints**:
   - The primary repository logic is strictly organized into:
     ```text
     Finance/
     ├── predict/                       # Quantitative Analysis & Research Reports (MASTER SOURCE OF TRUTH)
     ├── stockhold/                     # Interactive Web Application & Visual Dashboard
     └── GEMINI.md                      # Behavioral rules, facts & repo source of truth
     ```
   - For Streamlit Community Cloud hosting (`stockhold.streamlit.app`), the root directory maintains thin, pass-through deployment entrypoints (`app.py`, `requirements.txt`, `run_app.sh`, `README.md`) that delegate directly into `stockhold/` while resolving all paths.
   - No ad-hoc scripts, scratch files, or unversioned temporary files are permitted in the root folder.
   - All Streamlit web application components, requirements, launchers, and frontend docs reside within `stockhold/`, while all quantitative engines and research reports reside within `predict/`.

---

## 3. Core Valuation Invariants

1. **Trailing EPS Base**: Never use stale annual report numbers when fresh quarterly results exist; compute Rolling TTM EPS from the last 4 reported quarters:
   $$\text{TTM PAT} = \sum_{i=1}^{4} \text{PAT}_{\text{last 4 quarters}}, \quad \text{TTM EPS} = \frac{\text{TTM PAT}}{\text{Shares Outstanding}}$$
2. **Growth & Valuation Hurdle**: Target companies in sunrise sectors with $\ge 20\%$ guided CAGR where **2-Year Forward P/E $< 50$** and a mandated minimum **$\ge 50\%$ upside from current market price within 2 years in the Bull Case scenario**. Avoid banks/NBFCs (high leverage fragility) and sunset fossil fuels.
3. **Executive Summary Card**: Always begin analysis reports with the Valuation & Expected Target Price Summary Card as defined in `predict/references/report_template.md`. The top summary card MUST prominently display the **Probability-Weighted Expected Value** (Expected Target Price, Total Expected Return %, Annualized CAGR, Latest Market Cap, and Dynamic Probability Allocation).
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
   - Example (Oct 18, 2026 $\to$ Q3 FY27):
     - Running year is FY27. Because it is H2, 1-Year target rolls to **FY28** ($(1+g)^2$) and 2-Year target rolls to **FY29** ($(1+g)^3$).
   - **Omit Bear Case Scenario**: Remove the Bear case scenario entirely. Only provide **Base Case** and **Bull Case** scenarios.
   - **Dynamic Base & Bull P/E Multiples**: Never use fixed/arbitrary exit P/E multiples (like hardcoded 35x or 50x). Exit P/E ratios must be determined dynamically based on the expected ongoing growth rate at the end of the evaluation period:
     - **Bull Case**: Flawless execution or better; exit P/E is determined by the accelerated/sustained growth rate expected at the end of the evaluation period.
     - **Base Case**: Some targets are missed or delayed; exit P/E is determined by the more modest/delayed growth rate expected at the end of the evaluation period.
   - **Explicit Growth Rate Rationale**: Always state a clear, fundamental operational reason for the growth rate assumed in each scenario (volume runway, capacity additions, pricing power, margin expansion, or competitive friction).
   - **Dynamic Probability Weighting (Execution Credibility & Moat Calibration)**: The probability split between Base Case and Bull Case must NEVER be fixed (e.g. hardcoded 60/40). It must be dynamically calibrated based on **Founder/CEO execution credibility**, guidance track record, and competitive intensity:
     - *Elite Founder-Led / High-Credibility Execution (Consistently meets/beats guidance, e.g. Dixon, Trent, Netweb)*: Bull Case receives higher weightage $\implies$ **50% Base / 50% Bull** or **45% Base / 55% Bull**.
     - *Mature, Contracted Monopolies / Oligopolies with high stability*: e.g., **55% Base / 45% Bull**.
     - *Early-Stage / Fierce Multi-Player Price Wars with unproven margin delivery*: e.g., **65% Base / 35% Bull**.
     - *High Regulatory Vulnerability or History of Missed Guidance (e.g. sovereign supplier traps like ixigo)*: Base Case dominates $\implies$ **75% Base / 25% Bull**.
   - **Structured & Intuitive Report Presentation**: Reports must be visually structured, scannable, and clean—utilizing concise executive cards, clear comparative tables, bulleted thematic drivers, and explicit actionable price trigger ranges (Accumulate / Hold / Trim).
7. **Management Commentary on Forensic & Working Capital Anomalies**:
   - Whenever identifying red flags or friction points (e.g., expanding debtor days, CFO/PAT divergence, margin compression, write-offs, or slowing top-line growth), always investigate and explicitly incorporate **what management has stated in recent earnings calls, annual reports, or filings** regarding these specific anomalies (e.g., segment mix shifts, milestone-based billing, government payment cycles, or collection remediation).
8. **Regime Selection & Platform Operating Leverage Invariant (Regime 1 vs Regime 2)**:
   - **Regime 1 (Steady-State Margin Growth)**: Applied strictly to established compounders with mature, steady margins ($\ge 4\text{--}5\%$, e.g. Dixon, Kaynes, Polycab, HAL) where earnings grow linearly alongside revenue.
   - **Regime 2 (Non-Linear Operating Leverage & Margin Expansion)**: Mandatory for early-profitability platforms, quick-commerce, SaaS, or turnaround compounders where trailing net margin is thin ($<3\%$) but guided for operational leverage (e.g. Zomato/ETERNAL, Urban Company). Silent fallback to linear Regime 1 is strictly prohibited; models must explicitly specify Revenue CAGR, Current NPM, and Target Horizon NPM.
9. **Empirical Growth Derivation Bridge (Zero Arbitrary Numbers)**:
   - Never assume a CAGR out of thin air. Every report must present an explicit 4-point historical growth bridge:
     1. 3-Year Historical Revenue CAGR
     2. Last Reported FY / TTM YoY Growth Rate
     3. Segment Mix Dynamics (e.g., core service stability vs product ramp surges)
     4. Official Management Guidance from earnings transcripts.
   - Base Case CAGR must reflect conservative normalization or category maturation; Bull Case CAGR must reflect sustained historical velocity and full guidance execution.
10. **Minervini / CANSLIM Stage 2 Trend Confirmation Gate**:
    - A fundamentally approved stock must **never be entered in a Stage 4 downtrend**.
    - Mandatory Technical Confirmation: $\text{CMP} > \text{200-DMA}$, $\text{50-DMA} > \text{200-DMA}$, and **Relative Strength (RS vs Nifty 500) $\ge 70$**.
    - If CMP is below the 200-DMA, the stock is marked as `STAGE 4 CAUTION / WAIT FOR PULLBACK` to prevent catching falling knives and enduring 30-50% mark-to-market drawdowns.
11. **Quarterly Earnings Revision & Acceleration Score (EARS) & Torpedo Rule**:
    - Never rely solely on annual numbers or unanchored management guidance.
    - Validate empirical quarterly momentum: $\text{YoY PAT Growth}_{\text{Q}_0} > \text{YoY PAT Growth}_{\text{Q}_{-1}}$ and Quarterly $\text{CFO} / \text{Operating Profit} \ge 0.70$.
    - **March-Quarter Seasonality Invariant**: For companies with extreme Q4/March seasonality (e.g. Defense PSUs like HAL/BEL, Capital Goods, EPC where 40–55% of annual PAT is booked in March), sequential QoQ ($Q_0 \text{ vs } Q_{-1}$) produces false deceleration alarms (-60% June vs March). EARS mandates **Same-Quarter Year-over-Year Matching** ($\frac{\text{PAT}_{Q_0}-\text{PAT}_{Q_{-4}}}{\text{PAT}_{Q_{-4}}} > \frac{\text{PAT}_{Q_{-1}}-\text{PAT}_{Q_{-5}}}{\text{PAT}_{Q_{-5}}}$) and **Rolling 4-Quarter TTM PAT Compounding**, which completely neutralizes seasonal distortions. Torpedo miss triggers are strictly evaluated against seasonally adjusted consensus.
    - **Earnings Torpedo Stop**: Automatically trigger a **50% position trim or immediate exit** if a company reports a quarterly PAT miss of $>15\%$ against consensus or debtor days spike by $>30$ days.
12. **Regime 2 Normalized Margin Bridge for Turnarounds & Suppressed Earnings Compounders**:
    - Solves the depressed base earnings distortion where trailing P/E appears artificially inflated (300x–500x) due to rapid store rollouts (e.g. Trent), plant commissioning (e.g. Kaynes), or quick-commerce dark store buildouts (e.g. Zomato).
    - Compute **Normalized Target PAT**:
      $$\text{Normalized FY+2 PAT} = \text{Target FY+2 Revenue} \times \text{Steady-State Benchmark NPM (5% to 8\%)}$$
    - If 2-Year Forward Normalized P/E $< 45\times$ and Revenue CAGR $\ge 30\%$, it qualifies as an approved Regime 2 compounder, eliminating Type II missed multibagger errors.
13. **Dynamic Cash Harvesting Protocol & Trailing Stop-Loss Engine (The Cash Earning Invariant)**:
    - **Tranche 1 Profit Take (50% Realized Cash)**: When the market price hits the **Bull Case Target Price** within 12–18 months, immediately sell **50% of the position** to convert paper gains into realized cash profits.
    - **Dynamic Trailing Stop-Loss**: Maintain an automated trailing stop-loss at:
      $$\text{Stop Price} = \max(\text{Entry Price} \times 0.85, \; \text{Peak Price} \times 0.82, \; \text{50-Week EMA})$$
      on a weekly closing basis to protect capital, eliminate round-tripping, and maintain portfolio Sharpe ratio $>2.0$.
14. **Contracted Infrastructure & Mega-Cap Duopoly Cash Invariant (The Bharti Airtel Invariant)**:
    - Solves the Type II missed multibagger error on mega-cap fortress franchises ($\text{Mcap} \ge ₹50,000\text{ Cr}$) with massive operating cash flow ($\text{CFO/PAT} \ge 2.5\times$ or $\text{EBITDA Margin} \ge 40\%$) where heavy front-loaded capex depreciation artificially inflates trailing accounting P/E.
    - **Calibrated Hurdles**:
      - Bull Case Upside hurdle is calibrated from $\ge 50\%$ down to **$\ge 40\%$** (or Expected Value CAGR $\ge 18\%$).
      - Valuation is verified on **EV/EBITDA ($< 15\times$)** or **Cash Forward P/E** ($\frac{\text{CMP}}{\text{Cash EPS}_{t+2}} < 30\times$, where $\text{Cash EPS} = \text{EPS} + \text{Depreciation per share}$).
      - Dynamic Probability Allocation defaults to **55% Base / 45% Bull** reflecting duopoly pricing power and zero credit fragility.
15. **Cyclical Commodity Margin Peak & Global Dumping Guard (The Chemical Trap Guard)**:
    - Prevents false-positive entries into intermediate chemical/commodity processors (e.g. Deepak Nitrite, Rossari Biotech) where trailing 3-year revenue CAGR appears high due to temporary cyclical margin spikes.
    - **Margin Normalization Stress-Test**: If a company operates in non-patented chemicals, metals, or commodity intermediates, and $\text{TTM OPM} > 1.25 \times \text{5-Year Median OPM}$, earnings must NOT be projected from peak EPS. Projections must be anchored to **Normalized Median OPM EPS**.
    - **Global Dumping / Gross Margin Contraction Gate**: If quarterly Gross Margin contracts by $>300\text{ bps}$ YoY for 2 consecutive quarters ($\Delta \text{GM} = \text{GM}_{Q_0} - \text{GM}_{Q_{-4}} < -300\text{ bps}$) due to Chinese dumping or inventory destocking, the stock is marked as **`CYCLICAL DE-STOCKING TRAP`** and disqualified from entry until gross margins expand sequentially for 2 quarters.



