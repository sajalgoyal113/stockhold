# ⚡ StockHold — Simplifying Stock Analysis for Investors

StockHold is the interactive equity research and deterministic scenario valuation platform for Indian Equities (NSE/BSE). It is designed with the Google Stitch ultra-premium visual language and powered by Python, Streamlit, Plotly, and Google Gemini AI.

---

## 📁 Directory Structure

```text
stockhold/
├── app.py                     # Streamlit frontend & interactive dashboard
├── run_app.sh                 # One-click launch script
├── requirements.txt           # Python dependencies
├── README.md                  # StockHold application documentation
└── engine/                    # Backend computational & analytical engine
    ├── __init__.py
    ├── data_fetcher.py        # Screener.in consolidated scraper & historical quotes
    ├── valuation.py           # Deterministic forward PE compounding engine
    ├── forensics.py           # Cash flow hygiene & Altman Z''-score
    ├── reverse_dcf.py         # Michael Mauboussin reverse DCF engine
    └── ai_analyst.py          # Gemini Flash narrative & 7 Powers synthesis
```

---

## 🚀 How to Launch StockHold Locally

### Option 1: One-Click Launcher
From the repository root or inside `stockhold/`:
```bash
./run_app.sh
```

### Option 2: Direct Streamlit Execution
Using your active virtual environment:
```bash
source /Users/sajal.goyal@zomato.com/Documents/Git/venv/bin/activate
cd stockhold
streamlit run app.py --server.port 8501
```

Open your browser at:
```text
http://localhost:8501
```

---

## 🌐 Deploy Free to the Public ($0 Cloud Hosting)

You can share this app with friends, investors, or online communities completely free via Streamlit Community Cloud:

1. **Push your repository to GitHub**:
   ```bash
   git add .
   git commit -m "Update StockHold app"
   git push origin main
   ```

2. **Deploy on Streamlit Community Cloud**:
   * Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
   * Click **"New App"**.
   * Select your repository and branch (`main`).
   * Set Main file path: `stockhold/app.py`.
   * Click **"Deploy"**!
   * Within 60 seconds, you get a live shareable URL: `https://<YOUR_APP>.streamlit.app`.

3. **Google AI Studio API Key Configuration**:
   * In your Streamlit Cloud app settings, add `GEMINI_API_KEY` under **Secrets**, or paste your API key directly into the app sidebar in the browser.

---

## 🌟 Key Application Features

1. **Executive Valuation Summary Card**:
   - Rolling TTM Base EPS foundation (calculated from last 4 reported quarters).
   - **Probability-Weighted Expected Target Price**, Total Expected Return (%), and 2-Year Annualized CAGR (%).
   - Dynamic Probability Allocation (Base % vs. Bull %) calibrated to execution risk and founder credibility.
   - Institutional Conviction Verdict (**STRONG BUY**, **QUALIFIED BUY**, **ACCUMULATE ON DIPS**, **REJECT**).

2. **2-Year Forward Valuation Scenario Fan (Plotly)**:
   - Interactive chart featuring 365-day historical stock price, 50-DMA, and 200-DMA.
   - Forward projection cones to Base Case and Bull Case target price corridors at the 2-year horizon ($FY_{t+2}$).

3. **Deterministic Quantitative Engines**:
   - Compounding logic adhering to the H1 vs. H2 roll-forward calendar regime.
   - Dynamic exit P/E multiple derivation based on exit runway.
   - 4-Year cumulative CFO/PAT cash flow conversion and Emerging Markets **Altman Z''-Score**.
   - Solves for implied 10-year Free Cash Flow CAGR priced into Enterprise Value ($EV = \text{Mcap} + \text{Net Debt}$).

4. **AI Strategic Synthesis (Google AI Studio)**:
   - Hamilton Helmer's 7 Powers & Moat Audit.
   - Operational Pipeline & Order Book Visibility.
   - Forensic Anomalies & Management Commentary.
