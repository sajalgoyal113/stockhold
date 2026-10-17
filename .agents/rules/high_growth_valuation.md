---
description: Valuation and PAT estimation rule for hyper-growth platform compounders
globs: "**/*"
---

# Valuation Protocol for High-Growth & Early-Profitability Platform Compounders

When evaluating high-growth Indian companies (NSE/BSE), the agent must classify the stock into one of two operational regimes before running forward P/E and PAT CAGR calculations:

## 1. Regime Identification
- **Regime 1: Mature / Steady-State Margin Compounders** (EMS, CDMO, Industrials, Auto Ancillary, Chemicals):
  - Operating margins are mature and stable ($\pm 50-100\text{ bps}$).
  - Use standard linear top-line growth adjusted for dilution: $\text{PAT CAGR} \approx g_{\text{rev}} - \text{dilution}$.
- **Regime 2: Early-Profitability / Platform Compounders** (Quick Commerce, Consumer Tech, SaaS, Hyperlocal Delivery):
  - Current Net Profit Margin is temporarily suppressed ($<1.5\%$) due to front-loaded store gestation (e.g. Blinkit dark stores), rider incentives, marketing, and Ind AS 116 lease depreciation.
  - **NEVER use additive top-line growth** (e.g. $55\% - 2\% + 5\% = 52\%$) because it fails to capture non-linear operating leverage.

## 2. Compounding Formulation for Regime 2
Operating leverage is multiplicative, not additive:
$$\text{PAT}_t = \text{Revenue}_t \times \text{Net Profit Margin}_t$$
$$\text{PAT}_{t+2} = \text{Revenue}_0 \times (1 + g_{\text{rev}})^2 \times \text{NPM}_{t+2}$$
$$\text{2-Year PAT CAGR} = \left( (1 + g_{\text{rev}})^2 \times \frac{\text{NPM}_{t+2}}{\text{NPM}_0} \right)^{\frac{1}{2}} - 1$$

## 3. Required Execution Command
When running `forward_growth_pe.py` for Regime 2 stocks:
```bash
# Option A (Margin Expansion):
python3 .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py <TICKER> \
  --cmp <CMP> --eps <TTM_EPS> --pe <TTM_PE> \
  --rev-cagr <REV_CAGR> --current-margin <CURRENT_NPM> --target-margin-yr2 <TARGET_NPM>

# Option B (Direct Consensus FY+2 EPS):
python3 .agents/skills/indian-stock-analysis/scripts/forward_growth_pe.py <TICKER> \
  --cmp <CMP> --eps <TTM_EPS> --target-eps-yr2 <FY2_CONSENSUS_EPS>
```

## 4. Forward PEG Evaluation
For Regime 2 compounders with triple-digit PAT growth ($>100\%$), evaluate the **Forward PEG Ratio** ($\frac{\text{2-Yr Forward P/E}}{\text{PAT CAGR}}$). If Forward PEG $< 1.0\times$, recognize that the market is pricing high-growth operating leverage at a reasonable valuation despite elevated headline P/E multiples.
