# main file
import streamlit as st
import pandas as pd
import os
import sys
import platform
import importlib.metadata as importlib_metadata
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from utils.session import init_session, check_session_expiry, reset_session, get_session_info
from utils.ingestion import clean_dataframe, get_data_summary, auto_map_columns
from utils.analysis import (
    compute_kpis, monthly_trends, growth_rates,
    top_bottom_products, region_performance, smart_alerts, build_data_chunks
)
from utils.visualization import (
    monthly_trend_chart, growth_rate_chart, top_products_chart,
    region_pie_chart, region_bar_chart
)
from utils.embeddings import build_faiss_index, semantic_search
from utils.agents import check_api_key_valid
try:
    from utils.agents import (
        analyst_agent, narrator_agent, qa_agent, generate_executive_summary
    )
except Exception:
    pass



# ════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLING
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="BazaarAI — AI Data Analyst",
    page_icon="PK",
    layout="wide",
    initial_sidebar_state="expanded"
)


try:
    theme_base = st.get_option("theme.base")
except Exception:
    theme_base = "dark"

# Choose colors based on Streamlit theme base
if theme_base == "light":
    PRIMARY = "#0f5132"  # darker green for contrast on light
    BG = "#ffffff"
    TEXT = "#0b2f1a"
    ACCENT = "#198754"
else:
    PRIMARY = "#1e7145"
    BG = "rgba(10, 14, 39, 0.95)"
    TEXT = "#e8f0f5"
    ACCENT = "#16a34a"

st.markdown(f"""
<style>
    [data-testid="metric-container"] {{
        background-color: rgba(30, 113, 69, 0.08);
        border-left: 4px solid {PRIMARY};
        padding: 12px;
        border-radius: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: rgba(30, 113, 69, 0.06);
        border-radius: 6px;
        padding: 8px 14px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {PRIMARY};
        color: {TEXT};
    }}
    .stButton > button {{
        background-color: {PRIMARY};
        color: {TEXT};
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
    }}
    .stButton > button:hover {{
        background-color: {ACCENT};
    }}
    .stSuccess, .stInfo {{
        border-left: 4px solid {PRIMARY};
        border-radius: 6px;
    }}
    hr {{ border-color: rgba(30, 113, 69, 0.25); }}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ════════════════════════════════════════════════════════════════════════════

init_session()

# FIXED: Streamlit Cloud exposes secrets via st.secrets, NOT os.environ automatically.
# This bridges the gap so agents.py (which reads os.environ) works on all platforms.
if "GROQ_API_KEY" not in os.environ:
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

# Initialize tab state tracking
if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = 0  # Default to Overview tab

# Check API Key on startup
if st.session_state.api_key_valid is None:
    is_valid, error = check_api_key_valid()
    st.session_state.api_key_valid = is_valid
    st.session_state.api_key_error = error

if check_session_expiry():
    st.warning("Session expired. Please upload your data again.")
    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.image("https://flagcdn.com/w80/pk.png", width=50)
    st.title("BazaarAI")
    st.caption("**Agentic Sales Data Analyst**\nfor Pakistani Businesses")
    st.divider()

    # API Key Status
    if not st.session_state.api_key_valid:
        st.error("API Key Not Configured")
        with st.expander("Setup Instructions", expanded=False):
            st.markdown("""
**Streamlit Cloud Setup:**
1. Go to [Groq Console](https://console.groq.com)
2. Create/copy your API key
3. In Streamlit Cloud deployment:
   - Secrets → New secret
   - `GROQ_API_KEY` = your key

**Local Setup:**
```bash
export GROQ_API_KEY=your_key_here
streamlit run app_new.py
```

**Error:** Invalid or missing GROQ_API_KEY
            """)
    else:
        st.success("API Connected")

    st.subheader("Upload Data")
    language = st.selectbox("Language / Zaban", ["English", "Roman Urdu"], key="language")

    uploaded_file = st.file_uploader(
        "CSV ya Excel file upload karein",
        type=["csv", "xlsx", "xls"],
        help="Upload your sales data file (CSV or Excel format). Recommended: < 50MB"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "**Use sample data (optional):** open sample_data.csv in the repository"
        )

    with col2:
        analyze_disabled = uploaded_file is None or not st.session_state.api_key_valid
        analyze_btn = st.button(
            "Analyze",
            type="primary",
            use_container_width=True,
            disabled=analyze_disabled,
            help="Upload data first" if not uploaded_file else "API not configured" if not st.session_state.api_key_valid else ""
        )

    if st.session_state.get("analysis_done"):
        st.divider()
        info = get_session_info()
        if info:
            st.caption(f"**Session:** {info}")
        if st.button("Reset / New File", use_container_width=True):
            reset_session()
            st.rerun()

    st.divider()
    st.caption("**Powered by:**\nGroq LLaMA 3.3, FastEmbed, FAISS")

    # Deployment diagnostics (help debug Streamlit Cloud vs local differences)
    with st.expander("Deployment Diagnostics", expanded=False):
        try:
            st.write("**Runtime info**")
            st.write(f"Python: {platform.python_version()}")
            try:
                import streamlit as _st
                st.write(f"Streamlit: {_st.__version__}")
            except Exception:
                st.write("Streamlit: (not importable)")
            for pkg in ("plotly", "pandas", "numpy", "groq"):
                try:
                    ver = importlib_metadata.version(pkg)
                except Exception:
                    try:
                        mod = importlib.import_module(pkg)
                        ver = getattr(mod, "__version__", "unknown")
                    except Exception:
                        ver = "not installed"
                st.write(f"{pkg}: {ver}")

            st.write("**Environment**")
            st.write(f"Working dir: {os.getcwd()}")
            st.write(f"Entry file: {os.path.basename(__file__)}")
            env_key = os.environ.get("GROQ_API_KEY") or (st.secrets.get("GROQ_API_KEY") if hasattr(st, "secrets") else None)
            st.write(f"GROQ_API_KEY set: {'yes' if env_key else 'no'}")

            # show top of requirements.txt if present
            req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
            if os.path.exists(req_path):
                st.write("**requirements.txt (top lines)**")
                with open(req_path, "r", encoding="utf-8") as rf:
                    for i, line in enumerate(rf):
                        if i >= 10:
                            break
                        st.text(line.strip())
            else:
                st.write("requirements.txt: not found in repo root")
        except Exception as e:
            st.write(f"Diagnostics error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE
# ════════════════════════════════════════════════════════════════════════════

if analyze_btn and uploaded_file is not None:
    if not st.session_state.api_key_valid:
            st.error("Cannot proceed: API Key not configured. See sidebar for setup instructions.")
    else:
        with st.spinner("Analyzing your data..."):
            try:
                # Data ingestion
                df, col_types, auto_map = clean_dataframe(uploaded_file)
                st.session_state.df = df
                st.session_state.col_types = col_types
                st.session_state.upload_timestamp = datetime.now()

                if not st.session_state.get("column_map"):
                    st.session_state.column_map = auto_map

                column_map = st.session_state.column_map

                # If no date mapped, attempt automatic detection by sampling parse success
                if not column_map.get("date"):
                    try:
                        import pandas as _pd
                        best_col = None
                        best_ratio = 0.0
                        for col in df.columns:
                            try:
                                parsed = _pd.to_datetime(df[col], errors="coerce")
                                ratio = float(parsed.notna().mean())
                                # try dayfirst if low ratio
                                if ratio < 0.2:
                                    parsed2 = _pd.to_datetime(df[col], dayfirst=True, errors="coerce")
                                    ratio2 = float(parsed2.notna().mean())
                                    if ratio2 > ratio:
                                        ratio = ratio2
                                # treat Excel serial numbers
                                if ratio < 0.2 and _pd.api.types.is_numeric_dtype(df[col]):
                                    try:
                                        parsed3 = _pd.to_datetime(df[col], unit="d", origin="1899-12-30", errors="coerce")
                                        ratio3 = float(parsed3.notna().mean())
                                        if ratio3 > ratio:
                                            ratio = ratio3
                                    except Exception:
                                        pass

                                if ratio > best_ratio:
                                    best_ratio = ratio
                                    best_col = col
                            except Exception:
                                continue
                        if best_col and best_ratio >= 0.5:
                            column_map["date"] = best_col
                            st.info(f"Auto-detected date column: **{best_col}** (parsed {best_ratio*100:.0f}% values)")
                    except Exception:
                        pass

                # Analysis
                kpis = compute_kpis(df, column_map)
                st.session_state.kpis = kpis
                monthly = monthly_trends(df, column_map)
                alerts = smart_alerts(df, column_map, monthly=monthly)
                st.session_state.alerts = alerts

                # Trend analysis - with better date detection
               
                growth = growth_rates(df, column_map)
                top_products, bottom_products = top_bottom_products(df, column_map)
                regions = region_performance(df, column_map)

                st.session_state.monthly = monthly
                st.session_state.growth = growth
                st.session_state.top_products = top_products
                st.session_state.bottom_products = bottom_products
                st.session_state.regions = regions

                # RAG setup
                chunks = build_data_chunks(df, col_types, column_map, kpis, alerts)
                faiss_index, chunk_texts = build_faiss_index(chunks)
                st.session_state.faiss_index = faiss_index
                st.session_state.chunk_texts = chunk_texts

                st.session_state.analysis_done = True
                st.success(f"Analysis complete! **{len(df):,} records** processed.")
                
                # Show date detection / parsing diagnostics
                if column_map.get("date"):
                    parsed_count = 0
                    parsed_min = parsed_max = None
                    try:
                        import pandas as _pd
                        df_check = df.copy()
                        df_check[column_map['date']] = _pd.to_datetime(df_check[column_map['date']], errors='coerce')
                        parsed_count = int(df_check[column_map['date']].notna().sum())
                        if parsed_count > 0:
                            parsed_min = str(df_check[column_map['date']].min())
                            parsed_max = str(df_check[column_map['date']].max())
                    except Exception:
                        pass

                    if len(monthly) > 0:
                        st.info(f"Column detected: **{column_map['date']}** — {len(monthly)} months of data available.")
                    else:
                        if parsed_count > 0:
                            st.warning(
                                f"Column **{column_map['date']}** parsed {parsed_count} values (range: {parsed_min} → {parsed_max}) "
                                "but monthly aggregation produced no results. Check date granularity or column mapping."
                            )
                        else:
                            st.warning("No parsable dates found in the detected date column. Try selecting a different column or reformatting dates.")
                            st.info("Tip: common formats — YYYY-MM-DD, DD/MM/YYYY. For Excel exports, ensure dates are real dates, not text.")
                else:
                    st.warning("No date column detected. Trend analysis will be unavailable.")

                # Show a small parsing preview for debugging
                try:
                    if column_map.get("date") and column_map.get("revenue"):
                        with st.expander("Parsing Preview (first 10 rows)", expanded=False):
                            import pandas as _pd
                            preview = df[[column_map["date"], column_map["revenue"]]].copy()
                            preview["_parsed_date"] = _pd.to_datetime(preview[column_map["date"]], errors="coerce")
                            preview["_revenue_num"] = _pd.to_numeric(preview[column_map["revenue"]], errors="coerce")
                            st.dataframe(preview.head(10))
                except Exception:
                    pass

            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                import traceback
                st.text(traceback.format_exc()[:500])

# ════════════════════════════════════════════════════════════════════════════
# COLUMN MAPPING
# ════════════════════════════════════════════════════════════════════════════

if st.session_state.get("df") is not None and not st.session_state.get("analysis_done"):
    df = st.session_state.df
    st.subheader("Column Mapping")
    st.caption("Review auto-detected column assignments (you can adjust if needed)")
    
    col_options = ["None"] + list(df.columns)
    current_map = st.session_state.get("column_map", {})

    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        date_sel = st.selectbox("Date", col_options,
            index=col_options.index(current_map.get("date", "None")) if current_map.get("date") in col_options else 0,
            help="Required for trend analysis")
    with col2:
        rev_sel = st.selectbox("Revenue", col_options,
            index=col_options.index(current_map.get("revenue", "None")) if current_map.get("revenue") in col_options else 0,
            help="Primary metric")
    with col3:
        product_sel = st.selectbox("Product", col_options,
            index=col_options.index(current_map.get("product", "None")) if current_map.get("product") in col_options else 0)
    with col4:
        region_sel = st.selectbox("Region", col_options,
            index=col_options.index(current_map.get("region", "None")) if current_map.get("region") in col_options else 0)
    with col5:
        qty_sel = st.selectbox("Quantity", col_options,
            index=col_options.index(current_map.get("quantity", "None")) if current_map.get("quantity") in col_options else 0)

    new_map = {}
    if date_sel != "None": new_map["date"] = date_sel
    if rev_sel != "None": new_map["revenue"] = rev_sel
    if product_sel != "None": new_map["product"] = product_sel
    if region_sel != "None": new_map["region"] = region_sel
    if qty_sel != "None": new_map["quantity"] = qty_sel
    st.session_state.column_map = new_map

    # Guidance for date column
    if date_sel == "None":
        st.info("Select a date column to unlock trend analysis, growth rates, and time-based insights.")

# ════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

if st.session_state.get("analysis_done"):
    df = st.session_state.df
    kpis = st.session_state.kpis
    alerts = st.session_state.alerts
    column_map = st.session_state.column_map
    monthly = st.session_state.get("monthly", pd.DataFrame())
    growth = st.session_state.get("growth", pd.DataFrame())
    top_products = st.session_state.get("top_products", pd.DataFrame())
    bottom_products = st.session_state.get("bottom_products", pd.DataFrame())
    regions = st.session_state.get("regions", pd.DataFrame())

    tab_overview, tab_trends, tab_products, tab_regions, tab_summary, tab_chat = st.tabs([
        "Overview", "Trends", "Products", "Regions", "Summary", "Chat"
    ])

    # ── OVERVIEW TAB ────────────────────────────────────────────────────
    with tab_overview:
        st.subheader("Key Performance Indicators")

        def fmt_number(val):
            """Abbreviate large numbers so they never truncate."""
            if val >= 1_000_000:
                return f"PKR {val/1_000_000:.2f}M"
            elif val >= 1_000:
                return f"PKR {val/1_000:.1f}K"
            return f"PKR {val:,.0f}"

        def kpi_card(icon, label, value, delta=None, delta_val=None):
            if delta_val is not None:
                color = "#16a34a" if delta_val >= 0 else "#dc2626"
                arrow = "▲" if delta_val >= 0 else "▼"
                delta_html = f'<div style="font-size:13px;color:{color};margin-top:4px;">{arrow} {delta}</div>'
            else:
                delta_html = ""
            return f"""
            <div style="background:rgba(30,113,69,0.08);border:1px solid rgba(30,113,69,0.25);
                        border-radius:12px;padding:18px 20px;height:110px;
                        display:flex;flex-direction:column;justify-content:space-between;">
                <div style="font-size:12px;color:#6b7280;font-weight:500;text-transform:uppercase;
                            letter-spacing:0.05em;">{icon} {label}</div>
                <div style="font-size:22px;font-weight:700;color:#1e7145;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{value}</div>
                {delta_html}
            </div>"""

        kpi_items = []
        if kpis.get("total_revenue"):
            kpi_items.append(("💰", "Total Revenue", fmt_number(kpis["total_revenue"]), None, None))
        if kpis.get("avg_revenue"):
            kpi_items.append(("📊", "Avg Transaction", fmt_number(kpis["avg_revenue"]), None, None))
        if kpis.get("mom_growth") is not None:
            g = kpis["mom_growth"]
            kpi_items.append(("📈", "MoM Growth", f"{g:+.1f}%", f"{g:+.1f}%", g))
        if kpis.get("total_products"):
            kpi_items.append(("📦", "Products", str(int(kpis["total_products"])), None, None))
        if kpis.get("total_regions"):
            kpi_items.append(("🗺️", "Regions", str(int(kpis["total_regions"])), None, None))
        if kpis.get("total_quantity"):
            v = kpis["total_quantity"]
            kpi_items.append(("🛒", "Units Sold", f"{v/1000:.1f}K" if v >= 1000 else str(int(v)), None, None))

        # Render in rows of 3
        for row_start in range(0, len(kpi_items), 3):
            row = kpi_items[row_start:row_start+3]
            cols = st.columns(len(row))
            for col, (icon, label, value, delta, delta_val) in zip(cols, row):
                with col:
                    st.markdown(kpi_card(icon, label, value, delta, delta_val),
                                unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Alerts
        if alerts:
            st.subheader("Smart Alerts")
            for alert in alerts:
                if alert["type"] == "danger":
                    st.error(f"{alert['icon']} **{alert['title']}** — {alert['message']}")
                elif alert["type"] == "warning":
                    st.warning(f"{alert['icon']} **{alert['title']}** — {alert['message']}")
                else:
                    st.success(f"{alert['icon']} **{alert['title']}** — {alert['message']}")
        else:
            st.subheader("Smart Alerts")
            st.info("No alerts detected.")
            # Diagnostics to help understand why no alerts were raised
            diag = []
            try:
                diag.append(f"Months of data: {len(monthly)}")
                diag.append(f"Growth points: {len(growth)}")
                if not regions.empty:
                    diag.append(f"Top region: {regions.iloc[0]['Region']} ({regions.iloc[0]['Share_%']:.1f}%)")
                if not top_products.empty:
                    diag.append(f"Top product: {top_products.iloc[0]['Product']} (PKR {top_products.iloc[0]['Revenue']:,.0f})")
            except Exception:
                pass
            if diag:
                st.caption(" | ".join(diag))

        st.subheader("Data Preview")
        st.dataframe(df.head(15), use_container_width=True, height=400)
        st.caption(f"{len(df):,} total rows | {len(df.columns)} columns")

    # ── TRENDS TAB ──────────────────────────────────────────────────────
    with tab_trends:
        st.subheader("Revenue Trends")

        if not monthly.empty:
            fig_trend = monthly_trend_chart(monthly)
            if fig_trend:
                st.plotly_chart(fig_trend, use_container_width=True, key="trend_main")
                st.caption(f"{len(monthly)} months of data available")
        else:
            st.info("No date column or insufficient date data. "
                   "Please select a valid date column in the Column Mapping section.")

        if not growth.empty:
            st.subheader("Month-over-Month Growth")
            fig_growth = growth_rate_chart(growth)
            if fig_growth:
                st.plotly_chart(fig_growth, use_container_width=True, key="growth_main")

            col1, col2, col3 = st.columns(3)
            with col1:
                avg_growth = growth["Growth_%"].mean()
                st.metric("Average Growth", f"{avg_growth:+.1f}%")
            with col2:
                best = growth.loc[growth["Growth_%"].idxmax()]
                st.metric("Best Month", best["Month"], f"{best['Growth_%']:+.1f}%")
            with col3:
                worst = growth.loc[growth["Growth_%"].idxmin()]
                st.metric("Worst Month", worst["Month"], f"{worst['Growth_%']:+.1f}%")

            with st.expander("View Growth Data"):
                st.dataframe(growth, use_container_width=True)

    # ── PRODUCTS TAB ────────────────────────────────────────────────────
    with tab_products:
        st.subheader("Product Performance")

        if not top_products.empty:
            col_left, col_right = st.columns(2)
            with col_left:
                fig_top = top_products_chart(top_products, "Top 5 Products")
                if fig_top:
                    st.plotly_chart(fig_top, use_container_width=True, key="top_products")
            with col_right:
                fig_bottom = top_products_chart(bottom_products, "Bottom 5 Products")
                if fig_bottom:
                    st.plotly_chart(fig_bottom, use_container_width=True, key="bottom_products")

            st.subheader("Full Product Breakdown")
            product_col = column_map.get("product")
            rev_col = column_map.get("revenue")
            if product_col and rev_col:
                full_product = df.groupby(product_col)[rev_col].agg(["sum", "mean", "count"]).reset_index()
                full_product.columns = ["Product", "Total Revenue", "Avg Revenue", "Transactions"]
                full_product["Revenue Share %"] = (full_product["Total Revenue"] / full_product["Total Revenue"].sum() * 100).round(1)
                full_product = full_product.sort_values("Total Revenue", ascending=False)
                st.dataframe(full_product, use_container_width=True, height=400)
        else:
            st.info("No product column detected. Please select a Product column in Column Mapping.")

    # ── REGIONS TAB ─────────────────────────────────────────────────────
    with tab_regions:
        st.subheader("Regional Performance")

        if not regions.empty:
            col_left, col_right = st.columns(2)
            with col_left:
                fig_pie = region_pie_chart(regions)
                if fig_pie:
                    st.plotly_chart(fig_pie, use_container_width=True, key="region_pie")
            with col_right:
                fig_bar = region_bar_chart(regions)
                if fig_bar:
                    st.plotly_chart(fig_bar, use_container_width=True, key="region_bar")

            st.subheader("Region Details")
            st.dataframe(regions, use_container_width=True, height=400)

            if not monthly.empty and column_map.get("region") and column_map.get("date") and column_map.get("revenue"):
                st.subheader("Regional Monthly Trends")
                region_col = column_map["region"]
                date_col = column_map["date"]
                rev_col = column_map["revenue"]
                df2 = df.copy()
                df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
                df2 = df2.dropna(subset=[date_col])
                df2["_month"] = df2[date_col].dt.to_period("M").astype(str)
                regional_monthly = df2.groupby(["_month", region_col])[rev_col].sum().reset_index()
                regional_monthly.columns = ["Month", "Region", "Revenue"]
                import plotly.express as px
                # Use green shades for regions
                region_colors = ["#1e7145", "#16a34a", "#059669", "#047857", "#10b981", "#5134d3", "#6ee7b7"]
                fig_rtrend = px.line(
                    regional_monthly,
                    x="Month",
                    y="Revenue",
                    color="Region",
                    title="Regional Monthly Revenue Trends",
                    markers=True,
                    color_discrete_sequence=region_colors,
                )
                fig_rtrend.update_layout(
                    plot_bgcolor="rgba(10, 14, 39, 0.8)",
                    paper_bgcolor="rgba(10, 14, 39, 0.8)",
                    font=dict(color="#e8f0f5", size=12),
                    title_font_color="#e8f0f5",
                    xaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color="#e8f0f5")),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color="#e8f0f5")),
                    hovermode="x unified",
                    legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#1e7145", borderwidth=1),
                )
                fig_rtrend.update_traces(line=dict(width=2.5), marker=dict(size=6))
                st.plotly_chart(fig_rtrend, use_container_width=True, key="region_trends")
        else:
            st.info("No region column detected. Please select a Region column in Column Mapping.")

    # ── SUMMARY TAB ─────────────────────────────────────────────────────
    with tab_summary:
        st.subheader("AI Executive Summary")
        st.caption("**Powered by Groq LLaMA** — Situation, Complication, Resolution")

        if not st.session_state.api_key_valid:
            st.error("API Key not configured. See sidebar for setup instructions.")
        else:
            def on_summary_click():
                """Callback to keep Summary tab active"""
                st.session_state.selected_tab = 4

            if st.button("Generate Executive Summary", type="primary", on_click=on_summary_click):
                with st.spinner("AI analyst generating summary..."):
                    try:
                        summary = generate_executive_summary(
                            kpis, alerts, monthly, top_products, regions,
                            language=st.session_state.language,
                        )
                        st.session_state.executive_summary = summary
                        st.session_state.selected_tab = 4  # Ensure Summary tab stays active
                    except Exception as e:
                        st.error(f"Error generating summary: {str(e)}")

        if st.session_state.get("executive_summary"):
            st.markdown(st.session_state.executive_summary)
            st.divider()

            st.subheader("Story Feed")
            story_cols = st.columns(2)

            with story_cols[0]:
                st.markdown("#### Revenue Performance")
                if kpis.get("total_revenue"):
                    rev = kpis["total_revenue"]
                    st.info(f"Total revenue: **PKR {rev:,.0f}**")
                if kpis.get("mom_growth") is not None:
                    g = kpis["mom_growth"]
                    msg = f"Month-over-month: **{g:+.1f}%**"
                    if g > 0:
                        st.success(msg)
                    else:
                        st.error(msg)
                if not monthly.empty:
                    fig = monthly_trend_chart(monthly)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key="trend_story")

            with story_cols[1]:
                st.markdown("#### Product & Region Insights")
                if not top_products.empty:
                    best = top_products.iloc[0]
                    st.success(f"**{best['Product']}** — PKR {best['Revenue']:,.0f}")
                if not regions.empty:
                    top_region = regions.iloc[0]
                    st.info(f"**{top_region['Region']}** — {top_region['Share_%']:.1f}% of revenue")
                if not regions.empty:
                    fig = region_pie_chart(regions)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key="region_pie_story")

    # ── CHAT TAB ────────────────────────────────────────────────────────
    with tab_chat:
        st.subheader("Chat with Your Data")

        if not st.session_state.api_key_valid:
            st.error("API Key not configured. See sidebar for setup instructions.")
        else:
            lang = st.session_state.language
            placeholder = (
                "Apna sawal poochein... (e.g. 'Kaunsa product best hai?')"
                if lang == "Roman Urdu"
                else "Ask anything about your data... (e.g. 'Why are sales dropping?')"
            )

            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            if prompt := st.chat_input(placeholder):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
                        try:
                            rag_context = semantic_search(
                                prompt,
                                st.session_state.faiss_index,
                                st.session_state.chunk_texts,
                                k=5
                            )
                            response = qa_agent(
                                question=prompt,
                                df=df,
                                column_map=column_map,
                                rag_context=rag_context,
                                chat_history=st.session_state.chat_history[:-1],
                                language=lang
                            )
                            st.markdown(response)
                            st.session_state.chat_history.append({"role": "assistant", "content": response})
                        except Exception as e:
                            err_msg = f"Error: {str(e)}"
                            st.error(err_msg)
                            st.session_state.chat_history.append({"role": "assistant", "content": err_msg})

            if st.session_state.chat_history:
                if st.button("Clear Chat"):
                    st.session_state.chat_history = []
                    st.rerun()

            st.divider()
            st.subheader("Quick Questions")
            quick_questions = [
                "What is the overall revenue trend?",
                "Which product generates the most revenue?",
                "Which region is underperforming?",
                "What are the top business risks?",
                "Give me 5 growth recommendations.",
            ]
            q_cols = st.columns(min(3, len(quick_questions)))
            for i, q in enumerate(quick_questions):
                with q_cols[i % len(q_cols)]:
                    if st.button(q, key=f"quick_{i}", use_container_width=True):
                        st.session_state.chat_history.append({"role": "user", "content": q})
                        with st.spinner("Analyzing..."):
                            try:
                                rag_context = semantic_search(q, st.session_state.faiss_index, st.session_state.chunk_texts, k=4)
                                response = qa_agent(q, df, column_map, rag_context, st.session_state.chat_history[:-1], language=lang)
                                st.session_state.chat_history.append({"role": "assistant", "content": response})
                            except Exception as e:
                                st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {str(e)}"})  
                        

# ════════════════════════════════════════════════════════════════════════════
# LANDING PAGE
# ════════════════════════════════════════════════════════════════════════════

else:
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        st.title("BazaarAI")
        st.subheader("AI-Powered Sales Analytics for Pakistani Businesses")
        
        st.markdown("""
### Get Started in 3 Steps

**1. Upload Data** — CSV or Excel file with your sales data
**2. Map Columns** — Auto-detect date, revenue, product, region columns
**3. Get Insights** — AI-powered analysis, trends, and recommendations

### Key Features

- **Auto Column Detection** — Automatically identifies date, numeric, and categorical fields
- **Smart KPIs** — Revenue totals, growth rates, month-over-month trends
- **Smart Alerts** — Sales decline warnings, concentration risks, growth opportunities
- **AI Insights** — Groq LLaMA-powered executive summaries using SCR framework
- **Data Chat** — Ask natural language questions about your data
- **Regional Analysis** — Performance by geography and product
- **Bilingual** — English and Roman Urdu support

        """)
    
   
