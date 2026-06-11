# 📊 Stock & ETF P/E Valuation Tool

Personal stock valuation tool using **P/E relative comparison**.  
Supports **US stocks, ETFs** (via yfinance) and **A-shares** (via akshare).

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run app.py
```
The browser will open automatically at `http://localhost:8501`.

---

## Features

| Feature | Details |
|---------|---------|
| **Markets** | US stocks · US ETFs · A-shares (SH/SZ) |
| **Single analysis** | Full P/E breakdown, fair value range, insights |
| **Compare mode** | Side-by-side table + grouped bar chart |
| **Scoring** | Multi-dimension score → Undervalued / Fair / Overvalued |
| **Override** | Manually set industry P/E if auto-detection is off |
| **Editable benchmarks** | Adjust sector P/E norms in the sidebar |

---

## Scoring Model

Each dimension scores **−2 → +2**:

| Score | Meaning |
|-------|---------|
| +2 | >30% below benchmark (deeply cheap) |
| +1 | 15–30% below benchmark |
|  0 | Within ±15% (fair band) |
| −1 | 15–30% above benchmark |
| −2 | >30% above benchmark (expensive) |

**Dimensions used** (where data is available):
1. Trailing P/E vs Industry Median
2. Trailing P/E vs Market Historical Average (S&P500 avg ≈ 16.8x, CSI300 ≈ 13.5x)
3. Trailing P/E vs Stock's Own 5-Year Average
4. P/B Ratio (bonus dimension)

**Verdict thresholds** (score / max possible):
- ≥ 40% → 🟢 Undervalued
- 15–40% → 🟡 Slightly Undervalued
- ±15% → ⚪ Fair Value
- −15 to −40% → 🟠 Slightly Overvalued
- ≤ −40% → 🔴 Overvalued

---

## Ticker Format

| Market | Format | Example |
|--------|--------|---------|
| US Stock | Plain symbol | `AAPL` `MSFT` `NVDA` |
| US ETF | Plain symbol | `SPY` `QQQ` `VTI` |
| A-share Shanghai | `XXXXXX.SS` | `600519.SS` |
| A-share Shenzhen | `XXXXXX.SZ` | `000858.SZ` |

---

## Notes & Limitations

- **yfinance** data may have a 15–20 min delay for US markets.
- **akshare** A-share P/B data is real-time; sector classification is simplified.
- P/E is meaningless for companies with negative earnings — the tool will show "—".
- ETF P/E is the weighted average P/E of holdings (reported by provider).
- **This tool is for personal reference only and does not constitute financial advice.**

---

## Project Structure

```
stock_valuation/
├── app.py                   # Streamlit UI
├── requirements.txt
├── data/
│   └── fetcher.py           # yfinance + akshare data layer
├── models/
│   └── pe_valuation.py      # Scoring & valuation logic
└── utils/
    └── charts.py            # Plotly chart helpers
```
