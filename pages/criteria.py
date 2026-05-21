"""
pages/criteria.py — Adjust scoring criteria with live preview
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
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
    from utils.data_loader import COUNTY_REGISTRY
    county_choice = st.selectbox(
        "County",
        list(COUNTY_REGISTRY.keys()),
        index=list(COUNTY_REGISTRY.keys()).index(geo.get("county","St. Louis"))
              if geo.get("county","St. Louis") in COUNTY_REGISTRY else 0,
    )
    g1, g2 = st.columns(2)
    with g1:
        sd_options = COUNTY_REGISTRY[county_choice]["school_districts"]
        saved_sd = [s for s in geo.get("school_districts", [])
                    if s in sd_options]
        school_filter = st.multiselect(
            "School Districts",
            sd_options,
            default=saved_sd or ([sd_options[1]] if len(sd_options) > 1 else []),
        )
        if "ALL" in school_filter:
            school_filter = []
    with g2:
        city_options = COUNTY_REGISTRY[county_choice]["cities"]
        saved_city = geo.get("municipality","")
        municipality = st.selectbox(
            "Target City",
            city_options,
            index=city_options.index(saved_city)
                  if saved_city in city_options else 1,
            help="Used when pulling live data from GIS",
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

    # ── Budget ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💰 Acquisition Budget")
    st.caption(
        "Set a hard cap, a per-acre cap, or both. "
        "A parcel must pass all enabled limits."
    )
    b1, b2 = st.columns(2)
    with b1:
        use_hard_cap = st.checkbox(
            "Enable hard dollar cap",
            value=bool(price.get("max_land_value")),
            help="Never pay more than this regardless of lot size",
        )
        max_land_value = st.slider(
            "Max Land Value ($)",
            50000, 2000000,
            int(price.get("max_land_value", 500000)),
            25000, format="$%d",
            disabled=not use_hard_cap,
        )
        use_per_acre = st.checkbox(
            "Enable per-acre cap",
            value=bool(price.get("max_per_acre", True)),
            help="Budget scales with lot size",
        )
        max_per_acre = st.slider(
            "Max Land Value per Acre ($)",
            25000, 500000,
            int(price.get("max_per_acre", 125000)),
            5000, format="$%d",
            disabled=not use_per_acre,
        )
        no_cap_acres = st.slider(
            "No per-acre cap above (acres)",
            0.5, 10.0,
            float(price.get("no_cap_above_acres", 2.0)),
            0.5,
            disabled=not use_per_acre,
            help="Lots larger than this bypass the per-acre cap",
        )
        min_land_value = st.number_input(
            "Min land value ($) — exclude data errors",
            min_value=0, max_value=50000,
            value=int(price.get("min_land_value", 1000)),
            step=500,
        )
    with b2:
        st.markdown("**Budget preview by lot size:**")
        for ex_acres in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
            effective = []
            if use_hard_cap:
                effective.append(max_land_value)
            if use_per_acre and ex_acres < no_cap_acres:
                effective.append(ex_acres * max_per_acre)
            if not effective:
                display = "No limit set"
            else:
                display = f"${min(effective):,.0f}"
            st.markdown(f"- **{ex_acres} ac** → {display}")

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
                    "max_land_value":     max_land_value if use_hard_cap else None,
                    "max_per_acre":       max_per_acre if use_per_acre else None,
                    "no_cap_above_acres": no_cap_acres,
                    "min_land_value":     min_land_value,
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
        "price":     {"max_land_value": max_land_value if use_hard_cap else None,
                      "max_per_acre": max_per_acre if use_per_acre else None,
                      "no_cap_above_acres": no_cap_acres,
                      "min_land_value": min_land_value},
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
