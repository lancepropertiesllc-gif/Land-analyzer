"""
pages/map_view.py — Interactive map page
"""
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.map_builder import build_map, TILE_OPTIONS, fmt_col


def render(df, client):
    st.markdown("<h1>🗺️ Interactive Map</h1>", unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to see the map.")
        return

    # ── Controls ──────────────────────────────────────────────────────────────
    with st.expander("🎛️ Map Controls", expanded=True):
        row1 = st.columns([2, 2, 2, 2, 2])
        with row1[0]:
            min_score = st.slider("Min Opportunity Score", 0, 100, 30, 5,
                                  key="map_score")
        with row1[1]:
            min_distress = st.slider("Min Distress Score", 0, 100, 0, 5,
                                     key="map_distress")
        with row1[2]:
            tile_label = st.selectbox(
                "Map Style",
                list(TILE_OPTIONS.keys()),
                index=0,
                key="map_tile",
            )
        with row1[3]:
            show_cool = st.checkbox("Show Cool Leads", value=True, key="map_cool")
        with row1[4]:
            show_commercial = st.checkbox("Show Commercial / LLC", value=False,
                                          key="map_comm")

        row2 = st.columns([3, 1])
        with row2[0]:
            opp_types = st.multiselect(
                "Opportunity Types",
                ["Vacant Land", "Teardown Candidate", "Large Lot"],
                default=["Vacant Land", "Teardown Candidate", "Large Lot"],
                key="map_opp",
            )
        with row2[1]:
            show_flood = st.checkbox("Show Near Flood Zone", value=False,
                                     key="map_flood")

    # ── Apply filters ─────────────────────────────────────────────────────────
    map_df = df.copy()
    if "LEAD_SCORE" in map_df.columns:
        map_df = map_df[map_df["LEAD_SCORE"].fillna(0) >= min_score]
    if "DISTRESS_SCORE" in map_df.columns and min_distress > 0:
        map_df = map_df[map_df["DISTRESS_SCORE"].fillna(0) >= min_distress]
    if opp_types and "OPPORTUNITY_TYPE" in map_df.columns:
        map_df = map_df[map_df["OPPORTUNITY_TYPE"].isin(opp_types)]
    if not show_commercial and "IS_COMMERCIAL" in map_df.columns:
        map_df = map_df[~map_df["IS_COMMERCIAL"].fillna(False)]

    # ── Stats bar ─────────────────────────────────────────────────────────────
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Leads on Map", len(map_df))
    if "LEAD_TIER" in map_df.columns:
        c2.metric("🔥 Hot",  int((map_df["LEAD_TIER"]=="🔥 Hot").sum()))
        c3.metric("⭐ Warm", int((map_df["LEAD_TIER"]=="⭐ Warm").sum()))
    if "DISTRESS_SCORE" in map_df.columns:
        c4.metric("🚨 High Distress",
                  int((map_df["DISTRESS_SCORE"].fillna(0) >= 50).sum()))
    if "IS_VACANT" in map_df.columns:
        c5.metric("Vacant Lots", int(map_df["IS_VACANT"].sum()))

    if map_df.empty:
        st.warning("No leads match the current filters. Try lowering the score threshold.")
        return

    # ── Map ───────────────────────────────────────────────────────────────────
    with st.spinner("Building map..."):
        m = build_map(
            map_df,
            show_commercial=show_commercial,
            show_flood=show_flood,
            show_cool=show_cool,
            tile_label=tile_label,
        )

    map_data = st_folium(
        m,
        use_container_width=True,
        height=580,
        returned_objects=["last_object_clicked"],
    )

    # ── Click detail ──────────────────────────────────────────────────────────
    if map_data and map_data.get("last_object_clicked"):
        clicked = map_data["last_object_clicked"]
        lat = clicked.get("lat")
        lng = clicked.get("lng")
        if lat and lng and "LATITUDE" in map_df.columns:
            dists = ((map_df["LATITUDE"] - lat)**2 +
                     (map_df["LONGITUDE"] - lng)**2)
            if not dists.empty:
                nearest = map_df.loc[dists.idxmin()]
                _detail_panel(nearest)


def _detail_panel(row: pd.Series):
    st.markdown("---")
    st.markdown("### 📍 Selected Parcel")

    addr  = str(row.get("SITUS_ADDRESS","")).title()
    owner = str(row.get("OWNER_NAME","")).title()

    # Score badges
    score = float(row.get("LEAD_SCORE", 0) or 0)
    dst   = float(row.get("DISTRESS_SCORE", 0) or 0)
    tier  = str(row.get("LEAD_TIER",""))
    dtier = str(row.get("DISTRESS_TIER",""))
    c_opp = "#ef4444" if score >= 70 else "#f97316" if score >= 50 else "#3b82f6"
    c_dst = "#dc2626" if dst >= 50 else "#ea580c" if dst >= 30 else "#94a3b8"

    st.markdown(f"""
    <div style='margin-bottom:16px'>
        <div style='font-size:1.1rem;font-weight:700;color:inherit'>{addr}</div>
        <div style='color:inherit;margin:2px 0 8px'>{owner}</div>
        <span style='background:{c_opp};color:white;padding:4px 12px;
                     border-radius:20px;font-size:12px;font-weight:600;
                     margin-right:8px'>
            ⭐ {score:.0f}/100 {tier}
        </span>
        <span style='background:{c_dst};color:white;padding:4px 12px;
                     border-radius:20px;font-size:12px;font-weight:600'>
            🚨 {dst:.0f} {dtier}
        </span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Property**")
        fields = [
            ("Opportunity Type", "OPPORTUNITY_TYPE"),
            ("Lot Size",         "ACRES"),
            ("Lot Width",        "LOT_WIDTH"),
            ("School District",  "SCHOOL_DISTRICT"),
            ("Subdivision",      "SUBDIVISION"),
            ("Year Built",       "YEAR_BUILT"),
            ("Zoning",           "ZONING"),
        ]
        for label, key in fields:
            val = row.get(key)
            if pd.notna(val) and val != "" and val != 0:
                if key == "ACRES":
                    val = f"{float(val):.2f} acres"
                elif key == "LOT_WIDTH" and val:
                    val = f"{int(val)} ft"
                st.markdown(f"- **{label}:** {val}")

    with c2:
        st.markdown("**Financials**")
        fin_fields = [
            ("Land Value",    "LAND_VALUE",    True),
            ("Improvement",   "IMPROVEMENT_VALUE", True),
            ("Total Value",   "TOTAL_VALUE",   True),
            ("Est Annual Tax","EST_ANNUAL_TAX",True),
        ]
        for label, key, is_money in fin_fields:
            val = row.get(key)
            if pd.notna(val) and val != 0:
                disp = f"${float(val):,.0f}" if is_money else str(val)
                st.markdown(f"- **{label}:** {disp}")

        st.markdown("**Signals**")
        signal_fields = [
            ("Non-Owner Occ", "NON_OWNER_OCCUPIED"),
            ("Absentee Owner","ABSENTEE_OWNER"),
            ("Multi-Parcel",  "MULTI_PARCEL_OWNER"),
            ("Old Structure", "OLD_STRUCTURE"),
            ("Near Flood",    "NEAR_FLOOD_ZONE"),
        ]
        for label, key in signal_fields:
            val = row.get(key)
            if val:
                st.markdown(f"- **{label}:** ✅ Yes")

    with c3:
        st.markdown("**Mailing Address**")
        own_name  = str(row.get("OWNER_NAME","")).title()
        own_addr  = str(row.get("OWNER_ADDRESS","")).title()
        own_city  = str(row.get("OWNER_CITY","")).title()
        own_state = str(row.get("OWNER_STATE","MO"))
        own_zip   = str(row.get("OWNER_ZIP",""))
        st.code(
            f"{own_name}\n{own_addr}\n{own_city}, {own_state} {own_zip}",
            language=None,
        )
        st.caption("Copy this address for outreach letters")
