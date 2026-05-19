"""
components/map_builder.py — Build Folium map from leads DataFrame
"""
import folium
import pandas as pd
import numpy as np


TIER_COLORS = {
    "🔥 Hot":   {"color": "red",    "radius": 10},
    "⭐ Warm":  {"color": "orange", "radius": 7},
    "🌡️ Cool":  {"color": "blue",   "radius": 5},
    "❄️ Cold":  {"color": "gray",   "radius": 4},
}

DISTRESS_COLOR = "#dc2626"
FLOOD_COLOR    = "#06b6d4"
COMM_COLOR     = "purple"

BALLWIN_CENTER = [38.5953, -90.5454]


def _popup(row: pd.Series) -> folium.Popup:
    addr   = str(row.get("SITUS_ADDRESS", "")).title()
    owner  = str(row.get("OWNER_NAME", "")).title()
    score  = row.get("LEAD_SCORE", 0) or 0
    tier   = row.get("LEAD_TIER", "")
    dst    = row.get("DISTRESS_SCORE", 0) or 0
    dtier  = row.get("DISTRESS_TIER", "")
    opp    = row.get("OPPORTUNITY_TYPE", "")
    acres  = round(float(row.get("ACRES") or 0), 2)
    width  = row.get("LOT_WIDTH", None)
    ws     = f"{int(width)}ft" if pd.notna(width) and width else "?"
    land   = row.get("LAND_VALUE", 0) or 0
    imp    = row.get("IMPROVEMENT_VALUE", 0) or 0
    tax    = row.get("EST_ANNUAL_TAX", 0) or 0
    yr     = int(row.get("YEAR_BUILT") or 0) or "—"
    ab     = "Yes ⚡" if row.get("ABSENTEE_OWNER") else "No"
    noo    = "Yes ⚡" if row.get("NON_OWNER_OCCUPIED") else "No"
    multi  = str(int(row.get("OWNER_PARCEL_COUNT", 1) or 1))
    flood  = "Yes ⚠️" if row.get("NEAR_FLOOD_ZONE") else "No"
    sc     = row.get("SCHOOL_DISTRICT", "")
    sc_str = str(sc).title() if pd.notna(sc) else "?"
    c_opp  = "#ef4444" if score >= 70 else "#f97316" if score >= 50 else "#3b82f6"
    c_dst  = "#dc2626" if dst >= 50 else "#ea580c" if dst >= 30 else "#64748b"

    html = (
        f"<div style='font-family:system-ui;min-width:250px;font-size:12px'>"
        f"<div style='background:#1f2937;color:white;padding:8px;margin:-10px -10px 8px;"
        f"border-radius:6px 6px 0 0'>"
        f"<b style='font-size:13px'>{addr}</b><br>"
        f"<span style='opacity:.8'>{opp}</span></div>"
        f"<div style='display:flex;gap:6px;margin-bottom:8px'>"
        f"<span style='background:{c_opp};color:white;padding:2px 8px;"
        f"border-radius:4px;font-size:11px'>⭐ {score}/100 {tier}</span>"
        f"<span style='background:{c_dst};color:white;padding:2px 8px;"
        f"border-radius:4px;font-size:11px'>🚨 {dst} {dtier}</span></div>"
        f"<table style='width:100%;border-collapse:collapse;font-size:12px'>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Owner</td>"
        f"<td style='text-align:right;font-weight:600'>{owner}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Lot</td>"
        f"<td style='text-align:right'>{acres} ac | {ws} wide</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>School Dist</td>"
        f"<td style='text-align:right'>{sc_str}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Land value</td>"
        f"<td style='text-align:right'>${land:,.0f}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Improvement</td>"
        f"<td style='text-align:right'>${imp:,.0f}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Year built</td>"
        f"<td style='text-align:right'>{yr}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Est tax/yr</td>"
        f"<td style='text-align:right'>${tax:,.0f}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Non-owner occ</td>"
        f"<td style='text-align:right'>{noo}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Absentee</td>"
        f"<td style='text-align:right'>{ab}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Owner parcels</td>"
        f"<td style='text-align:right'>{multi}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:2px 4px'>Near flood</td>"
        f"<td style='text-align:right'>{flood}</td></tr>"
        f"</table></div>"
    )
    return folium.Popup(html, max_width=300)


def build_map(
    df: pd.DataFrame,
    center: list = BALLWIN_CENTER,
    zoom: int = 13,
    show_commercial: bool = False,
    show_flood: bool = False,
    show_cool: bool = False,
    tiles: str = "CartoDB positron",
) -> folium.Map:
    """Build and return a Folium map from a leads DataFrame."""

    m = folium.Map(location=center, zoom_start=zoom, tiles=tiles)

    # Layer groups
    hot_grp      = folium.FeatureGroup(name="🔥 Hot leads (score ≥70)",    show=True)
    warm_grp     = folium.FeatureGroup(name="⭐ Warm leads (score 50–69)",  show=True)
    cool_grp     = folium.FeatureGroup(name="🌡️ Cool leads (score 30–49)", show=show_cool)
    distress_grp = folium.FeatureGroup(name="🚨 High distress leads",       show=True)
    flood_grp    = folium.FeatureGroup(name="🌊 Near flood zone",           show=show_flood)
    comm_grp     = folium.FeatureGroup(name="🏢 Commercial/LLC owners",     show=show_commercial)

    mappable = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
    mappable = mappable[
        mappable["LATITUDE"].between(38.3, 39.0) &
        mappable["LONGITUDE"].between(-91.0, -90.0)
    ]

    for _, row in mappable.iterrows():
        tier     = row.get("LEAD_TIER", "🌡️ Cool")
        dst      = row.get("DISTRESS_SCORE", 0) or 0
        is_comm  = row.get("IS_COMMERCIAL", False)
        near_fl  = row.get("NEAR_FLOOD_ZONE", False)
        popup    = _popup(row)
        tooltip  = (
            str(row.get("SITUS_ADDRESS", "")).title() +
            f" | Score:{row.get('LEAD_SCORE',0):.0f}"
            f" Distress:{dst:.0f}"
        )

        # Routing logic
        if near_fl:
            color, radius, grp = FLOOD_COLOR, 5, flood_grp
        elif is_comm:
            color, radius, grp = COMM_COLOR, 7, comm_grp
        elif dst >= 50:
            color, radius, grp = DISTRESS_COLOR, 11, distress_grp
        elif tier == "🔥 Hot":
            color, radius, grp = "red", 10, hot_grp
        elif tier == "⭐ Warm":
            color, radius, grp = "orange", 7, warm_grp
        else:
            color, radius, grp = "blue", 5, cool_grp

        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=popup,
            tooltip=tooltip,
        ).add_to(grp)

    for grp in [hot_grp, warm_grp, cool_grp, distress_grp, flood_grp, comm_grp]:
        m.add_child(grp)

    folium.LayerControl(collapsed=False).add_to(m)

    # Legend
    m.get_root().html.add_child(folium.Element(
        "<div style='position:fixed;bottom:40px;left:20px;background:white;"
        "border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;"
        "font-family:system-ui;font-size:12px;z-index:9999;"
        "box-shadow:0 2px 8px rgba(0,0,0,.1)'>"
        "<b style='display:block;margin-bottom:6px'>Legend</b>"
        "<div>🔴 Hot — Opportunity ≥70</div>"
        "<div>🟠 Warm — Opportunity 50–69</div>"
        "<div>🔵 Cool — Opportunity 30–49</div>"
        "<div>🟥 High Distress — Distress ≥50</div>"
        "<div>🔵 Near flood zone</div>"
        "<div>🟣 Commercial/LLC</div>"
        "<hr style='margin:6px 0'>"
        "<small>Click any dot for details</small>"
        "</div>"
    ))

    return m
