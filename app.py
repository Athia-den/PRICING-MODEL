"""
app.py  —  Stock & ETF P/E Valuation Tool  v3
Inspired by fullratio.com layout
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from data.fetcher import fetch_stock, get_industry_benchmark_pe, get_market_avg_pe, INDUSTRY_PE_BENCHMARKS
from models.pe_valuation import run_valuation
from utils.charts import pe_gauge_chart, score_radar_chart, fair_value_range_chart

st.set_page_config(page_title="P/E Valuation Tool", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background:#0f172a;color:#f1f5f9}
section[data-testid="stSidebar"]{background:#1e293b}
section[data-testid="stSidebar"] *{color:#f1f5f9!important}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"]{color:#93c5fd!important;font-weight:600!important;font-size:.82rem!important;text-transform:uppercase!important;letter-spacing:.06em!important}
section[data-testid="stSidebar"] input,section[data-testid="stSidebar"] textarea{background:#0f172a!important;color:#f1f5f9!important;border:1px solid #475569!important;border-radius:6px!important}
section[data-testid="stSidebar"] hr{border-color:#334155!important;margin:10px 0!important}
[data-testid="stMetricValue"]{color:#f1f5f9!important;font-size:1.35rem!important}
[data-testid="stMetricLabel"]{color:#94a3b8!important}
.verdict-card{border-radius:12px;padding:22px 26px;text-align:center;margin-bottom:4px}
.verdict-green{background:rgba(34,197,94,.13);border:1px solid #22c55e}
.verdict-yellow{background:rgba(234,179,8,.13);border:1px solid #eab308}
.verdict-gray{background:rgba(148,163,184,.13);border:1px solid #94a3b8}
.verdict-orange{background:rgba(249,115,22,.13);border:1px solid #f97316}
.verdict-red{background:rgba(239,68,68,.13);border:1px solid #ef4444}
.insight-item{background:#1e293b;border-left:3px solid #3b82f6;padding:9px 13px;border-radius:6px;margin-bottom:7px;font-size:.88rem;color:#e2e8f0}
.hl-item{background:#1e293b;border-left:3px solid #0d9488;padding:8px 13px;border-radius:6px;margin-bottom:6px;font-size:.86rem;color:#e2e8f0}
.score-ring-wrap{text-align:center;padding:10px 0}
.section-header{font-size:1.05rem;font-weight:700;color:#93c5fd;margin:18px 0 10px;border-bottom:1px solid #1e293b;padding-bottom:6px}
.stat-row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #1e293b;font-size:.88rem}
.stat-label{color:#94a3b8}
.stat-value{color:#f1f5f9;font-weight:600}
.stat-value-green{color:#22c55e;font-weight:600}
.stat-value-red{color:#ef4444;font-weight:600}
.peer-row{display:flex;align-items:center;justify-content:space-between;padding:8px 10px;border-radius:6px;margin-bottom:4px;background:#1e293b;font-size:.87rem}
.score-bar-bg{height:8px;background:#334155;border-radius:4px;overflow:hidden;flex:1;margin:0 10px}
.score-bar-fill{height:100%;border-radius:4px}
</style>
""", unsafe_allow_html=True)

# ── helpers ──────────────────────────────────────────────────────────────────
C = {"green":"#22c55e","yellow":"#eab308","gray":"#94a3b8","orange":"#f97316","red":"#ef4444","blue":"#3b82f6","teal":"#0d9488"}

@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch(ticker):
    data = fetch_stock(ticker)
    if data.get("price") is None and data.get("trailing_pe") is None:
        st.cache_data.clear()
    return data

def fmt_large(n):
    if n is None: return "—"
    if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
    return f"${n:.0f}"

def fmt_pct(n, plus=False):
    if n is None: return "—"
    s = f"{n*100:+.1f}%" if plus else f"{n*100:.1f}%"
    return s

def fmt_x(n, dec=2):
    return f"{n:.{dec}f}x" if n is not None else "—"

def pct_color(v):
    if v is None: return "stat-value"
    return "stat-value-green" if v >= 0 else "stat-value-red"

def stat_row(label, value, color_class="stat-value"):
    st.markdown(f"<div class='stat-row'><span class='stat-label'>{label}</span>"
                f"<span class='{color_class}'>{value}</span></div>", unsafe_allow_html=True)

def score_donut(label, score, color):
    fig = go.Figure(go.Pie(
        values=[score, 100-score], hole=0.72,
        marker_colors=[color, "#1e293b"],
        textinfo="none", sort=False,
        direction="clockwise", rotation=90,
    ))
    fig.update_layout(
        showlegend=False, margin=dict(t=10,b=10,l=10,r=10), height=120,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=f"<b>{score}</b>", x=0.5, y=0.5,
                          font=dict(size=22, color=color), showarrow=False)],
    )
    st.plotly_chart(fig, width="stretch")
    st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:.78rem;margin-top:-10px'>{label}</div>",
                unsafe_allow_html=True)

def score_color(s):
    if s >= 70: return C["green"]
    if s >= 50: return C["yellow"]
    return C["red"]

def render_verdict(result):
    col = C.get(result.verdict_color, C["gray"])
    st.markdown(f"""
    <div class="verdict-card verdict-{result.verdict_color}">
      <div style="font-size:1.8rem;font-weight:700;color:{col}">{result.verdict}</div>
      <div style="color:#94a3b8;margin-top:5px;font-size:.87rem">
        Confidence: <b style="color:#f1f5f9">{result.confidence}</b> &nbsp;·&nbsp;
        Score: <b style="color:{col}">{result.total_score:+d}</b>/{len(result.dimension_scores)*2}
      </div>
    </div>""", unsafe_allow_html=True)

def peg_strip(result):
    peg = result.peg_ratio
    if not peg: return
    eg = result.earnings_growth
    if peg < 0.5:    pc,pb,pl = C["green"],  "rgba(34,197,94,.1)",  "Deeply Undervalued vs Growth"
    elif peg < 1.0:  pc,pb,pl = "#86efac",   "rgba(34,197,94,.07)", "Cheap vs Growth"
    elif peg < 1.5:  pc,pb,pl = C["gray"],   "rgba(148,163,184,.1)","Fair vs Growth"
    elif peg < 2.0:  pc,pb,pl = C["orange"], "rgba(249,115,22,.1)", "Slightly Expensive"
    else:            pc,pb,pl = C["red"],    "rgba(239,68,68,.1)",   "Expensive vs Growth"
    gs = f"  ·  Earnings Growth: {eg*100:.0f}%" if eg else ""
    st.markdown(
        f"<div style='background:{pb};border:1px solid {pc};border-radius:8px;"
        f"padding:9px 14px;margin:6px 0;display:flex;align-items:center;gap:14px;'>"
        f"<span style='font-size:1.05rem;font-weight:700;color:{pc}'>PEG {peg:.2f}</span>"
        f"<span style='color:#94a3b8'>→</span>"
        f"<span style='color:{pc};font-weight:600'>{pl}</span>"
        f"<span style='color:#64748b;font-size:.8rem'>{gs}</span>"
        f"<span style='margin-left:auto;color:#475569;font-size:.76rem'>Lynch: PEG&lt;1 cheap · &gt;2 pricey</span>"
        f"</div>", unsafe_allow_html=True)

def pe_history_table(hist_annual: dict, trailing_pe):
    if not hist_annual: return
    st.markdown("<div class='section-header'>📅 Annual P/E History</div>", unsafe_allow_html=True)
    years = sorted(hist_annual.keys(), reverse=True)
    rows = []
    for i, y in enumerate(years):
        pe = hist_annual[y]
        prev_pe = hist_annual.get(years[i+1]) if i+1 < len(years) else None
        chg = f"{(pe/prev_pe-1)*100:+.1f}%" if prev_pe else "—"
        rows.append({"Year": str(y), "Avg P/E": f"{pe:.1f}x", "YoY Change": chg})
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", height=min(320, 46 + len(rows)*35), hide_index=True)

def peer_compare(data, result):
    """Build a quick peer table from yfinance sector peers."""
    # Known peer map for common tickers
    PEER_MAP = {
        "AAPL":["MSFT","GOOGL","META","AMZN"],
        "MSFT":["AAPL","GOOGL","AMZN","CRM"],
        "NVDA":["AMD","INTC","QCOM","AVGO"],
        "TSLA":["GM","F","RIVN","NIO"],
        "AMZN":["MSFT","GOOGL","META","BABA"],
        "META":["SNAP","PINS","GOOGL","TWTR"],
        "SMCI":["HPQ","IBM","DELL","INTC"],
        "DELL":["HPQ","SMCI","IBM","INTC"],
        "HPQ": ["DELL","SMCI","IBM","LNVGY"],
        "GOOGL":["META","MSFT","AMZN","SNAP"],
        "JPM": ["BAC","WFC","GS","MS"],
        "BAC": ["JPM","WFC","C","GS"],
    }
    ticker = result.ticker
    peers  = PEER_MAP.get(ticker, [])
    if not peers: return

    st.markdown("<div class='section-header'>👥 Peer Comparison</div>", unsafe_allow_html=True)
    peer_rows = [{"Ticker": ticker, "Name": result.name[:22],
                  "P/E": fmt_x(result.trailing_pe,1),
                  "Forward P/E": fmt_x(result.forward_pe,1),
                  "PEG": fmt_x(result.peg_ratio,2),
                  "P/B": fmt_x(result.pb_ratio,2),
                  "Market Cap": fmt_large(data.get("market_cap")),
                  "Current": "← You"}]
    for p in peers[:4]:
        try:
            pd_ = cached_fetch(p)
            peer_rows.append({
                "Ticker": p,
                "Name": pd_.get("name","")[:22],
                "P/E": fmt_x(pd_.get("trailing_pe"),1),
                "Forward P/E": fmt_x(pd_.get("forward_pe"),1),
                "PEG": fmt_x(pd_.get("peg_ratio"),2),
                "P/B": fmt_x(pd_.get("pb_ratio"),2) if (pd_.get("pb_ratio") and pd_.get("pb_ratio",0)>0) else "—",
                "Market Cap": fmt_large(pd_.get("market_cap")),
                "Current": "",
            })
        except Exception:
            pass
    pf = pd.DataFrame(peer_rows)
    st.dataframe(pf, width="stretch", height=min(280, 46+len(peer_rows)*35), hide_index=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 P/E Valuation Tool")
    st.markdown("---")
    mode = st.radio("Mode", ["Single Stock / ETF", "Compare Multiple"])
    st.markdown("---")
    if mode == "Single Stock / ETF":
        ticker_input = st.text_input("Ticker Symbol",
            placeholder="AAPL · SPY · SMCI · 600519.SS").strip().upper()
    else:
        tickers_raw = st.text_area("Tickers (one per line or comma-separated)",
            placeholder="AAPL\nMSFT\nDELL", height=130)
    st.markdown("---")
    override_pe = st.number_input("Override Industry P/E (0 = auto)", 0.0, 200.0, 0.0, 0.5)
    st.markdown("---")
    with st.expander("Sector Benchmarks"):
        for k, v in INDUSTRY_PE_BENCHMARKS.items():
            INDUSTRY_PE_BENCHMARKS[k] = st.number_input(k, value=float(v), step=0.5, key=f"bm_{k}")
    st.markdown("---")
    st.markdown("<small style='color:#64748b'>yfinance (US/ETF) · akshare (A-share)<br>Cache: 5 min · Not financial advice</small>",
                unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# Stock & ETF Valuation")
st.markdown("<p style='color:#94a3b8;margin-top:-10px'>P/E relative valuation · US stocks · A-shares · ETFs</p>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SINGLE MODE
# ══════════════════════════════════════════════════════════════════════════════
if mode == "Single Stock / ETF":
    if not ticker_input:
        st.info("Enter a ticker in the sidebar to begin. Examples: AAPL · NVDA · SMCI · SPY · 600519.SS")
        st.stop()

    with st.spinner(f"Fetching {ticker_input}…"):
        try:
            data = cached_fetch(ticker_input)
        except Exception as e:
            st.error(f"Failed to fetch {ticker_input}: {e}"); st.stop()

    sector      = data.get("sector", "Unknown")
    industry_pe = override_pe if override_pe > 0 else get_industry_benchmark_pe(sector)
    mkt_pe      = get_market_avg_pe(data["market"])
    result      = run_valuation(data, industry_pe, mkt_pe)

    # ── Row 1: Name + badges + verdict ───────────────────────────────────
    c_name, c_verdict = st.columns([2.2, 1])
    with c_name:
        st.markdown(f"### {result.name}")
        mkt_badge  = "🇺🇸 US" if result.market == "US" else "🇨🇳 A-share"
        type_badge = data.get("quote_type","STOCK")
        for badge in [mkt_badge, type_badge, sector, data.get("industry","")]:
            if badge:
                st.markdown(f"<span style='background:#1e293b;border:1px solid #334155;"
                            f"border-radius:4px;padding:2px 8px;font-size:.78rem;color:#94a3b8;"
                            f"margin-right:5px'>{badge}</span>", unsafe_allow_html=True)
        if data.get("website"):
            st.markdown(f"<a href='{data['website']}' style='color:#3b82f6;font-size:.8rem'>{data['website']}</a>",
                        unsafe_allow_html=True)
    with c_verdict:
        render_verdict(result)

    peg_strip(result)
    st.markdown("---")

    # ── Row 2: 4 category score donuts ────────────────────────────────────
    st.markdown("<div class='section-header'>📊 Overall Scores</div>", unsafe_allow_html=True)
    d1,d2,d3,d4 = st.columns(4)
    with d1: score_donut("Valuation",     result.score_valuation,     score_color(result.score_valuation))
    with d2: score_donut("Growth",        result.score_growth,        score_color(result.score_growth))
    with d3: score_donut("Profitability", result.score_profitability, score_color(result.score_profitability))
    with d4: score_donut("Health",        result.score_health,        score_color(result.score_health))
    st.markdown("---")

    # ── Row 3: Key metrics ─────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📌 Key Statistics</div>", unsafe_allow_html=True)
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    price_str = f"{result.currency} {result.price:.2f}" if result.price else "—"
    def _pdelta(pct):
        if pct is None: return None
        return f"{'▲' if pct>0 else '▼'} {abs(pct)*100:.1f}% vs benchmark"
    m1.metric("Price", price_str)
    m2.metric("Trailing P/E", fmt_x(result.trailing_pe,1), delta=_pdelta(result.pe_vs_industry_pct), delta_color="inverse")
    m3.metric("Forward P/E",  fmt_x(result.forward_pe,1))
    peg_note = (("< 1 Cheap ▼" if result.peg_ratio < 1 else ("1-1.5 Fair" if result.peg_ratio < 1.5 else "> 1.5 Pricey ▲"))
                if result.peg_ratio else None)
    m4.metric("PEG Ratio", fmt_x(result.peg_ratio,2), delta=peg_note,
              delta_color="inverse" if result.peg_ratio else "off")
    m5.metric("P/B Ratio", fmt_x(result.pb_ratio,2))
    m6.metric("P/S Ratio", fmt_x(result.ps_ratio,2))
    st.markdown("---")

    # ── Row 4: Charts ──────────────────────────────────────────────────────
    chart_c, radar_c = st.columns([3, 2])
    with chart_c:
        fig_g = pe_gauge_chart(result.trailing_pe or result.forward_pe,
                               result.industry_pe, result.market_avg_pe, result.hist_pe_5y)
        st.plotly_chart(fig_g, width="stretch")
    with radar_c:
        if len(result.dimension_scores) >= 3:
            st.plotly_chart(score_radar_chart(result.dimension_scores), width="stretch")
        else:
            st.markdown("#### Score Breakdown")
            for dim, sc in result.dimension_scores.items():
                col = C["green"] if sc>0 else (C["red"] if sc<0 else C["gray"])
                bw  = int((sc+2)/4*100)
                st.markdown(
                    f"<div style='margin-bottom:9px'>"
                    f"<div style='font-size:.82rem;color:#94a3b8;margin-bottom:3px'>{dim}</div>"
                    f"<div style='display:flex;align-items:center;gap:8px'>"
                    f"<div class='score-bar-bg'><div class='score-bar-fill' style='width:{bw}%;background:{col}'></div></div>"
                    f"<span style='color:{col};font-weight:700;min-width:24px'>{sc:+d}</span></div></div>",
                    unsafe_allow_html=True)

    # ── Fair value ─────────────────────────────────────────────────────────
    if result.fair_price_mid and result.price:
        st.markdown("---")
        st.markdown("<div class='section-header'>🎯 Fair Value Estimate</div>", unsafe_allow_html=True)
        st.caption("Industry median P/E × trailing EPS  ·  ±15% safety band")
        st.plotly_chart(fair_value_range_chart(result.price, result.fair_price_low,
                        result.fair_price_mid, result.fair_price_high, result.currency),
                        width="stretch")
        fv1,fv2,fv3 = st.columns(3)
        fv1.metric("Fair Value Low",  f"{result.currency} {result.fair_price_low:.2f}")
        fv2.metric("Fair Value Mid",  f"{result.currency} {result.fair_price_mid:.2f}")
        fv3.metric("Fair Value High", f"{result.currency} {result.fair_price_high:.2f}")

    st.markdown("---")

    # ── Row 5: Highlights + Insights side by side ─────────────────────────
    hl_c, ins_c = st.columns(2)
    with hl_c:
        st.markdown("<div class='section-header'>⚡ Highlights</div>", unsafe_allow_html=True)
        for h in result.highlights:
            st.markdown(f"<div class='hl-item'>{h}</div>", unsafe_allow_html=True)
    with ins_c:
        st.markdown("<div class='section-header'>📝 Valuation Insights</div>", unsafe_allow_html=True)
        for i in result.insights:
            st.markdown(f"<div class='insight-item'>{i}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Row 6: Detailed stats in 3 columns ────────────────────────────────
    col_val, col_prof, col_health = st.columns(3)

    with col_val:
        st.markdown("<div class='section-header'>💰 Valuation</div>", unsafe_allow_html=True)
        stat_row("Market Cap",      fmt_large(data.get("market_cap")))
        stat_row("Enterprise Value",fmt_large(data.get("enterprise_value")))
        stat_row("EV/EBITDA",       fmt_x(data.get("ev_ebitda"),1))
        stat_row("EV/Revenue",      fmt_x(data.get("ev_revenue"),2))
        stat_row("Trailing P/E",    fmt_x(result.trailing_pe,1))
        stat_row("Forward P/E",     fmt_x(result.forward_pe,1))
        stat_row("PEG Ratio",       fmt_x(result.peg_ratio,2))
        stat_row("P/B Ratio",       fmt_x(result.pb_ratio,2))
        stat_row("P/S Ratio",       fmt_x(result.ps_ratio,2))
        stat_row("52W High",        f"${data['week52_high']:.2f}" if data.get("week52_high") else "—")
        stat_row("52W Low",         f"${data['week52_low']:.2f}"  if data.get("week52_low")  else "—")
        stat_row("50D Avg",         f"${data['avg50']:.2f}"       if data.get("avg50")        else "—")
        stat_row("200D Avg",        f"${data['avg200']:.2f}"      if data.get("avg200")       else "—")

    with col_prof:
        st.markdown("<div class='section-header'>📈 Financials & Growth</div>", unsafe_allow_html=True)
        stat_row("Revenue (TTM)",   fmt_large(data.get("total_revenue")))
        stat_row("Gross Profit",    fmt_large(data.get("gross_profit")))
        stat_row("Net Income",      fmt_large(data.get("net_income")))
        stat_row("EBITDA",          fmt_large(data.get("ebitda")))
        stat_row("Free Cash Flow",  fmt_large(data.get("free_cashflow")))
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        rg_v = data.get("revenue_growth")
        eg_v = data.get("earnings_growth")
        stat_row("Revenue Growth YoY",  fmt_pct(rg_v, plus=True),
                 "stat-value-green" if (rg_v and rg_v>0) else "stat-value-red" if rg_v else "stat-value")
        stat_row("Earnings Growth YoY", fmt_pct(eg_v, plus=True),
                 "stat-value-green" if (eg_v and eg_v>0) else "stat-value-red" if eg_v else "stat-value")
        stat_row("Gross Margin",    fmt_pct(data.get("gross_margin")))
        stat_row("Operating Margin",fmt_pct(data.get("operating_margin")))
        stat_row("Net Margin",      fmt_pct(data.get("net_margin")))
        stat_row("ROE",             fmt_pct(data.get("roe")))
        stat_row("ROA",             fmt_pct(data.get("roa")))
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        stat_row("Dividend/Share",  f"${data['dividend_rate']:.2f}" if data.get("dividend_rate") else "N/A")
        stat_row("Dividend Yield",  fmt_pct(data.get("dividend_yield")) if data.get("dividend_yield") else "N/A")
        stat_row("Payout Ratio",    fmt_pct(data.get("payout_ratio"))  if data.get("payout_ratio")  else "N/A")

    with col_health:
        st.markdown("<div class='section-header'>🏥 Financial Health</div>", unsafe_allow_html=True)
        cr = data.get("current_ratio"); qr = data.get("quick_ratio"); de = data.get("debt_to_equity")
        stat_row("Current Ratio",   f"{cr:.2f}" if cr else "—",
                 "stat-value-green" if (cr and cr>1.5) else "stat-value-red" if (cr and cr<1) else "stat-value")
        stat_row("Quick Ratio",     f"{qr:.2f}" if qr else "—",
                 "stat-value-green" if (qr and qr>1) else "stat-value-red" if (qr and qr<0.5) else "stat-value")
        stat_row("Debt/Equity",     f"{de:.0f}%" if de else "—",
                 "stat-value-green" if (de and de<50) else "stat-value-red" if (de and de>200) else "stat-value")
        stat_row("Total Debt",      fmt_large(data.get("total_debt")))

    st.markdown("---")

    # ── P/E History table ──────────────────────────────────────────────────
    pe_history_table(data.get("hist_pe_annual",{}), result.trailing_pe)

    # ── Peer comparison ────────────────────────────────────────────────────
    with st.spinner("Loading peer data…"):
        peer_compare(data, result)

    st.markdown("---")
    with st.expander("🔍 Raw Data"):
        st.json({k:v for k,v in data.items() if v is not None and k not in ["description","hist_pe_annual"]})

    if data.get("description"):
        with st.expander("ℹ️ About"):
            st.write(data["description"])

    st.markdown("<small style='color:#475569'>⚠️ For personal reference only — not financial advice.</small>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPARE MULTIPLE MODE
# ══════════════════════════════════════════════════════════════════════════════
else:
    raw     = tickers_raw.replace(",","\n") if "tickers_raw" in dir() else ""
    tickers = [t.strip().upper() for t in raw.split("\n") if t.strip()]

    if not tickers:
        st.info("Enter tickers in the sidebar (one per line or comma-separated).")
        st.stop()

    col_r, col_i = st.columns([1,5])
    with col_r:
        if st.button("🔄 Refresh"):
            st.cache_data.clear(); st.rerun()
    with col_i:
        st.caption("Click Refresh if any ticker shows Insufficient Data.")

    results, errors = [], []
    prog = st.progress(0, text="Fetching…")
    for i, tk in enumerate(tickers):
        try:
            d   = cached_fetch(tk)
            s   = d.get("sector","Unknown")
            ipe = override_pe if override_pe > 0 else get_industry_benchmark_pe(s)
            mpe = get_market_avg_pe(d["market"])
            results.append((tk, d, run_valuation(d, ipe, mpe)))
        except Exception as e:
            errors.append(f"{tk}: {e}")
        prog.progress((i+1)/len(tickers), text=f"Fetched {tk}")
    prog.empty()

    for e in errors: st.warning(f"⚠️ {e}")
    if not results: st.error("No data fetched."); st.stop()

    # Summary table
    st.markdown("### Comparison Table")
    rows = []
    for tk, d, r in results:
        peg = r.peg_ratio
        peg_s = ("—" if peg is None else f"{peg:.2f} ✅" if peg<1 else f"{peg:.2f} ⚪" if peg<1.5 else f"{peg:.2f} ⚠️")
        pb = r.pb_ratio
        rows.append({
            "Ticker": r.ticker, "Name": r.name[:22],
            "Price": f"{r.currency} {r.price:.2f}" if r.price else "—",
            "Trailing P/E": fmt_x(r.trailing_pe,1), "Forward P/E": fmt_x(r.forward_pe,1),
            "PEG": peg_s, "Industry P/E": fmt_x(r.industry_pe,1),
            "vs Industry": f"{r.pe_vs_industry_pct*100:+.0f}%" if r.pe_vs_industry_pct is not None else "—",
            "P/B": fmt_x(pb,2) if (pb and pb>0) else "—",
            "Valuation": r.score_valuation, "Growth": r.score_growth,
            "Score": r.total_score, "Verdict": r.verdict, "Confidence": r.confidence,
        })
    df = pd.DataFrame(rows)

    def style_v(val):
        if "Undervalued" in str(val): return "color:#22c55e;font-weight:600"
        if "Overvalued"  in str(val): return "color:#ef4444;font-weight:600"
        if "Slightly"    in str(val): return "color:#eab308;font-weight:600"
        return "color:#94a3b8"

    st.dataframe(
        df.style.map(style_v, subset=["Verdict"])
                .map(lambda v: "color:#22c55e" if isinstance(v,str) and v.startswith("+") else
                               "color:#ef4444" if isinstance(v,str) and v.startswith("-") else "",
                     subset=["vs Industry"]),
        width="stretch", height=min(420, 80+len(rows)*38), hide_index=True)

    st.markdown("---")
    st.markdown("### P/E Visual Comparison")
    fig = go.Figure()
    tl = [r.ticker for _,_,r in results]
    fig.add_trace(go.Bar(name="Trailing P/E", x=tl, y=[r.trailing_pe or 0 for _,_,r in results],
        marker_color=[{"green":"#22c55e","yellow":"#eab308","gray":"#94a3b8","orange":"#f97316","red":"#ef4444"}.get(r.verdict_color,"#94a3b8") for _,_,r in results],
        opacity=0.9, text=[fmt_x(r.trailing_pe,1) for _,_,r in results], textposition="outside"))
    fig.add_trace(go.Bar(name="Forward P/E", x=tl, y=[r.forward_pe or 0 for _,_,r in results],
        marker_color="#3b82f6", opacity=0.5, text=[fmt_x(r.forward_pe,1) for _,_,r in results], textposition="outside"))
    fig.add_trace(go.Scatter(name="Industry P/E", x=tl, y=[r.industry_pe for _,_,r in results],
        mode="markers", marker=dict(symbol="line-ew", size=20, color="#f59e0b", line=dict(width=3,color="#f59e0b"))))
    fig.update_layout(barmode="group", paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
        font=dict(color="#f1f5f9"), xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155",title="P/E Ratio"),
        legend=dict(bgcolor="#1e293b",bordercolor="#334155",borderwidth=1),
        margin=dict(t=30,b=20,l=20,r=20), height=380)
    st.plotly_chart(fig, width="stretch")

    # Score comparison
    st.markdown("---")
    st.markdown("### Score Comparison")
    fig2 = go.Figure()
    cats = ["Valuation","Growth","Profitability","Health"]
    for _,_,r in results:
        fig2.add_trace(go.Bar(name=r.ticker,
            x=cats, y=[r.score_valuation, r.score_growth, r.score_profitability, r.score_health],
            text=[r.score_valuation, r.score_growth, r.score_profitability, r.score_health],
            textposition="outside"))
    fig2.add_hline(y=50, line_dash="dot", line_color="#475569", annotation_text="Neutral (50)")
    fig2.update_layout(barmode="group", paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
        font=dict(color="#f1f5f9"), xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155", title="Score (0–100)", range=[0,110]),
        legend=dict(bgcolor="#1e293b",bordercolor="#334155",borderwidth=1),
        margin=dict(t=30,b=20,l=20,r=20), height=360)
    st.plotly_chart(fig2, width="stretch")

    st.markdown("<small style='color:#475569'>⚠️ For personal reference only — not financial advice.</small>",
                unsafe_allow_html=True)
