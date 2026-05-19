"""
pages/overview.py — Dashboard overview
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

DARK  = "#0f172a"
MID   = "#475569"
LIGHT = "#f1f5f9"
WHITE = "#ffffff"

def fmt_col(col: str) -> str:
    return col.replace("_", " ").title()

def chart_layout(fig, title="", height=320):
    """Apply consistent readable styling to any plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(color=DARK, size=14, family="Arial"),
                   x=0, xanchor="left"),
        height=height,
        margin=dict(t=45, b=10, l=10, r=10),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(family="Arial", size=12, color=DARK),
        legend=dict(
            font=dict(color=DARK, size=11, family="Arial"),
            bgcolor=WHITE,
            bordercolor="#e2e8f0",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(
        tickfont=dict(color=DARK, size=11, family="Arial"),
        titlefont=dict(color=DARK, size=12, family="Arial"),
        showgrid=True, gridcolor="#f1f5f9",
        linecolor="#e2e8f0",
    )
    fig.update_yaxes(
        tickfont=dict(color=DARK, size=11, family="Arial"),
        titlefont=dict(color=DARK, size=12, family="Arial"),
        showgrid=True, gridcolor="#f1f5f9",
        linecolor="#e2e8f0",
    )
    return fig


def render(df, client):
    client_name  = client.get("name", "Dashboard")
    client_color = client.get("color", "#1d4ed8")

    st.markdown(f"## 📊 Overview")
    st.caption(f"{client_name} — Lead intelligence summary")

    if df is None or df.empty:
        st.info("👈 Load your leads data using the sidebar to get started.")
        _getting_started()
        return

    total     = len(df)
    hot       = int((df.get("LEAD_TIER", pd.Series(dtype=str)) == "🔥 Hot").sum())
    warm      = int((df.get("LEAD_TIER", pd.Series(dtype=str)) == "⭐ Warm").sum())
    vacant    = int(df.get("IS_VACANT", pd.Series(dtype=bool)).sum())
    absentee  = int(df.get("ABSENTEE_OWNER", pd.Series(dtype=bool)).sum())
    high_dist = int((df.get("DISTRESS_SCORE", pd.Series(dtype=float)).fillna(0) >= 50).sum())

    # ── KPI Row ───────────────────────────────────────────────────────────
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

    # ── Score histogram ───────────────────────────────────────────────────
    with col1:
        if "LEAD_SCORE" in df.columns:
            fig = px.histogram(
                df, x="LEAD_SCORE", nbins=25,
                color_discrete_sequence=[client_color],
                labels={"LEAD_SCORE": "Lead Score", "count": "Parcels"},
            )
            fig.add_vline(x=70, line_dash="dash", line_color="#ef4444",
                          annotation_text="Hot",
                          annotation_font=dict(color="#ef4444", size=11),
                          annotation_position="top right")
            fig.add_vline(x=50, line_dash="dash", line_color="#f97316",
                          annotation_text="Warm",
                          annotation_font=dict(color="#f97316", size=11),
                          annotation_position="top right")
            fig.update_xaxes(title_text="Lead Score")
            fig.update_yaxes(title_text="Parcels", showgrid=True, gridcolor=LIGHT)
            fig = chart_layout(fig, title="Lead Score Distribution")
            st.plotly_chart(fig, use_container_width=True)

    # ── Pie chart ─────────────────────────────────────────────────────────
    with col2:
        if "OPPORTUNITY_TYPE" in df.columns:
            counts = df["OPPORTUNITY_TYPE"].value_counts()
            fig2 = go.Figure(data=[go.Pie(
                labels=counts.index.tolist(),
                values=counts.values.tolist(),
                hole=0.45,
                marker_colors=["#3b82f6", "#f97316", "#22c55e"],
                textinfo="percent",
                textfont=dict(size=12, color=WHITE, family="Arial"),
                insidetextorientation="auto",
            )])
            fig2.update_layout(
                title=dict(text="Opportunity Types",
                           font=dict(color=DARK, size=14, family="Arial"),
                           x=0, xanchor="left"),
                height=320,
                margin=dict(t=45, b=70, l=10, r=10),
                paper_bgcolor=WHITE,
                font=dict(family="Arial", size=12, color=DARK),
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=-0.35,
                    xanchor="center", x=0.5,
                    font=dict(color=DARK, size=11, family="Arial"),
                    bgcolor=WHITE,
                ),
                showlegend=True,
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Market Intelligence")
    col3, col4 = st.columns(2)

    # ── Distress signals bar ──────────────────────────────────────────────
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
            textfont=dict(color=DARK, size=11, family="Arial"),
        ))
        fig3.update_xaxes(title_text="Parcels", showgrid=True, gridcolor=LIGHT,
                          tickfont=dict(color=DARK, size=11),
                          titlefont=dict(color=DARK, size=12))
        fig3.update_yaxes(tickfont=dict(color=DARK, size=11),
                          titlefont=dict(color=DARK, size=12))
        fig3 = chart_layout(fig3, title="Distress Signals")
        st.plotly_chart(fig3, use_container_width=True)

    # ── Scatter ───────────────────────────────────────────────────────────
    with col4:
        if "LEAD_SCORE" in df.columns and "DISTRESS_SCORE" in df.columns:
            plot_df = df.dropna(subset=["LEAD_SCORE","DISTRESS_SCORE"]).copy()
            plot_df = plot_df[plot_df["DISTRESS_SCORE"] > 0]

            if not plot_df.empty:
                color_col = "OPPORTUNITY_TYPE" if "OPPORTUNITY_TYPE" in plot_df.columns else None
                color_map = {
                    "Vacant Land":        "#3b82f6",
                    "Teardown Candidate": "#f97316",
                    "Large Lot":          "#22c55e",
                }
                fig4 = go.Figure()

                if color_col:
                    for opp_type, color in color_map.items():
                        sub = plot_df[plot_df[color_col] == opp_type]
                        if not sub.empty:
                            fig4.add_trace(go.Scatter(
                                x=sub["LEAD_SCORE"],
                                y=sub["DISTRESS_SCORE"],
                                mode="markers",
                                name=opp_type,
                                marker=dict(color=color, size=7, opacity=0.7),
                                text=sub.get("SITUS_ADDRESS",
                                    pd.Series([""] * len(sub))).fillna(""),
                                hovertemplate=(
                                    "<b>%{text}</b><br>"
                                    "Score: %{x}<br>"
                                    "Distress: %{y}<extra></extra>"
                                ),
                            ))
                else:
                    fig4.add_trace(go.Scatter(
                        x=plot_df["LEAD_SCORE"],
                        y=plot_df["DISTRESS_SCORE"],
                        mode="markers",
                        marker=dict(color=client_color, size=7, opacity=0.7),
                    ))

                # Best leads quadrant
                fig4.add_shape(type="rect", x0=50, y0=30, x1=105, y1=105,
                               fillcolor="rgba(220,38,38,0.05)",
                               line=dict(color="rgba(220,38,38,0.3)",
                                         dash="dash", width=1))
                fig4.add_annotation(x=77, y=98, text="Best leads",
                                    showarrow=False,
                                    font=dict(color="#dc2626", size=11, family="Arial"))

                fig4.update_xaxes(title_text="Opportunity Score", range=[0,105])
                fig4.update_yaxes(title_text="Distress Score",    range=[0,105])
                fig4 = chart_layout(fig4, title="Opportunity vs Distress Score")
                fig4.update_layout(legend=dict(
                    font=dict(color=DARK, size=11, family="Arial"),
                    bgcolor=WHITE, bordercolor="#e2e8f0", borderwidth=1,
                    orientation="h", yanchor="bottom", y=-0.35,
                    xanchor="center", x=0.5,
                ))
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
        m3.metric("Avg Improvement", f"${df['IMPROVEMENT_VALUE'].mean():,.0f}")
    if "LEAD_SCORE" in df.columns:
        m4.metric("Avg Lead Score",
                  f"{df['LEAD_SCORE'].mean():.1f}",
                  f"Top: {df['LEAD_SCORE'].max():.0f}")


def _getting_started():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Option 1 — Upload CSV**")
        st.caption("Run Notebook 01, download private_leads.csv, upload via sidebar.")
    with col2:
        st.markdown("**Option 2 — Google Drive**")
        st.caption("Save CSV to Drive, get share link, paste in sidebar.")
    with col3:
        st.markdown("**Option 3 — Live Pull**")
        st.caption("Enter municipality, click Pull Live Data (~30 sec).")
