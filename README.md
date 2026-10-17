# ⚡ StockHold — Simplifying Stock Analysis for Investors

An institutional-grade equity research and deterministic scenario valuation platform for Indian Equities (NSE/BSE), styled with the Google Stitch design system and powered by Python, Streamlit, Plotly, and Google Gemini AI.

---

## 🌟 Key Features

1. **Top Executive Valuation Summary Card**:
   * Rolling TTM Base EPS foundation (calculated from last 4 reported quarters).
   * **Probability-Weighted Expected Target Price**, Total Expected Return (%), and 2-Year Annualized CAGR (%).
   * Dynamic Probability Allocation (Base % vs. Bull %) calibrated to execution risk and founder credibility.
   * Institutional Conviction Verdict (**STRONG BUY**, **QUALIFIED BUY**, **ACCUMULATE ON DIPS**, **REJECT**).

2. **2-Year Forward Valuation Scenario Fan (Plotly)**:
   * Interactive chart featuring 365-day historical stock price, 50-DMA, and 200-DMA.
   * Forward projection cones to Base Case and Bull Case target price corridors at the 2-year horizon ($FY_{t+2}$).

3. **Deterministic Quantitative Engines (Zero Arithmetic Hallucination)**:
   * **Forward Growth P/E Engine**: Compounding logic adhering to the H1 vs. H2 roll-forward calendar regime, dynamic exit P/E multiple derivation based on exit runway, and PEG calibration (1.6x Base / 1.85x Bull).
   * **Forensic Accounting Audit**: 4-Year cumulative CFO/PAT cash flow conversion, trade receivables vs. sales growth check, promoter pledging audit, and Emerging Markets **Altman Z''-Score**.
   * **Expectations Investing (Reverse DCF)**: Solves for the implied 10-year Free Cash Flow CAGR priced into Enterprise Value ($EV = \text{Mcap} + \text{Net Debt}$) along with a sensitivity heatmap across WACCs (10% to 13%) and terminal growth rates (4% to 6%).

4. **AI-Powered Strategic Synthesis (Google AI Studio)**:
   * **Hamilton Helmer's 7 Powers & Moat Audit** (Switching Costs, Process Power, Scale Economies, Anti-Disintermediation).
   * **Operational Pipeline & Order Book Visibility**.
   * **Forensic Anomalies & Management Commentary** (explaining DSO movements, milestone billing, and tax adjustments).
   * **3 Upside Catalysts & 3 Structural Kill-Switches**.

5. **Instant Report Export**:
   * One-click download of the complete institutional equity research report in Markdown (`.md`).

---

## 🚀 How to Run Locally

### 1. Quick Launch
Run the launcher script:
```bash
./run_app.sh
```
Or run directly with the virtual environment:
```bash
./venv/bin/streamlit run app.py
```

### 2. Access the Web App
Open your web browser and go to:
```text
http://localhost:8501
```

---

## 🌐 Deploy Free to the Public ($0 Cloud Hosting)

You can share this app with friends, investors, or online communities completely free:

1. **Push this folder to a GitHub Repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of DalalStreet Alpha stock valuation app"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/dalalstreet-alpha.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Community Cloud ($0)**:
   * Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
   * Click **"New App"**.
   * Select your repository: `<YOUR_USERNAME>/dalalstreet-alpha`.
   * Set Main file path: `app.py`.
   * Click **"Deploy"**!
   * Within 60 seconds, you get a live shareable URL: `https://your-app.streamlit.app`.

3. **Optional: Add your Google AI Studio Free API Key**:
   * In your Streamlit Cloud app settings, add `GEMINI_API_KEY` under Secrets, or paste your free API key into the sidebar directly in the browser.

---

## 📁 Project Architecture

```text
Finance/
├── app.py                     # Streamlit frontend & interactive dashboard
├── run_app.sh                 # One-click local launch script
├── requirements.txt           # Python dependencies
├── README.md                  # System documentation
└── engine/
    ├── __init__.py
    ├── data_fetcher.py        # Screener.in consolidated scraper & price history
    ├── valuation.py           # Deterministic forward PE compounding engine
    ├── forensics.py           # Cash flow hygiene & Altman Z''-score
    ├── reverse_dcf.py         # Michael Mauboussin reverse DCF engine
    └── ai_analyst.py          # Gemini Flash narrative & 7 Powers synthesis
```
