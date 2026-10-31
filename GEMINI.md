# Equity Research Directives (Indian Equities)

> **Architectural Status (Oct 31, 2026 Evolution):**
> Modules **1, 3, 4, 5, 6, 8, and 9** are implemented and active in `predict/scripts/` and `stockhold/engine/`.
> **Module 2** (SGR ceiling, size decay, debt/working capital drag haircuts) is **skipped** per user directive.
> **Module 7 Solution (Approach A - Active)**: Early-profitability hyper-growth platform compounders (e.g., Eternal/Zomato) with thin trailing margins ($<3\%$) and high P/E ($>100\times$) are admitted for forward valuation via the **Cash-Flow Validated Operating Leverage Bridge** when verified cash generation ($\text{CFO} > 0$), scale ($\text{Sales} \ge ₹1,000\text{ Cr}$), top-line velocity ($\text{Sales}_{3Y} \ge 25\%$), clean balance sheet ($\text{Debt/Mcap} < 0.15$), and concall guidance are on file. Unverified, unguided, or cash-burning low-margin businesses fail closed with `NO VALUATION`.

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
│   │   ├── guidance_fetcher.py   # Concall transcript guidance extractor & reliability
│   │   └── ai_analyst.py         # Google Gemini AI synthesis & 7 Powers audit
│   ├── run_app.sh                # Streamlit launcher script
│   ├── requirements.txt          # Web app dependencies
│   └── README.md                 # StockHold application documentation
│
├── predict/                       # Quantitative Analysis, Modeling & Research Reports (MASTER SOURCE OF TRUTH)
│   ├── scripts/                  # Deterministic valuation & audit engines
│   │   ├── forward_growth_pe.py  # Master forward growth & dynamic P/E compounding engine
│   │   ├── guidance_fetcher.py   # Concall transcript guidance extractor & delivery scorer
│   │   ├── forensic_audit.py     # 4-year cumulative cash flow & Dalal Street red-flag audit
│   │   ├── reverse_dcf.py        # Implied 10-year FCF CAGR root-finder & sensitivity
│   │   ├── evaluate_portfolio.py # Batch portfolio & watchlist valuation analyzer
│   │   └── generate_html_report.py # Institutional interactive HTML report & portal generator
│   ├── data/                     # Data stores, guidance registries & point-in-time calibrations
│   │   └── guidance_registry.json # Machine-verified concall guidance quotes & delivery records
│   ├── references/               # Valuation models, templates, protocols & checklists
│   │   ├── analysis_protocol.md  # 5-step institutional stock analysis protocol
│   │   ├── report_template.md    # Institutional equity research report template
│   │   ├── forensic_checklist.md # 10-point forensic accounting checklist
│   │   └── valuation_models.md   # Hamilton Helmer 7 Powers & valuation frameworks
│   ├── reports/                  # Generated institutional research reports & portal index
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
   - All analytical scripts (`forward_growth_pe.py`, `guidance_fetcher.py`, `forensic_audit.py`, `reverse_dcf.py`, `evaluate_portfolio.py`, `generate_html_report.py`) and reference documentation are consolidated directly inside `predict/` so that all files are visible, editable, and version-controlled.
   - **Do NOT store stock analysis facts, learned preferences, or corrections in the auto-memory system.** All new stock-related insights, model updates, company notes, and portfolio evaluations must be recorded directly in `predict/` (for models/reports) or in `GEMINI.md` (for behavioral directives and rules).

4. **Python Runtime Environment**:
   - The primary execution environment is `/Users/sajal.goyal@zomato.com/Documents/Git/venv` (Python 3.13) or local `stockhold/venv`.

5. **Deterministic Math Invariant**:
   - Financial ratios, exit multiples, compounded EPS, and implied growth rates must ALWAYS be calculated deterministically via Python engines (`predict/scripts/`). Never hallucinate numerical projections.

6. **Zero Manual Quote Entry & Dual-Source Live Quote Verification**:
   - Never manually pass or hardcode stock prices (CMP), Market Cap, or TTM EPS from memory or unverified notes.
   - **Mandatory Dual-Source Live Verification**: Before running any valuation engine (`forward_growth_pe.py`, `reverse_dcf.py`) or generating equity research reports, the agent MUST explicitly cross-verify the stock's latest closing/current market price (CMP), Market Cap, and 52-week range using live market query tools (`search_web`).
   - **Strict Cache Provenance & Prohibition of Silent Fallbacks**: Offline database snapshots must NEVER be silently labeled or treated as live data. If live web scraping is blocked or throttled, prominent warnings must be emitted.
   - **Independent Fundamental EPS Anchoring**: Trailing TTM EPS is an audited fundamental accounting metric ($\sum \text{PAT}_{\text{last 4 quarters}} / \text{Shares}$). When CMP changes, TTM EPS remains anchored while Trailing P/E recalibrates dynamically ($\text{P/E} = \text{CMP} / \text{TTM EPS}$).
   - **Price Drift Threshold**: If any passed or cached CMP deviates by $>2\%$ from the live trading price, the engine flags a prominent `[PRICE DRIFT WARNING]` and synchronizes to the verified live price.

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

8. **Management Guidance Before Any Conclusion or Target Price (Module 3)**:
   - Before stating a verdict or target price for a stock, check its latest concall guidance (revenue growth, margins, capex, order book) and its delivery track record.
   - If `guidance_fetcher` returns nothing current (`guidance_status` $\ne$ `REVENUE`), read the latest transcript or investor presentation, and register verified guidance (with source + as-of date) in `predict/data/guidance_registry.json` before concluding, or state explicitly that the conclusion is provisional because no guidance was found.
   - Report guidance next to the model's growth anchor and bear/bull growth, and explain any gap.

9. **Mandatory Default Unbiased Screening (Zero Portfolio Anchoring)**:
   - **Default Operating Invariant**: Unless the user explicitly asks about their existing portfolio or names specific tickers, the agent MUST ALWAYS by default run an unbiased, broad-universe market screen across Large, Mid, Small, and Micro-caps using `predict/scripts/screen_universe.py`.
   - The agent is STRICTLY FORBIDDEN from defaulting to or prioritizing companies from existing portfolio files.

10. **Mandatory Default HTML Research Report Deliverable (Zero Standalone Markdown)**:
    - **Default Deliverable Invariant**: When analysing any stock, company, sector theme, or portfolio, the agent must ALWAYS by default generate and deliver an interactive, institutional-grade `.html` report in `predict/reports/` using `predict/scripts/generate_html_report.py` instead of delivering a standalone `.md` markdown file.
    - Automatically re-index the Research Coverage Portal (`predict/reports/index.html`). Standalone markdown files are never the end deliverable.

11. **Mandatory 1-2 Line Investment Action Commentary (Why Buy or Avoid)**:
    - Every generated equity analysis report and Research Coverage Portal card MUST prominently display a sharp, high-contrast 1-2 line commentary explaining why we are recommending to BUY / ACCUMULATE or AVOID / REJECT the stock (distilling core operational catalysts, structural moat, or disqualifying red flags/valuation risks).
    - In HTML reports, render this commentary in a dedicated callout chip directly within the top Hero Banner alongside the Conviction Verdict badge for instant scanning.

---

## 3. Core Valuation Invariants (as implemented in `predict/scripts/forward_growth_pe.py`)

Every rule in this section is enforced in code:

1. **Trailing EPS Base**:
   - Rolling TTM EPS = sum of the last 4 reported quarterly EPS (fallback: TTM PAT / shares).
   - One-off exceptional items are not stripped automatically; check exceptional items manually before trusting a TTM spike.

2. **Fixed 2-Year Horizon (No H1/H2 Calendar Cliff - Module 1)**:
   - The valuation target is the price **2.0 years after the as-of date** (`HORIZON_YEARS = 2.0`).
   - EPS is compounded from the **end of the TTM window** (last reported quarter, else the last quarter-end at least 45 days before the as-of date) to the target date, so the TTM's head start is not compounded twice.
   - Annualized CAGR always uses $T = 2.0$: $\text{CAGR} = (\text{Target}/\text{CMP})^{1/2} - 1$.
   - The exit P/E is applied as a trailing multiple on the TTM EPS at the target date.

3. **Growth Anchor (Central Baseline Input)**:
   - **Growth Anchor** (`base_cagr`): Central EPS CAGR estimate (an input, **not a scenario** and never a target) derived from historical sales/PAT velocity and concall guidance.
   - **Bull Kicker** = $\min(12, \max(4, 0.12 \times \text{PAT}_{3Y}))$ points. Weak or falling profits get the smallest kicker, never a larger one.
   - **Bull Growth** = anchor + kicker (or concall guidance). **Bear Growth** = 25% of the anchor (or anchor $- 5$ pts if anchor $\le 0$).
   - *Note on Module 2*: Sustainable Growth Rate (SGR) ceiling, size decay, and 15% debt/WC drag haircuts are configurable via `--enable-module-2` (currently disabled pending user discussion).

4. **Unknown $\ne$ Good (Fail Closed - Module 8)**:
   - Missing ROCE, CFO/PAT, Altman Z'', or pledge data is flagged in `sparse_fields`. It is never replaced by a "healthy" default.
   - **Quality Tier** (PEG 1.60 / 1.85) requires known ROCE $\ge 25\%$, gross debt/Mcap $< 0.15$, and known CFO/PAT $\ge 0.80$. Otherwise PEG is 1.50 / 1.75, or 1.15 / 1.40 if fragile.
   - **Fragile** = gross debt/Mcap $> 0.40$, known CFO/PAT $< 0.40$, known ROCE $< 12\%$, known Altman $< 2.6$, or pledge $> 10\%$.
   - Missing Altman is neutral: no tier change either way.
   - Missing price history $\implies$ `TREND UNKNOWN`; missing quarterly data $\implies$ `EARS UNKNOWN`.

5. **Exit Multiples Grounded in Current P/E & Quality (Module 4)**:
   - Exit P/E = $\text{PEG} \times \text{end-of-period growth}$ (where end growth = $80\%$ of horizon growth, capped at $25\%$).
   - **No free re-rating floors.** Absolute floors are 8x anchor and 10x bull. Caps are 40x / 55x when current P/E $< 22$, else 60x / 85x.
   - **Re-rating vs today's P/E is strictly clamped**:
     | Quality Category | Anchor Exit P/E $\le$ | Bull Exit P/E $\le$ |
     | :--- | :---: | :---: |
     | **Known Quality** ($\text{ROCE} \ge 18\%$ and $\text{CFO/PAT} \ge 0.80$, not fragile) | $1.75\times$ current | $2.25\times$ current |
     | **Normal** | $1.25\times$ current | $1.60\times$ current |
     | **Fragile** | $0.85\times$ current | $1.05\times$ current |
   - The market's current multiple is empirical evidence; fragile companies are forced to de-rate.

6. **Disciplined Bear / Bull Scenario Architecture (Module 6)**:
   - **Two Scenarios**: Bear Case (growth stall + multiple de-rating) and Bull Case (execution of guidance + operating leverage).
   - **Bear Probability**: Starts at implied weight: $(\text{bull} - \text{anchor}) / (\text{bull} - \text{bear})$.
     - Adjusted by risk factors (+10 if fragile, +5 if CFO/PAT $< 0.60$, +5 if debtor days $> 120$, etc.), clamped to 20%–60%. Bull probability = $100 - \text{bear}$.
   - Expected Target Price = $\text{Bull Prob} \times \text{Bull Target} + \text{Bear Prob} \times \text{Bear Target}$.

7. **Strict Verdict Waterfall in Python (Module 5)**:
   1. Loss-making / negative TTM EPS $\implies$ `DISQUALIFIED / NO VALUATION` (targets set to CMP, 0% return; no fabricated downside).
      - Trailing P/E $> 100\times$ on thin ($<3\%$) margins without steady-state margin evidence $\implies$ `NO VALUATION` (a P/E target on such EPS is meaningless). *Exception (Approach A)*: Cash-flow-validated hyper-growth platform compounders ($\text{CFO} > 0$, $\text{Sales} \ge ₹1,000\text{ Cr}$, $\text{Sales}_{3Y} \ge 25\%$, $\text{Debt/Mcap} < 0.15$) with concall guidance are valued via the **Operating Leverage & Margin Expansion Bridge** using concall-guided steady-state NPM and forward revenue compounding.
   2. Banks / NBFCs / Insurers $\implies$ `NOT APPLICABLE / NO VALUATION`.
   3. Missing growth data $\implies$ `INSUFFICIENT DATA / NO VALUATION`.
   4. Growth Filter: **Probability-weighted EPS growth $\ge 20\%$** (14% for known-quality non-fragile stocks at P/E $\le 18\times$).
   5. 2-Year Forward P/E on expected EPS $\le 80\times$.
   6. Bull 2-Year upside $\ge 50\%$.
   7. Expected CAGR $\ge \text{HURDLE\_RATE}$ (12% p.a.).
   8. Classification: `STRONG BUY` (Bear loss $\le 30\%$) vs `QUALIFIED BUY` (size for drawdown).
   9. **Momentum Gates**:
      - PAT down YoY in each of last 2 quarters $\implies$ `WATCHLIST / EARNINGS CONTRACTION - WAIT FOR PAT GROWTH`.
      - Sales growth below 12% in each of last 2 quarters $\implies$ `WATCHLIST / GROWTH KILL SWITCH ACTIVE`.
   10. **Technical Trend Gate**:
       - Any BUY with CMP below 200-DMA $\implies$ `WATCHLIST / STAGE 4 - WAIT FOR TREND`.

8. **Forensics & Reverse DCF Decision Overrides (Module 8 & `decision.py`)**:
   - Altman Z'' is computed strictly from reported accounting items (Other Assets − Other Liabilities, Reserves, PBT + Interest). Missing item $\implies$ UNAVAILABLE.
   - `BUY` $\implies$ `AVOID` if 4Y CFO/PAT $< 0.50$, Debt/Equity $> 1.0$, or Altman Z'' $< 1.10$.
   - Reverse DCF: If implied 10Y FCF CAGR exceeds Bull EPS CAGR, `BUY` is downgraded to `ACCUMULATE ON DIPS`.

---

## 4. Qualitative Research Checklist (Analyst Judgment; Not Hardcoded)

Include these in research reports:
1. **Client concentration**: Top 5 / Top 10 revenue share and single-client exposure.
2. **Order book visibility**: Book-to-bill ratio, program pipeline, and % forward revenue covered.
3. **Management commentary on anomalies**: Concall explanations on debtor days, working capital, or margin compressions.
4. **Guidance vs model bridge**: Concall guidance next to model growth anchor and bear/bull assumptions.
5. **Contract directionality**: Verify whether a contract announcement is revenue or an outbound take-or-pay liability.
6. **Empirical growth bridge**: 3Y revenue CAGR, latest YoY velocity, and segment mix dynamics.

---

## 5. Validation Status & Known Limits

- **The model has not been shown to beat the index.** On point-in-time backtests, no simple threshold combination made approved names outperform rejected ones.
- **Backtest Limits**: Historical universes had survivorship bias, data from Screener represents today's restated numbers, and stop-losses were originally fitted.
- **Verdicts are research aids, not personalized financial advice.**
