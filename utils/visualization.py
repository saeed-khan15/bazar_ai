import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# Dark green theme colors
THEME_PRIMARY = "#1e7145"       # Dark green
THEME_ACCENT = "#16a34a"        # Bright green
THEME_DANGER = "#dc2626"        # Red
THEME_BG = "rgba(0,0,0,0)"      # Dark background
THEME_TEXT = "#e8f0f5"          # Light text
COLORS = ["#1e7145", "#16a34a", "#059669", "#047857", "#10b981", "#34d399"]


def monthly_trend_chart(monthly_df):
    if monthly_df.empty:
        return None
    fig = px.line(
        monthly_df, x="Month", y="Revenue",
        title="📈 Monthly Revenue Trend",
        markers=True,
        color_discrete_sequence=[THEME_PRIMARY]
    )
    fig.update_layout(
        xaxis_title="Month", yaxis_title="Revenue (PKR)",
        plot_bgcolor=THEME_BG, paper_bgcolor=THEME_BG,
        font=dict(family="Arial", size=13, color=THEME_TEXT),
        hovermode="x unified",
        title_font_color=THEME_TEXT,
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color=THEME_TEXT)),
        yaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color=THEME_TEXT))
    )
    fig.update_traces(line=dict(width=3, color=THEME_PRIMARY), 
                     marker=dict(size=8, color=THEME_PRIMARY))
    return fig


def growth_rate_chart(growth_df):
    if growth_df.empty:
        return None
    colors = ["#16A34A" if v >= 0 else "#DC2626" for v in growth_df["Growth_%"]]
    fig = go.Figure(go.Bar(
        x=growth_df["Month"],
        y=growth_df["Growth_%"],
        marker_color=colors,
        text=[f"{v:.1f}%" for v in growth_df["Growth_%"]],
        textposition="outside"
    ))
    fig.update_layout(
        title="Month-over-Month Growth Rate (%)",
        xaxis_title="Month", yaxis_title="Growth %",
        plot_bgcolor=THEME_BG, paper_bgcolor=THEME_BG,
        font=dict(family="Arial", size=13, color=THEME_TEXT),
        title_font_color=THEME_TEXT,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color=THEME_TEXT)),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color=THEME_TEXT)),
        margin=dict(t=50, b=40)
    )
    fig.update_traces(textfont=dict(color=THEME_TEXT))
    return fig


def top_products_chart(top_df, title="🏆 Top Products by Revenue"):
    if top_df.empty:
        return None
    # Use a single accent color for better contrast on dark background
    fig = px.bar(
        top_df.sort_values("Revenue"), x="Revenue", y="Product",
        orientation="h", title=title,
        text="Revenue",
    )
    fig.update_traces(marker_color=THEME_ACCENT, texttemplate="%{text:,.0f}", textposition="outside",
                     textfont=dict(color=THEME_TEXT, size=11))
    fig.update_layout(
        plot_bgcolor=THEME_BG, paper_bgcolor=THEME_BG,
        font=dict(family="Arial", size=13, color=THEME_TEXT),
        title_font_color=THEME_TEXT,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color=THEME_TEXT)),
        yaxis=dict(tickfont=dict(color=THEME_TEXT))
    )
    return fig


def region_pie_chart(region_df):
    if region_df.empty:
        return None
    fig = px.pie(
        region_df, names="Region", values="Revenue",
        title="🗺️ Revenue by Region",
        color_discrete_sequence=COLORS,
        hole=0.35
    )
    fig.update_traces(textposition="inside", textinfo="percent+label",
                     textfont=dict(size=12, color=THEME_TEXT))
    fig.update_layout(
        font=dict(family="Arial", size=13, color=THEME_TEXT),
        paper_bgcolor=THEME_BG,
        title_font_color=THEME_TEXT
    )
    return fig


def region_bar_chart(region_df):
    if region_df.empty:
        return None
    fig = px.bar(
        region_df.sort_values("Revenue", ascending=False), x="Region", y="Revenue",
        title="🗺️ Region-wise Revenue",
        color="Region",
        color_discrete_sequence=COLORS,
        text="Revenue",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                     textfont=dict(color=THEME_TEXT, size=11))
    fig.update_layout(
        plot_bgcolor=THEME_BG, paper_bgcolor=THEME_BG,
        font=dict(family="Arial", size=13, color=THEME_TEXT),
        title_font_color=THEME_TEXT,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color=THEME_TEXT)),
        yaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color=THEME_TEXT))
    )
    return fig


def auto_chart(df, x_col, y_col, chart_hint="bar", title="Chart"):
    if df.empty:
        return None
    try:
        if chart_hint == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, markers=True,
                          color_discrete_sequence=[THEME_PRIMARY])
        elif chart_hint == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title,
                         color_discrete_sequence=COLORS, hole=0.3)
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=title)
            fig.update_traces(marker_color=THEME_ACCENT)
            fig.update_layout(coloraxis_showscale=False)
        fig.update_layout(
            plot_bgcolor=THEME_BG, paper_bgcolor=THEME_BG,
            font=dict(family="Arial", size=13, color=THEME_TEXT),
            title_font_color=THEME_TEXT
        )
        return fig
    except Exception:
        return None


def kpi_delta_indicator(value, reference, title, format_str="{:,.0f}"):
    delta = value - reference if reference else 0
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=value,
        delta={"reference": reference, "valueformat": ".1f"},
        title={"text": title, "font": {"size": 16, "color": THEME_TEXT}},
        number={"valueformat": ",.0f", "font": {"color": THEME_TEXT}}
    ))
    fig.update_layout(
        height=150, 
        margin=dict(t=40, b=10, l=10, r=10),
        paper_bgcolor=THEME_BG,
        plot_bgcolor=THEME_BG,
        font=dict(color=THEME_TEXT)
    )
    return fig
