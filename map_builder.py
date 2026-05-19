"""
components/map_builder.py — Build Folium map from leads DataFrame
"""
import folium
import pandas as pd
import numpy as np

BALLWIN_CENTER = [38.5953, -90.5454]

# Only use tiles that work without attribution issues
TILE_OPTIONS = {
    "Light (Default)":   "CartoDB positron",
    "Dark Mode":         "CartoDB dark_matter",
    "Street Map":        "OpenStreetMap",
}


def clean_col(name: str) -> str:
    """Replace underscores with spaces for display."""
    return str(name).replace("_", " ").title()


def _popup(row: pd.Series) -> folium.Popup:
    addr  = str(row.get("SITUS_ADDRESS", "")).title()
    owner = str(row.get("OWNER_NAME", "")).title()
    score = float(row.get("LEAD_SCORE", 0) or 0)
    tier  = str(row.get("LEAD_TIER", ""))
    dst   = float(row.get("DISTRESS_SCORE", 0) or 0)
    dtier = str(row.get("DISTRESS_TIER", ""))
    opp   = str(row.get("OPPORTUNITY_TYPE", ""))
    acres = round(float(row.get("ACRES") or 0), 2)
    width = row.get("LOT_WIDTH", None)
    ws    = f"{int(width)}ft" if pd.notna(width) and width else "Unknown"
    land  = float(row.get("LAND_VALUE", 0) or 0)
    imp   = float(row.get("IMPROVEMENT_VALUE", 0) or 0)
    yr    = int(row.get("YEAR_BUILT") or 0) or "—"
    ab    = "Yes ⚡" if row.get("ABSENTEE_OWNER") else "No"
    noo   = "Yes ⚡" if row.get("NON_OWNER_OCCUPIED") else "No"
    multi = str(int(row.get("OWNER_PARCEL_COUNT", 1) or 1))
    sc    = str(row.get("SCHOOL_DISTRICT", "")).title()
    flood = "Yes ⚠️" if row.get("NEAR_FLOOD_ZONE") else "No"
    c_opp = "#ef4444" if score >= 70 else "#f97316" if score >= 50 else "#3b82f6"
    c_dst = "#dc2626" if dst >= 50 else "#ea580c" if dst >= 30 else "#64748b"

    rows = [
        ("Owner",          owner),
        ("Lot Size",       f"{acres} ac  |  {ws} wide"),
        ("School Dist",    sc),
        ("Land Value",     f"${land:,.0f}"),
        ("Improvement",    f"${imp:,.0f}"),
        ("Year Built",     str(yr)),
        ("Non-Owner Occ",  noo),
        ("Absentee",       ab),
        ("Owner Parcels",  multi),
        ("Near Flood",     flood),
    ]
    table_rows = "".join(
        f"<tr><td style='color:#6b7280;padding:2px 6px 2px 0;white-space:nowrap'>"
        f"{label}</td><td style='text-align:right;font-weight:500'>{val}</td></tr>"
        for label, val in rows
    )

    html = f"""
    <div style='font-family:system-ui,sans-serif;min-width:260px;font-size:12px'>
        <div style='background:#1f2937;color:white;padding:10px 12px;
                    margin:-10px -10px 10px;border-radius:6px 6px 0 0'>
            <b style='font-size:13px'>{addr}</b><br>
            <span style='opacity:.75;font-size:11px'>{opp}</span>
        </div>
        <div style='display:flex;gap:6px;margin-bottom:8px'>
            <span style='background:{c_opp};color:white;padding:3px 10px;
                         border-radius:20px;font-size:11px;font-weight:600'>
                ⭐ {score:.0f}/100 {tier}
            </span>
            <span style='background:{c_dst};color:white;padding:3px 10px;
                         border-radius:20px;font-size:11px;font-weight:600'>
                🚨 {dst:.0f} {dtier}
            </span>
        </div>
        <table style='width:100%;border-collapse:collapse'>
            {table_rows}
        </table>
    </div>"""
    return folium.Popup(html, max_width=300)


def build_map(
    df: pd.DataFrame,
    center: list = BALLWIN_CENTER,
    zoom: int = 13,
    show_commercial: bool = False,
    show_flood: bool = False,
    show_cool: bool = True,
    tile_label: str = "Light (Default)",
) -> folium.Map:
    """Build Folium map. tile_label must be a key in TILE_OPTIONS."""
    tiles = TILE_OPTIONS.get(tile_label, "CartoDB positron")
    m = folium.Map(location=center, zoom_start=zoom, tiles=tiles)

    # Layer groups — shown/hidden by default
    hot_grp      = folium.FeatureGroup(name="🔴 Hot Leads (Score ≥ 70)",     show=True)
    warm_grp     = folium.FeatureGroup(name="🟠 Warm Leads (Score 50–69)",    show=True)
    cool_grp     = folium.FeatureGroup(name="🔵 Cool Leads (Score 30–49)",    show=show_cool)
    distress_grp = folium.FeatureGroup(name="🟥 High Distress (Distress ≥ 50)", show=True)
    flood_grp    = folium.FeatureGroup(name="💧 Near Flood Zone",             show=show_flood)
    comm_grp     = folium.FeatureGroup(name="🟣 Commercial / LLC Owners",     show=show_commercial)

    # Filter to mappable rows
    mappable = df.dropna(subset=["LATITUDE","LONGITUDE"]).copy()
    mappable = mappable[
        mappable["LATITUDE"].between(38.3, 39.0) &
        mappable["LONGITUDE"].between(-91.0, -90.0)
    ]

    for _, row in mappable.iterrows():
        tier    = str(row.get("LEAD_TIER", "🌡️ Cool"))
        dst     = float(row.get("DISTRESS_SCORE", 0) or 0)
        is_comm = bool(row.get("IS_COMMERCIAL", False))
        near_fl = bool(row.get("NEAR_FLOOD_ZONE", False))
        popup   = _popup(row)
        score   = float(row.get("LEAD_SCORE", 0) or 0)
        tooltip = f"{str(row.get('SITUS_ADDRESS','')).title()} | Score: {score:.0f} | Distress: {dst:.0f}"

        # Priority routing — most specific first
        if near_fl:
            color, radius, grp = "#0ea5e9", 6, flood_grp
        elif is_comm:
            color, radius, grp = "#9333ea", 7, comm_grp
        elif dst >= 50:
            color, radius, grp = "#dc2626", 11, distress_grp
        elif tier == "🔥 Hot":
            color, radius, grp = "#ef4444", 10, hot_grp
        elif tier == "⭐ Warm":
            color, radius, grp = "#f97316", 7, warm_grp
        else:
            color, radius, grp = "#3b82f6", 5, cool_grp

        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            stroke=True,
            weight=1.5,
            popup=popup,
            tooltip=tooltip,
        ).add_to(grp)

    for grp in [hot_grp, warm_grp, cool_grp, distress_grp, flood_grp, comm_grp]:
        m.add_child(grp)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # Legend — dark background so text is always readable
    m.get_root().html.add_child(folium.Element("""
    <div style='position:fixed;bottom:30px;left:20px;
                background:rgba(15,23,42,0.92);
                border:1px solid rgba(255,255,255,0.1);
                border-radius:10px;padding:14px 18px;
                font-family:system-ui,sans-serif;font-size:12px;
                z-index:9999;color:white;
                box-shadow:0 4px 16px rgba(0,0,0,0.3)'>
        <div style='font-weight:700;margin-bottom:8px;font-size:13px;
                    color:#f1f5f9;letter-spacing:0.02em'>Map Legend</div>
        <div style='display:flex;flex-direction:column;gap:5px'>
            <div><span style='display:inline-block;width:10px;height:10px;
                 border-radius:50%;background:#ef4444;margin-right:8px'></span>
                 Hot Lead — Score ≥ 70</div>
            <div><span style='display:inline-block;width:10px;height:10px;
                 border-radius:50%;background:#f97316;margin-right:8px'></span>
                 Warm Lead — Score 50–69</div>
            <div><span style='display:inline-block;width:10px;height:10px;
                 border-radius:50%;background:#3b82f6;margin-right:8px'></span>
                 Cool Lead — Score 30–49</div>
            <div><span style='display:inline-block;width:10px;height:10px;
                 border-radius:50%;background:#dc2626;margin-right:8px;
                 border:2px solid #fca5a5'></span>
                 High Distress — Distress ≥ 50</div>
            <div><span style='display:inline-block;width:10px;height:10px;
                 border-radius:50%;background:#0ea5e9;margin-right:8px'></span>
                 Near Flood Zone</div>
            <div><span style='display:inline-block;width:10px;height:10px;
                 border-radius:50%;background:#9333ea;margin-right:8px'></span>
                 Commercial / LLC Owner</div>
        </div>
        <div style='margin-top:10px;padding-top:8px;
                    border-top:1px solid rgba(255,255,255,0.1);
                    font-size:11px;color:#94a3b8'>
            Click any dot for full details
        </div>
    </div>"""))

    return m
