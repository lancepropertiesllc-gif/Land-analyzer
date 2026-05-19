"""
app.py — Land Finder Dashboard
Multi-client builder intelligence platform
Run: streamlit run app.py
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Land Finder",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide default Streamlit menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #111827;
    }
    section[data-testid="stSidebar"] * {
        color: #f9fafb !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #9ca3af !important;
        font-size: 0.85rem !important;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 6px 6px 0 0;
        font-weight: 500;
    }

    /* Button styling */
    .stButton button[kind="primary"] {
        background: #1d4ed8;
        border: none;
    }

    /* Data table */
    .stDataFrame {font-size: 13px;}

    /* Tier badge colors */
    .tier-hot  {color: #dc2626; font-weight: 700;}
    .tier-warm {color: #ea580c; font-weight: 700;}
    .tier-cool {color: #2563eb; font-weight: 700;}
    .tier-cold {color: #6b7280;}
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
from utils.auth import require_auth, logout, is_admin

client = require_auth()
client_name = client.get("name", "User")
client_color = client.get("color", "#1d4ed8")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='padding:16px 0 8px'>
        <div style='font-size:1.4rem;font-weight:700'>🏗️ Land Finder</div>
        <div style='font-size:0.85rem;opacity:.7;margin-top:2px'>
            Builder Intelligence Platform
        </div>
    </div>
    <div style='background:{client_color};border-radius:6px;
                padding:8px 12px;margin:8px 0 16px'>
        <div style='font-size:0.8rem;opacity:.8'>Signed in as</div>
        <div style='font-weight:600'>{client_name}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    st.markdown("**Navigation**")
    page = st.radio(
        "Go to",
        ["📊 Overview", "🗺️ Map", "📋 Leads", "⚙️ Criteria"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Data source selector
    st.markdown("**Data Source**")
    data_source = st.selectbox(
        "Load leads from",
        ["Upload CSV", "Google Drive Link", "Live GIS Pull"],
        label_visibility="collapsed"
    )

    if data_source == "Upload CSV":
        uploaded = st.file_uploader(
            "Upload private_leads.csv",
            type=["csv"],
            label_visibility="collapsed"
        )
        if uploaded and "leads_df" not in st.session_state:
            from utils.data_loader import load_from_upload
            with st.spinner("Loading..."):
                st.session_state["leads_df"] = load_from_upload(uploaded)
            st.success(f"Loaded {len(st.session_state['leads_df']):,} leads")

    elif data_source == "Google Drive Link":
        drive_url = st.text_input(
            "Paste Google Drive share link",
            placeholder="https://drive.google.com/file/d/...",
            label_visibility="collapsed"
        )
        if st.button("Load from Drive", use_container_width=True):
            from utils.data_loader import load_from_drive
            with st.spinner("Fetching from Google Drive..."):
                st.session_state["leads_df"] = load_from_drive(drive_url)
            if not st.session_state["leads_df"].empty:
                st.success(f"Loaded {len(st.session_state['leads_df']):,} leads")

    elif data_source == "Live GIS Pull":
        municipality = st.text_input("Municipality", value="Ballwin")
        school_dist  = st.text_input("School District", value="ROCKWOOD")
        if st.button("Pull Live Data", use_container_width=True, type="primary"):
            from utils.data_loader import load_from_gis
            progress_text = st.empty()
            def progress_cb(n):
                progress_text.text(f"Fetched {n:,} parcels...")
            with st.spinner("Pulling from STL County GIS..."):
                st.session_state["leads_df"] = load_from_gis(
                    municipality=municipality,
                    school_district=school_dist,
                    progress_callback=progress_cb,
                )
            progress_text.empty()
            if not st.session_state["leads_df"].empty:
                st.success(f"Loaded {len(st.session_state['leads_df']):,} parcels")

    st.markdown("---")

    if st.button("Sign Out", use_container_width=True):
        logout()

# ── Load and apply client criteria ────────────────────────────────────────────
from utils.data_loader import apply_client_filters

raw_df = st.session_state.get("leads_df", None)
criteria = client.get("criteria", {})

if raw_df is not None and not raw_df.empty:
    # Admin sees everything; clients see filtered view
    if is_admin():
        df = raw_df.copy()
    else:
        df = apply_client_filters(raw_df, criteria)
else:
    df = None

# ── Route to pages ────────────────────────────────────────────────────────────
if page == "📊 Overview":
    from pages.overview import render
    render(df, client)

elif page == "🗺️ Map":
    from pages.map_view import render
    render(df, client)

elif page == "📋 Leads":
    from pages.lead_table import render
    render(df, client)

elif page == "⚙️ Criteria":
    from pages.criteria import render
    render(df, client, raw_df)
