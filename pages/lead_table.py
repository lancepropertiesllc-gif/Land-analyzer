"""
pages/lead_table.py — Sortable, filterable lead table with export
"""
import io
import csv
import pandas as pd
import streamlit as st


def fmt_col(col: str) -> str:
    return col.replace("_", " ").title()


def render(df, client):
    st.markdown("<h1>📋 Lead Table</h1>", unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            score_range = st.slider("Opportunity Score", 0, 100, (0, 100), 5,
                                    key="lt_score")
        with fc2:
            distress_min = st.slider("Min Distress Score", 0, 100, 0, 5,
                                     key="lt_distress")
        with fc3:
            opp_options = (df["OPPORTUNITY_TYPE"].dropna().unique().tolist()
                           if "OPPORTUNITY_TYPE" in df.columns else [])
            opp_filter = st.multiselect("Opportunity Type", opp_options,
                                         default=opp_options, key="lt_opp")

        fc4, fc5, fc6, fc7 = st.columns(4)
        with fc4:
            absentee_only = st.checkbox("Absentee Owners Only", key="lt_ab")
        with fc5:
            noo_only = st.checkbox("Non-Owner Occupied Only", key="lt_noo")
        with fc6:
            hide_commercial = st.checkbox("Hide Commercial / LLC", key="lt_comm",
                                          value=False)
        with fc7:
            hide_flood = st.checkbox("Exclude Near Flood Zone", key="lt_flood",
                                     value=False)

    # ── Apply filters ─────────────────────────────────────────────────────────
    fdf = df.copy()
    if "LEAD_SCORE" in fdf.columns:
        fdf = fdf[fdf["LEAD_SCORE"].fillna(0).between(*score_range)]
    if "DISTRESS_SCORE" in fdf.columns and distress_min > 0:
        fdf = fdf[fdf["DISTRESS_SCORE"].fillna(0) >= distress_min]
    if opp_filter and "OPPORTUNITY_TYPE" in fdf.columns:
        fdf = fdf[fdf["OPPORTUNITY_TYPE"].isin(opp_filter)]
    if absentee_only and "ABSENTEE_OWNER" in fdf.columns:
        fdf = fdf[fdf["ABSENTEE_OWNER"] == True]
    if noo_only and "NON_OWNER_OCCUPIED" in fdf.columns:
        fdf = fdf[fdf["NON_OWNER_OCCUPIED"] == True]
    if hide_commercial and "IS_COMMERCIAL" in fdf.columns:
        fdf = fdf[~fdf["IS_COMMERCIAL"].fillna(False)]
    if hide_flood and "NEAR_FLOOD_ZONE" in fdf.columns:
        fdf = fdf[~fdf["NEAR_FLOOD_ZONE"].fillna(False)]

    # ── Metrics ───────────────────────────────────────────────────────────────
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Filtered Leads", f"{len(fdf):,}")
    if "LEAD_SCORE" in fdf.columns and not fdf.empty:
        m2.metric("Avg Score", f"{fdf['LEAD_SCORE'].mean():.1f}")
    if "LAND_VALUE" in fdf.columns and not fdf.empty:
        m3.metric("Avg Land Value", f"${fdf['LAND_VALUE'].mean():,.0f}")
    if "ABSENTEE_OWNER" in fdf.columns and not fdf.empty:
        m4.metric("Absentee Owners", int(fdf["ABSENTEE_OWNER"].sum()))

    # ── Sort ──────────────────────────────────────────────────────────────────
    sort_options = [c for c in ["LEAD_SCORE","DISTRESS_SCORE","ACRES","LAND_VALUE"]
                    if c in fdf.columns]
    sc1, sc2 = st.columns([3,1])
    with sc1:
        sort_by = st.selectbox("Sort by",
                               [fmt_col(c) for c in sort_options],
                               key="lt_sort")
        # Map back to actual column
        sort_col = sort_options[[fmt_col(c) for c in sort_options].index(sort_by)] \
            if sort_by in [fmt_col(c) for c in sort_options] else sort_options[0]
    with sc2:
        ascending = st.checkbox("Ascending", value=False, key="lt_asc")

    # ── Column display ────────────────────────────────────────────────────────
    default_cols = [c for c in [
        "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","DISTRESS_TIER",
        "SITUS_ADDRESS","OWNER_NAME","OPPORTUNITY_TYPE",
        "ACRES","LOT_WIDTH","LAND_VALUE","IMPROVEMENT_VALUE",
        "NON_OWNER_OCCUPIED","ABSENTEE_OWNER","MULTI_PARCEL_OWNER",
        "OLD_STRUCTURE","SCHOOL_DISTRICT",
    ] if c in fdf.columns]

    with st.expander("📐 Choose Columns"):
        all_cols = list(fdf.columns)
        selected = st.multiselect(
            "Columns",
            all_cols,
            default=default_cols,
            format_func=fmt_col,
            key="lt_cols",
        )
    if not selected:
        selected = default_cols

    display_df = (fdf[selected].sort_values(sort_col, ascending=ascending)
                  if sort_col in fdf.columns else fdf[selected])

    # Rename columns for display
    display_renamed = display_df.copy()
    display_renamed.columns = [fmt_col(c) for c in display_renamed.columns]

    st.dataframe(display_renamed, use_container_width=True,
                 hide_index=True, height=480)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Export")
    e1, e2, e3 = st.columns(3)

    with e1:
        csv_bytes = (fdf.drop(columns=["geometry"], errors="ignore")
                       .to_csv(index=False).encode("utf-8"))
        st.download_button(
            "⬇️ Download All Columns (CSV)",
            data=csv_bytes,
            file_name="leads_filtered.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with e2:
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                fdf.drop(columns=["geometry"], errors="ignore").to_excel(
                    writer, index=False, sheet_name="Leads"
                )
                hot = fdf[fdf.get("LEAD_TIER","") == "🔥 Hot"] \
                    if "LEAD_TIER" in fdf.columns else pd.DataFrame()
                if not hot.empty:
                    hot.drop(columns=["geometry"], errors="ignore").to_excel(
                        writer, index=False, sheet_name="Hot Leads")
            st.download_button(
                "⬇️ Download Excel",
                data=buf.getvalue(),
                file_name="leads_filtered.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except ImportError:
            st.info("Install openpyxl for Excel export")

    with e3:
        outreach_cols = [c for c in [
            "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","OPPORTUNITY_TYPE",
            "SITUS_ADDRESS","SITUS_CITY","SITUS_ZIP",
            "OWNER_NAME","OWNER_ADDRESS","OWNER_CITY","OWNER_STATE","OWNER_ZIP",
            "ACRES","LAND_VALUE","IMPROVEMENT_VALUE","ABSENTEE_OWNER",
            "NON_OWNER_OCCUPIED","MULTI_PARCEL_OWNER",
        ] if c in fdf.columns]
        out_csv = (fdf[outreach_cols]
                   .to_csv(index=False, quoting=csv.QUOTE_ALL)
                   .encode("utf-8"))
        st.download_button(
            "⬇️ Download Outreach CSV",
            data=out_csv,
            file_name="outreach_ready.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Parcel detail ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Parcel Detail")

    addr_col = "SITUS_ADDRESS" if "SITUS_ADDRESS" in fdf.columns else fdf.columns[0]
    addr_options = fdf[addr_col].fillna("Unknown").tolist()

    if addr_options:
        sel = st.selectbox("Select a parcel", addr_options,
                           format_func=lambda x: str(x).title(),
                           key="lt_detail")
        match = fdf[fdf[addr_col] == sel]
        if not match.empty:
            row = match.iloc[0]
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Property Info**")
                prop_fields = ["SITUS_ADDRESS","SCHOOL_DISTRICT","SUBDIVISION",
                               "ACRES","LOT_WIDTH","LOT_DIM","YEAR_BUILT",
                               "BUILDING_SQFT","ZONING","LAND_USE_NAME","TENURE"]
                for f in prop_fields:
                    if f in row.index and pd.notna(row[f]) and row[f] != "":
                        st.markdown(f"- **{fmt_col(f)}:** {row[f]}")
            with d2:
                st.markdown("**Owner & Financial**")
                fin_fields = ["OWNER_NAME","OWNER_ADDRESS","OWNER_CITY",
                              "OWNER_STATE","OWNER_ZIP","TENURE",
                              "LAND_VALUE","IMPROVEMENT_VALUE","TOTAL_VALUE",
                              "LEAD_SCORE","DISTRESS_SCORE","NON_OWNER_OCCUPIED",
                              "ABSENTEE_OWNER","MULTI_PARCEL_OWNER"]
                for f in fin_fields:
                    if f in row.index and pd.notna(row[f]) and row[f] != "":
                        val = row[f]
                        if f in ["LAND_VALUE","IMPROVEMENT_VALUE","TOTAL_VALUE"]:
                            val = f"${float(val):,.0f}"
                        st.markdown(f"- **{fmt_col(f)}:** {val}")

            # Mailing block
            own_name  = str(row.get("OWNER_NAME","")).title()
            own_addr  = str(row.get("OWNER_ADDRESS","")).title()
            own_city  = str(row.get("OWNER_CITY","")).title()
            own_state = str(row.get("OWNER_STATE","MO"))
            own_zip   = str(row.get("OWNER_ZIP",""))
            st.markdown("**Copy-Ready Mailing Address:**")
            st.code(f"{own_name}\n{own_addr}\n{own_city}, {own_state} {own_zip}",
                    language=None)
