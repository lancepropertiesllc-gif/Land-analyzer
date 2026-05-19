"""
app.py — Land Finder Dashboard
Run: streamlit run app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Land Finder",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
    .stApp {background: #f8fafc;}

    section[data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {color: #cbd5e1 !important;}
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        background: #1e293b !important;
        color: #f1f5f9 !important;
        border-color: #334155 !important;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
    }

    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="metric-container"] label {
        color: #64748b !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    h1 {color: #0f172a !important; font-weight: 700 !important; font-size: 1.6rem !important;}
    h2, h3 {color: #1e293b !important; font-weight: 600 !important;}

    .stTabs [data-baseweb="tab-list"] {
        gap: 2px; background: #f1f5f9; padding: 4px; border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px; border-radius: 6px; font-weight: 500;
        font-size: 0.9rem; color: #64748b; background: transparent; border: none;
    }
    .stTabs [aria-selected="true"] {
        background: white !important; color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .stButton > button {border-radius: 8px; font-weight: 500;}
    .stButton > button[kind="primary"] {background: #1d4ed8; border: none; color: white;}
    .stButton > button[kind="primary"]:hover {background: #1e40af;}
    .stDataFrame {border-radius: 8px; border: 1px solid #e2e8f0;}
    .streamlit-expanderHeader {font-weight: 600 !important; background: white; border-radius: 8px;}
    hr {border-color: #e2e8f0 !important;}
    .stAlert {border-radius: 8px !important;}
</style>
""", unsafe_allow_html=True)

from utils.auth import require_auth, logout, is_admin
client = require_auth()
client_name  = client.get("name", "User")
client_color = client.get("color", "#1d4ed8")

with st.sidebar:
    st.markdown(f"""
    <div style='padding:20px 4px 12px'>
        <div style='font-size:1.3rem;font-weight:800;color:#f8fafc;letter-spacing:-0.02em'>
            🏗️ Land Finder
        </div>
        <div style='font-size:0.75rem;color:#64748b;margin-top:2px'>
            Builder Intelligence Platform
        </div>
    </div>
    <div style='background:linear-gradient(135deg,{client_color},{client_color}cc);
                border-radius:8px;padding:10px 14px;margin:0 0 16px'>
        <div style='font-size:0.7rem;color:rgba(255,255,255,0.7);
                    text-transform:uppercase;letter-spacing:0.08em'>Signed in as</div>
        <div style='font-weight:600;color:white;font-size:0.95rem;margin-top:2px'>
            {client_name}
        </div>
    </div>
    <div style='font-size:0.7rem;color:#475569;text-transform:uppercase;
                letter-spacing:0.1em;margin-bottom:6px'>Navigation</div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["📊  Overview", "🗺️  Map", "📋  Leads", "⚙️  Criteria"],
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin:16px 0;border-top:1px solid #1e293b'></div>",
                unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:0.7rem;color:#475569;text-transform:uppercase;
                letter-spacing:0.1em;margin-bottom:6px'>Data Source</div>
    """, unsafe_allow_html=True)

    data_source = st.selectbox("ds", ["Upload CSV","Google Drive Link","Live GIS Pull"],
                                label_visibility="collapsed")

    if data_source == "Upload CSV":
        uploaded = st.file_uploader("csv", type=["csv"], label_visibility="collapsed")
        if uploaded:
            from utils.data_loader import load_from_upload
            with st.spinner("Loading..."):
                st.session_state["leads_df"] = load_from_upload(uploaded)
            st.success(f"✓ {len(st.session_state['leads_df']):,} leads loaded")

    elif data_source == "Google Drive Link":
        drive_url = st.text_input("url", placeholder="https://drive.google.com/file/d/...",
                                   label_visibility="collapsed")
        if st.button("Load from Drive", use_container_width=True):
            from utils.data_loader import load_from_drive
            with st.spinner("Fetching..."):
                st.session_state["leads_df"] = load_from_drive(drive_url)
            if not st.session_state.get("leads_df", {}) is not None:
                st.success(f"✓ {len(st.session_state['leads_df']):,} leads")

    elif data_source == "Live GIS Pull":
        municipality = st.text_input("muni", value="Ballwin",
                                      placeholder="Municipality",
                                      label_visibility="collapsed")
        school_dist  = st.text_input("sd", value="ROCKWOOD",
                                      placeholder="School District",
                                      label_visibility="collapsed")
        if st.button("Pull Live Data", use_container_width=True, type="primary"):
            from utils.data_loader import load_from_gis
            prog = st.empty()
            def cb(n): prog.caption(f"Fetched {n:,} parcels...")
            with st.spinner("Pulling from STL County GIS..."):
                st.session_state["leads_df"] = load_from_gis(
                    municipality=municipality, school_district=school_dist,
                    progress_callback=cb)
            prog.empty()
            if not st.session_state["leads_df"].empty:
                st.success(f"✓ {len(st.session_state['leads_df']):,} parcels")

    if "leads_df" in st.session_state and not st.session_state["leads_df"].empty:
        n = len(st.session_state["leads_df"])
        st.markdown(f"""
        <div style='background:#064e3b;border-radius:6px;padding:8px 12px;
                    margin-top:8px;font-size:0.8rem;color:#6ee7b7'>
            ✓ {n:,} leads in memory
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin:16px 0;border-top:1px solid #1e293b'></div>",
                unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        logout()

from utils.data_loader import apply_client_filters
raw_df   = st.session_state.get("leads_df", None)
criteria = client.get("criteria", {})
if raw_df is not None and not raw_df.empty:
    df = raw_df.copy() if is_admin() else apply_client_filters(raw_df, criteria)
else:
    df = None

if "Overview" in page:
    from pages.overview import render; render(df, client)
elif "Map" in page:
    from pages.map_view import render; render(df, client)
elif "Leads" in page:
    from pages.lead_table import render; render(df, client)
elif "Criteria" in page:
    from pages.criteria import render; render(df, client, raw_df)
