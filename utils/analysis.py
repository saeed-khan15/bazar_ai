import pandas as pd
import numpy as np


def compute_kpis(df, column_map):
    kpis = {}
    rev_col = column_map.get("revenue")
    date_col = column_map.get("date")
    product_col = column_map.get("product")
    region_col = column_map.get("region")
    qty_col = column_map.get("quantity")

    if rev_col:
        kpis["total_revenue"] = df[rev_col].sum()
        kpis["avg_revenue"] = df[rev_col].mean()
        kpis["max_revenue"] = df[rev_col].max()

    if qty_col:
        kpis["total_quantity"] = df[qty_col].sum()

    if product_col:
        kpis["total_products"] = df[product_col].nunique()

    if region_col:
        kpis["total_regions"] = df[region_col].nunique()

    if date_col and rev_col:
        df_dated = df.dropna(subset=[date_col]).copy()
        df_dated[date_col] = pd.to_datetime(df_dated[date_col], errors="coerce")
        df_dated = df_dated.dropna(subset=[date_col])
        if len(df_dated) > 0:
            df_dated["_month"] = df_dated[date_col].dt.to_period("M")
            monthly = df_dated.groupby("_month")[rev_col].sum().sort_index()
            if len(monthly) >= 2:
                last_month = monthly.iloc[-1]
                prev_month = monthly.iloc[-2]
                if prev_month > 0:
                    kpis["mom_growth"] = ((last_month - prev_month) / prev_month) * 100
                kpis["last_month_revenue"] = last_month

    return kpis


def monthly_trends(df, column_map):
    date_col = column_map.get("date")
    rev_col = column_map.get("revenue")
    if not date_col or not rev_col:
        return pd.DataFrame()
    # Initial attempt: normal datetime parsing
    df2 = df.dropna(subset=[date_col]).copy()
    # Try parse with default settings
    df2["_parsed"] = pd.to_datetime(df2[date_col], errors="coerce")

    # If no valid parsed dates, try dayfirst parsing
    if df2["_parsed"].notna().sum() == 0:
        df2["_parsed"] = pd.to_datetime(df2[date_col], dayfirst=True, errors="coerce")

    # If still none, and column is numeric (Excel serials), try Excel epoch fallback
    if df2["_parsed"].notna().sum() == 0 and pd.api.types.is_numeric_dtype(df2[date_col]):
        try:
            df2["_parsed"] = pd.to_datetime(df2[date_col], unit="d", origin="1899-12-30", errors="coerce")
        except Exception:
            pass

    # Final cleanup
    df2 = df2.dropna(subset=["_parsed"])
    if len(df2) == 0:
        return pd.DataFrame()

    df2["_month"] = df2["_parsed"].dt.to_period("M")
    monthly = df2.groupby("_month")[rev_col].sum().reset_index()
    monthly.columns = ["Month", "Revenue"]
    monthly["Month"] = monthly["Month"].astype(str)
    return monthly


def growth_rates(df, column_map):
    monthly = monthly_trends(df, column_map)
    if monthly.empty or len(monthly) < 2:
        return pd.DataFrame()

    monthly = monthly.copy()
    monthly["Growth_%"] = monthly["Revenue"].pct_change() * 100
    monthly["6M_Avg_Growth"] = monthly["Growth_%"].rolling(6).mean()
    return monthly.dropna(subset=["Growth_%"])


def top_bottom_products(df, column_map, n=5):
    product_col = column_map.get("product")
    rev_col = column_map.get("revenue")
    if not product_col or not rev_col:
        return pd.DataFrame(), pd.DataFrame()

    by_product = df.groupby(product_col)[rev_col].sum().reset_index()
    by_product.columns = ["Product", "Revenue"]
    by_product = by_product.sort_values("Revenue", ascending=False)

    top = by_product.head(n).reset_index(drop=True)
    bottom = by_product.tail(n).reset_index(drop=True)
    return top, bottom


def region_performance(df, column_map):
    region_col = column_map.get("region")
    rev_col = column_map.get("revenue")
    if not region_col or not rev_col:
        return pd.DataFrame()

    by_region = df.groupby(region_col)[rev_col].sum().reset_index()
    by_region.columns = ["Region", "Revenue"]
    by_region = by_region.sort_values("Revenue", ascending=False).reset_index(drop=True)
    by_region["Share_%"] = (by_region["Revenue"] / by_region["Revenue"].sum() * 100).round(2)
    return by_region


def smart_alerts(df, column_map, monthly=None):
    alerts = []
    rev_col = column_map.get("revenue")
    date_col = column_map.get("date")
    product_col = column_map.get("product")
    region_col = column_map.get("region")
    # Work on a numeric-safe copy to avoid string/format issues in revenue sums
    df_work = df.copy()
    if rev_col and rev_col in df_work.columns:
        df_work[rev_col] = pd.to_numeric(df_work[rev_col], errors="coerce").fillna(0)

      if date_col and rev_col:
        if monthly is None:
            monthly = monthly_trends(df_work, column_map)
        if len(monthly) >= 2:
            last = monthly.iloc[-1]["Revenue"]
            prev = monthly.iloc[-2]["Revenue"]
            if prev > 0:
                change = (last - prev) / prev * 100
                if change <= -30:
                    alerts.append({
                        "type": "danger",
                        "icon": "🚨",
                        "title": "Sharp Revenue Decline",
                        "message": f"Revenue dropped {abs(change):.1f}% last month. Immediate attention required."
                    })
                elif change <= -10:
                    alerts.append({
                        "type": "warning",
                        "icon": "⚠️",
                        "title": "Revenue Decline",
                        "message": f"Revenue declined {abs(change):.1f}% compared to previous month."
                    })
                elif change >= 20:
                    alerts.append({
                        "type": "success",
                        "icon": "📈",
                        "title": "Strong Growth",
                        "message": f"Revenue grew {change:.1f}% last month. Strong momentum!"
                    })

    if region_col and rev_col:
        by_region = region_performance(df_work, column_map)
        if len(by_region) > 0:
            top_share = by_region.iloc[0]["Share_%"]
            top_region = by_region.iloc[0]["Region"]
            if top_share > 60:
                alerts.append({
                    "type": "warning",
                    "icon": "⚠️",
                    "title": "Region Concentration Risk",
                    "message": f"{top_region} accounts for {top_share:.1f}% of revenue. High geographic dependency."
                })

    if product_col and rev_col:
        top, _ = top_bottom_products(df_work, column_map, n=1)
        if len(top) > 0:
            total_rev = df[rev_col].sum()
            if total_rev > 0:
                top_share = top.iloc[0]["Revenue"] / total_rev * 100
                top_product = top.iloc[0]["Product"]
                if top_share > 50:
                    alerts.append({
                        "type": "warning",
                        "icon": "⚠️",
                        "title": "Product Concentration Risk",
                        "message": f"'{top_product}' drives {top_share:.1f}% of revenue. Diversification advised."
                    })

    if date_col and rev_col:
        growth = growth_rates(df_work, column_map)
        if len(growth) >= 6:
            recent_avg = growth.tail(3)["Growth_%"].mean()
            if recent_avg > 10:
                alerts.append({
                    "type": "success",
                    "icon": "🚀",
                    "title": "Growth Opportunity",
                    "message": f"Average 3-month growth is {recent_avg:.1f}%. Good time to expand."
                })

    return alerts


def build_data_chunks(df, col_types, column_map, kpis, alerts):
    chunks = []

    summary_lines = [f"Business dataset with {len(df)} records and {len(df.columns)} columns."]
    if kpis.get("total_revenue"):
        summary_lines.append(f"Total revenue: {kpis['total_revenue']:,.0f}")
    if kpis.get("mom_growth") is not None:
        summary_lines.append(f"Month-over-month growth: {kpis['mom_growth']:.1f}%")
    chunks.append("SUMMARY: " + " ".join(summary_lines))

    monthly = monthly_trends(df, column_map)
    if not monthly.empty:
        top3 = monthly.nlargest(3, "Revenue")[["Month", "Revenue"]].to_dict("records")
        desc = "MONTHLY TRENDS: " + "; ".join([f"{r['Month']}: {r['Revenue']:,.0f}" for r in top3])
        chunks.append(desc)

    top, bottom = top_bottom_products(df, column_map)
    if not top.empty:
        chunks.append("TOP PRODUCTS: " + ", ".join([f"{r['Product']} ({r['Revenue']:,.0f})" for _, r in top.iterrows()]))
    if not bottom.empty:
        chunks.append("BOTTOM PRODUCTS: " + ", ".join([f"{r['Product']} ({r['Revenue']:,.0f})" for _, r in bottom.iterrows()]))

    regions = region_performance(df, column_map)
    if not regions.empty:
        chunks.append("REGION PERFORMANCE: " + ", ".join([f"{r['Region']} {r['Share_%']:.1f}%" for _, r in regions.iterrows()]))

    if alerts:
        chunks.append("ALERTS: " + "; ".join([a["message"] for a in alerts]))

    rev_col = column_map.get("revenue")
    if rev_col:
        stats = df[rev_col].describe()
        chunks.append(f"REVENUE STATS: mean={stats['mean']:,.0f}, median={df[rev_col].median():,.0f}, std={stats['std']:,.0f}")

    for col, ctype in col_types.items():
        if ctype == "categorical" and col in df.columns:
            vc = df[col].value_counts().head(5)
            chunks.append(f"COLUMN {col.upper()}: " + ", ".join([f"{k}={v}" for k, v in vc.items()]))

    return chunks
