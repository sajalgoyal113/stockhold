# Institutional Valuation & Expectations Framework

This guide outlines the mathematical foundations and frameworks used in the Apex Stock Analysis Protocol.

---

## 1. Michael Mauboussin’s Expectations Investing & Reverse DCF

Traditional DCF attempts to predict cash flows 10 years out and discounts them back to calculate an intrinsic value. This is fraught with error because small tweaks in growth rates or terminal multiples drastically distort the output.

**Expectations Investing inverts the question:**
> *"Given the current Enterprise Value (EV) established by the market, what set of operating cash flow expectations (growth, margin, duration) must the company fulfill to justify this price at its cost of capital?"*

### Mathematical Formulation
$$\text{Enterprise Value (EV)} = \sum_{t=1}^{N} \frac{\text{FCF}_t}{(1 + \text{WACC})^t} + \frac{\text{FCF}_N \times (1 + g_{\text{term}})}{(\text{WACC} - g_{\text{term}}) \times (1 + \text{WACC})^N}$$
Where:
* $\text{FCF}_t = \text{FCF}_0 \times (1 + g_{\text{implied}})^t$
* $\text{WACC}$: Weighted Average Cost of Capital (typically $11.0\% - 12.5\%$ for Indian equities, reflecting India 10Y G-Sec $\approx 6.8\% - 7.2\%$ + Equity Risk Premium $\approx 4.5\% - 5.5\% \times \beta$).
* $g_{\text{term}}$: Terminal growth rate (capped at long-term Indian nominal GDP growth proxy, typically $4.5\% - 5.5\%$).

We solve for $g_{\text{implied}}$ via numerical root-finding (binary search).

### Feasibility Benchmarking
* If $g_{\text{implied}} > 30\%$, the market is pricing in exceptional, rare 10-year compounding. The probability of disappointment is elevated.
* If $g_{\text{implied}} < 8\%$, the market has deeply discounted the company's prospects, creating an asymmetric upside margin of safety if the core business remains intact.

---

## 2. Hamilton Helmer’s 7 Powers (Moat Durability)

A business can only earn persistent economic profits (ROIC > WACC) if it possesses at least one of the 7 structural powers:

1. **Scale Economies**: Per-unit cost decreases as production scale increases (e.g., manufacturing giants, delivery density).
2. **Network Effects**: Value of the service increases as new users join (e.g., platforms, payment switches, stock exchanges).
3. **Counter-Positioning**: A newcomer adopts an attractive new business model that incumbents cannot easily copy without cannibalizing their existing profit pools.
4. **Switching Costs**: The cost, operational friction, or risk for a customer to switch to an alternative is prohibitive (e.g., mission-critical enterprise software, core banking platforms).
5. **Branding**: An established, durable perception that elicits a higher willingness-to-pay from consumers in the absence of objective functional superiority.
6. **Cornered Resource**: Preferential access to a scarce asset, patent portfolio, mineral deposit, or extraordinary talent.
7. **Process Power**: Embedded company-wide organization and tacit know-how that enables lower costs or superior quality, impossible to copy via simple hiring or reverse-engineering.

---

## 3. Capital Allocation: ROIIC vs WACC Spread

Value creation is not determined by revenue growth; it is determined by the **spread between Return on Incremental Invested Capital (ROIIC) and WACC**:

$$\text{ROIIC} = \frac{\Delta \text{NOPAT}}{\Delta \text{Invested Capital}} = \frac{\text{NOPAT}_t - \text{NOPAT}_{t-n}}{\text{Invested Capital}_t - \text{Invested Capital}_{t-n}}$$

* **Invested Capital** = Net Fixed Assets + Net Working Capital - Cash & Equivalents.
* If $\text{ROIIC} > \text{WACC}$: The company reinvests profits at high rates. High growth accelerates compounding.
* If $\text{ROIIC} = \text{WACC}$: Growth is economically neutral; it neither creates nor destroys per-share wealth.
* If $\text{ROIIC} < \text{WACC}$: Growth destroys shareholder capital. The faster the company grows, the more equity value is destroyed.

---

## 4. Dynamic Exit Multiple & Asymmetric Scenario Architecture

Fixed or hardcoded exit multiples (e.g. arbitrarily picking 35x Base or 50x Bull) fail to capture differences in business reinvestment moats and terminal runways. The exit P/E multiple at the end of the evaluation period must be **dynamically derived from the expected ongoing growth rate at that horizon ($g_{\text{exit}}$)**:

$$\text{Exit P/E} = \text{Justified Forward PEG} \times (g_{\text{exit}} \times 100)$$

Where Justified Forward PEG reflects capital return quality, reinvestment moats, balance sheet strength, and India's structural macroeconomic dynamics (10-12% nominal GDP, domestic mutual fund SIP liquidity, and scarcity of clean debt-free compounders):
* **Indian Capital-Light / Tech & Consumer Compounders (Zero Debt, High Reinvestment)**:
  * **Base Case PEG**: $\approx \mathbf{1.5\times - 1.75\times}$ (Reflects baseline multiple for 15-18% growth $\implies \mathbf{24\times - 30\times\text{ P/E}}$ in Indian markets).
  * **Bull Case PEG**: $\approx \mathbf{1.8\times - 2.0\times}$ (Reflects scarcity premium for sustained 25%+ compounding $\implies \mathbf{45\times - 52\times\text{ P/E}}$).
* **Capital-Intensive / Moderate ROIC / Cyclicals (ROIC 12-18%)**: PEG $\approx 1.0\times - 1.25\times$.

### Two-State Evaluation Architecture:
1. **Base Case Scenario (Execution Friction / Delayed Targets)**:
   * **Thesis**: Certain operational milestones (new capacity ramp, enterprise customer signups, segment expansion) face delays or competitive headwinds. Growth is achieved but delayed by 1–2 years.
   * **End-Period Growth ($g_{\text{base, exit}}$)**: Settles at a more mature, moderate pace as initial hyper-growth decelerates.
   * **Exit Multiple**: Calibrated to this lower, sustainable ongoing growth rate ($g_{\text{base, exit}}$) at a moderate PEG ($\sim 1.0\times - 1.2\times$).
2. **Bull Case Scenario (Flawless Execution / Structural Outperformance)**:
   * **Thesis**: Management executes as planned or exceeds milestones; network density, operating leverage, and margin expansion kick in fully; market share is consolidated.
   * **End-Period Growth ($g_{\text{bull, exit}}$)**: Retains high momentum and extended secular runway at the horizon end.
   * **Exit Multiple**: Dynamically expands to reflect high continuing runway and scarcity value at a premium PEG ($\sim 1.3\times - 1.5\times$).

### Dynamic Probability Weighting (Founder & Execution Credibility Calibration):
The probability allocation between Base Case and Bull Case must NEVER be hardcoded to a fixed 60/40 ratio for all companies. It is dynamically calibrated according to:
1. **Founder / CEO Execution Credibility & Guidance History**: Does management consistently achieve or exceed ambitious forward targets (e.g. founder-led compounders like Deepinder Goyal at Eternal, Sunil Vachani at Dixon, Trent)?
2. **Moat Defensibility & Competitive Intensity**: Settled duopoly/monopoly vs high-burn multi-player price wars.
3. **Ecosystem & Regulatory Fragility**: Single-client dependency, raw material risk, or sovereign regulatory traps.

**Calibration Tiers**:
* **Tier 1: Elite Founder Execution / Proven Guidance Delivery** (e.g. Deepinder Goyal / Eternal, Dixon, Trent):
  * **Bull Case Weightage: 50% to 55%** | **Base Case Weightage: 45% to 50%**.
  * *Rationale*: Exceptional track record of turning loss-making bets into high-margin profit machines warrants equal or greater probability on Bull execution.
* **Tier 2: Mature Contracted Monopolies / Oligopolies** (e.g. HAL, BEL, CDMO leaders):
  * **Bull Case Weightage: 40% to 45%** | **Base Case Weightage: 55% to 60%**.
* **Tier 3: Early-Stage Multi-Player Price Wars with Unproven Margins**:
  * **Bull Case Weightage: 30% to 35%** | **Base Case Weightage: 65% to 70%**.
* **Tier 4: High Regulatory Vulnerability or History of Missed Timelines** (e.g. ixigo / IRCTC trap):
  * **Bull Case Weightage: 20% to 25%** | **Base Case Weightage: 75% to 80%**.

*Note: The Bear case is omitted from the forward target summary card, focusing the investment hurdle strictly on whether the Base Case provides acceptable compounding and the Bull Case delivers the mandated $\ge 50\%$ 2-year upside.*

---

## 5. Operating Leverage & Non-Linear PAT CAGR in Platform / High-Growth Stocks

### The Two Valuation Regimes
When projecting forward earnings (FY+1 and FY+2), companies fall into two distinct operating regimes:

1. **Regime 1: Mature / Steady-State Margin Compounders** (EMS, CDMO, Industrials, Consumer Staples):
   * Net Profit Margins (NPM) are mature and fluctuate within a narrow band ($\pm 50-100\text{ bps}$).
   * PAT CAGR closely tracks Top-line Revenue CAGR adjusted for share dilution.
   * *Formula*: $\text{PAT CAGR} \approx g_{\text{rev}} - \text{Dilution} + \Delta\text{Margin}$.

2. **Regime 2: Early-Profitability Platform / Hyper-Growth Compounders** (Quick Commerce, Consumer Tech, SaaS):
   * Current Net Profit Margin is artificially suppressed ($<1.0\%-1.5\%$) due to heavy store gestation, customer acquisition, or front-loaded lease depreciation under Ind AS 116.
   * As network density and store vintage mature, Net Profit Margin expands by **$3\times-5\times$** (e.g. $0.6\% \rightarrow 3.0\%$).
   * In this regime, **treating top-line growth as equal to PAT growth is a fatal modeling error**.

### The Non-Linear Margin Expansion Formulation
$$\text{PAT}_t = \text{Revenue}_t \times \text{Net Profit Margin (NPM)}_t$$

$$\text{PAT}_{t+2} = \text{Revenue}_0 \times (1 + g_{\text{rev}})^2 \times \text{NPM}_{t+2}$$

$$\text{Net 2-Year PAT CAGR} = \left( (1 + g_{\text{rev}})^2 \times \frac{\text{NPM}_{t+2}}{\text{NPM}_0} \right)^{\frac{1}{2}} - 1$$

### Example (Eternal / Quick Commerce):
* $\text{Revenue}_0 = ₹67,408\text{ Cr}$, $\text{NPM}_0 = 0.64\% \implies \text{PAT}_0 = ₹433\text{ Cr}$.
* Projected 2-Year Revenue CAGR = $32\%$ ($\text{Revenue}_{t+2} = ₹117,000\text{ Cr}$).
* Projected FY+2 Mature NPM = $3.00\% \implies \text{PAT}_{t+2} = ₹3,510\text{ Cr}$.
* **Effective 2-Year PAT CAGR**:
  $$\text{CAGR} = \sqrt{\frac{3,510}{433}} - 1 = \sqrt{8.11} - 1 = \mathbf{184.7\%\text{ p.a.}}$$
* **Impact on Forward Valuation**:
  * Naive 52% CAGR $\implies$ FY+2 EPS ₹1.05 $\implies$ Forward P/E **308.6x** (distorted).
  * True 185% Operating Leverage CAGR $\implies$ FY+2 EPS ₹3.63 $\implies$ Forward P/E **88.9x** (Forward PEG = 0.48x).

