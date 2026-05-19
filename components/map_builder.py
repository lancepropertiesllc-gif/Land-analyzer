"""
components/map_builder.py
"""
import folium
import pandas as pd

BALLWIN_CENTER = [38.5953, -90.5454]
TILE_OPTIONS = {
    "Light (Default)": "OpenStreetMap",
    "Street Map":      "OpenStreetMap",
    "Dark Mode":       "OpenStreetMap",
}


def fmt_col(name: str) -> str:
    return str(name).replace("_", " ").title()


def _safe(val, default=""):
    if val is None:
        return default
    try:
        import pandas as pd
        if pd.isna(val):
            return default
    except Exception:
        pass
    return val


def _popup(row: pd.Series) -> folium.Popup:
    addr  = str(_safe(row.get("SITUS_ADDRESS"), "Unknown")).title()
    owner = str(_safe(row.get("OWNER_NAME"), "Unknown")).title()
    score = float(_safe(row.get("LEAD_SCORE"), 0))
    tier  = str(_safe(row.get("LEAD_TIER"), ""))
    dst   = float(_safe(row.get("DISTRESS_SCORE"), 0))
    opp   = str(_safe(row.get("OPPORTUNITY_TYPE"), ""))
    acres = round(float(_safe(row.get("ACRES"), 0)), 2)
    width = _safe(row.get("LOT_WIDTH"), None)
    ws    = f"{int(width)}ft" if width else "Unknown"
    land  = float(_safe(row.get("LAND_VALUE"), 0))
    imp   = float(_safe(row.get("IMPROVEMENT_VALUE"), 0))
    yr    = _safe(row.get("YEAR_BUILT"), "")
    yr    = str(int(float(yr))) if yr else "N/A"
    ab    = "Yes" if _safe(row.get("ABSENTEE_OWNER"), False) else "No"
    noo   = "Yes" if _safe(row.get("NON_OWNER_OCCUPIED"), False) else "No"
    sc    = str(_safe(row.get("SCHOOL_DISTRICT"), "")).title()

    c_opp = "#ef4444" if score >= 70 else "#f97316" if score >= 50 else "#3b82f6"
    c_dst = "#dc2626" if dst >= 50 else "#ea580c" if dst >= 30 else "#64748b"

    html = f"""
    <div style="font-family:Arial,sans-serif;min-width:230px;font-size:12px">
      <div style="background:#1f2937;color:white;padding:8px 10px;
                  margin:-10px -10px 8px;border-radius:4px 4px 0 0">
        <b>{addr}</b><br>
        <span style="opacity:.75;font-size:11px">{opp}</span>
      </div>
      <div style="margin-bottom:6px">
        <span style="background:{c_opp};color:white;padding:2px 8px;
                     border-radius:10px;font-size:11px;margin-right:4px">
          Score: {score:.0f} {tier}
        </span>
        <span style="background:{c_dst};color:white;padding:2px 8px;
                     border-radius:10px;font-size:11px">
          Distress: {dst:.0f}
        </span>
      </div>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="color:#6b7280;padding:2px 4px">Owner</td>
            <td style="text-align:right;font-weight:500">{owner}</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">Lot</td>
            <td style="text-align:right">{acres} ac | {ws} wide</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">School</td>
            <td style="text-align:right">{sc}</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">Land Value</td>
            <td style="text-align:right">${land:,.0f}</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">Improvement</td>
            <td style="text-align:right">${imp:,.0f}</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">Year Built</td>
            <td style="text-align:right">{yr}</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">Non-Owner Occ</td>
            <td style="text-align:right">{noo}</td></tr>
        <tr><td style="color:#6b7280;padding:2px 4px">Absentee</td>
            <td style="text-align:right">{ab}</td></tr>
      </table>
    </div>"""
    return folium.Popup(html, max_width=280)


def build_map(
    df: pd.DataFrame,
    center: list = BALLWIN_CENTER,
    zoom: int = 13,
    show_commercial: bool = False,
    show_flood: bool = False,
    show_cool: bool = True,
    tile_label: str = "Light (Default)",
) -> folium.Map:

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    hot_grp      = folium.FeatureGroup(name="Hot Leads (70+)",      show=True)
    warm_grp     = folium.FeatureGroup(name="Warm Leads (50-69)",    show=True)
    cool_grp     = folium.FeatureGroup(name="Cool Leads (30-49)",    show=show_cool)
    distress_grp = folium.FeatureGroup(name="High Distress (50+)",   show=True)
    flood_grp    = folium.FeatureGroup(name="Near Flood Zone",       show=show_flood)
    comm_grp     = folium.FeatureGroup(name="Commercial / LLC",      show=show_commercial)

    mappable = df.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
    mappable = mappable[
        mappable["LATITUDE"].between(38.3, 39.0) &
        mappable["LONGITUDE"].between(-91.0, -90.0)
    ]

    for _, row in mappable.iterrows():
        tier     = str(_safe(row.get("LEAD_TIER"), ""))
        dst      = float(_safe(row.get("DISTRESS_SCORE"), 0))
        is_comm  = bool(_safe(row.get("IS_COMMERCIAL"), False))
        near_fl  = bool(_safe(row.get("NEAR_FLOOD_ZONE"), False))
        score    = float(_safe(row.get("LEAD_SCORE"), 0))
        popup    = _popup(row)
        addr     = str(_safe(row.get("SITUS_ADDRESS"), "")).title()
        tooltip  = f"{addr} | Score: {score:.0f} | Distress: {dst:.0f}"

        if near_fl:
            color, radius, grp = "#0ea5e9", 6, flood_grp
        elif is_comm:
            color, radius, grp = "#9333ea", 7, comm_grp
        elif dst >= 50:
            color, radius, grp = "#dc2626", 11, distress_grp
        elif "Hot" in tier:
            color, radius, grp = "#ef4444", 10, hot_grp
        elif "Warm" in tier:
            color, radius, grp = "#f97316", 7, warm_grp
        else:
            color, radius, grp = "#3b82f6", 5, cool_grp

        folium.CircleMarker(
            location=[float(row["LATITUDE"]), float(row["LONGITUDE"])],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            weight=1.5,
            popup=popup,
            tooltip=tooltip,
        ).add_to(grp)

    for grp in [hot_grp, warm_grp, cool_grp, distress_grp, flood_grp, comm_grp]:
        m.add_child(grp)

    folium.LayerControl(collapsed=False).add_to(m)

    m.get_root().html.add_child(folium.Element("""
    <div style="position:fixed;bottom:30px;left:20px;
                background:rgba(15,23,42,0.9);border-radius:8px;
                padding:12px 16px;font-family:Arial,sans-serif;
                font-size:12px;z-index:9999;color:white;
                box-shadow:0 4px 12px rgba(0,0,0,0.3)">
      <b style="display:block;margin-bottom:6px;font-size:13px">Legend</b>
      <div style="margin:3px 0">
        <span style="display:inline-block;width:10px;height:10px;
               border-radius:50%;background:#ef4444;margin-right:8px"></span>
        Hot — Score 70+</div>
      <div style="margin:3px 0">
        <span style="display:inline-block;width:10px;height:10px;
               border-radius:50%;background:#f97316;margin-right:8px"></span>
        Warm — Score 50-69</div>
      <div style="margin:3px 0">
        <span style="display:inline-block;width:10px;height:10px;
               border-radius:50%;background:#3b82f6;margin-right:8px"></span>
        Cool — Score 30-49</div>
      <div style="margin:3px 0">
        <span style="display:inline-block;width:10px;height:10px;
               border-radius:50%;background:#dc2626;margin-right:8px;
               border:2px solid #fca5a5"></span>
        High Distress</div>
      <div style="margin:3px 0">
        <span style="display:inline-block;width:10px;height:10px;
               border-radius:50%;background:#0ea5e9;margin-right:8px"></span>
        Near Flood Zone</div>
      <div style="margin:3px 0">
        <span style="display:inline-block;width:10px;height:10px;
               border-radius:50%;background:#9333ea;margin-right:8px"></span>
        Commercial / LLC</div>
      <div style="margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.15);
                  font-size:10px;color:#94a3b8">Click any dot for details</div>
    </div>"""))

    return m
