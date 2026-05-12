import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Theme tokens — light-theme compatible ────────────────────────────────────
PRIMARY   = "#1e7145"
ACCENT    = "#16a34a"
DANGER    = "#dc2626"
WARNING   = "#f59e0b"
TEXT_DARK = "#1f2937"   # headings / values
TEXT_MID  = "#374151"   # body text
TEXT_SOFT = "#6b7280"   # axis labels / subtitles
GRID      = "rgba(0,0,0,0.06)"
BG        = "rgba(0,0,0,0)"   # transparent — inherits Streamlit background
COLORS    = ["#1e7145", "#16a34a", "#059669", "#047857", "#10b981", "#34d399"]

# Shared layout defaults applied to every chart
_BASE = dict(
    plot_bgcolor  = BG,
    paper_bgcolor = BG,
    font          = dict(family="Inter, Arial, sans-serif", size=13, color=TEXT_MID),
    margin        = dict(l=10, r=20, t=50, b=40),
    hoverlabel    = dict(bgcolor=PRIMARY, font_size=13, font_color="white"),
)


def _fmt(v):
    """Abbreviate large numbers: 1500000 → PKR 1.50M"""
    if v >= 1_000_000: return f"PKR {v/1_000_000:.2f}M"
    if v >= 1_000:     return f"PKR {v/1_000:.1f}K"
    return f"PKR {v:,.0f}"


# ── 1. Monthly Revenue Trend ─────────────────────────────────────────────────
def monthly_trend_chart(monthly_df):
    if monthly_df.empty:
        return None

    monthly_df = monthly_df.copy()
    monthly_df["label"] = monthly_df["Revenue"].apply(_fmt)

    fig = px.area(
        monthly_df, x="Month", y="Revenue",
        title="📈 Monthly Revenue Trend",
        markers=True,
        text="label",
    )
    fig.update_traces(
        line=dict(width=3, color=PRIMARY),
        marker=dict(size=9, color=PRIMARY, line=dict(width=2, color="white")),
        fillcolor="rgba(30,113,69,0.10)",
        textposition="top center",
        textfont=dict(size=11, color=PRIMARY),
        hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        **_BASE,
        xaxis_title=None,
        yaxis_title="Revenue (PKR)",
        title_font=dict(size=15, color=PRIMARY),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color=TEXT_SOFT, size=11),
            tickangle=-30,
        ),
        yaxis=dict(
            gridcolor=GRID,
            tickfont=dict(color=TEXT_SOFT, size=11),
            tickformat="~s",
        ),
    )
    return fig


# ── 2. Month-over-Month Growth Rate ─────────────────────────────────────────
def growth_rate_chart(growth_df):
    if growth_df.empty:
        return None

    colors = [ACCENT if v >= 0 else DANGER for v in growth_df["Growth_%"]]
    labels = [f"{v:+.1f}%" for v in growth_df["Growth_%"]]

    fig = go.Figure(go.Bar(
        x=growth_df["Month"],
        y=growth_df["Growth_%"],
        marker_color=colors,
        marker_line_width=0,
        text=labels,
        textposition="outside",
        textfont=dict(size=12, color=TEXT_DARK),
        hovertemplate="<b>%{x}</b><br>Growth: %{text}<extra></extra>",
    ))
    fig.add_hline(
        y=0, line_dash="dot",
        line_color="rgba(0,0,0,0.2)", line_width=1,
    )
    fig.update_layout(
        **_BASE,
        title="📊 Month-over-Month Growth Rate",
        title_font=dict(size=15, color=PRIMARY),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color=TEXT_SOFT, size=11),
            tickangle=-30,
            title=None,
        ),
        yaxis=dict(
            gridcolor=GRID,
            tickfont=dict(color=TEXT_SOFT, size=11),
            ticksuffix="%",
            title=None,
            zeroline=False,
        ),
        bargap=0.4,
    )
    return fig


# ── 3. Top / Bottom Products ─────────────────────────────────────────────────
def top_products_chart(top_df, title="🏆 Top Products by Revenue"):
    if top_df.empty:
        return None

    df = top_df.sort_values("Revenue").copy()
    df["label"] = df["Revenue"].apply(_fmt)

    n = len(df)
    bar_colors = [
        f"rgba(22,163,74,{0.40 + 0.60*(i/max(n-1,1))})"
        for i in range(n)
    ]

    fig = px.bar(
        df, x="Revenue", y="Product",
        orientation="h",
        title=title,
        text="label",
    )
    fig.update_traces(
        marker_color=bar_colors,
        marker_line_width=0,
        textposition="inside",
        textfont=dict(color="white", size=12, family="Arial"),
        hovertemplate="<b>%{y}</b><br>Revenue: %{x:,.0f}<extra></extra>",
    )
    fig.update_layout(
        **_BASE,
        title_font=dict(size=15, color=PRIMARY),
        xaxis=dict(
            showgrid=True,
            gridcolor=GRID,
            tickfont=dict(color=TEXT_SOFT, size=11),
            tickformat="~s",
            title=dict(text="Revenue (PKR)", font=dict(color=TEXT_SOFT, size=12)),
        ),
        yaxis=dict(
            tickfont=dict(color=TEXT_DARK, size=12),
            title=None,
        ),
        bargap=0.35,
    )
    return fig


# ── 4. Region Pie Chart ───────────────────────────────────────────────────────
def region_pie_chart(region_df):
    if region_df.empty:
        return None

    fig = px.pie(
        region_df, names="Region", values="Revenue",
        title="🗺️ Revenue by Region",
        color_discrete_sequence=COLORS,
        hole=0.42,
    )
    fig.update_traces(
        textposition="outside",
        textinfo="label+percent",
        textfont=dict(size=12, color=TEXT_DARK),
        marker=dict(line=dict(color="white", width=2)),
        hovertemplate="<b>%{label}</b><br>Revenue: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        pull=[0.04] * len(region_df),
    )
    fig.update_layout(
        **_BASE,
        title_font=dict(size=15, color=PRIMARY),
        legend=dict(
            orientation="v",
            font=dict(size=12, color=TEXT_MID),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


# ── 5. Region Bar Chart ───────────────────────────────────────────────────────
def region_bar_chart(region_df):
    if region_df.empty:
        return None

    df = region_df.sort_values("Revenue", ascending=False).copy()
    df["label"] = df["Revenue"].apply(_fmt)

    fig = px.bar(
        df, x="Region", y="Revenue",
        title="🗺️ Region-wise Revenue",
        color="Region",
        color_discrete_sequence=COLORS,
        text="label",
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(color=TEXT_DARK, size=11),
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        **_BASE,
        title_font=dict(size=15, color=PRIMARY),
        coloraxis_showscale=False,
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color=TEXT_DARK, size=12),
            title=None,
        ),
        yaxis=dict(
            gridcolor=GRID,
            tickfont=dict(color=TEXT_SOFT, size=11),
            tickformat="~s",
            title=dict(text="Revenue (PKR)", font=dict(color=TEXT_SOFT, size=12)),
        ),
        bargap=0.35,
    )
    return fig


# ── 6. Auto Chart (generic fallback) ─────────────────────────────────────────
def auto_chart(df, x_col, y_col, chart_hint="bar", title="Chart"):
    if df.empty:
        return None
    try:
        if chart_hint == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, markers=True,
                          color_discrete_sequence=[PRIMARY])
            fig.update_traces(line=dict(width=3), marker=dict(size=8))
        elif chart_hint == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title,
                         color_discrete_sequence=COLORS, hole=0.35)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=title)
            fig.update_traces(marker_color=ACCENT, marker_line_width=0)
            fig.update_layout(coloraxis_showscale=False)
        fig.update_layout(
            **_BASE,
            title_font=dict(size=15, color=PRIMARY),
            xaxis=dict(tickfont=dict(color=TEXT_SOFT)),
            yaxis=dict(tickfont=dict(color=TEXT_SOFT), gridcolor=GRID),
        )
        return fig
    except Exception:
        return None


# ── 7. KPI Delta Indicator ────────────────────────────────────────────────────
def kpi_delta_indicator(value, reference, title, format_str="{:,.0f}"):
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=value,
        delta={"reference": reference, "valueformat": ".1f",
               "increasing": {"color": ACCENT}, "decreasing": {"color": DANGER}},
        title={"text": title, "font": {"size": 14, "color": TEXT_SOFT}},
        number={"valueformat": ",.0f", "font": {"color": TEXT_DARK, "size": 28}},
    ))
    fig.update_layout(
        height=150,
        margin=dict(t=40, b=10, l=10, r=10),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
    )
    return fig
