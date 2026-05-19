"""
pages/overview.py — Dashboard overview with KPIs and charts
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def fmt_col(col: str) -> str:
    return col.replace("_", " ").title()


def render(df, client):
    client_name  = client.get("name", "Dashboard")
    client_color = client.get("color", "#1d4ed8")

    st.markdown(f"""
    <h1>📊 Overview</h1>
    <p style='color:inherit;margin-bottom:28px;font-size:0.95rem'>
        {client_name} &nbsp;·&nbsp; Lead intelligence summary
    </p>
    """, unsafe_allow_html=True)

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to get started.")
        _getting_started()
        return

    total     = len(df)
    hot       = int((df.get("LEAD_TIER","") == "🔥 Hot").sum())
    warm      = int((df.get("LEAD_TIER","") == "⭐ Warm").sum())
    vacant    = int(df.get("IS_VACANT", pd.Series(dtype=bool)).sum())
    absentee  = int(df.get("ABSENTEE_OWNER", pd.Series(dtype=bool)).sum())
    high_dist = int((df.get("DISTRESS_SCORE", pd.Series(dtype=float)).fillna(0) >= 50).sum())

    # ── KPI Row ───────────────────────────────────────────────────────────────
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Leads",       f"{total:,}")
    c2.metric("🔥 Hot Leads",      f"{hot:,}",
              delta=f"{hot/total*100:.1f}% of total" if total else None)
    c3.metric("⭐ Warm Leads",     f"{warm:,}")
    c4.metric("Vacant Lots",       f"{vacant:,}")
    c5.metric("Absentee Owners",   f"{absentee:,}")
    c6.metric("🚨 High Distress",  f"{high_dist:,}")

    st.markdown("<div style='margin:24px 0 16px;border-top:1px solid #e2e8f0'></div>",
                unsafe_allow_html=True)

    # ── Charts row 1: Score dist + Opportunity pie ────────────────────────────
    st.markdown("### Lead Distribution")
    col1, col2 = st.columns([3, 2])

    with col1:
        if "LEAD_SCORE" in df.columns:
            fig = px.histogram(
                df, x="LEAD_SCORE", nbins=25,
                color_discrete_sequence=[client_color],
                labels={"LEAD_SCORE": "Lead Score", "count": "Parcels"},
                title="Lead Score Distribution",
            )
            fig.add_vline(x=70, line_dash="dash", line_color="#ef4444",
                          annotation_text="Hot ≥70",
                          annotation_font_color="#ef4444",
                          annotation_position="top right")
            fig.add_vline(x=50, line_dash="dash", line_color="#f97316",
                          annotation_text="Warm ≥50",
                          annotation_font_color="#f97316",
                          annotation_position="top right")
            fig.update_layout(
                height=320, margin=dict(t=40,b=20,l=20,r=20),
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(family="system-ui", size=12),
                title_font_size=14,
            )
            fig.update_xaxes(showgrid=False, title="Lead Score")
            fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", title="Parcels")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "OPPORTUNITY_TYPE" in df.columns:
            counts = df["OPPORTUNITY_TYPE"].value_counts()
            fig2 = px.pie(
                values=counts.values,
                names=counts.index,
                color_discrete_sequence=["#3b82f6","#f97316","#22c55e"],
                hole=0.55,
                title="Opportunity Types",
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label")
            fig2.update_layout(
                height=320, margin=dict(t=40,b=20,l=20,r=20),
                showlegend=False,
                paper_bgcolor="white",
                font=dict(family="system-ui", size=12),
                title_font_size=14,
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # ── Charts row 2: Distress signals + Scatter ──────────────────────────────
    st.markdown("### Market Intelligence")
    col3, col4 = st.columns(2)

    with col3:
        signals = {
            "Non-Owner Occupied":  int(df.get("NON_OWNER_OCCUPIED", pd.Series()).sum()),
            "Old Structure 50+yr": int(df.get("OLD_STRUCTURE", pd.Series()).sum()),
            "Absentee Owner":      int(df.get("ABSENTEE_OWNER", pd.Series()).sum()),
            "Multi-Parcel Owner":  int(df.get("MULTI_PARCEL_OWNER", pd.Series()).sum()),
            "Near Flood Zone":     int(df.get("NEAR_FLOOD_ZONE", pd.Series()).sum()),
            "High Distress ≥50":   int((df.get("DISTRESS_SCORE",
                                         pd.Series(dtype=float)).fillna(0) >= 50).sum()),
        }
        sig_df = pd.DataFrame({"Signal": list(signals.keys()),
                               "Count":  list(signals.values())})
        sig_df = sig_df.sort_values("Count", ascending=True)
        fig3 = px.bar(
            sig_df, x="Count", y="Signal", orientation="h",
            color_discrete_sequence=["#dc2626"],
            title="Distress Signals",
            labels={"Count": "Parcels", "Signal": ""},
        )
        fig3.update_layout(
            height=320, margin=dict(t=40,b=20,l=20,r=20),
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="system-ui", size=12), title_font_size=14,
        )
        fig3.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
        fig3.update_yaxes(showgrid=False)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        if "LEAD_SCORE" in df.columns and "DISTRESS_SCORE" in df.columns:
            plot_df = df.dropna(subset=["LEAD_SCORE","DISTRESS_SCORE"]).copy()
            plot_df = plot_df[plot_df["DISTRESS_SCORE"] > 0]
            if not plot_df.empty:
                hover_data = {}
                if "SITUS_ADDRESS" in plot_df.columns:
                    hover_data["SITUS_ADDRESS"] = True
                if "OWNER_NAME" in plot_df.columns:
                    hover_data["OWNER_NAME"] = True
                if "OPPORTUNITY_TYPE" in plot_df.columns:
                    hover_data["OPPORTUNITY_TYPE"] = True

                fig4 = px.scatter(
                    plot_df,
                    x="LEAD_SCORE",
                    y="DISTRESS_SCORE",
                    color="OPPORTUNITY_TYPE" if "OPPORTUNITY_TYPE" in plot_df.columns else None,
                    hover_data=hover_data if hover_data else None,
                    labels={
                        "LEAD_SCORE":    "Opportunity Score",
                        "DISTRESS_SCORE":"Distress Score",
                        "OPPORTUNITY_TYPE": "Type",
                        "SITUS_ADDRESS": "Address",
                        "OWNER_NAME":    "Owner",
                    },
                    title="Opportunity vs Distress Score",
                    opacity=0.65,
                    color_discrete_map={
                        "Vacant Land":         "#3b82f6",
                        "Teardown Candidate":  "#f97316",
                        "Large Lot":           "#22c55e",
                    },
                )
                # Best leads quadrant
                fig4.add_shape(
                    type="rect", x0=50, y0=30, x1=105, y1=105,
                    fillcolor="rgba(220,38,38,0.04)",
                    line=dict(color="rgba(220,38,38,0.25)", dash="dash", width=1),
                )
                fig4.add_annotation(
                    x=77, y=98, text="Best leads",
                    showarrow=False,
                    font=dict(color="#dc2626", size=11, family="system-ui"),
                )
                fig4.update_layout(
                    height=320, margin=dict(t=40,b=20,l=20,r=20),
                    plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family="system-ui", size=12), title_font_size=14,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1),
                )
                fig4.update_xaxes(showgrid=True, gridcolor="#f1f5f9",
                                   range=[0, 105], title="Opportunity Score")
                fig4.update_yaxes(showgrid=True, gridcolor="#f1f5f9",
                                   range=[0, 105], title="Distress Score")
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("<div style='margin:8px 0 0;border-top:1px solid #e2e8f0'></div>",
                unsafe_allow_html=True)

    # ── Top leads table ───────────────────────────────────────────────────────
    st.markdown("### 🔥 Top Leads")

    sort_col = "LEAD_SCORE" if "LEAD_SCORE" in df.columns else df.columns[0]
    top = df.nlargest(20, sort_col) if sort_col in df.columns else df.head(20)

    show = [c for c in [
        "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","DISTRESS_TIER",
        "SITUS_ADDRESS","OWNER_NAME","OPPORTUNITY_TYPE",
        "ACRES","LOT_WIDTH","LAND_VALUE","IMPROVEMENT_VALUE",
        "NON_OWNER_OCCUPIED","ABSENTEE_OWNER","IS_ROCKWOOD",
    ] if c in top.columns]

    # Rename columns for display
    display_top = top[show].copy()
    display_top.columns = [fmt_col(c) for c in display_top.columns]

    st.dataframe(display_top, use_container_width=True, hide_index=True, height=420)

    # ── Market summary ────────────────────────────────────────────────────────
    st.markdown("<div style='margin:8px 0 0;border-top:1px solid #e2e8f0'></div>",
                unsafe_allow_html=True)
    st.markdown("### Market Summary")
    m1,m2,m3,m4 = st.columns(4)

    if "ACRES" in df.columns:
        m1.metric("Avg Lot Size",
                  f"{df['ACRES'].mean():.2f} ac",
                  f"Median: {df['ACRES'].median():.2f} ac")
    if "LAND_VALUE" in df.columns:
        m2.metric("Avg Land Value",
                  f"${df['LAND_VALUE'].mean():,.0f}",
                  f"Median: ${df['LAND_VALUE'].median():,.0f}")
    if "IMPROVEMENT_VALUE" in df.columns:
        m3.metric("Avg Improvement", f"${df['IMPROVEMENT_VALUE'].mean():,.0f}")
    if "LEAD_SCORE" in df.columns:
        m4.metric("Avg Lead Score",
                  f"{df['LEAD_SCORE'].mean():.1f}",
                  f"Top score: {df['LEAD_SCORE'].max():.0f}")


def _getting_started():
    st.markdown("""
    <div style='background:white;border:1px solid #e2e8f0;border-radius:12px;
                padding:32px;margin-top:16px'>
        <h3 style='margin-top:0'>Getting Started</h3>
        <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px'>
            <div>
                <div style='font-weight:600;color:#1d4ed8;margin-bottom:6px'>
                    Option 1 — Upload CSV
                </div>
                <p style='color:inherit;font-size:0.9rem'>
                    Run Notebook 01 in Google Colab, download
                    <code>private_leads.csv</code>, then upload it using
                    the sidebar.
                </p>
            </div>
            <div>
                <div style='font-weight:600;color:#1d4ed8;margin-bottom:6px'>
                    Option 2 — Google Drive
                </div>
                <p style='color:inherit;font-size:0.9rem'>
                    Save your CSV to Google Drive, get a shareable link,
                    and paste it in the sidebar.
                </p>
            </div>
            <div>
                <div style='font-weight:600;color:#1d4ed8;margin-bottom:6px'>
                    Option 3 — Live Pull
                </div>
                <p style='color:inherit;font-size:0.9rem'>
                    Enter a municipality and click Pull Live Data to fetch
                    fresh parcels directly from STL County GIS (~30 sec).
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
