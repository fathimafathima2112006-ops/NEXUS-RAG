import streamlit as st
from src.auth.auth_ui import render_auth
from src.ui.dashboard import render_dashboard

st.set_page_config(
    page_title="NEXUS RAG",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    render_auth()
else:
    render_dashboard()
