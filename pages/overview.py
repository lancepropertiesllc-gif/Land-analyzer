"""
pages/overview.py — Dashboard overview
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DARK = "#0f172a"

def fmt_col(col: str) -> str:
    return col.replace("_", " ").title()

def fix(fig, title="", height=320):
    """Force all text to dark on every chart element."""
    fig.update_layout(
        title_text=title,
        title_font_color=DARK,
        title_font_size=14,
        height=height,
        margin=dict(t=45, b=10, l=10, r=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color=DARK,
        font_size=12,
        legend_font_color=DARK,
        legend_bgcolor="#ffffff",
        legend_bordercolor="#e2e8f0",
        legend_borderwidth=1,
    )
    fig.update_xaxes(
        color=DARK,
        tickcolor=DARK,
        tickfont_color=DARK,
        title_font_color=DARK,
        gridcolor="#f1f5f9",
        linecolor="#e2e8f0",
    )
    fig.update_yaxes(
        color=DARK,
        tickcolor=DARK,
        tickfont_color=DARK,
        title_font_color=DARK,
        gridcolor="#f1f5f9",
        linecolor="#e2e8f0",
    )
    return fig


def render(df, client):
    client_name  = client.get("name", "Dashboard")
    client_color = client.get("color", "#1d4ed8")

    st.markdown("## 📊 Overview")
    st.caption(f"{client_name} — Lead intelligence summary")

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to get started.")
        st.markdown("**Option 1** — Upload CSV from Notebook 01")
        st.markdown("**Option 2** — Paste a Google Drive share link")
        st.markdown("**Option 3** — Pull live from STL County GIS")
        return

    total     = len(df)
    hot       = int((df.get("LEAD_TIER", pd.Series(dtype=str)) == "🔥 Hot").sum())
    warm      = int((df.get("LEAD_TIER", pd.Series(dtype=str)) == "⭐ Warm").sum())
    vacant    = int(df.get("IS_VACANT", pd.Series(dtype=bool)).sum())
    absentee  = int(df.get("ABSENTEE_OWNER", pd.Series(dtype=bool)).sum())
    high_dist = int((df.get("DISTRESS_SCORE", pd.Series(dtype=float)).fillna(0) >= 50).sum())

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Leads",      f"{total:,}")
    c2.metric("🔥 Hot Leads",     f"{hot:,}")
    c3.metric("⭐ Warm Leads",    f"{warm:,}")
    c4.metric("Vacant Lots",      f"{vacant:,}")
    c5.metric("Absentee Owners",  f"{absentee:,}")
    c6.metric("🚨 High Distress", f"{high_dist:,}")

    st.markdown("---")
    st.markdown("### Lead Distribution")
    col1, col2 = st.columns([3, 2])

    with col1:
        if "LEAD_SCORE" in df.columns:
            fig = px.histogram(
                df, x="LEAD_SCORE", nbins=25,
                color_discrete_sequence=[client_color],
            )
            fig.add_vline(x=70, line_dash="dash", line_color="#ef4444",
                          annotation_text="Hot",
                          annotation_font_color="#ef4444",
                          annotation_position="top right")
            fig.add_vline(x=50, line_dash="dash", line_color="#f97316",
                          annotation_text="Warm",
                          annotation_font_color="#f97316",
                          annotation_position="top right")
            fig.update_xaxes(title_text="Lead Score")
            fig.update_yaxes(title_text="Parcels")
            fig = fix(fig, title="Lead Score Distribution")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "OPPORTUNITY_TYPE" in df.columns:
            counts = df["OPPORTUNITY_TYPE"].value_counts()
            fig2 = go.Figure(data=[go.Pie(
                labels=counts.index.tolist(),
                values=counts.values.tolist(),
                hole=0.4,
                marker_colors=["#3b82f6","#f97316","#22c55e"],
                textinfo="percent+label",
                textfont_color=DARK,
                textfont_size=11,
                insidetextorientation="auto",
            )])
            fig2.update_layout(
                title_text="Opportunity Types",
                title_font_color=DARK,
                title_font_size=14,
                height=320,
                margin=dict(t=45, b=10, l=10, r=10),
                paper_bgcolor="#ffffff",
                font_color=DARK,
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Market Intelligence")
    col3, col4 = st.columns(2)

    with col3:
        signals = {
            "Non-Owner Occupied":  int(df.get("NON_OWNER_OCCUPIED", pd.Series()).sum()),
            "Old Structure 50+yr": int(df.get("OLD_STRUCTURE", pd.Series()).sum()),
            "Absentee Owner":      int(df.get("ABSENTEE_OWNER", pd.Series()).sum()),
            "Multi-Parcel Owner":  int(df.get("MULTI_PARCEL_OWNER", pd.Series()).sum()),
            "Near Flood Zone":     int(df.get("NEAR_FLOOD_ZONE", pd.Series()).sum()),
            "High Distress 50+":   int((df.get("DISTRESS_SCORE",
                                    pd.Series(dtype=float)).fillna(0) >= 50).sum()),
        }
        sig_df = pd.DataFrame({
            "Signal": list(signals.keys()),
            "Count":  list(signals.values()),
        }).sort_values("Count", ascending=True)

        fig3 = go.Figure(go.Bar(
            x=sig_df["Count"],
            y=sig_df["Signal"],
            orientation="h",
            marker_color="#dc2626",
            text=sig_df["Count"],
            textposition="outside",
            textfont_color=DARK,
            textfont_size=11,
        ))
        fig3.update_xaxes(title_text="Parcels")
        fig3 = fix(fig3, title="Distress Signals")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        if "LEAD_SCORE" in df.columns and "DISTRESS_SCORE" in df.columns:
            plot_df = df.dropna(subset=["LEAD_SCORE","DISTRESS_SCORE"]).copy()
            plot_df = plot_df[plot_df["DISTRESS_SCORE"] > 0]

            if not plot_df.empty:
                color_map = {
                    "Vacant Land":        "#3b82f6",
                    "Teardown Candidate": "#f97316",
                    "Large Lot":          "#22c55e",
                }
                fig4 = go.Figure()
                if "OPPORTUNITY_TYPE" in plot_df.columns:
                    for opp, color in color_map.items():
                        sub = plot_df[plot_df["OPPORTUNITY_TYPE"] == opp]
                        if not sub.empty:
                            hover = sub.get("SITUS_ADDRESS",
                                    pd.Series([""] * len(sub))).fillna("")
                            fig4.add_trace(go.Scatter(
                                x=sub["LEAD_SCORE"],
                                y=sub["DISTRESS_SCORE"],
                                mode="markers",
                                name=opp,
                                marker_color=color,
                                marker_size=7,
                                opacity=0.7,
                                text=hover,
                                hovertemplate="<b>%{text}</b><br>Score: %{x}<br>Distress: %{y}<extra></extra>",
                            ))

                fig4.add_shape(
                    type="rect", x0=50, y0=30, x1=105, y1=105,
                    fillcolor="rgba(220,38,38,0.05)",
                    line_color="rgba(220,38,38,0.3)",
                    line_dash="dash", line_width=1,
                )
                fig4.add_annotation(
                    x=77, y=98, text="Best leads", showarrow=False,
                    font_color="#dc2626", font_size=11,
                )
                fig4.update_xaxes(title_text="Opportunity Score", range=[0,105])
                fig4.update_yaxes(title_text="Distress Score",    range=[0,105])
                fig4 = fix(fig4, title="Opportunity vs Distress Score")
                fig4.update_layout(
                    legend_font_color=DARK,
                    legend_orientation="h",
                    legend_yanchor="bottom", legend_y=-0.35,
                    legend_xanchor="center", legend_x=0.5,
                )
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🔥 Top Leads")
    sort_col = "LEAD_SCORE" if "LEAD_SCORE" in df.columns else df.columns[0]
    top = df.nlargest(20, sort_col) if sort_col in df.columns else df.head(20)
    show = [c for c in [
        "LEAD_SCORE","LEAD_TIER","DISTRESS_SCORE","DISTRESS_TIER",
        "SITUS_ADDRESS","OWNER_NAME","OPPORTUNITY_TYPE",
        "ACRES","LOT_WIDTH","LAND_VALUE","IMPROVEMENT_VALUE",
        "NON_OWNER_OCCUPIED","ABSENTEE_OWNER","IS_ROCKWOOD",
    ] if c in top.columns]
    display_top = top[show].copy()
    display_top.columns = [fmt_col(c) for c in display_top.columns]
    st.dataframe(display_top, use_container_width=True, hide_index=True, height=420)

    st.markdown("---")
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
        m3.metric("Avg Improvement",
                  f"${df['IMPROVEMENT_VALUE'].mean():,.0f}")
    if "LEAD_SCORE" in df.columns:
        m4.metric("Avg Lead Score",
                  f"{df['LEAD_SCORE'].mean():.1f}",
                  f"Top: {df['LEAD_SCORE'].max():.0f}")
