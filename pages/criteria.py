"""
pages/criteria.py — Adjust scoring criteria with live preview
"""
import pandas as pd
import streamlit as st
from utils.data_loader import apply_client_filters


def fmt_col(col: str) -> str:
    return col.replace("_", " ").title()


def render(df, client, raw_df):
    st.markdown("<h1>⚙️ Criteria & Filters</h1>", unsafe_allow_html=True)
    st.caption("Adjust your search criteria. Changes apply to Overview and Map when you click Apply.")

    if raw_df is None or raw_df.empty:
        st.info("👈 Load your leads data first using the sidebar.")
        return

    st.info(
        "Adjust the filters below and click **Apply Criteria** to update your lead list. "
        "These changes are session-only — contact your consultant to save permanently."
    )

    saved   = client.get("criteria", {})
    geo     = saved.get("geography", {})
    lot     = saved.get("lot", {})
    price   = saved.get("price", {})
    scoring = saved.get("scoring", {})

    # ── Geography ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📍 Geography")
    g1, g2 = st.columns(2)
    with g1:
        sd_options = ["ROCKWOOD","PARKWAY","KIRKWOOD","LINDBERGH"]
        current_sd = [s for s in geo.get("school_districts", ["ROCKWOOD"])
                      if s in sd_options]
        school_filter = st.multiselect(
            "School Districts",
            sd_options + ["All Districts"],
            default=current_sd or ["ROCKWOOD"],
        )
        if "All Districts" in school_filter:
            school_filter = []
    with g2:
        municipality = st.text_input(
            "Target Municipality",
            value=geo.get("municipality","Ballwin"),
            help="Used when pulling live data from STL County GIS",
        )

    # ── Lot Requirements ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📐 Lot Requirements")
    l1, l2 = st.columns(2)
    with l1:
        min_acres = st.slider("Minimum Lot Size (acres)",
                              0.0, 2.0, float(lot.get("min_acres", 0.23)), 0.05)
        min_width = st.slider("Minimum Lot Width (ft)",
                              0, 200, int(lot.get("min_lot_width_ft", 100)), 5,
                              help="Set to 0 to disable width filter")
    with l2:
        st.markdown("**Lot size breakdown in current dataset:**")
        if "ACRES" in raw_df.columns:
            bins   = [0, 0.25, 0.5, 1.0, 2.0, 5.0, 100]
            labels = ["Under 0.25 ac","0.25–0.5 ac","0.5–1 ac",
                      "1–2 ac","2–5 ac","Over 5 ac"]
            raw_df2 = raw_df.copy()
            raw_df2["_bin"] = pd.cut(raw_df2["ACRES"].fillna(0),
                                      bins=bins, labels=labels)
            counts = raw_df2["_bin"].value_counts().sort_index()
            for label, count in counts.items():
                pct = count / len(raw_df2) * 100
                excluded = (label == "Under 0.25 ac" and min_acres > 0.25) or \
                           (label == "0.25–0.5 ac" and min_acres > 0.5)
                prefix = "~~" if excluded else ""
                st.markdown(f"{prefix}{label}: {count:,} ({pct:.0f}%){prefix}")

    # ── Budget ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💰 Acquisition Budget")
    b1, b2 = st.columns(2)
    with b1:
        max_per_acre = st.slider(
            "Max Land Value per Acre ($)",
            50000, 500000,
            int(price.get("max_land_value_per_acre", 125000)),
            5000, format="$%d",
            help="Budget scales with lot size — larger lots get higher caps",
        )
        no_cap_acres = st.slider(
            "No Price Cap Above (acres)",
            1.0, 5.0, float(price.get("no_cap_above_acres", 2.0)), 0.5,
        )
    with b2:
        st.markdown("**Effective budget by lot size:**")
        for ex in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]:
            cap = "No limit" if ex >= no_cap_acres \
                  else f"${max(250000, ex * max_per_acre):,.0f}"
            st.markdown(f"- **{ex} acres** → {cap}")

    # ── Deal Types ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🏗️ Deal Types")
    current_types = saved.get("deal_types",
                              ["Vacant Land","Teardown Candidate","Large Lot"])
    dt1, dt2, dt3 = st.columns(3)
    inc_vacant   = dt1.checkbox("Vacant Land",        value="Vacant Land" in current_types)
    inc_teardown = dt2.checkbox("Teardown Candidate", value="Teardown Candidate" in current_types)
    inc_large    = dt3.checkbox("Large Lot",          value="Large Lot" in current_types)
    deal_types = (
        (["Vacant Land"] if inc_vacant else []) +
        (["Teardown Candidate"] if inc_teardown else []) +
        (["Large Lot"] if inc_large else [])
    )

    # ── Scoring Thresholds ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🎯 Score Thresholds")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        min_lead = st.slider("Min Opportunity Score", 0, 100,
                             int(scoring.get("min_lead_score", 0)), 5)
    with s2:
        min_dist = st.slider("Min Distress Score", 0, 100, 0, 5)
    with s3:
        excl_flood = st.checkbox("Exclude Flood Zone",
                                  value=scoring.get("exclude_flood_zone", True))
    with s4:
        excl_hoa = st.checkbox("Exclude HOA / Gov",
                                value=scoring.get("exclude_hoa_gov", True))

    # ── Apply / Reset ─────────────────────────────────────────────────────────
    st.markdown("---")
    col_a, col_r = st.columns(2)
    with col_a:
        if st.button("✅ Apply Criteria", type="primary", use_container_width=True):
            new_criteria = {
                "geography": {
                    "municipality":    municipality,
                    "school_districts": school_filter,
                },
                "lot": {
                    "min_acres":        min_acres,
                    "min_lot_width_ft": min_width if min_width > 0 else None,
                },
                "price": {
                    "max_land_value_per_acre": max_per_acre,
                    "no_cap_above_acres":      no_cap_acres,
                },
                "deal_types": deal_types,
                "scoring": {
                    "min_lead_score":    min_lead,
                    "min_distress_score":min_dist,
                    "exclude_flood_zone":excl_flood,
                    "exclude_hoa_gov":   excl_hoa,
                },
            }
            filtered = apply_client_filters(raw_df, new_criteria)
            if min_dist > 0 and "DISTRESS_SCORE" in filtered.columns:
                filtered = filtered[filtered["DISTRESS_SCORE"].fillna(0) >= min_dist]
            st.session_state["leads_df"] = filtered
            st.session_state["client"]["criteria"] = new_criteria
            st.success(f"✅ Applied — {len(filtered):,} leads match your criteria.")

    with col_r:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            if "leads_df" in st.session_state:
                del st.session_state["leads_df"]
            st.rerun()

    # ── Live preview ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 👁️ Live Preview")
    st.caption("This updates as you change the sliders above — click Apply to lock it in.")

    preview_criteria = {
        "geography": {"school_districts": school_filter or []},
        "lot":       {"min_acres": min_acres,
                      "min_lot_width_ft": min_width if min_width > 0 else None},
        "price":     {"max_land_value_per_acre": max_per_acre,
                      "no_cap_above_acres": no_cap_acres},
        "deal_types": deal_types,
        "scoring":   {"min_lead_score": min_lead,
                      "exclude_flood_zone": excl_flood},
    }
    preview = apply_client_filters(raw_df, preview_criteria)

    pc1,pc2,pc3,pc4,pc5 = st.columns(5)
    pc1.metric("Leads",   f"{len(preview):,}")
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
        top10 = (preview[show].nlargest(10,"LEAD_SCORE")
                 if "LEAD_SCORE" in preview.columns
                 else preview[show].head(10))
        top10_display = top10.copy()
        top10_display.columns = [fmt_col(c) for c in top10_display.columns]
        st.dataframe(top10_display, use_container_width=True, hide_index=True)
