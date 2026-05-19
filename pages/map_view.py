"""
pages/map_view.py — Interactive map page
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from components.map_builder import build_map, TILE_OPTIONS, fmt_col


def render(df, client):
    st.markdown("## 🗺️ Interactive Map")

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to see the map.")
        return

    with st.expander("Map Controls", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            min_score = st.slider("Min Opportunity Score", 0, 100, 30, 5, key="map_score")
        with c2:
            tile_label = st.selectbox("Map Style", list(TILE_OPTIONS.keys()), key="map_tile")
        with c3:
            show_cool = st.checkbox("Show Cool Leads", value=True, key="map_cool")

        c4, c5, c6 = st.columns(3)
        with c4:
            opp_types = st.multiselect(
                "Opportunity Types",
                ["Vacant Land", "Teardown Candidate", "Large Lot"],
                default=["Vacant Land", "Teardown Candidate", "Large Lot"],
                key="map_opp",
            )
        with c5:
            show_commercial = st.checkbox("Show Commercial / LLC", value=False, key="map_comm")
        with c6:
            show_flood = st.checkbox("Show Near Flood Zone", value=False, key="map_flood")

    map_df = df.copy()
    if "LEAD_SCORE" in map_df.columns:
        map_df = map_df[map_df["LEAD_SCORE"].fillna(0) >= min_score]
    if opp_types and "OPPORTUNITY_TYPE" in map_df.columns:
        map_df = map_df[map_df["OPPORTUNITY_TYPE"].isin(opp_types)]
    if not show_commercial and "IS_COMMERCIAL" in map_df.columns:
        map_df = map_df[~map_df["IS_COMMERCIAL"].fillna(False)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads on Map", len(map_df))
    if "LEAD_TIER" in map_df.columns:
        c2.metric("Hot",  int((map_df["LEAD_TIER"] == "🔥 Hot").sum()))
        c3.metric("Warm", int((map_df["LEAD_TIER"] == "⭐ Warm").sum()))
    if "DISTRESS_SCORE" in map_df.columns:
        c4.metric("High Distress", int((map_df["DISTRESS_SCORE"].fillna(0) >= 50).sum()))

    if map_df.empty:
        st.warning("No leads match current filters.")
        return

    with st.spinner("Building map..."):
        m = build_map(
            map_df,
            show_commercial=show_commercial,
            show_flood=show_flood,
            show_cool=show_cool,
            tile_label=tile_label,
        )

    st_folium(m, use_container_width=True, height=560)
