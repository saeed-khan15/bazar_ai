# utils/report.py
"""
BazaarAI — HTML Business Report Generator
Assembles KPIs, charts, alerts, and AI summary into a
self-contained, print-ready HTML report.
"""

import base64
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(v):
    """Abbreviate large numbers."""
    if v >= 1_000_000: return f"PKR {v/1_000_000:.2f}M"
    if v >= 1_000:     return f"PKR {v/1_000:.1f}K"
    return f"PKR {v:,.0f}"


def _chart_to_b64(fig) -> Optional[str]:
    """
    Convert a Plotly figure to a base64-encoded PNG string.
    Requires kaleido: pip install kaleido
    Returns None gracefully if kaleido is unavailable.
    """
    try:
        img_bytes = fig.to_image(format="png", width=800, height=380, scale=2)
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception:
        return None


def _alert_badge(alert: Dict) -> str:
    """Render a single alert as an HTML badge row."""
    color_map = {
        "danger":     ("#fef2f2", "#dc2626", "#fca5a5"),
        "warning":    ("#fffbeb", "#d97706", "#fcd34d"),
        "success":    ("#f0fdf4", "#16a34a", "#86efac"),
    }
    bg, text, border = color_map.get(alert.get("type", "warning"),
                                     color_map["warning"])
    icon  = alert.get("icon", "ℹ️")
    title = alert.get("title", "")
    msg   = alert.get("message", "")
    return f"""
    <div style="background:{bg};border-left:4px solid {border};border-radius:6px;
                padding:10px 14px;margin-bottom:8px;">
        <span style="font-weight:600;color:{text};">{icon} {title}</span>
        <span style="color:#374151;font-size:13px;margin-left:8px;">{msg}</span>
    </div>"""


# ── Main report builder ───────────────────────────────────────────────────────

def build_html_report(
    filename:          str,
    kpis:              Dict[str, Any],
    alerts:            List[Dict],
    executive_summary: str,
    top_products:      pd.DataFrame,
    bottom_products:   pd.DataFrame,
    regions:           pd.DataFrame,
    fig_trend=None,
    fig_growth=None,
    fig_top=None,
    fig_bottom=None,
    fig_pie=None,
    fig_region_bar=None,
    language:          str = "English",
) -> str:
    """
    Build and return a self-contained HTML report string.
    All charts are embedded as base64 PNGs — no external files needed.
    """

    now      = datetime.now().strftime("%B %d, %Y  %H:%M")
    biz_name = filename.replace(".csv", "").replace(".xlsx", "").replace("_", " ").title()

    # ── KPI cards ──────────────────────────────────────────────────────────────
    kpi_items = []
    if kpis.get("total_revenue"):
        kpi_items.append(("💰", "Total Revenue",    _fmt(kpis["total_revenue"])))
    if kpis.get("avg_revenue"):
        kpi_items.append(("📊", "Avg Transaction",  _fmt(kpis["avg_revenue"])))
    if kpis.get("mom_growth") is not None:
        g = kpis["mom_growth"]
        arrow = "▲" if g >= 0 else "▼"
        color = "#16a34a" if g >= 0 else "#dc2626"
        kpi_items.append(("📈", "MoM Growth",
                           f'<span style="color:{color}">{arrow} {g:+.1f}%</span>'))
    if kpis.get("total_products"):
        kpi_items.append(("📦", "Products",         str(int(kpis["total_products"]))))
    if kpis.get("total_regions"):
        kpi_items.append(("🗺️", "Regions",          str(int(kpis["total_regions"]))))
    if kpis.get("total_quantity"):
        q = kpis["total_quantity"]
        kpi_items.append(("🛒", "Units Sold",
                           f"{q/1000:.1f}K" if q >= 1000 else str(int(q))))

    kpi_html = ""
    for icon, label, value in kpi_items:
        kpi_html += f"""
        <div class="kpi-card">
            <div class="kpi-label">{icon} {label}</div>
            <div class="kpi-value">{value}</div>
        </div>"""

    # ── Charts ─────────────────────────────────────────────────────────────────
    def chart_block(fig, caption):
        if fig is None:
            return ""
        b64 = _chart_to_b64(fig)
        if b64 is None:
            return f'<p style="color:#9ca3af;font-size:12px;">⚠️ Chart unavailable (kaleido not installed)</p>'
        return f"""
        <div class="chart-wrap">
            <img src="data:image/png;base64,{b64}" alt="{caption}"
                 style="width:100%;border-radius:8px;" />
            <p class="chart-caption">{caption}</p>
        </div>"""

    trend_html      = chart_block(fig_trend,      "Monthly Revenue Trend")
    growth_html     = chart_block(fig_growth,     "Month-over-Month Growth Rate")
    top_html        = chart_block(fig_top,        "Top 5 Products by Revenue")
    bottom_html     = chart_block(fig_bottom,     "Bottom 5 Products by Revenue")
    pie_html        = chart_block(fig_pie,        "Revenue by Region")
    region_bar_html = chart_block(fig_region_bar, "Region-wise Revenue Breakdown")

    # ── Alerts ─────────────────────────────────────────────────────────────────
    alerts_html = "".join([_alert_badge(a) for a in alerts]) if alerts \
                  else '<p style="color:#9ca3af;">No alerts for this dataset.</p>'

    # ── Top / Bottom products table ────────────────────────────────────────────
    def product_table(df, title, color):
        if df.empty:
            return ""
        rows = ""
        for i, row in df.iterrows():
            rows += f"""
            <tr>
                <td style="padding:7px 10px;border-bottom:1px solid #f3f4f6;">
                    {row['Product']}</td>
                <td style="padding:7px 10px;border-bottom:1px solid #f3f4f6;
                            text-align:right;font-weight:600;color:{color};">
                    {_fmt(row['Revenue'])}</td>
            </tr>"""
        return f"""
        <div style="flex:1;min-width:260px;">
            <h4 style="color:{color};margin:0 0 8px;">{title}</h4>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="background:#f9fafb;">
                        <th style="padding:7px 10px;text-align:left;
                                   color:#6b7280;font-weight:500;">Product</th>
                        <th style="padding:7px 10px;text-align:right;
                                   color:#6b7280;font-weight:500;">Revenue</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>"""

    products_html = f"""
    <div style="display:flex;gap:24px;flex-wrap:wrap;">
        {product_table(top_products,    "🏆 Top Products",    "#1e7145")}
        {product_table(bottom_products, "⚠️ Bottom Products", "#d97706")}
    </div>"""

    # ── Executive summary ──────────────────────────────────────────────────────
    # Convert markdown bold (**text**) to HTML <strong>
    import re
    summary_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>',
                          executive_summary or "No summary generated.")
    summary_html = summary_html.replace("\n", "<br>")

    # ── Assemble full HTML ─────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BazaarAI Business Report — {biz_name}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', Arial, sans-serif;
    background: #f8fafc;
    color: #1f2937;
    font-size: 14px;
    line-height: 1.6;
  }}

  /* ── Page wrapper ── */
  .page {{
    max-width: 1000px;
    margin: 0 auto;
    background: white;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(135deg, #1e7145 0%, #16a34a 100%);
    padding: 32px 40px;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .header-logo {{ font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
  .header-sub  {{ font-size: 13px; opacity: 0.85; margin-top: 2px; }}
  .header-meta {{ text-align: right; font-size: 12px; opacity: 0.8; line-height: 1.8; }}
  .header-meta strong {{ font-size: 16px; font-weight: 600; opacity: 1; }}

  /* ── Section ── */
  .section {{
    padding: 28px 40px;
    border-bottom: 1px solid #f1f5f9;
  }}
  .section-title {{
    font-size: 16px;
    font-weight: 600;
    color: #1e7145;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #dcfce7;
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  /* ── KPI cards ── */
  .kpi-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
  }}
  .kpi-card {{
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 14px 20px;
    flex: 1;
    min-width: 140px;
    max-width: 200px;
  }}
  .kpi-label {{
    font-size: 11px;
    font-weight: 500;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }}
  .kpi-value {{
    font-size: 20px;
    font-weight: 700;
    color: #1e7145;
  }}

  /* ── Charts ── */
  .chart-wrap   {{ margin-bottom: 16px; }}
  .chart-caption {{
    font-size: 12px;
    color: #9ca3af;
    text-align: center;
    margin-top: 6px;
  }}
  .chart-row {{
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
  }}
  .chart-row .chart-wrap {{ flex: 1; min-width: 280px; }}

  /* ── Summary ── */
  .summary-box {{
    background: #f8fafc;
    border-left: 4px solid #1e7145;
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    font-size: 13px;
    color: #374151;
    line-height: 1.8;
  }}

  /* ── Footer ── */
  .footer {{
    background: #1e7145;
    color: rgba(255,255,255,0.7);
    text-align: center;
    padding: 16px 40px;
    font-size: 12px;
  }}
  .footer strong {{ color: white; }}

  /* ── Print styles ── */
  @media print {{
    body {{ background: white; }}
    .page {{ box-shadow: none; max-width: 100%; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div>
      <div class="header-logo">🏪 BazaarAI</div>
      <div class="header-sub">Agentic Sales Data Analyst for Pakistani Businesses</div>
    </div>
    <div class="header-meta">
      <strong>{biz_name}</strong><br>
      Business Performance Report<br>
      Generated: {now}
    </div>
  </div>

  <!-- KPIs -->
  <div class="section">
    <div class="section-title">📊 Key Performance Indicators</div>
    <div class="kpi-grid">{kpi_html}</div>
  </div>

  <!-- SMART ALERTS -->
  <div class="section">
    <div class="section-title">🔔 Smart Alerts</div>
    {alerts_html}
  </div>

  <!-- REVENUE TREND -->
  <div class="section">
    <div class="section-title">📈 Revenue Trends</div>
    {trend_html}
    {growth_html}
  </div>

  <!-- PRODUCT PERFORMANCE -->
  <div class="section">
    <div class="section-title">📦 Product Performance</div>
    <div class="chart-row">
      <div class="chart-wrap" style="flex:1;min-width:280px;">{top_html}</div>
      <div class="chart-wrap" style="flex:1;min-width:280px;">{bottom_html}</div>
    </div>
    <br>
    {products_html}
  </div>

  <!-- REGIONAL PERFORMANCE -->
  <div class="section">
    <div class="section-title">🗺️ Regional Performance</div>
    <div class="chart-row">
      <div class="chart-wrap" style="flex:1;min-width:280px;">{pie_html}</div>
      <div class="chart-wrap" style="flex:1;min-width:280px;">{region_bar_html}</div>
    </div>
  </div>

  <!-- EXECUTIVE SUMMARY -->
  <div class="section">
    <div class="section-title">🧠 AI Executive Summary</div>
    <div class="summary-box">{summary_html}</div>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Generated by <strong>BazaarAI</strong> — AI-Powered Sales Analytics for Pakistani Businesses &nbsp;|&nbsp;
    <strong>{now}</strong> &nbsp;|&nbsp; Data source: {filename}
  </div>

</div>
</body>
</html>"""

    return html
