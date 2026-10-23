"""Plotly figures styled for the dark CodeGuard theme."""
from __future__ import annotations

import plotly.graph_objects as go

import config

_FONT = dict(family="Segoe UI, Inter, system-ui, sans-serif", color="#e2e8f0")
_GRID = "rgba(148,163,184,0.18)"


def _base(fig: go.Figure, height: int = 320, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color="#f5c542"), x=0.01),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=_FONT,
        margin=dict(l=10, r=10, t=44 if title else 14, b=10),
        legend=dict(font=dict(color="#e2e8f0")),
    )
    return fig


def signal_chart(result) -> go.Figure:
    """Horizontal bars: score of each signal for one pair."""
    keys = [k for k in config.SIGNAL_KEYS if result.signals.get(k) is not None]
    labels = [config.SIGNAL_LABELS[k] for k in keys]
    values = [result.signals[k] for k in keys]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=values, colorscale=[[0, "#60a5fa"], [1, "#a78bfa"]], cmin=0, cmax=100),
        text=[f"{v:.1f}%" for v in values], textposition="outside",
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 115], gridcolor=_GRID, ticksuffix="%")
    fig.update_yaxes(autorange="reversed")
    return _base(fig, 300, "Signal breakdown")


def risk_gauge(result) -> go.Figure:
    steps = [
        dict(range=[0, result.thresholds.get("low_max", 30)], color="rgba(52,211,153,.35)"),
        dict(range=[result.thresholds.get("low_max", 30),
                    result.thresholds.get("moderate_max", 60)], color="rgba(251,191,36,.35)"),
        dict(range=[result.thresholds.get("moderate_max", 60), 100], color="rgba(248,113,113,.35)"),
    ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=result.overall,
        number=dict(suffix="%", font=dict(color="#f1f5f9")),
        gauge=dict(axis=dict(range=[0, 100], tickcolor="#94a3b8"),
                   bar=dict(color=config.RISK_COLORS[result.risk]),
                   steps=steps, bgcolor="rgba(0,0,0,0)", borderwidth=0),
    ))
    return _base(fig, 230)


def pair_heatmap(names: list, results: list, cluster: bool = True) -> go.Figure:
    """Colour-coded square matrix of overall similarity for every compared pair.

    With ``cluster`` the files are re-ordered so similar files sit together,
    which makes copying groups show up as bright blocks.
    """
    from src.batch import cluster_order, similarity_matrix

    order = cluster_order(names, results) if cluster else list(names)
    z = similarity_matrix(order, results)
    for i in range(len(order)):
        z[i][i] = None                       # blank diagonal
    show_text = len(order) <= 25
    fig = go.Figure(go.Heatmap(
        z=z, x=order, y=order, zmin=0, zmax=100, hoverongaps=False,
        colorscale=[[0, "#0f1a45"], [0.3, "#2563eb"], [0.6, "#a78bfa"], [1, "#f5c542"]],
        text=[[("" if v is None else f"{v:.0f}") for v in row] for row in z],
        texttemplate="%{text}" if show_text else None,
        textfont=dict(size=10, color="#f8fafc"),
        hovertemplate="%{y}<br>%{x}<br>%{z:.1f}%<extra></extra>",
        colorbar=dict(title="%", tickfont=dict(color="#e2e8f0")),
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickangle=-45)
    return _base(fig, max(340, 36 * len(order) + 160), "Similarity heatmap")


def distribution_chart(rows: list, low_max: float = 30, moderate_max: float = 60) -> go.Figure:
    scores = [r["overall"] for r in rows]
    fig = go.Figure(go.Histogram(
        x=scores, xbins=dict(start=0, end=100, size=10),
        marker=dict(color="#60a5fa", line=dict(color="#0a1128", width=1)),
        hovertemplate="%{x}%: %{y} comparison(s)<extra></extra>",
    ))
    for edge, color in ((low_max, config.RISK_COLORS["Moderate"]),
                        (moderate_max, config.RISK_COLORS["High"])):
        fig.add_vline(x=edge, line=dict(color=color, dash="dash", width=1.5))
    fig.update_xaxes(range=[0, 100], title="Overall similarity (%)", gridcolor=_GRID)
    fig.update_yaxes(title="Comparisons", gridcolor=_GRID, dtick=1)
    return _base(fig, 320, "Similarity distribution")


def risk_donut(rows: list) -> go.Figure:
    counts = {lvl: sum(1 for r in rows if r["risk"] == lvl) for lvl in config.RISK_LEVELS}
    fig = go.Figure(go.Pie(
        labels=list(counts), values=list(counts.values()), hole=0.6, sort=False,
        marker=dict(colors=[config.RISK_COLORS[l] for l in counts],
                    line=dict(color="#0a1128", width=2)),
        textinfo="label+value",
    ))
    return _base(fig, 320, "Risk indicators")


def timeline_chart(rows: list) -> go.Figure:
    ordered = sorted(rows, key=lambda r: r["id"])
    fig = go.Figure(go.Scatter(
        x=[r["created_at"] for r in ordered], y=[r["overall"] for r in ordered],
        mode="markers+lines",
        marker=dict(size=9, color=[config.RISK_COLORS.get(r["risk"], "#94a3b8") for r in ordered],
                    line=dict(color="#0a1128", width=1)),
        line=dict(color="rgba(148,163,184,.4)", width=1),
        text=[f'{r["file_a"]} vs {r["file_b"]}' for r in ordered],
        hovertemplate="%{text}<br>%{y:.1f}%<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 100], title="Similarity (%)", gridcolor=_GRID)
    fig.update_xaxes(gridcolor=_GRID)
    return _base(fig, 320, "Comparisons over time")
