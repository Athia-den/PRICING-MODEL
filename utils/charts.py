"""
utils/charts.py
Plotly chart helpers for the Streamlit app.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional


COLORS = {
    "green":  "#22c55e",
    "yellow": "#eab308",
    "gray":   "#94a3b8",
    "orange": "#f97316",
    "red":    "#ef4444",
    "blue":   "#3b82f6",
    "bg":     "#0f172a",
    "surface":"#1e293b",
    "border": "#334155",
    "text":   "#f1f5f9",
    "muted":  "#94a3b8",
}


def pe_gauge_chart(current_pe: Optional[float], industry_pe: float,
                   market_avg_pe: float, hist_pe_5y: Optional[float]) -> go.Figure:
    """Bullet / gauge showing current P/E vs benchmarks."""

    benchmarks = {"Industry Median": industry_pe, "Market Avg": market_avg_pe}
    if hist_pe_5y:
        benchmarks["5Y Own Avg"] = hist_pe_5y

    categories = list(benchmarks.keys()) + (["Current P/E"] if current_pe else [])
    values     = list(benchmarks.values()) + ([current_pe] if current_pe else [])
    bar_colors = [COLORS["muted"]] * len(benchmarks)
    if current_pe:
        min_bm = min(benchmarks.values())
        bar_colors.append(COLORS["green"] if current_pe < min_bm else
                          COLORS["red"]   if current_pe > max(benchmarks.values()) else
                          COLORS["yellow"])

    fig = go.Figure(go.Bar(
        x=categories,
        y=values,
        marker_color=bar_colors,
        text=[f"{v:.1f}x" for v in values],
        textposition="outside",
        textfont=dict(color=COLORS["text"], size=13),
    ))
    fig.update_layout(
        title=dict(text="P/E Comparison", font=dict(color=COLORS["text"], size=15)),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
        xaxis=dict(gridcolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], title="P/E Ratio"),
        margin=dict(t=50, b=20, l=20, r=20),
        height=320,
    )
    return fig


def score_radar_chart(dimension_scores: dict) -> go.Figure:
    """Spider/radar showing score per valuation dimension."""
    if not dimension_scores:
        return go.Figure()

    dims   = list(dimension_scores.keys())
    scores = list(dimension_scores.values())
    # Close the radar loop
    dims_c   = dims + [dims[0]]
    scores_c = scores + [scores[0]]

    fig = go.Figure(go.Scatterpolar(
        r=scores_c,
        theta=dims_c,
        fill="toself",
        fillcolor="rgba(59,130,246,0.25)",
        line=dict(color=COLORS["blue"], width=2),
        marker=dict(size=6, color=COLORS["blue"]),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=COLORS["surface"],
            radialaxis=dict(
                visible=True, range=[-2, 2],
                tickvals=[-2, -1, 0, 1, 2],
                ticktext=["−2", "−1", "0", "+1", "+2"],
                gridcolor=COLORS["border"],
                linecolor=COLORS["border"],
                tickfont=dict(color=COLORS["muted"], size=10),
            ),
            angularaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"],
                             tickfont=dict(color=COLORS["text"], size=11)),
        ),
        paper_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
        margin=dict(t=30, b=30, l=30, r=30),
        height=300,
        showlegend=False,
        title=dict(text="Score by Dimension", font=dict(color=COLORS["text"], size=15)),
    )
    return fig


def fair_value_range_chart(price: float, low: float, mid: float,
                           high: float, currency: str) -> go.Figure:
    """Horizontal bar showing current price vs fair value range."""
    sym = "$" if currency == "USD" else ("¥" if currency == "CNY" else currency + " ")

    fig = go.Figure()

    # Fair value range band
    fig.add_shape(type="rect",
        x0=low, x1=high, y0=-0.4, y1=0.4,
        fillcolor="rgba(59,130,246,0.2)", line=dict(color=COLORS["blue"], width=1))

    # Mid line
    fig.add_shape(type="line",
        x0=mid, x1=mid, y0=-0.4, y1=0.4,
        line=dict(color=COLORS["blue"], width=2, dash="dot"))

    # Current price marker
    p_color = COLORS["green"] if price <= mid else COLORS["red"]
    fig.add_trace(go.Scatter(
        x=[price], y=[0],
        mode="markers+text",
        marker=dict(size=16, color=p_color, symbol="diamond"),
        text=[f"  Current {sym}{price:.2f}"],
        textposition="middle right",
        textfont=dict(color=COLORS["text"], size=12),
        name="Current Price",
    ))

    # Annotations for band edges
    for val, label in [(low, f"Low {sym}{low:.2f}"), (mid, f"Fair {sym}{mid:.2f}"),
                       (high, f"High {sym}{high:.2f}")]:
        fig.add_annotation(x=val, y=0.55, text=label,
                           showarrow=False, font=dict(color=COLORS["muted"], size=10))

    fig.update_layout(
        title=dict(text="Fair Value Range (Industry P/E × EPS)", font=dict(color=COLORS["text"], size=15)),
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(color=COLORS["text"]),
        xaxis=dict(gridcolor=COLORS["border"], title=f"Price ({currency})"),
        yaxis=dict(visible=False, range=[-1, 1]),
        margin=dict(t=50, b=40, l=20, r=120),
        height=200,
        showlegend=False,
    )
    return fig


def multi_stock_table(results: list) -> pd.DataFrame:
    rows = []
    for r in results:
        # PEG label
        peg = r.peg_ratio
        if peg is None:        peg_str = "—"
        elif peg < 1.0:        peg_str = f"{peg:.2f} ✅"
        elif peg < 1.5:        peg_str = f"{peg:.2f} ⚪"
        else:                  peg_str = f"{peg:.2f} ⚠️"

        rows.append({
            "Ticker":         r.ticker,
            "Name":           r.name[:24],
            "Price":          f"{r.currency} {r.price:.2f}" if r.price else "—",
            "Trailing P/E":   f"{r.trailing_pe:.1f}x" if r.trailing_pe else "—",
            "Forward P/E":    f"{r.forward_pe:.1f}x"  if r.forward_pe  else "—",
            "PEG":            peg_str,
            "Industry P/E":   f"{r.industry_pe:.1f}x",
            "vs Industry":    f"{r.pe_vs_industry_pct*100:+.0f}%" if r.pe_vs_industry_pct is not None else "—",
            "P/B":            f"{r.pb_ratio:.2f}x" if r.pb_ratio else "—",
            "Score":          r.total_score,
            "Verdict":        r.verdict,
            "Confidence":     r.confidence,
        })
    return pd.DataFrame(rows)
