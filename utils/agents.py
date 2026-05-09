# utils/agents.py
import os
import pandas as pd
import numpy as np
from groq import Groq

MODEL = "llama-3.3-70b-versatile"

_client = None
_cached_key = None  # FIXED: track which key the client was built with
_api_key_error = None


def get_client():
    """
    Get or create Groq client.
    FIXED: previously cached _client globally with no key check — if a user
    entered a wrong key, got an error, then entered the correct key, the old
    broken client was returned forever. Now we rebuild whenever the key changes.
    """
    global _client, _cached_key, _api_key_error

    api_key = os.environ.get("GROQ_API_KEY", "").strip()

    if not api_key:
        _api_key_error = "GROQ_API_KEY environment variable is not set"
        raise ValueError(_api_key_error)

    # Return cached client only if the key hasn't changed
    if _client is not None and _cached_key == api_key:
        return _client

    try:
        _client = Groq(api_key=api_key)
        _cached_key = api_key
        _api_key_error = None
        return _client
    except Exception as e:
        _client = None
        _cached_key = None
        _api_key_error = str(e)
        raise


def check_api_key_valid():
    """Check if API key is configured and return (is_valid, error_message)."""
    try:
        get_client()
        return True, None
    except Exception as e:
        return False, str(e)


def _call_groq(system_prompt, user_prompt, max_tokens=1024):
    """Call Groq API with error handling. Timeout reduced to 15s for better UX."""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.4,
            timeout=15.0  # Reduced from 30s — 30s spinner looks like a crash
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            raise ValueError(f"Invalid Groq API Key. Please check your key in Streamlit secrets. Error: {error_msg}")
        elif "timeout" in error_msg.lower():
            raise ValueError("Groq API request timed out after 15s. Please try again.")
        else:
            raise ValueError(f"Error calling Groq API: {error_msg}")


def analyst_agent(df, column_map, question, language="English"):
    rev_col = column_map.get("revenue")
    date_col = column_map.get("date")
    product_col = column_map.get("product")
    region_col = column_map.get("region")

    stats_lines = []
    if rev_col:
        stats_lines.append(f"Total {rev_col}: {df[rev_col].sum():,.2f}")
        stats_lines.append(f"Average {rev_col}: {df[rev_col].mean():,.2f}")
    if product_col and rev_col:
        top_products = df.groupby(product_col)[rev_col].sum().nlargest(5).to_dict()
        stats_lines.append(f"Top products: {top_products}")
    if region_col and rev_col:
        by_region = df.groupby(region_col)[rev_col].sum().to_dict()
        stats_lines.append(f"Revenue by region: {by_region}")
    if date_col and rev_col:
        df2 = df.copy()
        df2[date_col] = pd.to_datetime(df2[date_col], errors="coerce")
        df2 = df2.dropna(subset=[date_col])
        if len(df2) > 0:
            monthly = df2.groupby(df2[date_col].dt.to_period("M"))[rev_col].sum().tail(6).to_dict()
            stats_lines.append(f"Last 6 months: {monthly}")

    data_context = "\n".join(stats_lines)

    if language == "Roman Urdu":
        lang_instruction = (
            "Respond ONLY in Roman Urdu (Urdu written using Latin letters). Do NOT use Urdu/Arabic script. "
            "Keep it short, natural, and idiomatic (examples: 'Sales barh gai hain', 'Revenue kam ho raha hai'). "
            "Do not include an English translation."
        )
    else:
        lang_instruction = "Respond in clear English."

    system = f"""You are an expert AI business analyst specializing in Pakistani businesses.
You have access to sales data statistics. Provide data-driven, actionable insights.
{lang_instruction}
Always refer to specific numbers from the data. Be concise but insightful."""

    user = f"""Data Statistics:
{data_context}

Question: {question}

Provide a precise, data-driven answer using the statistics above."""

    return _call_groq(system, user, max_tokens=800)


def narrator_agent(analysis_data, language="English"):
    if language == "Roman Urdu":
        lang_instruction = (
            "Write ONLY in Roman Urdu (Latin script). Avoid Arabic/Urdu script. Use natural transliteration examples: "
            "'Sales barh gai hain', 'Faisla isi mahine lena chahiye'. Do not add English translation."
        )
    else:
        lang_instruction = "Write in professional English."

    system = f"""You are a business narrator that converts data analysis into compelling business stories.
Use the SCR framework: Situation → Complication → Resolution.
{lang_instruction}
Be specific with numbers. Focus on actionable insights for Pakistani business owners."""

    user = f"""Here is the business analysis data:
{analysis_data}

Create a structured executive narrative using:
1. **Situation**: What does the data show about the current state?
2. **Complication**: What challenges or risks are present?
3. **Resolution**: What actions should the business take?

Be specific, reference actual numbers, and provide 3-5 actionable recommendations."""

    return _call_groq(system, user, max_tokens=1000)


def qa_agent(question, df, column_map, rag_context, chat_history, language="English"):
    if language == "Roman Urdu":
        lang_instruction = (
            "Respond ONLY in Roman Urdu (Latin letters). Do NOT use Arabic/Urdu script. Keep replies concise and use idiomatic Roman Urdu. "
            "Examples: 'Kaunsa product sab se acha hai?', 'Sales kam ho rahi hain'."
        )
    else:
        lang_instruction = "Respond in clear, professional English."

    history_text = ""
    if chat_history:
        recent = chat_history[-4:]
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent])

    rev_col = column_map.get("revenue")
    quick_stats = ""
    if rev_col:
        quick_stats = f"Total revenue: {df[rev_col].sum():,.0f} | Mean: {df[rev_col].mean():,.0f} | Rows: {len(df)}"

    context_text = "\n".join(rag_context) if rag_context else "No specific context retrieved."

    system = f"""You are BazaarAI, an expert AI data analyst for Pakistani businesses.
You answer questions about uploaded business data conversationally but precisely.
{lang_instruction}

Always:
- Reference specific numbers from the data
- Give actionable business advice
- Be concise (3-6 sentences unless detail is needed)
- If asked about trends, mention specific months/products/regions"""

    user = f"""Relevant Data Context:
{context_text}

Quick Stats: {quick_stats}

Recent Conversation:
{history_text}

User Question: {question}

Answer the question accurately using the data context and stats."""

    return _call_groq(system, user, max_tokens=700)


def generate_executive_summary(kpis, alerts, monthly_df, top_products, regions, language="English"):
    if language == "Roman Urdu":
        lang_instruction = (
            "Write the executive summary ONLY in Roman Urdu (use Latin characters). Do NOT include Urdu script or English translations. "
            "Be concise, use clear transliteration (e.g., 'Revenue barh raha hai', 'Customer retention kam hai')."
        )
    else:
        lang_instruction = "Write in professional English."

    kpi_text = "\n".join([f"- {k}: {v:,.2f}" if isinstance(v, (int, float)) else f"- {k}: {v}"
                          for k, v in kpis.items()])
    alerts_text = "\n".join([f"- {a['title']}: {a['message']}" for a in alerts]) if alerts else "No critical alerts."
    products_text = top_products.to_string(index=False) if not top_products.empty else "No product data."
    regions_text = regions.to_string(index=False) if not regions.empty else "No region data."

    system = f"""You are BazaarAI — a senior AI business analyst for Pakistani businesses.
Generate a concise executive summary in markdown format.
{lang_instruction}"""

    user = f"""KPIs:
{kpi_text}

Alerts:
{alerts_text}

Top Products:
{products_text}

Regional Performance:
{regions_text}

Generate a markdown executive summary with:
## Executive Summary
- 2-3 paragraph overview of business performance
- Key metrics highlighted in **bold**
- 3-5 strategic recommendations as bullet points
- Overall business health rating (Excellent/Good/Needs Attention/Critical)"""

    return _call_groq(system, user, max_tokens=900)
