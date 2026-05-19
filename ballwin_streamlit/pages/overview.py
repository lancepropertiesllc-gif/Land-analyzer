"""
pages/overview.py — Dashboard overview with KPIs and charts
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def render(df, client):
    client_name  = client.get("name", "Dashboard")
    client_color = client.get("color", "#1d4ed8")

    st.markdown(f"""
    <h1 style='margin-bottom:4px'>📊 Overview</h1>
    <p style='color:#6b7280;margin-bottom:24px'>
        {client_name} — Lead intelligence summary
    </p>
    """, unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to get started.")
        _show_getting_started()
        return

    # ── KPI Row ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    total       = len(df)
    hot         = int((df.get("LEAD_TIER","") == "🔥 Hot").sum())
    warm        = int((df.get("LEAD_TIER","") == "⭐ Warm").sum())
    vacant      = int(df.get("IS_VACANT", pd.Series(dtype=bool)).sum())
    absentee    = int(df.get("ABSENTEE_OWNER", pd.Series(dtype=bool)).sum())
    high_dist   = int((df.get("DISTRESS_SCORE", 0) >= 50).sum())

    col1.metric("Total Leads",       f"{total:,}")
    col2.metric("🔥 Hot",            f"{hot:,}",
                delta=f"{hot/total*100:.1f}%" if total else None)
    col3.metric("⭐ Warm",           f"{warm:,}")
    col4.metric("Vacant Lots",       f"{vacant:,}")
    col5.metric("Absentee Owners",   f"{absentee:,}")
    col6.metric("🚨 High Distress",  f"{high_dist:,}")

    st.markdown("---")

    # ── Charts Row 1 ─────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("Lead Score Distribution")
        if "LEAD_SCORE" in df.columns:
            fig = px.histogram(
                df, x="LEAD_SCORE", nbins=20,
                color_discrete_sequence=[client_color],
                labels={"LEAD_SCORE": "Lead Score"},
            )
            fig.add_vline(x=70, line_dash="dash", line_color="red",
                          annotation_text="Hot", annotation_position="top right")
            fig.add_vline(x=50, line_dash="dash", line_color="orange",
                          annotation_text="Warm", annotation_position="top right")
            fig.update_layout(height=280, margin=dict(t=10,b=10,l=10,r=10),
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Opportunity Type")
        if "OPPORTUNITY_TYPE" in df.columns:
            counts = df["OPPORTUNITY_TYPE"].value_counts()
            fig = px.pie(
                values=counts.values, names=counts.index,
                color_discrete_sequence=["#3b82f6","#f97316","#22c55e"],
                hole=0.45,
            )
            fig.update_layout(height=280, margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)

    with c3:
        st.subheader("Distress Signals")
        signals = {
            "Non-owner occupied": int(df.get("NON_OWNER_OCCUPIED", pd.Series(dtype=bool)).sum()),
            "Old structure 50+yr": int(df.get("OLD_STRUCTURE", pd.Series(dtype=bool)).sum()),
            "Absentee owner":     int(df.get("ABSENTEE_OWNER", pd.Series(dtype=bool)).sum()),
            "Multi-parcel owner": int(df.get("MULTI_PARCEL_OWNER", pd.Series(dtype=bool)).sum()),
            "Near flood zone":    int(df.get("NEAR_FLOOD_ZONE", pd.Series(dtype=bool)).sum()),
            "High distress ≥50":  int((df.get("DISTRESS_SCORE",0) >= 50).sum()),
        }
        sig_df = pd.DataFrame({"Signal": list(signals.keys()),
                               "Count": list(signals.values())})
        fig = px.bar(sig_df, x="Count", y="Signal", orientation="h",
                     color_discrete_sequence=["#dc2626"])
        fig.update_layout(height=280, margin=dict(t=10,b=10,l=10,r=10),
                          yaxis_title="", xaxis_title="Parcels")
        st.plotly_chart(fig, use_container_width=True)

    # ── Charts Row 2 ─────────────────────────────────────────────────────────
    c4, c5 = st.columns(2)

    with c4:
        st.subheader("Lot Size vs Land Value")
        if "ACRES" in df.columns and "LAND_VALUE" in df.columns:
            plot_df = df.dropna(subset=["ACRES","LAND_VALUE"]).copy()
            plot_df = plot_df[
                (plot_df["ACRES"] < 10) &
                (plot_df["LAND_VALUE"] < 600000) &
                (plot_df["ACRES"] > 0)
            ]
            fig = px.scatter(
                plot_df,
                x="ACRES",
                y="LAND_VALUE",
                color="LEAD_TIER" if "LEAD_TIER" in plot_df.columns else None,
                color_discrete_map={
                    "🔥 Hot": "red", "⭐ Warm": "orange",
                    "🌡️ Cool": "steelblue", "❄️ Cold": "lightgray"
                },
                hover_data=["SITUS_ADDRESS"] if "SITUS_ADDRESS" in plot_df.columns else None,
                labels={"ACRES": "Lot Size (acres)", "LAND_VALUE": "Land Value ($)"},
                opacity=0.6,
            )
            fig.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)

    with c5:
        st.subheader("Lead Score vs Distress Score")
        if "LEAD_SCORE" in df.columns and "DISTRESS_SCORE" in df.columns:
            plot_df2 = df.dropna(subset=["LEAD_SCORE","DISTRESS_SCORE"])
            fig = px.scatter(
                plot_df2,
                x="LEAD_SCORE",
                y="DISTRESS_SCORE",
                color="OPPORTUNITY_TYPE" if "OPPORTUNITY_TYPE" in plot_df2.columns else None,
                hover_data=["SITUS_ADDRESS","OWNER_NAME"] if "SITUS_ADDRESS" in plot_df2.columns else None,
                labels={"LEAD_SCORE": "Opportunity Score",
                        "DISTRESS_SCORE": "Distress Score"},
                opacity=0.6,
            )
            # Highlight top-right quadrant (high opp + high distress)
            fig.add_shape(type="rect", x0=50, y0=30, x1=100, y1=100,
                          fillcolor="rgba(220,38,38,0.05)",
                          line=dict(color="rgba(220,38,38,0.3)", dash="dash"))
            fig.add_annotation(x=75, y=95, text="Best leads",
                               showarrow=False, font=dict(color="#dc2626", size=11))
            fig.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)

    # ── Top Leads Table ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔥 Top Leads — Quick View")

    sort_col = "LEAD_SCORE" if "LEAD_SCORE" in df.columns else df.columns[0]
    top = df.nlargest(15, sort_col) if sort_col in df.columns else df.head(15)

    show = [c for c in [
        "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","DISTRESS_TIER",
        "SITUS_ADDRESS","OWNER_NAME","OPPORTUNITY_TYPE",
        "ACRES","LOT_WIDTH","LAND_VALUE","IMPROVEMENT_VALUE",
        "NON_OWNER_OCCUPIED","ABSENTEE_OWNER","IS_ROCKWOOD",
    ] if c in top.columns]

    st.dataframe(top[show], use_container_width=True, hide_index=True)

    # ── Market summary ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Market Summary")
    m1, m2, m3, m4 = st.columns(4)

    if "ACRES" in df.columns:
        m1.metric("Avg Lot Size",
                  f"{df['ACRES'].mean():.2f} ac",
                  f"Median: {df['ACRES'].median():.2f} ac")
    if "LAND_VALUE" in df.columns:
        m2.metric("Avg Land Value",
                  f"${df['LAND_VALUE'].mean():,.0f}",
                  f"Median: ${df['LAND_VALUE'].median():,.0f}")
    if "IMPROVEMENT_VALUE" in df.columns:
        m3.metric("Avg Improvement",
                  f"${df['IMPROVEMENT_VALUE'].mean():,.0f}")
    if "LEAD_SCORE" in df.columns:
        m4.metric("Avg Lead Score",
                  f"{df['LEAD_SCORE'].mean():.1f}",
                  f"Max: {df['LEAD_SCORE'].max():.0f}")


def _show_getting_started():
    st.markdown("""
    ### Getting Started

    **Option 1 — Upload your leads CSV** *(fastest)*
    1. Run Notebook 01 in Google Colab
    2. Download `private_leads.csv`
    3. Upload it using the sidebar

    **Option 2 — Google Drive link**
    1. Save your leads CSV to Google Drive
    2. Get a shareable link (Anyone with link → Viewer)
    3. Paste the link in the sidebar

    **Option 3 — Live GIS pull**
    1. Enter municipality name (e.g. "Ballwin")
    2. Click "Pull Live Data"
    3. Waits ~30 seconds while it fetches fresh parcel data
    """)
