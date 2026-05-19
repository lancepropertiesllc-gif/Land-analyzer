"""
utils/auth.py — Client authentication and session management
"""
import yaml
import hashlib
import streamlit as st
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "clients.yaml"


def load_clients() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f).get("clients", {})


def check_password(client_key: str, password: str, clients: dict) -> bool:
    client = clients.get(client_key, {})
    return client.get("password", "") == password


def login_screen():
    """Render login screen and return (client_key, client_config) or None."""
    clients = load_clients()

    st.markdown("""
    <div style='text-align:center;padding:60px 0 20px'>
        <h1 style='font-size:2.2rem;font-weight:700;color:#1f2937'>
            🏗️ Land Finder
        </h1>
        <p style='color:#6b7280;font-size:1.1rem'>
            Builder Intelligence Platform
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Sign In")
        client_options = {v["name"]: k for k, v in clients.items()}
        selected_name = st.selectbox("Select your account", list(client_options.keys()))
        password = st.text_input("Password", type="password")

        if st.button("Sign In", use_container_width=True, type="primary"):
            client_key = client_options[selected_name]
            if check_password(client_key, password, clients):
                st.session_state["authenticated"] = True
                st.session_state["client_key"]    = client_key
                st.session_state["client"]         = clients[client_key]
                st.rerun()
            else:
                st.error("Incorrect password")

        st.markdown("""
        <p style='text-align:center;color:#9ca3af;font-size:0.85rem;margin-top:16px'>
            Contact your consultant to reset your password
        </p>
        """, unsafe_allow_html=True)


def require_auth():
    """Call at top of every page. Returns client config or stops execution."""
    if not st.session_state.get("authenticated"):
        login_screen()
        st.stop()
    return st.session_state["client"]


def is_admin() -> bool:
    return st.session_state.get("client", {}).get("role") == "admin"


def get_client_criteria() -> dict:
    return st.session_state.get("client", {}).get("criteria", {})


def logout():
    for key in ["authenticated", "client_key", "client", "leads_df"]:
        st.session_state.pop(key, None)
    st.rerun()
