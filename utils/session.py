import streamlit as st
import uuid
from datetime import datetime, timedelta


SESSION_TTL_HOURS = 24


def init_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.upload_timestamp = None
        st.session_state.df = None
        st.session_state.column_map = {}
        st.session_state.analysis_done = False
        st.session_state.faiss_index = None
        st.session_state.chunk_texts = []
        st.session_state.chat_history = []
        st.session_state.language = "English"
        st.session_state.kpis = {}
        st.session_state.alerts = []
        st.session_state.api_key_valid = None
        st.session_state.api_key_error = None
        st.session_state.executive_summary = None


def check_session_expiry():
    if st.session_state.get("upload_timestamp") is None:
        return False
    expiry = st.session_state.upload_timestamp + timedelta(hours=SESSION_TTL_HOURS)
    if datetime.now() > expiry:
        reset_session()
        return True
    return False


def reset_session():
    st.session_state.upload_timestamp = None
    st.session_state.df = None
    st.session_state.column_map = {}
    st.session_state.analysis_done = False
    st.session_state.faiss_index = None
    st.session_state.chunk_texts = []
    st.session_state.chat_history = []
    st.session_state.kpis = {}
    st.session_state.alerts = []


def get_session_info():
    if st.session_state.get("upload_timestamp"):
        expiry = st.session_state.upload_timestamp + timedelta(hours=SESSION_TTL_HOURS)
        remaining = expiry - datetime.now()
        hours_left = max(0, int(remaining.total_seconds() // 3600))
        minutes_left = max(0, int((remaining.total_seconds() % 3600) // 60))
        return f"{hours_left}h {minutes_left}m remaining"
    return None
