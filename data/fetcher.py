"""
data/fetcher.py  —  v3
Fetches comprehensive stock data modelled after fullratio.com
"""

import yfinance as yf
import pandas as pd
import numpy as np

# ─── Industry P/E benchmarks ─────────────────────────────────────────────────
INDUSTRY_PE_BENCHMARKS = {
    "Technology": 28, "Consumer Cyclical": 22, "Communication Services": 20,
    "Healthcare": 22, "Financials": 13, "Industrials": 20,
    "Consumer Defensive": 21, "Energy": 12, "Utilities": 16,
    "Real Estate": 35, "Basic Materials": 15, "ETF": 20,
    "A_Technology": 40, "A_Consumer": 25, "A_Healthcare": 30,
    "A_Financials": 8, "A_Industrials": 22, "A_Energy": 10,
    "A_Materials": 14, "A_RealEstate": 12, "A_Utilities": 15, "Unknown": 20,
}
SP500_HIST_AVG_PE  = 16.8
CSI300_HIST_AVG_PE = 13.5

def detect_market(ticker: str) -> str:
    t = ticker.strip().upper()
    return "CN" if (t.endswith(".SS") or t.endswith(".SZ")) else "US"

def _safe_float(v):
    try:
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return None

def fetch_us(ticker: str) -> dict:
    t    = yf.Ticker(ticker)
    info = t.info

    # ── Basic info ────────────────────────────────────────────────────────
    name       = info.get("longName") or info.get("shortName") or ticker
    quote_type = info.get("quoteType", "")
    sector     = info.get("sector") or ("ETF" if quote_type == "ETF" else "Unknown")
    industry   = info.get("industry", "")
    website    = info.get("website", "")
    description= info.get("longBusinessSummary", "")
    currency   = info.get("currency", "USD")

    # ── Price & valuation ─────────────────────────────────────────────────
    price       = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    trailing_pe = _safe_float(info.get("trailingPE"))
    forward_pe  = _safe_float(info.get("forwardPE"))
    pb_ratio    = _safe_float(info.get("priceToBook"))
    ps_ratio    = _safe_float(info.get("priceToSalesTrailing12Months"))
    eps_ttm     = _safe_float(info.get("trailingEps"))
    market_cap  = _safe_float(info.get("marketCap"))
    ev          = _safe_float(info.get("enterpriseValue"))
    ev_ebitda   = _safe_float(info.get("enterpriseToEbitda"))
    ev_revenue  = _safe_float(info.get("enterpriseToRevenue"))

    # Filter nonsensical P/B (negative book value)
    if pb_ratio is not None and pb_ratio < 0:
        pb_ratio = None

    # ── PEG ───────────────────────────────────────────────────────────────
    peg_ratio = _safe_float(info.get("trailingPegRatio") or info.get("pegRatio"))
    earnings_growth = _safe_float(info.get("earningsGrowth"))
    revenue_growth  = _safe_float(info.get("revenueGrowth"))
    if (peg_ratio is None or peg_ratio <= 0) and trailing_pe and earnings_growth and earnings_growth > 0:
        peg_ratio = round(trailing_pe / (earnings_growth * 100), 2)
    if peg_ratio is not None and (peg_ratio <= 0 or peg_ratio > 100):
        peg_ratio = None

    # ── Profitability ─────────────────────────────────────────────────────
    gross_margin    = _safe_float(info.get("grossMargins"))
    operating_margin= _safe_float(info.get("operatingMargins"))
    net_margin      = _safe_float(info.get("profitMargins"))
    roe             = _safe_float(info.get("returnOnEquity"))
    roa             = _safe_float(info.get("returnOnAssets"))

    # ── Financial health ──────────────────────────────────────────────────
    current_ratio   = _safe_float(info.get("currentRatio"))
    quick_ratio     = _safe_float(info.get("quickRatio"))
    debt_to_equity  = _safe_float(info.get("debtToEquity"))
    total_debt      = _safe_float(info.get("totalDebt"))
    free_cashflow   = _safe_float(info.get("freeCashflow"))
    dividend_yield  = _safe_float(info.get("dividendYield"))
    payout_ratio    = _safe_float(info.get("payoutRatio"))
    dividend_rate   = _safe_float(info.get("dividendRate"))

    # ── Revenue / earnings ────────────────────────────────────────────────
    total_revenue    = _safe_float(info.get("totalRevenue"))
    gross_profit     = _safe_float(info.get("grossProfits"))
    operating_income = _safe_float(info.get("operatingCashflow"))  # proxy
    net_income       = _safe_float(info.get("netIncomeToCommon"))
    ebitda           = _safe_float(info.get("ebitda"))

    # ── 52-week range ─────────────────────────────────────────────────────
    week52_high = _safe_float(info.get("fiftyTwoWeekHigh"))
    week52_low  = _safe_float(info.get("fiftyTwoWeekLow"))
    avg50       = _safe_float(info.get("fiftyDayAverage"))
    avg200      = _safe_float(info.get("twoHundredDayAverage"))

    # ── Historical P/E (5Y) ───────────────────────────────────────────────
    hist_pe_5y = None
    hist_pe_annual = {}   # {year: avg_pe}
    try:
        hist = t.history(period="5y")
        if not hist.empty and eps_ttm and eps_ttm > 0:
            hist_pe_5y = round(hist["Close"].mean() / eps_ttm, 1)
            # Annual breakdown
            hist["year"] = hist.index.year
            hist["pe"]   = hist["Close"] / eps_ttm
            hist_pe_annual = hist.groupby("year")["pe"].mean().round(1).to_dict()
    except Exception:
        pass

    # ── Peer tickers from yfinance ────────────────────────────────────────
    peers = []
    try:
        recs = t.recommendations
        if recs is not None and not recs.empty:
            pass  # recommendations don't give peers directly
    except Exception:
        pass

    return {
        "ticker": ticker.upper(), "name": name, "market": "US",
        "quote_type": quote_type, "sector": sector, "industry": industry,
        "website": website, "description": description[:300] if description else "",
        "currency": currency, "price": price,
        "trailing_pe": trailing_pe, "forward_pe": forward_pe,
        "current_pe": trailing_pe or forward_pe,
        "pb_ratio": pb_ratio, "ps_ratio": ps_ratio,
        "peg_ratio": peg_ratio, "eps_ttm": eps_ttm,
        "market_cap": market_cap, "enterprise_value": ev,
        "ev_ebitda": ev_ebitda, "ev_revenue": ev_revenue,
        "gross_margin": gross_margin, "operating_margin": operating_margin,
        "net_margin": net_margin, "roe": roe, "roa": roa,
        "current_ratio": current_ratio, "quick_ratio": quick_ratio,
        "debt_to_equity": debt_to_equity, "total_debt": total_debt,
        "free_cashflow": free_cashflow,
        "revenue_growth": revenue_growth, "earnings_growth": earnings_growth,
        "dividend_yield": dividend_yield, "dividend_rate": dividend_rate,
        "payout_ratio": payout_ratio,
        "total_revenue": total_revenue, "gross_profit": gross_profit,
        "net_income": net_income, "ebitda": ebitda,
        "week52_high": week52_high, "week52_low": week52_low,
        "avg50": avg50, "avg200": avg200,
        "hist_pe_5y": hist_pe_5y, "hist_pe_annual": hist_pe_annual,
    }

def fetch_cn(ticker: str) -> dict:
    try:
        import akshare as ak
    except ImportError:
        raise ImportError("akshare not installed.")
    raw = ticker.strip().upper()
    code = raw.split(".")[0] if "." in raw else raw
    try:
        spot = ak.stock_zh_a_spot_em()
        row  = spot[spot["代码"] == code]
        price    = _safe_float(row["最新价"].values[0])      if not row.empty else None
        pe_ttm   = _safe_float(row["市盈率-动态"].values[0]) if not row.empty else None
        pb_ratio = _safe_float(row["市净率"].values[0])      if not row.empty else None
        name     = str(row["名称"].values[0])                if not row.empty else code
        mkt_cap  = _safe_float(row["总市值"].values[0])      if not row.empty else None
    except Exception:
        price = pe_ttm = pb_ratio = mkt_cap = None
        name = code
    base = {k: None for k in ["forward_pe","peg_ratio","eps_ttm","enterprise_value",
            "ev_ebitda","ev_revenue","ps_ratio","gross_margin","operating_margin",
            "net_margin","roe","roa","current_ratio","quick_ratio","debt_to_equity",
            "total_debt","free_cashflow","revenue_growth","earnings_growth",
            "dividend_yield","dividend_rate","payout_ratio","total_revenue",
            "gross_profit","net_income","ebitda","week52_high","week52_low",
            "avg50","avg200","hist_pe_5y","website","description"]}
    base.update({
        "ticker": raw, "name": name, "market": "CN", "quote_type": "STOCK",
        "sector": "Unknown", "industry": "", "currency": "CNY",
        "price": price, "trailing_pe": pe_ttm, "current_pe": pe_ttm,
        "pb_ratio": pb_ratio if (pb_ratio and pb_ratio > 0) else None,
        "market_cap": mkt_cap, "hist_pe_annual": {},
    })
    return base

def fetch_stock(ticker: str) -> dict:
    market = detect_market(ticker)
    data = fetch_cn(ticker) if market == "CN" else fetch_us(ticker)
    return data

def get_industry_benchmark_pe(sector: str) -> float:
    return INDUSTRY_PE_BENCHMARKS.get(sector, INDUSTRY_PE_BENCHMARKS["Unknown"])

def get_market_avg_pe(market: str) -> float:
    return SP500_HIST_AVG_PE if market == "US" else CSI300_HIST_AVG_PE
