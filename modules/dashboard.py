"""
Risk dashboard visualizations (Plotly).

Turns the flat "score / count" metrics of the original app into a
proper analytics view: a radar chart of per-category scores and a
horizontal severity bar so the risk profile is scannable at a glance.
"""

import plotly.graph_objects as go

from modules.agents import AnalysisResult

LEVEL_COLORS = {"HIGH": "#e74c3c", "MED": "#f39c12", "LOW": "#f1c40f"}


def category_radar(result: AnalysisResult) -> go.Figure:
    categories = [a.agent_name for a in result.agents]
    scores = [a.category_score for a in result.agents]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=scores + [scores[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Category score",
            line_color="#2ecc71",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(l=30, r=30, t=20, b=20),
        height=380,
    )
    return fig


def severity_breakdown(result: AnalysisResult) -> go.Figure:
    counts = {"HIGH": 0, "MED": 0, "LOW": 0}
    for f in result.all_flags:
        counts[f.level] = counts.get(f.level, 0) + 1

    fig = go.Figure(
        go.Bar(
            x=list(counts.values()),
            y=list(counts.keys()),
            orientation="h",
            marker_color=[LEVEL_COLORS[k] for k in counts.keys()],
        )
    )
    fig.update_layout(
        xaxis_title="Number of flags",
        margin=dict(l=30, r=30, t=20, b=20),
        height=250,
    )
    return fig
