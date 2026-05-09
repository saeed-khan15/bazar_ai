import pandas as pd
import numpy as np
import io
import re
from datetime import datetime


def load_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file format. Please upload CSV or Excel.")
    return df


def normalize_column_names(df):
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9_]", "_", col.strip().lower().replace(" ", "_"))
        for col in df.columns
    ]
    df.columns = [re.sub(r"_+", "_", col).strip("_") for col in df.columns]
    return df


def detect_column_types(df):
    col_types = {}
    for col in df.columns:
        sample = df[col].dropna()
        if len(sample) == 0:
            col_types[col] = "unknown"
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            col_types[col] = "date"
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            col_types[col] = "numeric"
            continue
        if len(sample) > 0:
            try:
                # FIXED: infer_datetime_format removed in pandas 2.2 — omit it (it's the default)
                parsed = pd.to_datetime(sample.iloc[:min(20, len(sample))], errors="coerce")
                if parsed.notna().mean() > 0.7:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    col_types[col] = "date"
                    continue
            except Exception:
                pass
        n_unique = df[col].nunique()
        n_total = len(df[col].dropna())
        if n_unique / max(n_total, 1) < 0.3 or n_unique <= 30:
            col_types[col] = "categorical"
        else:
            col_types[col] = "text"
    return col_types, df


def handle_missing_values(df, col_types):
    df = df.copy()
    for col, ctype in col_types.items():
        if ctype == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val if not pd.isna(median_val) else 0)
        elif ctype == "categorical":
            df[col] = df[col].fillna("Unknown")
        elif ctype == "date":
            pass
        else:
            df[col] = df[col].fillna("")
    return df


def auto_map_columns(df, col_types):
    mapping = {"date": None, "revenue": None, "product": None, "region": None, "quantity": None}
    date_keywords = ["date", "time", "month", "year", "day", "period", "tarikh"]
    revenue_keywords = ["revenue", "sales", "amount", "income", "total", "price", "value", "bikri", "amdani", "rasid"]
    product_keywords = ["product", "item", "goods", "category", "type", "naam", "mal", "product_name"]
    region_keywords = ["region", "city", "area", "location", "zone", "state", "province", "shehar", "علاقہ"]
    quantity_keywords = ["quantity", "qty", "units", "count", "sold", "tedad"]

    def best_match(keywords, eligible_cols):
        for kw in keywords:
            for col in eligible_cols:
                if kw in col.lower():
                    return col
        return None

    date_cols = [c for c, t in col_types.items() if t == "date"]
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    cat_cols = [c for c, t in col_types.items() if t == "categorical"]

    mapping["date"] = best_match(date_keywords, date_cols) or (date_cols[0] if date_cols else None)
    mapping["revenue"] = best_match(revenue_keywords, numeric_cols) or (numeric_cols[0] if numeric_cols else None)
    mapping["quantity"] = best_match(quantity_keywords, numeric_cols)
    mapping["product"] = best_match(product_keywords, cat_cols) or (cat_cols[0] if cat_cols else None)
    mapping["region"] = best_match(region_keywords, cat_cols) or (cat_cols[1] if len(cat_cols) > 1 else None)

    return {k: v for k, v in mapping.items() if v is not None}


def get_data_summary(df, col_types, column_map):
    lines = []
    lines.append(f"Dataset has {len(df)} rows and {len(df.columns)} columns.")
    lines.append(f"Columns: {', '.join(df.columns.tolist())}")

    for col, ctype in col_types.items():
        if ctype == "numeric":
            lines.append(f"  - {col} (numeric): min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")
        elif ctype == "categorical":
            top = df[col].value_counts().head(5).index.tolist()
            lines.append(f"  - {col} (categorical): {len(df[col].unique())} unique values. Top: {', '.join(str(v) for v in top)}")
        elif ctype == "date":
            valid = df[col].dropna()
            if len(valid) > 0:
                lines.append(f"  - {col} (date): from {valid.min()} to {valid.max()}")

    if column_map.get("revenue"):
        total = df[column_map["revenue"]].sum()
        lines.append(f"Total {column_map['revenue']}: {total:,.2f}")

    return "\n".join(lines)


def clean_dataframe(uploaded_file):
    df = load_file(uploaded_file)
    df = normalize_column_names(df)
    col_types, df = detect_column_types(df)
    df = handle_missing_values(df, col_types)
    column_map = auto_map_columns(df, col_types)
    return df, col_types, column_map
