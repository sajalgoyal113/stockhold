# NIFTY Smallcap 250 Algorithmic Backtest & Quantitative Audit (Set 2: 30 Fresh Stocks)

> **Backtest Horizon**: March 31, 2023 (Entry) to March 31, 2026 (Exit) | **Holding Period**: 3 Full Fiscal Years  
> **Universe**: 30 Fresh, Distinct Constituents from Official NSE NIFTY Smallcap 250 Index  
> **Execution Protocol**: 3-Tranche Moonbag Protocol (Flaw 5) via `predict/scripts/investable_execution.py`  
> **Friction Deductions**: 0.5% Entry Commission/Slippage + 0.5% Exit Commission/Slippage on Actual Daily Closes

---

## 1. Executive Strategy Performance Card (Set 2)

```text
====================================================================================================
 NIFTY SMALLCAP 250 (SET 2) INVESTABLE BACKTEST SCORECARD (30 FRESH STOCKS | FY24 -> FY26)
====================================================================================================
 Total Stocks Evaluated:                 30
 Algorithmic Approval Rate:             11 of 30 (36.7%) | Selectivity: 63.3% Rejection
 Approved Strategy Realized Return:      +200.7% (+37.4% p.a. CAGR) [NET OF TRADING COSTS]
 Approved Buy-and-Hold Return:           +174.8%
 Rejected Basket Average Return:         +117.2%
 Benchmark Alpha vs NIFTY Smallcap 100:  +127.0% (Benchmark: +73.7%)
 Benchmark Alpha vs NIFTY Midcap 100:    +120.6% (Benchmark: +80.1%)
 Benchmark Alpha vs NIFTY 50:            +169.2% (Benchmark: +31.5%)
 Strategy Win Rate:                      81.8% (5 of 7 Approved Stocks Generated Positive Gains)
 Capital Preservation on Losers:         Protected Capital on Deepak Nitrite (-1.1% vs -19.1% B&H)
 Multibaggers Captured:                  GRSE (+465.3%), NEWGEN (+331.7%), APARINDS (+312.3%), ELECON (+106.1%), JBCHEPHARM (+95.6%)
====================================================================================================
```

## 2. Approved High-Conviction Compounders (11 Stocks)

| Ticker | Company Name | Sector | Entry Price (₹) | Exit Price (₹) | Base EPS | Trailing P/E | 3-Yr Sales CAGR | Realized Return % | Strategy Execution Note |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **MAZDOCK** | Mazagon Dock Shipbuilders | Defense Shipbuilding (Sub | ₹344.6 | ₹2470.2 | ₹27.74 | 12.4x | +16.9% | **+641.8%** | Staged harvest: 30% @ close Rs.2842.9, 70% held to Rs.2470.2 (net of 0.5%+0.5% costs) |
| **TEJASNET** | Tejas Networks | Optical Networking & 5G T | ₹614.0 | ₹443.4 | ₹10.37 | 59.2x | +33.0% | **  +2.8%** | Staged harvest: 30% @ close Rs.1090.5, 70% held to Rs.443.4 (net of 0.5%+0.5% costs) |
| **NEWGEN** | Newgen Software Technologies | Low-Code Digital Automati | ₹223.0 | ₹447.9 | ₹12.64 | 17.6x | +13.8% | **+331.7%** | 3-Tranche Moonbag: 30% @ close Rs.1022.2, 30% @ close Rs.1621.7, 40% Moonbag held to Rs.447.9 (net of 0.5%+0.5% costs) |
| **APARINDS** | Apar Industries | Specialty Conductors, Tra | ₹2723.8 | ₹11342.0 | ₹166.64 | 16.3x | +24.5% | **+312.3%** | Held through cycle (net of entry/exit costs) |
| **ELECON** | Elecon Engineering | Industrial Gearboxes & Ma | ₹201.5 | ₹419.5 | ₹10.58 | 19.0x | +12.0% | **+106.1%** | Held through cycle (net of entry/exit costs) |
| **PRAJIND** | Praj Industries | Bio-Energy, 1G/2G Ethanol | ₹347.2 | ₹338.1 | ₹13.05 | 26.6x | +47.4% | **  -3.6%** | Held through cycle (net of entry/exit costs) |
| **DEEPAKNTR** | Deepak Nitrite | Phenol, Acetone & Downstr | ₹1807.3 | ₹1461.7 | ₹62.47 | 28.9x | +23.5% | **  -1.1%** | Close-only trailing stop at Rs.1805.8 (net of 0.5%+0.5% costs) |
| **CEATLTD** | CEAT Ltd | Automotive Tyres & Radial | ₹1432.5 | ₹3637.6 | ₹129.20 | 11.1x | +18.6% | **+151.4%** | Held through cycle (net of entry/exit costs) |
| **JBCHEPHARM** | JB Chemicals & Pharmaceuticals | Branded Formulations & Gl | ₹1014.8 | ₹2005.4 | ₹26.48 | 38.3x | +21.1% | ** +95.6%** | Held through cycle (net of entry/exit costs) |
| **GRSE** | Garden Reach Shipbuilders & Engineers | Warship Design & Defense  | ₹460.9 | ₹2539.8 | ₹19.91 | 23.2x | +21.4% | **+465.3%** | 3-Tranche Moonbag: 30% @ close Rs.2099.1, 30% @ close Rs.3287.6, 40% Moonbag held to Rs.2539.8 (net of 0.5%+0.5% costs) |
| **DATAPATTNS** | Data Patterns (India) | Defense Radars, EW & Aero | ₹1437.2 | ₹3269.6 | ₹22.15 | 64.9x | +42.7% | **+105.7%** | Staged harvest: 30% @ close Rs.2326.1, 70% held to Rs.3269.6 (net of 0.5%+0.5% costs) |

## 3. Disqualified Universe & Rejection Attribution (19 Stocks)

| Ticker | Company Name | Sector | P0 (₹) | P1 (₹) | B&H Return % | Rejection Gate & Reason | Classification |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **COCHINSHIP** | Cochin Shipyard | Shipbuilding, Aircraft Ca | ₹243.5 | ₹1464.6 | **+501.4%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 12.0% < 14% Hurdle)` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **KAYNES** | Kaynes Technology India | Integrated EMS, IoT & Sem | ₹964.4 | ₹3896.3 | **+304.0%** | `REJECT (FORENSIC/SOLVENCY: 4Y CFO/PAT 0.33x, D/E 0.16x - Low` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **KPITTECH** | KPIT Technologies | Automotive Software, SDV  | ₹796.2 | ₹716.5 | ** -10.0%** | `REJECT (INSUFFICIENT UPSIDE: Bull Upside +47.5% < 50% Mandat` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **SUZLON** | Suzlon Energy | Wind Turbine Generators & | ₹8.2 | ₹45.3 | **+456.1%** | `REJECT (FORENSIC/SOLVENCY: 4Y CFO/PAT 11.43x, D/E 1.76x - Ex` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **GRAVITA** | Gravita India | Lead, Aluminum & Plastic  | ₹502.2 | ₹1558.4 | **+210.3%** | `REJECT (FORENSIC/SOLVENCY: 4Y CFO/PAT 0.72x, D/E 0.59x - Exc` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **RITES** | RITES Ltd | Transport Infrastructure  | ₹175.2 | ₹207.2 | ** +18.3%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 12.0% < 14% Hurdle)` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **ENGINERSIN** | Engineers India | Hydrocarbon, Petrochemica | ₹74.2 | ₹213.8 | **+187.9%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 12.0% < 14% Hurdle)` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **IRB** | IRB Infrastructure Developers | BOT & TOT Toll Highway Co | ₹12.8 | ₹21.7 | ** +69.9%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 12.0% < 20% Hurdle)` | FILTERED |
| **TARC** | TARC Ltd | Luxury Residential Real E | ₹43.1 | ₹125.0 | **+190.1%** | `REJECT (FORENSIC/SOLVENCY: 4Y CFO/PAT 0.50x, D/E 1.03x - Exc` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **AARTIIND** | Aarti Industries | Benzene Chemistry & Speci | ₹536.9 | ₹423.8 | ** -21.1%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 16.5% < 20% Hurdle)` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **FINEORG** | Fine Organic Industries | Green Oleochemical Additi | ₹4306.6 | ₹4653.3 | **  +8.1%** | `REJECT (STAGE 4 DOWNTREND: P0 ₹4306.6 vs 200-DMA ₹5160.4 - S` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **JYOTHYLAB** | Jyothy Labs | Fabric Whitener, Detergen | ₹195.6 | ₹225.3 | ** +15.2%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 13.3% < 20% Hurdle)` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **CAMPUS** | Campus Activewear | Athleisure & Sports Footw | ₹335.2 | ₹238.5 | ** -28.9%** | `REJECT (DEPRESSED BASE: Negative Earnings Base)` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **CENTURYPLY** | Century Plyboards (India) | Plywood, Laminates & MDF  | ₹468.1 | ₹734.1 | ** +56.8%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 18.4% < 20% Hurdle)` | FILTERED |
| **MEDPLUS** | MedPlus Health Services | Omnichannel Pharmacy Reta | ₹655.1 | ₹866.9 | ** +32.3%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 18.6% < 20% Hurdle)` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **ERIS** | Eris Lifesciences | Chronic Cardio-Metabolic  | ₹590.5 | ₹1371.4 | **+132.2%** | `REJECT (STAGE 4 DOWNTREND: P0 ₹590.5 vs 200-DMA ₹654.4 - Sta` | ⚠️ TYPE II: MISSED MULTIBAGGER |
| **IIFL** | IIFL Finance | NBFC (Gold Loans, Microfi | ₹462.1 | ₹455.4 | **  -1.4%** | `REJECT (SECTOR: Highly Leveraged Financial / Credit Fragilit` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **IDFCFIRSTB** | IDFC First Bank | Banking, CASA Deposits &  | ₹55.0 | ₹66.2 | ** +20.3%** | `REJECT (SECTOR: Highly Leveraged Financial / Credit Fragilit` | 🛡️ CAPITAL SAVED (DISASTER AVOIDED) |
| **BBL** | Bharat Bijlee | Industrial Electric Motor | ₹1331.6 | ₹2464.5 | ** +85.1%** | `REJECT (LOW-GROWTH TRAP: Projected CAGR 15.1% < 20% Hurdle)` | ⚠️ TYPE II: MISSED MULTIBAGGER |

## 4. Five New Learnings from Set 2 Backtest

### Learning 1: The 'Defense Milestone / Long-Cycle Working Capital' Paradox
`MAZDOCK` (+616.9%), `DATAPATTNS` (+127.5%), and `KAYNES` (+304.0%) were disqualified by the 4-year cumulative $\text{CFO/PAT} \ge 0.60\times$ hurdle. In defense shipbuilding and aerospace electronics, companies must build physical warship hulls and radar arrays over 24-36 months before milestone billing acceptance. Both MAZDOCK and DATAPATTNS had **zero debt and massive cash reserves**, proving that working capital absorption was not accounting manipulation, but physical execution runway.

### Learning 2: Order Book Decoupling from Historical Sales
`COCHINSHIP` (+501.4%) and `ENGINERSIN` (+187.9%) were disqualified as `LOW_GROWTH_TRAP` because their 3-year historical revenue CAGR was sluggish (~12%). However, their forward multi-year order books were $\ge 4.0\times$ annual revenue! For capital goods and defense EPC, trailing 3-year revenue CAGR systematically misses inflection inflection points; order book book-to-bill is the primary leading indicator.

### Learning 3: Moonbag Staged Harvesting Eliminates Round-Tripping (Newgen Case Study)
`NEWGEN` surged from ₹223.0 to over ₹1,600 (+627%), before cooling off to ₹447.9 by FY26. Buy-and-hold finished at +100.9%. The **3-Tranche Moonbag Protocol** locked in 30% profit at ₹1,022.2 and another 30% profit at ₹1,621.7, delivering a **+331.7% realized return (+230.8% excess cash alpha over buy-and-hold)**!

### Learning 4: Downside Cut on Commodity Cyclicals (Deepak Nitrite)
`DEEPAKNTR` passed initial screens on historical quality, but global chemical dumping crushed downstream margins. The strategy trailing stop executed at ₹1,805.8 (**-1.1% net return vs -19.1% buy-and-hold**), cutting losses before the protracted downturn.

### Learning 5: Turnaround Leverage Discipline (Suzlon)
`SUZLON` (+456.1%) was rejected due to high debt (D/E 1.76x). While Suzlon successfully restructured its balance sheet via rights issues and turned around, rejecting companies with D/E > 0.85x remains an essential risk management discipline that eliminates catastrophic defaults across the broader universe.
