"""
pages/map_view.py — Interactive Folium map page
"""
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from components.map_builder import build_map


def render(df, client):
    st.markdown("<h1 style='margin-bottom:4px'>🗺️ Interactive Map</h1>",
                unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to see the map.")
        return

    # ── Map controls ──────────────────────────────────────────────────────────
    with st.expander("🎛️ Map Controls", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            min_score = st.slider("Min Lead Score", 0, 100, 30, 5)
        with c2:
            min_distress = st.slider("Min Distress Score", 0, 100, 0, 5)
        with c3:
            show_commercial = st.checkbox("Show Commercial/LLC", value=False)
        with c4:
            show_flood = st.checkbox("Show Near Flood Zone", value=False)
        with c5:
            show_cool = st.checkbox("Show Cool leads", value=True)

        opp_types = st.multiselect(
            "Opportunity Types",
            ["Vacant Land", "Teardown Candidate", "Large Lot"],
            default=["Vacant Land", "Teardown Candidate", "Large Lot"],
        )
        tile_style = st.selectbox(
            "Map Style",
            ["CartoDB positron", "CartoDB dark_matter",
             "OpenStreetMap", "Stamen Terrain"],
            index=0,
        )

    # ── Apply map filters ─────────────────────────────────────────────────────
    map_df = df.copy()

    if "LEAD_SCORE" in map_df.columns:
        map_df = map_df[map_df["LEAD_SCORE"] >= min_score]
    if "DISTRESS_SCORE" in map_df.columns:
        map_df = map_df[map_df["DISTRESS_SCORE"] >= min_distress]
    if opp_types and "OPPORTUNITY_TYPE" in map_df.columns:
        map_df = map_df[map_df["OPPORTUNITY_TYPE"].isin(opp_types)]
    if not show_commercial and "IS_COMMERCIAL" in map_df.columns:
        map_df = map_df[~map_df["IS_COMMERCIAL"].fillna(False)]

    # ── Stats bar ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads on map", len(map_df))
    if "LEAD_TIER" in map_df.columns:
        c2.metric("🔥 Hot",  int((map_df["LEAD_TIER"]=="🔥 Hot").sum()))
        c3.metric("⭐ Warm", int((map_df["LEAD_TIER"]=="⭐ Warm").sum()))
    if "DISTRESS_SCORE" in map_df.columns:
        c4.metric("🚨 High Distress", int((map_df["DISTRESS_SCORE"]>=50).sum()))

    # ── Build and render map ──────────────────────────────────────────────────
    if map_df.empty:
        st.warning("No leads match the current map filters. Try lowering the score threshold.")
        return

    with st.spinner("Building map..."):
        m = build_map(
            map_df,
            show_commercial=show_commercial,
            show_flood=show_flood,
            show_cool=show_cool,
            tiles=tile_style,
        )

    map_data = st_folium(m, use_container_width=True, height=600,
                         returned_objects=["last_object_clicked"])

    # ── Click detail panel ────────────────────────────────────────────────────
    if map_data and map_data.get("last_object_clicked"):
        clicked = map_data["last_object_clicked"]
        lat = clicked.get("lat")
        lng = clicked.get("lng")
        if lat and lng and "LATITUDE" in map_df.columns:
            # Find nearest parcel
            dists = ((map_df["LATITUDE"] - lat)**2 +
                     (map_df["LONGITUDE"] - lng)**2)
            nearest = map_df.loc[dists.idxmin()]
            _show_detail_panel(nearest)


def _show_detail_panel(row: pd.Series):
    """Show a detail panel below the map for the clicked parcel."""
    st.markdown("---")
    st.markdown("### 📍 Selected Parcel")

    addr  = str(row.get("SITUS_ADDRESS","")).title()
    owner = str(row.get("OWNER_NAME","")).title()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Address:** {addr}")
        st.markdown(f"**Owner:** {owner}")
        st.markdown(f"**School District:** {row.get('SCHOOL_DISTRICT','?')}")
        st.markdown(f"**Subdivision:** {row.get('SUBDIVISION','?')}")
    with c2:
        st.markdown(f"**Opportunity Score:** {row.get('LEAD_SCORE',0):.0f}/100 {row.get('LEAD_TIER','')}")
        st.markdown(f"**Distress Score:** {row.get('DISTRESS_SCORE',0):.0f}/100 {row.get('DISTRESS_TIER','')}")
        st.markdown(f"**Opportunity Type:** {row.get('OPPORTUNITY_TYPE','')}")
        st.markdown(f"**Lot Size:** {row.get('ACRES',0):.2f} acres | {int(row.get('LOT_WIDTH',0) or 0)}ft wide")
    with c3:
        st.markdown(f"**Land Value:** ${row.get('LAND_VALUE',0):,.0f}")
        st.markdown(f"**Improvement:** ${row.get('IMPROVEMENT_VALUE',0):,.0f}")
        st.markdown(f"**Year Built:** {int(row.get('YEAR_BUILT',0) or 0) or '—'}")
        st.markdown(f"**Non-owner occ.:** {'Yes ⚡' if row.get('NON_OWNER_OCCUPIED') else 'No'}")

    # Mailing address
    st.markdown("**Owner Mailing Address:**")
    own_addr  = str(row.get("OWNER_ADDRESS","")).title()
    own_city  = str(row.get("OWNER_CITY","")).title()
    own_state = str(row.get("OWNER_STATE","MO"))
    own_zip   = str(row.get("OWNER_ZIP",""))
    st.code(f"{owner}\n{own_addr}\n{own_city}, {own_state} {own_zip}")
