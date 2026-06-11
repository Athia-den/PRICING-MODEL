"""
models/pe_valuation.py  —  v3
Comprehensive valuation with 4 score categories like fullratio.com
"""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ValuationResult:
    ticker: str; name: str; market: str; price: Optional[float]; currency: str
    trailing_pe: Optional[float]; forward_pe: Optional[float]
    pb_ratio: Optional[float]; ps_ratio: Optional[float]
    peg_ratio: Optional[float]; hist_pe_5y: Optional[float]
    earnings_growth: Optional[float]; revenue_growth: Optional[float]
    industry_pe: float; market_avg_pe: float
    pe_vs_industry_pct: Optional[float]
    pe_vs_market_pct: Optional[float]
    pe_vs_hist5y_pct: Optional[float]
    # 4 category scores (0-100 each, like fullratio)
    score_valuation:    int = 50
    score_growth:       int = 50
    score_profitability:int = 50
    score_health:       int = 50
    # PE scoring dimensions
    dimension_scores: dict = field(default_factory=dict)
    total_score: int = 0
    verdict: str = "Insufficient Data"
    verdict_color: str = "gray"
    confidence: str = "Low"
    fair_price_low: Optional[float] = None
    fair_price_mid: Optional[float] = None
    fair_price_high: Optional[float] = None
    insights: list = field(default_factory=list)
    highlights: list = field(default_factory=list)

def _safe(v): return v if (v is not None and v == v) else None
def _pct(v, b): return (v - b) / b if (v and b and b != 0) else None

def _score_pe(pct):
    if pct is None: return 0
    if pct < -0.30: return +2
    if pct < -0.15: return +1
    if pct <=  0.15: return 0
    if pct <=  0.30: return -1
    return -2

def _score_peg(peg):
    if peg is None: return 0
    if peg < 0.5: return +2
    if peg < 1.0: return +1
    if peg < 1.5: return 0
    if peg < 2.0: return -1
    return -2

def _score_pb(pb):
    if pb is None: return 0
    if pb < 1.0: return +2
    if pb < 1.5: return +1
    if pb < 3.0: return 0
    if pb < 5.0: return -1
    return -2

def _verdict(score, n):
    if n == 0: return "Insufficient Data", "gray", "Low"
    r = score / (n * 2)
    if r >= 0.40:  v, c = "🟢 Undervalued",          "green"
    elif r >= 0.15: v, c = "🟡 Slightly Undervalued", "yellow"
    elif r >= -0.15: v, c = "⚪ Fair Value",           "gray"
    elif r >= -0.40: v, c = "🟠 Slightly Overvalued",  "orange"
    else:            v, c = "🔴 Overvalued",            "red"
    conf = "High" if n >= 4 else ("Medium" if n >= 2 else "Low")
    return v, c, conf

def _clamp(v, lo=0, hi=100): return max(lo, min(hi, int(v)))

def _valuation_score(pe_vs_ind, pe_vs_mkt, peg, pb, ps):
    pts = 50
    if pe_vs_ind is not None: pts += -pe_vs_ind * 60
    if peg is not None:
        if peg < 1:   pts += 20
        elif peg < 1.5: pts += 5
        elif peg > 2: pts -= 20
    if pb is not None:
        if pb < 1.5: pts += 10
        elif pb > 5: pts -= 10
    return _clamp(pts)

def _growth_score(rev_g, earn_g):
    pts = 50
    if rev_g is not None:  pts += rev_g * 100
    if earn_g is not None: pts += earn_g * 80
    return _clamp(pts)

def _profit_score(gross_m, net_m, roe, roa):
    pts = 50
    if gross_m is not None: pts += (gross_m - 0.3) * 60
    if net_m   is not None: pts += (net_m   - 0.1) * 80
    if roe     is not None: pts += (roe     - 0.15) * 50
    if roa     is not None: pts += (roa     - 0.08) * 50
    return _clamp(pts)

def _health_score(current_r, quick_r, de, fcf):
    pts = 50
    if current_r is not None:
        if current_r > 2:   pts += 15
        elif current_r > 1: pts += 5
        else:               pts -= 20
    if quick_r is not None:
        if quick_r > 1: pts += 10
        else:           pts -= 10
    if de is not None:
        if de < 50:   pts += 15
        elif de < 100: pts += 5
        elif de < 200: pts -= 10
        else:          pts -= 20
    if fcf is not None and fcf > 0: pts += 10
    return _clamp(pts)

def run_valuation(data: dict, industry_pe: float, market_avg_pe: float) -> ValuationResult:
    tp  = _safe(data.get("trailing_pe"))
    fp  = _safe(data.get("forward_pe"))
    pb  = _safe(data.get("pb_ratio"))
    ps  = _safe(data.get("ps_ratio"))
    peg = _safe(data.get("peg_ratio"))
    h5y = _safe(data.get("hist_pe_5y"))
    eps = _safe(data.get("eps_ttm"))
    price = _safe(data.get("price"))
    eg  = _safe(data.get("earnings_growth"))
    rg  = _safe(data.get("revenue_growth"))
    gm  = _safe(data.get("gross_margin"))
    nm  = _safe(data.get("net_margin"))
    roe = _safe(data.get("roe"))
    roa = _safe(data.get("roa"))
    cr  = _safe(data.get("current_ratio"))
    qr  = _safe(data.get("quick_ratio"))
    de  = _safe(data.get("debt_to_equity"))
    fcf = _safe(data.get("free_cashflow"))

    primary_pe = tp if (tp and tp > 0) else fp
    pe_vs_ind  = _pct(primary_pe, industry_pe)
    pe_vs_mkt  = _pct(primary_pe, market_avg_pe)
    pe_vs_hist = _pct(primary_pe, h5y)

    # PE dimension scores
    dims = {}
    if pe_vs_ind  is not None: dims["vs Industry P/E"]   = _score_pe(pe_vs_ind)
    if pe_vs_mkt  is not None: dims["vs Market Avg P/E"] = _score_pe(pe_vs_mkt)
    if pe_vs_hist is not None: dims["vs Own 5Y Avg P/E"] = _score_pe(pe_vs_hist)
    if peg is not None and (eg is None or eg > 0): dims["PEG Ratio"] = _score_peg(peg)
    if pb  is not None: dims["P/B Ratio"] = _score_pb(pb)
    total = sum(dims.values())
    verdict, color, conf = _verdict(total, len(dims))

    # 4 category scores
    sv = _valuation_score(pe_vs_ind, pe_vs_mkt, peg, pb, ps)
    sg = _growth_score(rg, eg)
    sp = _profit_score(gm, nm, roe, roa)
    sh = _health_score(cr, qr, de, fcf)

    # Fair value
    fl = fm = fh = None
    if eps and eps > 0:
        fl = round(eps * industry_pe * 0.85, 2)
        fm = round(eps * industry_pe,        2)
        fh = round(eps * industry_pe * 1.15, 2)

    # Insights
    ins = []
    if primary_pe and pe_vs_ind is not None:
        d = "below" if pe_vs_ind < 0 else "above"
        ins.append(f"P/E **{primary_pe:.1f}x** is **{abs(pe_vs_ind)*100:.0f}% {d}** the industry median of {industry_pe:.1f}x.")
    if pe_vs_hist is not None and h5y:
        d = "below" if pe_vs_hist < 0 else "above"
        ins.append(f"P/E is **{abs(pe_vs_hist)*100:.0f}% {d}** its own 5-year average of {h5y:.1f}x.")
    if peg and eg and eg > 0:
        lbl = "cheap" if peg < 1 else ("fair" if peg < 1.5 else "expensive")
        ins.append(f"PEG **{peg:.2f}** (growth {eg*100:.0f}%) — **{lbl}** relative to growth rate.")
    if fp and tp and fp < tp * 0.95:
        ins.append(f"Forward P/E ({fp:.1f}x) < Trailing ({tp:.1f}x) — analysts expect **earnings to grow**.")
    elif fp and tp and fp > tp * 1.05:
        ins.append(f"Forward P/E ({fp:.1f}x) > Trailing ({tp:.1f}x) — analysts expect **earnings to decline**. ⚠️")
    if pb: ins.append(f"P/B **{pb:.2f}x**" + (" — trading below book value." if pb < 1 else "."))
    if not ins: ins.append("Insufficient data to generate insights.")

    # Auto highlights (like fullratio)
    hl = []
    if rg  is not None: hl.append(f"Revenue growth: **{rg*100:+.0f}% YoY**")
    if eg  is not None: hl.append(f"Earnings growth: **{eg*100:+.0f}% YoY**")
    if nm  is not None: hl.append(f"Net margin: **{nm*100:.1f}%**")
    if roe is not None: hl.append(f"Return on equity (ROE): **{roe*100:.1f}%**")
    if de  is not None:
        lbl = "low (healthy)" if de < 50 else ("moderate" if de < 150 else "high ⚠️")
        hl.append(f"Debt/Equity: **{de:.0f}%** — {lbl}")
    if cr  is not None:
        lbl = "healthy" if cr > 1.5 else ("tight ⚠️" if cr < 1 else "adequate")
        hl.append(f"Current ratio: **{cr:.2f}** — {lbl}")
    if fm and price:
        margin = (fm - price) / fm * 100
        lbl = f"**{abs(margin):.0f}% below** fair value" if margin > 0 else f"**{abs(margin):.0f}% above** fair value"
        hl.append(f"Industry P/E fair value: **${fm:.2f}** — price is {lbl}.")

    return ValuationResult(
        ticker=data["ticker"], name=data["name"], market=data["market"],
        price=price, currency=data.get("currency","USD"),
        trailing_pe=tp, forward_pe=fp, pb_ratio=pb, ps_ratio=ps,
        peg_ratio=peg, hist_pe_5y=h5y,
        earnings_growth=eg, revenue_growth=rg,
        industry_pe=industry_pe, market_avg_pe=market_avg_pe,
        pe_vs_industry_pct=pe_vs_ind, pe_vs_market_pct=pe_vs_mkt,
        pe_vs_hist5y_pct=pe_vs_hist,
        score_valuation=sv, score_growth=sg,
        score_profitability=sp, score_health=sh,
        dimension_scores=dims, total_score=total,
        verdict=verdict, verdict_color=color, confidence=conf,
        fair_price_low=fl, fair_price_mid=fm, fair_price_high=fh,
        insights=ins, highlights=hl,
    )
