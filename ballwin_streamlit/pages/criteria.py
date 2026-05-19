"""
pages/criteria.py — Adjust scoring criteria with live preview
"""
import pandas as pd
import streamlit as st
from utils.data_loader import apply_client_filters


def render(df, client, raw_df):
    st.markdown("<h1 style='margin-bottom:4px'>⚙️ Criteria & Filters</h1>",
                unsafe_allow_html=True)
    st.caption("Adjust your search criteria. Changes apply instantly to Overview and Map.")

    if raw_df is None or raw_df.empty:
        st.info("👈 Load your leads data first using the sidebar.")
        return

    st.info(
        "**How this works:** Adjust the filters below and click Apply. "
        "Your Overview and Map will update to match the new criteria. "
        "These settings are temporary — to save permanently, "
        "ask your consultant to update your client profile."
    )

    # ── Geography ─────────────────────────────────────────────────────────────
    st.subheader("📍 Geography")
    c1, c2 = st.columns(2)

    saved = client.get("criteria", {})
    geo = saved.get("geography", {})
    lot = saved.get("lot", {})
    price = saved.get("price", {})
    scoring = saved.get("scoring", {})

    with c1:
        sd_options = ["ROCKWOOD","PARKWAY","KIRKWOOD","LINDBERGH","ALL"]
        current_sd = geo.get("school_districts", ["ROCKWOOD"])
        school_filter = st.multiselect(
            "School Districts",
            sd_options,
            default=current_sd,
            help="Filter to specific school districts"
        )
        if "ALL" in school_filter:
            school_filter = []

    with c2:
        municipality = st.text_input(
            "Municipality",
            value=geo.get("municipality", "Ballwin"),
            help="City name — used when pulling live GIS data"
        )

    # ── Lot Requirements ──────────────────────────────────────────────────────
    st.subheader("📐 Lot Requirements")
    c3, c4 = st.columns(2)

    with c3:
        min_acres = st.slider(
            "Minimum lot size (acres)",
            0.0, 2.0,
            float(lot.get("min_acres", 0.23)),
            0.05,
            help="0.23 acres ≈ 10,000 sqft"
        )
        min_width = st.slider(
            "Minimum lot width (ft)",
            0, 200,
            int(lot.get("min_lot_width_ft", 100)),
            5,
            help="Set to 0 to disable width filter"
        )

    with c4:
        st.markdown("**Current lot size distribution:**")
        if "ACRES" in raw_df.columns:
            bins = [0, 0.25, 0.5, 1.0, 2.0, 5.0, 100]
            labels = ["<0.25ac","0.25-0.5ac","0.5-1ac","1-2ac","2-5ac","5ac+"]
            raw_df["_acre_bin"] = pd.cut(
                raw_df["ACRES"].fillna(0), bins=bins, labels=labels
            )
            counts = raw_df["_acre_bin"].value_counts().sort_index()
            for label, count in counts.items():
                pct = count / len(raw_df) * 100
                flagged = "◀" if (
                    (label == "<0.25ac" and min_acres > 0.25) or
                    (label == "0.25-0.5ac" and min_acres > 0.5)
                ) else ""
                st.markdown(
                    f"{'~~' if flagged else ''}{label}: {count:,} ({pct:.0f}%)"
                    f"{'~~' if flagged else ''} {flagged}"
                )

    # ── Price / Budget ────────────────────────────────────────────────────────
    st.subheader("💰 Acquisition Budget")
    c5, c6 = st.columns(2)

    with c5:
        max_per_acre = st.slider(
            "Max land value per acre ($)",
            50000, 500000,
            int(price.get("max_land_value_per_acre", 125000)),
            5000,
            format="$%d",
            help="Price cap scales with lot size. 1 acre = this value, 2 acres = 2x this value"
        )
        no_cap_acres = st.slider(
            "No price cap above (acres)",
            1.0, 5.0,
            float(price.get("no_cap_above_acres", 2.0)),
            0.5,
            help="Lots larger than this have no price cap"
        )

    with c6:
        st.markdown("**Budget preview:**")
        for acres_ex in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]:
            if acres_ex >= no_cap_acres:
                cap_str = "No cap"
            else:
                cap = max(250000, acres_ex * max_per_acre)
                cap_str = f"${cap:,.0f}"
            st.markdown(f"- {acres_ex} acres → {cap_str}")

    # ── Deal Types ────────────────────────────────────────────────────────────
    st.subheader("🏗️ Deal Types")
    c7, c8, c9 = st.columns(3)

    current_types = saved.get("deal_types", ["Vacant Land","Teardown Candidate","Large Lot"])
    inc_vacant    = c7.checkbox("Vacant Land",          value="Vacant Land" in current_types)
    inc_teardown  = c8.checkbox("Teardown Candidate",   value="Teardown Candidate" in current_types)
    inc_large     = c9.checkbox("Large Lot",            value="Large Lot" in current_types)

    deal_types = []
    if inc_vacant:    deal_types.append("Vacant Land")
    if inc_teardown:  deal_types.append("Teardown Candidate")
    if inc_large:     deal_types.append("Large Lot")

    # ── Scoring Thresholds ────────────────────────────────────────────────────
    st.subheader("🎯 Scoring Thresholds")
    c10, c11, c12 = st.columns(3)

    with c10:
        min_lead_score = st.slider(
            "Min Lead Score",
            0, 100,
            int(scoring.get("min_lead_score", 0)),
            5
        )
    with c11:
        min_distress = st.slider(
            "Min Distress Score",
            0, 100, 0, 5
        )
    with c12:
        exclude_flood = st.checkbox(
            "Exclude flood zone parcels",
            value=scoring.get("exclude_flood_zone", True)
        )
        exclude_hoa = st.checkbox(
            "Exclude HOA/Gov parcels",
            value=scoring.get("exclude_hoa_gov", True)
        )

    # ── Apply and preview ─────────────────────────────────────────────────────
    st.markdown("---")
    col_apply, col_reset = st.columns(2)

    with col_apply:
        if st.button("✅ Apply Criteria", type="primary", use_container_width=True):
            # Build criteria dict from form values
            new_criteria = {
                "geography": {
                    "municipality":    municipality,
                    "school_districts": school_filter or [],
                },
                "lot": {
                    "min_acres":         min_acres,
                    "min_lot_width_ft":  min_width if min_width > 0 else None,
                },
                "price": {
                    "max_land_value_per_acre": max_per_acre,
                    "no_cap_above_acres":      no_cap_acres,
                },
                "deal_types": deal_types,
                "scoring": {
                    "min_lead_score":    min_lead_score,
                    "min_distress_score": min_distress,
                    "exclude_flood_zone": exclude_flood,
                    "exclude_hoa_gov":    exclude_hoa,
                },
            }

            # Apply to raw data
            filtered = apply_client_filters(raw_df, new_criteria)
            if min_distress > 0 and "DISTRESS_SCORE" in filtered.columns:
                filtered = filtered[filtered["DISTRESS_SCORE"] >= min_distress]

            st.session_state["leads_df"] = filtered

            # Update client criteria in session
            st.session_state["client"]["criteria"] = new_criteria

            st.success(f"✅ Applied! {len(filtered):,} leads match your criteria.")
            st.balloons()

    with col_reset:
        if st.button("🔄 Reset to Saved Defaults", use_container_width=True):
            if "leads_df" in st.session_state:
                del st.session_state["leads_df"]
            st.rerun()

    # ── Live preview ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("👁️ Live Preview")

    preview_criteria = {
        "geography": {"school_districts": school_filter or []},
        "lot":       {"min_acres": min_acres,
                      "min_lot_width_ft": min_width if min_width > 0 else None},
        "price":     {"max_land_value_per_acre": max_per_acre,
                      "no_cap_above_acres": no_cap_acres},
        "deal_types": deal_types,
        "scoring":   {"min_lead_score": min_lead_score,
                      "exclude_flood_zone": exclude_flood},
    }

    preview = apply_client_filters(raw_df, preview_criteria)

    pc1, pc2, pc3, pc4, pc5 = st.columns(5)
    pc1.metric("Leads", len(preview))
    if "LEAD_TIER" in preview.columns:
        pc2.metric("🔥 Hot",  int((preview["LEAD_TIER"]=="🔥 Hot").sum()))
        pc3.metric("⭐ Warm", int((preview["LEAD_TIER"]=="⭐ Warm").sum()))
    if "IS_VACANT" in preview.columns:
        pc4.metric("Vacant", int(preview["IS_VACANT"].sum()))
    if "ABSENTEE_OWNER" in preview.columns:
        pc5.metric("Absentee", int(preview["ABSENTEE_OWNER"].sum()))

    if not preview.empty:
        show = [c for c in [
            "LEAD_SCORE","LEAD_TIER","SITUS_ADDRESS","OWNER_NAME",
            "OPPORTUNITY_TYPE","ACRES","LAND_VALUE",
        ] if c in preview.columns]
        st.dataframe(
            preview[show].nlargest(10, "LEAD_SCORE")
            if "LEAD_SCORE" in preview.columns else preview[show].head(10),
            use_container_width=True,
            hide_index=True,
        )
