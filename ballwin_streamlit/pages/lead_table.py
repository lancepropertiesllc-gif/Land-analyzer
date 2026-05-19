"""
pages/lead_table.py — Sortable, filterable lead table with export
"""
import io
import csv
import pandas as pd
import streamlit as st


def render(df, client):
    st.markdown("<h1 style='margin-bottom:4px'>📋 Lead Table</h1>",
                unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar.")
        return

    # ── Sidebar filters ───────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Table Filters**")

    score_range = st.sidebar.slider(
        "Lead Score Range", 0, 100, (0, 100), 5,
        key="table_score_range"
    )
    distress_min = st.sidebar.slider(
        "Min Distress Score", 0, 100, 0, 5,
        key="table_distress_min"
    )

    opp_options = df["OPPORTUNITY_TYPE"].dropna().unique().tolist() \
        if "OPPORTUNITY_TYPE" in df.columns else []
    opp_filter = st.sidebar.multiselect(
        "Opportunity Type", opp_options, default=opp_options,
        key="table_opp_filter"
    )

    absentee_only  = st.sidebar.checkbox("Absentee Owners Only",    key="table_ab")
    noo_only       = st.sidebar.checkbox("Non-Owner Occupied Only",  key="table_noo")
    commercial_off = st.sidebar.checkbox("Hide Commercial/LLC",      key="table_comm",
                                          value=False)
    flood_off      = st.sidebar.checkbox("Exclude Near Flood Zone",  key="table_flood",
                                          value=False)

    # ── Apply filters ─────────────────────────────────────────────────────────
    fdf = df.copy()

    if "LEAD_SCORE" in fdf.columns:
        fdf = fdf[fdf["LEAD_SCORE"].between(*score_range)]
    if "DISTRESS_SCORE" in fdf.columns:
        fdf = fdf[fdf["DISTRESS_SCORE"] >= distress_min]
    if opp_filter and "OPPORTUNITY_TYPE" in fdf.columns:
        fdf = fdf[fdf["OPPORTUNITY_TYPE"].isin(opp_filter)]
    if absentee_only and "ABSENTEE_OWNER" in fdf.columns:
        fdf = fdf[fdf["ABSENTEE_OWNER"] == True]
    if noo_only and "NON_OWNER_OCCUPIED" in fdf.columns:
        fdf = fdf[fdf["NON_OWNER_OCCUPIED"] == True]
    if commercial_off and "IS_COMMERCIAL" in fdf.columns:
        fdf = fdf[~fdf["IS_COMMERCIAL"].fillna(False)]
    if flood_off and "NEAR_FLOOD_ZONE" in fdf.columns:
        fdf = fdf[~fdf["NEAR_FLOOD_ZONE"].fillna(False)]

    # ── Metrics ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filtered Leads", len(fdf))
    if "LEAD_SCORE" in fdf.columns and not fdf.empty:
        c2.metric("Avg Score", f"{fdf['LEAD_SCORE'].mean():.1f}")
    if "LAND_VALUE" in fdf.columns and not fdf.empty:
        c3.metric("Avg Land Value", f"${fdf['LAND_VALUE'].mean():,.0f}")
    if "ABSENTEE_OWNER" in fdf.columns and not fdf.empty:
        c4.metric("Absentee Owners", int(fdf["ABSENTEE_OWNER"].sum()))

    # ── Column selection ──────────────────────────────────────────────────────
    all_cols = list(fdf.columns)
    default_cols = [c for c in [
        "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","DISTRESS_TIER",
        "SITUS_ADDRESS","OWNER_NAME","OPPORTUNITY_TYPE",
        "ACRES","LOT_WIDTH","LAND_VALUE","IMPROVEMENT_VALUE",
        "NON_OWNER_OCCUPIED","ABSENTEE_OWNER","MULTI_PARCEL_OWNER",
        "OLD_STRUCTURE","SCHOOL_DISTRICT","IS_ROCKWOOD",
    ] if c in all_cols]

    with st.expander("📐 Column Selection"):
        selected_cols = st.multiselect(
            "Choose columns to display",
            all_cols,
            default=default_cols,
            key="table_cols"
        )

    if not selected_cols:
        selected_cols = default_cols

    # ── Sort ──────────────────────────────────────────────────────────────────
    sort_options = [c for c in ["LEAD_SCORE","DISTRESS_SCORE","ACRES","LAND_VALUE"]
                    if c in fdf.columns]
    col_sort, col_asc = st.columns([3,1])
    with col_sort:
        sort_by = st.selectbox("Sort by", sort_options,
                               index=0, key="table_sort")
    with col_asc:
        ascending = st.checkbox("Ascending", value=False, key="table_asc")

    display_df = fdf[selected_cols].sort_values(
        sort_by, ascending=ascending
    ) if sort_by in fdf.columns else fdf[selected_cols]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    # ── Export buttons ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Export")
    e1, e2, e3 = st.columns(3)

    with e1:
        csv_data = fdf.drop(
            columns=["geometry"], errors="ignore"
        ).to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV (all columns)",
            data=csv_data,
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
                # Hot leads sheet
                hot = fdf[fdf.get("LEAD_TIER","") == "🔥 Hot"] \
                    if "LEAD_TIER" in fdf.columns else pd.DataFrame()
                if not hot.empty:
                    hot.drop(columns=["geometry"], errors="ignore").to_excel(
                        writer, index=False, sheet_name="Hot Leads"
                    )
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
        # Outreach-ready export (just the mailing fields)
        outreach_cols = [c for c in [
            "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","OPPORTUNITY_TYPE",
            "SITUS_ADDRESS","SITUS_CITY","SITUS_ZIP",
            "OWNER_NAME","OWNER_ADDRESS","OWNER_CITY","OWNER_STATE","OWNER_ZIP",
            "ACRES","LAND_VALUE","IMPROVEMENT_VALUE","ABSENTEE_OWNER",
        ] if c in fdf.columns]
        outreach_csv = fdf[outreach_cols].to_csv(
            index=False, quoting=csv.QUOTE_ALL
        ).encode("utf-8")
        st.download_button(
            "⬇️ Download Outreach CSV",
            data=outreach_csv,
            file_name="outreach_ready.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Single parcel detail ──────────────────────────────────────────────────
    if not display_df.empty:
        st.markdown("---")
        st.subheader("🔍 Parcel Detail")
        addr_options = display_df.get(
            "SITUS_ADDRESS", display_df.iloc[:,0]
        ).fillna("Unknown").tolist()
        selected_addr = st.selectbox(
            "Select a parcel for full detail",
            addr_options,
            key="table_detail_select"
        )
        if selected_addr and "SITUS_ADDRESS" in fdf.columns:
            row = fdf[fdf["SITUS_ADDRESS"] == selected_addr]
            if not row.empty:
                row = row.iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Property Info**")
                    for field in ["SITUS_ADDRESS","SCHOOL_DISTRICT","SUBDIVISION",
                                  "ACRES","LOT_WIDTH","LOT_DIM","YEAR_BUILT",
                                  "BUILDING_SQFT","ZONING","LAND_USE_NAME"]:
                        if field in row.index and pd.notna(row[field]):
                            st.markdown(f"- **{field}:** {row[field]}")
                with c2:
                    st.markdown("**Owner & Financial Info**")
                    for field in ["OWNER_NAME","OWNER_ADDRESS","OWNER_CITY",
                                  "OWNER_STATE","OWNER_ZIP","TENURE",
                                  "LAND_VALUE","IMPROVEMENT_VALUE","TOTAL_VALUE",
                                  "ASSESSED_TOTAL","LEAD_SCORE","DISTRESS_SCORE"]:
                        if field in row.index and pd.notna(row[field]):
                            st.markdown(f"- **{field}:** {row[field]}")

                # Copy-ready mailing address block
                own_name  = str(row.get("OWNER_NAME","")).title()
                own_addr  = str(row.get("OWNER_ADDRESS","")).title()
                own_city  = str(row.get("OWNER_CITY","")).title()
                own_state = str(row.get("OWNER_STATE","MO"))
                own_zip   = str(row.get("OWNER_ZIP",""))
                st.markdown("**Mailing Address (copy-ready):**")
                st.code(
                    f"{own_name}\n{own_addr}\n{own_city}, {own_state} {own_zip}"
                )
