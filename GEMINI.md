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
│   │   ├── evaluate_portfolio.py # Batch portfolio & watchlist valuation analyzer
│   │   └── generate_html_report.py # Institutional interactive HTML report & portal generator
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
   - All analytical scripts (`forward_growth_pe.py`, `forensic_audit.py`, `reverse_dcf.py`, `evaluate_portfolio.py`, `generate_html_report.py`) and reference documentation (`report_template.md`, `forensic_checklist.md`, `valuation_models.md`) are consolidated directly inside `predict/` so that all files are visible, editable, and version-controlled.
   - **Do NOT store stock analysis facts, learned preferences, or corrections in the auto-memory system.** All new stock-related insights, model updates, company notes, and portfolio evaluations must be recorded directly in `predict/` (for models/reports) or in `GEMINI.md` (for behavioral directives and rules).

4. **Python Runtime Environment**:
   - The primary execution environment is `/Users/sajal.goyal@zomato.com/Documents/Git/venv` (Python 3.13) or local `stockhold/venv`.

5. **Deterministic Math Invariant**:
   - Financial ratios, exit multiples, compounded EPS, and implied growth rates must ALWAYS be calculated deterministically via Python engines (`predict/scripts/`). Never hallucinate numerical projections.

6. **Zero Manual Quote Entry & Dual-Source Live Quote Verification**:
   - Never manually pass or hardcode stock prices (CMP), Market Cap, or TTM EPS from memory or unverified notes.
   - **Mandatory Dual-Source Live Verification**: Before running any valuation engine (`forward_growth_pe.py`, `reverse_dcf.py`) or generating equity research reports, the agent MUST explicitly cross-verify the stock's latest closing/current market price (CMP), Market Cap, and 52-week range using live market query tools (`search_web`).
   - **Strict Cache Provenance & Prohibition of Silent Fallbacks**: Offline database snapshots (`portfolio_fundamentals.json`) must NEVER be silently labeled or treated as live data. If live web scraping is blocked, throttled, or encounters connection timeouts, `data_fetcher.py` and `forward_growth_pe.py` must emit prominent `⚠️ [STALE CACHE WARNING]` alerts, and the verified live market quote must be injected explicitly via `--cmp <verified_cmp> --mcap <verified_mcap>`.
   - **Independent Fundamental EPS Anchoring (Zero P/E-Driven EPS Distortion)**: Trailing TTM EPS is an audited fundamental accounting metric ($\sum \text{PAT}_{\text{last 4 quarters}} / \text{Shares}$). When CMP changes, TTM EPS must remain anchored to audited fundamentals while Trailing P/E recalibrates dynamically ($\text{P/E} = \text{CMP} / \text{TTM EPS}$). Calculation engines must NEVER arbitrarily scale down EPS when a stock price falls.
   - **Price Drift Threshold**: If any passed or cached CMP deviates by $>2\%$ from the live trading price, the engine must flag a prominent `[PRICE DRIFT WARNING]` and synchronize to the verified live price.

7. **Streamlit Cloud Deployment Invariant & Root Structure Protection**:
   - The root directory `Finance/` MUST ALWAYS contain STRICTLY AND ONLY the documented cloud deployment entrypoints and primary workspaces:
     ```text
     Finance/
     ├── app.py                         # Streamlit Community Cloud root entrypoint (delegates to stockhold/app.py)
     ├── requirements.txt               # Streamlit Community Cloud root dependencies
     ├── run_app.sh                     # Root launcher delegating to stockhold/run_app.sh
     ├── README.md                      # Repository documentation & guide
     ├── GEMINI.md                      # Behavioral rules, facts & repo source of truth
     ├── predict/                       # Quantitative Analysis & Research Reports (MASTER SOURCE OF TRUTH)
     └── stockhold/                     # Interactive Web Application & Visual Dashboard
     ```
   - **Root Deployment Invariant**: The files `app.py`, `requirements.txt`, `run_app.sh`, and `README.md` in the root repository are mandatory deployment entrypoints for **Streamlit Community Cloud (`https://stockhold.streamlit.app/`)**. They must NEVER be deleted.
   - All underlying Streamlit application code, Google Stitch styling, and web components reside in `stockhold/`. Root `app.py` delegates directly to `stockhold/app.py`.
   - Zero root pollution: No unversioned scratch files, temporary dumps, or extraneous pass-through files outside the documented set above are permitted in `Finance/`.

8. **Mandatory Default Unbiased Screening (Zero Portfolio Anchoring)**:
   - **Default Operating Invariant**: Unless the user explicitly asks about their existing portfolio or names specific tickers, the agent MUST ALWAYS by default run an unbiased, broad-universe market screen across Large, Mid, Small, and Micro-caps using `predict/scripts/screen_universe.py`.
   - The agent is STRICTLY FORBIDDEN from defaulting to or prioritizing companies from existing portfolio files (`portfolio_research_report.md` or prior reports in `predict/reports/`).

9. **Mandatory Default HTML Research Report Deliverable (Zero Standalone Markdown)**:
   - **Default Deliverable Invariant**: When analysing any stock, company, sector theme, or portfolio, the agent must ALWAYS by default generate and deliver an interactive, institutional-grade `.html` report in `predict/reports/` using `predict/scripts/generate_html_report.py` instead of delivering a standalone `.md` markdown file.
   - The agent must automatically compile the research analysis into HTML, link the generated `.html` file prominently in the final response, and automatically re-index the Research Coverage Portal (`predict/reports/index.html`). Standalone markdown files are never the end deliverable.

10. **Mandatory 1-2 Line Investment Action Commentary (Why Buy or Avoid)**:
   - **Commentary Invariant**: Every generated equity analysis report and Research Coverage Portal card MUST prominently display a sharp, high-contrast 1-2 line commentary explaining why we are recommending to BUY / ACCUMULATE or AVOID / REJECT the stock (distilling core operational catalysts, structural moat, or disqualifying red flags/valuation risks).
   - In HTML reports, this commentary must be rendered in a dedicated callout chip directly within the top Hero Banner alongside the Conviction Verdict badge for instant scanning.

---

## 3. Core Valuation Invariants

1. **Trailing EPS Base**: Never use stale annual report numbers when fresh quarterly results exist; compute Rolling TTM EPS from the last 4 reported quarters:
   $$\text{TTM PAT} = \sum_{i=1}^{4} \text{PAT}_{\text{last 4 quarters}}, \quad \text{TTM EPS} = \frac{\text{TTM PAT}}{\text{Shares Outstanding}}$$
2. **Growth & Valuation Hurdle**: Target companies in sunrise sectors with $\ge 20\%$ guided CAGR where **2-Year Forward P/E $\le 80$** and a mandated minimum **$\ge 50\%$ upside from current market price within 2 years in the Bull Case scenario**. Avoid banks/NBFCs (high leverage fragility) and sunset fossil fuels.
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
   - **Horizon-Aware Annualized CAGR Invariant**: When computing annualized CAGR over the evaluation horizon, the exponent MUST strictly match the forward compounding years ($T = \text{comp\_years\_yr2}$):
     $$\text{CAGR} = \left(\frac{\text{Target Price}}{\text{CMP}}\right)^{1/T} - 1$$
     where $T = 2$ in H1 and $T = 3$ in H2. Hardcoding `** 0.5` is strictly prohibited.
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
16. **Unbiased Thematic Discovery & Zero Portfolio Anchoring Invariant**:
    - **Zero Portfolio Retrospective Bias**: When analyzing an open-ended theme, sector, or emerging technology (e.g., self-driving AI, green hydrogen, robotics, defense electronics), the agent is STRICTLY PROHIBITED from defaulting to or prioritizing tickers from the existing 25-stock portfolio (`portfolio_research_report.md` or prior reports).
    - **Mandatory Broad-Universe Screening**: The agent must conduct a fresh, unbiased market-wide discovery process evaluating at least 8 to 12 distinct companies spanning Large, Mid, Small, and Micro-caps using `predict/scripts/screen_universe.py`.
    - **Dual-Tier Archetype Classification**:
      - **Tier 1 (Established Quality Compounders)**: Proven profitability, $\text{ROCE} \ge 18\%$, $\text{CFO/PAT} \ge 0.80\text{x}$, and $\text{3-Year Growth} \ge 20\%$.
      - **Tier 2 (Emerging Pure-Play Innovators / R&D Stage)**: Early-stage pure-plays with heavy R&D investment ($>5\%$ of sales) or recent commercialization where trailing accounting ROCE is temporarily suppressed by upfront capex, but thematic exposure is 100%.
    - **Geographic Reality Disclosure**: If the technology has limited listed pure-play representation on Indian exchanges (e.g., autonomous driving neural networks, advanced EUV semiconductors, foundation AI models), the analysis MUST explicitly disclose the domestic market limitation upfront and present the global technology benchmarks (US/Global leaders) alongside Indian Tier-2 enablers.
17. **Single-Order Revenue Cliff & Order Book Sustainability Guard (The Single-Order Cliff Guard)**:
    - In order-driven, EPC, capital goods, defense, EMS, or project-based businesses, always audit whether trailing or forward growth is predominantly reliant on a single large, non-recurring contract.
    - Evaluate the execution cliff risk: Will company revenue and margins drop precipitously once that anchor order completes?
    - Mandatory audits: Book-to-Bill ratio ($\ge 1.0\text{--}1.2\times$), client/program diversification across the order backlog, recurring vs one-off milestone billing mix, and new contract intake run-rate. If forward numbers depend on a single non-repeat contract with no visible replacement pipeline, tag as `SINGLE-ORDER CLIFF RISK` and haircut growth or reject.
18. **Management Guidance vs Proposed Research Projections Bridge (The Guidance Transparency Invariant)**:
    - Whenever official management guidance is available (from earnings calls, concall transcripts, investor presentations, or annual filings), research reports and models must ALWAYS explicitly present a side-by-side comparison bridge displaying:
      1. **What Management is Targeting**: Guided Revenue CAGR, PAT/EBITDA margins, capex budget, order inflow targets, and target horizon.
      2. **What We are Proposing**: Our research model's Base Case and Bull Case projections.
      3. **Variance & Operational Rationale**: Detailed fundamental reasoning explaining any divergence (e.g. conservative haircut for historical delivery delays, regulatory discounts, or operating leverage upside exceeding management's base guidance).
19. **Low-P/E Value Trap & Balance Sheet Drag Guard (The Anti-Value Trap Invariant)**:
    - Solves the mathematical distortion where low-P/E stocks ($< 22\times$) with slow top-line growth and high debt were erroneously awarded massive price targets due to unhedged multiple expansion and depressed-base PAT spikes.
    - **Trough-Base PAT Rebound Guard**: For standard non-platform companies, sustainable earnings growth is bounded by organic revenue velocity ($\le \text{Sales 3Y} \times 1.25$). If 3-year PAT growth significantly exceeds sales growth while 5-year profit growth is low ($< 15\%$), it is flagged as a `Trough-Base Rebound Artifact` and anchored to sales velocity.
    - **Debt & Working Capital Drag Haircut**: Apply an automatic 10% to 35% growth penalty to projected CAGR if $\text{Net Debt}/\text{Mcap} > 0.35$, $\text{CFO/PAT} < 0.60$, or $\text{Debtor Days} > 100$, reflecting debt service eating operating profits and working capital lockup.
    - **Quality-Anchored Exit Multiples (Zero Low-P/E Free Rides)**: Low starting P/E stocks ($< 22\times$) with fragile balance sheets ($\text{D/Mcap} > 0.35$, $\text{ROCE} < 18\%$, or $\text{CFO/PAT} < 0.60$) must NEVER receive multiple expansion. Base Case exit multiple is derated down to $\min(\text{Current P/E} \times 0.85, 6\text{x}\text{--}9\text{x})$, and Bull Case is capped near current P/E ($\le \text{Current P/E} \times 1.05$).
    - **Strict Disqualification Waterfall**: If projected Base or Bull CAGR $< 20\%$ or Bull Upside $< 50\%$, the stock MUST be immediately stamped `REJECT / LOW-GROWTH VALUE TRAP`. Multiple expansion cannot be used to artificially force hurdle compliance.
20. **Algorithmic Calibration Invariant & Zero Unanchored Overrides (The Deterministic Repeatability Invariant)**:
    - Eliminates model drift and contradictory verdicts when re-analyzing stocks across sessions.
    - **Mandatory Default to First-Principles Calibration**: All valuation runs in `predict/scripts/forward_growth_pe.py` MUST default strictly to endogenous first-principles calibration (`calibrate_first_principles()`), which calculates sustainable growth (SGR) and dynamic exit P/Es directly from audited financial statements (`data_fetcher.py`).
    - **Prohibition of Subjective / Manual Overrides**: Ad-hoc manual injection of arbitrary growth rates (`--growth`, `--bull-growth`) or arbitrary exit multiples (`--base-pe`, `--bull-pe`) without verified concall transcripts and a formal Guidance Reconciliation Bridge (Rule 18) is STRICTLY PROHIBITED.
    - **The Multiple Compression Invariant (Zero Multiple Inflation)**: For stocks trading at hyper-elevated multiples ($> 80\text{x}\text{--}100\text{x}$ P/E), multiple compression toward sustainable PEG bounds ($1.4\text{x}\text{--}1.7\text{x}$ on end growth) is mandatory. The agent is strictly forbidden from arbitrarily holding exit multiples at 50x–60x simply to manufacture paper upside.
21. **Primary Regulatory Due Diligence & Contract Asymmetry Invariant (The Take-or-Pay Liability Guard)**:
    - **Mandatory Directionality Verification**: When evaluating major commercial contracts, joint ventures, or capacity reservations, the agent must verify primary regulatory filings (SEC 8-K/10-K, BSE/NSE exchange disclosures) to determine counterparty cash flow directionality: is the company receiving revenue, or committing to outbound fixed liabilities?
    - **Prohibition of Mislabeled Wholesale Commitments**: A wholesale purchase obligation, capacity reservation, or take-or-pay contract must NEVER be mislabeled as an order book win or revenue backlog.
    - **Existential Asymmetry Gate**: If a company enters an outbound take-or-pay liability where annual cash commitments exceed $>50\%$ of trailing annual turnover, the model must treat this as a high-risk operational fixed drain, stress-test underutilization risks, and flag a `TAKE-OR-PAY ASYMMETRY ALERT`.
    - **Regulatory Invalidation Audit**: The agent must audit whether assets deployed under overseas agreements comply with the regulatory mandates of the company's core client base (e.g. RBI, SEBI, CERT-In data localization rules barring overseas hosting of Indian financial workloads).
22. **Deterministic File Naming & Single-Source-of-Truth Idempotence**:
    - **Strict File Naming Standard**: Every equity research report and compiled HTML dashboard MUST follow a deterministic naming standard based strictly on the lower-case stock ticker:
      `predict/reports/<ticker_lower>_research_report.md`
      `predict/reports/<ticker_lower>_research_report.html`
    - **Prohibition of Variant or Orphan Names**: Creating naming variants (e.g. `esds_software`, `esds_software_solution`, `_new.html`, `_v2.html`) is strictly prohibited.
    - **Idempotent Overwrite Invariant**: Re-analyzing or updating a stock must always idempotently overwrite the existing report in-place, followed by an immediate portal re-index (`python3 predict/scripts/generate_html_report.py --all`) to eliminate conflicting duplicate versions.

23. **Centralized Management Guidance & Deterministic Parity Invariant (The Single Source of Truth Architecture)**:
    - Official management guidance, contracted order backlogs, and multi-year capex roadmaps must NEVER be passed as ad-hoc, manual CLI flags that vary between screens, single-stock runs, or batch evaluations.
    - **Single Source of Truth Store**: All vetted concall management guidance, contracted order backlogs, and dynamic exit multiple calibrations must reside centrally in `predict/data/guidance_registry.json`.
    - **Deterministic Engine Ingestion**: All analytical tools—including `forward_growth_pe.py`, `screen_universe.py`, `evaluate_portfolio.py`, and `stockhold/engine/valuation.py`—must automatically ingest `predict/data/guidance_registry.json`.
    - **Zero Mathematical Drift Mandate**: Standalone single-stock runs, thematic universe screens, batch portfolio evaluations, and the web application dashboard MUST ALWAYS produce 100% mathematically identical numbers (CMP, Mcap, TTM EPS, target price, exit P/E, and expected CAGR) down to the decimal point.
    - **Prohibition of Report Memoization**: Analytical scripts must never scrape or anchor to prior static markdown/HTML reports to maintain consistency. Consistency must be enforced deterministically at the quantitative calculation and guidance ingestion engine level.

24. **Zero-Debt Long-Cycle Working Capital & Generalized Asymmetric Re-Rating Invariants**:
    - **Zero-Debt Long-Cycle Working Capital Invariant**: In capital goods, defense systems, aerospace, and heavy industrial manufacturing with 24–48 month build cycles, physical inventory and work-in-progress (WIP) absorb cash prior to sovereign milestone clearance. If the franchise is **virtually debt-free ($\text{Debt/Equity} \le 0.05\text{x}$ or Net Cash)** and cumulative 4-year operating cash flow is positive ($\sum \text{CFO} > 0$), there is zero risk of credit default or insolvency. The 4-year cumulative $\text{CFO/PAT}$ hurdle is calibrated to $\ge 0.30\times$. If $\text{Debt/Equity} > 0.05\text{x}$, the standard $\ge 0.60\times$ hurdle remains strictly non-negotiable.
    - **Generalized Asymmetric Re-Rating Invariant (GARP Spread)**: If a company enters at deep-value valuation ($\text{Current P/E} \le 18.0\times$ or $\text{Forward P/E} \le 18.0\times$), maintains safe serviceable leverage ($\text{D/E} \le 0.50\text{x}$ or $\text{D/E} \le 0.85\text{x}$ with $\text{CFO/PAT} \ge 1.50\times$), and exhibits proven capital efficiency ($\text{ROCE} \ge 20\%$ or $\text{CFO/PAT} \ge 1.50\times$ or $\text{D/E} \le 0.15\text{x}$), the forward growth hurdle is calibrated down from $20.0\%$ to $14.0\%$. Modest EPS growth of $14\%\text{--}19\%$ combined with multiple expansion from $10\text{--}16\times$ up to $22\text{--}28\times$ reliably delivers $>50\%\text{--}150\%$ returns with superior downside margin of safety.

25. **Quality-Anchored Exit Multiples, Anti-Fragility Safeguard & Methodology Integrity Watchdog**:
    - **Zero False-Fragility Penalties on Missing Fields**: Missing or sparse data for a secondary metric (such as Altman Z-Score) must NEVER automatically brand a company as "fragile". If a company demonstrates pristine balance sheet health—specifically $\text{ROCE} \ge 25\%$, $\text{Debt/Mcap} < 0.15\times$ (or Net Cash), and $\text{CFO/PAT} \ge 0.70\times$—it is demonstrably high-quality. Imposing a fragile-tier PEG penalty on such businesses constitutes a catastrophic Type II false-negative error. Missing balance sheet metrics default safely to neutral.
    - **Realistic Quality PEG Bounds in Indian Equities**: In the Indian market (where Nifty 50 trades at 1.6x–1.8x PEG), high-ROCE, net-cash sunrise sector leaders compounding at $\ge 20\%$ must be valued within verified quality PEG bounds: **Base PEG of $1.50\text{x}\text{--}1.60\text{x}$** (reflecting conservative terminal multiple normalization) and **Bull PEG of $1.75\text{x}\text{--}1.85\text{x}$** (reflecting sustained moat leadership). Exit multiples must never be artificially clamped to fractions of trailing P/E ($\le \text{Current P/E} \times 0.90$) for quality franchises, and justified re-rating floors (Base 15x–35x, Bull 20x–50x) must apply to mispriced low-starting-P/E compounders.
    - **Multi-Source Fundamental Enrichment Invariant**: When live scraping is throttled or yields sparse top-ratio fields, calculation engines (`forward_growth_pe.py`, `evaluate_portfolio.py`, `screen_universe.py`) must automatically enrich missing parameters from `predict/data/portfolio_fundamentals.json` to prevent synthetic fragility downgrades.
    - **Automated Methodology Integrity Watchdog**: Calculation engines (`forward_growth_pe.py`, `safety_guard.py`, `valuation.py`) must continuously run `verify_methodology_integrity()` prior to evaluating any company. If any parameter drift, unearned PEG compression ($<1.45\text{x}$ Base, $<1.70\text{x}$ Bull), or artificial exit P/E suppression is detected, the engine must immediately emit a high-priority `⚠️ [METHODOLOGY INTEGRITY ALERT]` and fail synthesis audits until restored.






