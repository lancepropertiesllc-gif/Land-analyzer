"""
utils/data_loader.py — Multi-county data loading
Supports: St. Louis County, St. Charles County
"""
import io
import re
import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path

HEADERS = {"User-Agent": "LandFinder/2.0 (Multi-County)"}

# ── County registry ───────────────────────────────────────────────────────
COUNTY_REGISTRY = {
    "St. Louis": {
        "url": (
            "https://maps.stlouisco.com/hosting/rest/services"
            "/Accela/Accela_Parcels/FeatureServer/0/query"
        ),
        "city_field":   "MUNICIPALITY",
        "school_field": "SCHOOL_DISTRICT",
        "cities": [
            "ALL (Entire County)",
            "Ballwin", "Chesterfield", "Clayton", "Creve Coeur",
            "Des Peres", "Ellisville", "Eureka", "Florissant",
            "Hazelwood", "Kirkwood", "Ladue", "Manchester",
            "Maplewood", "Maryland Heights", "Mehlville",
            "Overland", "Richmond Heights", "Rock Hill",
            "St. Ann", "Town and Country", "University City",
            "Webster Groves", "Wildwood",
        ],
        "school_districts": [
            "ALL", "ROCKWOOD", "PARKWAY", "KIRKWOOD",
            "LINDBERGH", "MEHLVILLE", "HAZELWOOD",
            "PATTONVILLE", "FERGUSON-FLORISSANT",
        ],
        "fields": [
            "LOCATOR","OWNER_NAME","OWN_ADD","OWN_CITY","OWN_STATE","OWN_ZIP",
            "PROP_ADD","PROP_ZIP","MUNICIPALITY","ACRES","APPLANDVAL","APPIMPVAL",
            "TOTAPVAL","TOTASSMT","LUC","LANDUSE2","LUCODE","PROPCLASS",
            "YEARBLT","RESQFT","SCHOOL_DISTRICT","LOTDIM","TENURE",
            "SUBDIVISION","ZONING","MUNI_ZONING","CODE_ENFORCEMENT_DISTRICT",
        ],
        "field_map": {
            "LOCATOR":"PARCEL_ID","OWNER_NAME":"OWNER_NAME",
            "OWN_ADD":"OWNER_ADDRESS","OWN_CITY":"OWNER_CITY",
            "OWN_STATE":"OWNER_STATE","OWN_ZIP":"OWNER_ZIP",
            "PROP_ADD":"SITUS_ADDRESS","PROP_ZIP":"SITUS_ZIP",
            "MUNICIPALITY":"SITUS_CITY","ACRES":"ACRES",
            "APPLANDVAL":"LAND_VALUE","APPIMPVAL":"IMPROVEMENT_VALUE",
            "TOTAPVAL":"TOTAL_VALUE","TOTASSMT":"ASSESSED_TOTAL",
            "LUC":"LAND_USE_CODE","LUCODE":"LAND_USE_NAME",
            "PROPCLASS":"PROPERTY_CLASS","YEARBLT":"YEAR_BUILT",
            "RESQFT":"BUILDING_SQFT","SCHOOL_DISTRICT":"SCHOOL_DISTRICT",
            "LOTDIM":"LOT_DIM","TENURE":"TENURE",
            "SUBDIVISION":"SUBDIVISION","ZONING":"ZONING",
        },
    },
    "St. Charles": {
        "url": (
            "https://gis-dev.sccmo.org/scc_gis/rest/services"
            "/appservices/JS_parcel_info/MapServer/0/query"
        ),
        "city_field":   "Municipality",
        "school_field": "SchoolDistrict",
        "cities": [
            "ALL (Entire County)",
            "City of O'Fallon", "City of St Peters",
            "City of Wentzville", "City of St Charles",
            "City of Cottleville", "City of Lake Saint Louis",
            "Dardenne Prairie", "City of Weldon Spring Heights",
            "City of Augusta", "City of Flint Hill",
            "City of Foristell", "City of New Melle",
            "Unincorporated County",
        ],
        "school_districts": [
            "ALL", "WENTZVILLE", "FRANCIS HOWELL",
            "FORT ZUMWALT", "ST CHARLES", "ORCHARD FARM",
        ],
        "fields": [
            "account","owner","MailingAddress","SiteAddress","SitusZip",
            "Municipality","parcel_acres","ResidentialLandValue",
            "ResidentialImprovementValue","CommercialLandValue",
            "CommercialImprovementValue","TotalMarketValue",
            "proptype","property_category","year_built","parcel_age_years",
            "SchoolDistrict","LotSize","Subdivision",
            "most_recent_sales_price","most_recent_sales_date",
            "latitude","longitude","tax_district","base_area_sq_ft",
        ],
        "field_map": {
            "account":"PARCEL_ID","owner":"OWNER_NAME",
            "MailingAddress":"OWNER_MAILING","SiteAddress":"SITUS_ADDRESS",
            "SitusZip":"SITUS_ZIP","Municipality":"SITUS_CITY",
            "parcel_acres":"ACRES","ResidentialLandValue":"LAND_VALUE",
            "ResidentialImprovementValue":"IMPROVEMENT_VALUE",
            "TotalMarketValue":"TOTAL_VALUE",
            "proptype":"PROP_TYPE","property_category":"PROPERTY_CLASS",
            "year_built":"YEAR_BUILT","parcel_age_years":"STRUCTURE_AGE",
            "SchoolDistrict":"SCHOOL_DISTRICT","LotSize":"LOT_DIM",
            "Subdivision":"SUBDIVISION",
            "most_recent_sales_price":"LAST_SALE_PRICE",
            "latitude":"LATITUDE","longitude":"LONGITUDE",
            "tax_district":"TAX_CODE","base_area_sq_ft":"BUILDING_SQFT",
        },
    },
}


# ── CSV Upload ────────────────────────────────────────────────────────────
def load_from_upload(uploaded_file) -> pd.DataFrame:
    try:
        df = pd.read_csv(uploaded_file)
        return _standardize(df)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()


# ── Google Drive ──────────────────────────────────────────────────────────
def load_from_drive(share_url: str) -> pd.DataFrame:
    try:
        file_id = None
        for pat in [r"/file/d/([a-zA-Z0-9_-]+)", r"id=([a-zA-Z0-9_-]+)"]:
            m = re.search(pat, share_url)
            if m:
                file_id = m.group(1)
                break
        if not file_id:
            st.error("Could not extract file ID from Google Drive URL")
            return pd.DataFrame()
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        return _standardize(df)
    except Exception as e:
        st.error(f"Google Drive load failed: {e}")
        return pd.DataFrame()


# ── Live GIS Pull ─────────────────────────────────────────────────────────
def load_from_gis(
    county: str = "St. Louis",
    city: str = "Ballwin",
    school_districts: list = None,
    progress_callback=None,
) -> pd.DataFrame:
    """Pull live parcel data for any supported county and city."""

    if county not in COUNTY_REGISTRY:
        st.error(f"County '{county}' not in registry")
        return pd.DataFrame()

    source = COUNTY_REGISTRY[county]
    url    = source["url"]
    fields = source["fields"]

    # Build WHERE clause
    parts = []
    city_field   = source["city_field"]
    school_field = source["school_field"]

    if city and "ALL" not in city:
        if county == "St. Charles":
            city_clean = city.replace("City of ", "").strip()
            parts.append(f"UPPER({city_field}) LIKE '%{city_clean.upper()}%'")
        else:
            parts.append(f"{city_field} = '{city}'")

    if school_districts:
        sd_clean = [s for s in school_districts if s != "ALL"]
        if sd_clean:
            sd_clauses = " OR ".join(
                f"UPPER({school_field}) LIKE '%{sd.upper()}%'"
                for sd in sd_clean
            )
            parts.append(f"({sd_clauses})")

    where = " AND ".join(parts) if parts else "1=1"

    # Fetch with pagination
    all_features = []
    offset = 0
    page_size = 1000

    while True:
        params = {
            "where":             where,
            "outFields":         ",".join(fields),
            "returnGeometry":    "true",
            "outSR":             "4326",
            "f":                 "geojson",
            "resultOffset":      offset,
            "resultRecordCount": page_size,
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=60)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            st.error(f"GIS fetch error at offset {offset}: {e}")
            break

        features = data.get("features", [])
        if not features:
            break
        all_features.extend(features)

        if progress_callback:
            progress_callback(len(all_features))

        if len(features) < page_size:
            break
        offset += page_size
        time.sleep(0.3)

    if not all_features:
        return pd.DataFrame()

    # Parse features
    field_map = source["field_map"]
    rows = []
    for feat in all_features:
        props = feat.get("properties") or feat.get("attributes", {})
        geom  = feat.get("geometry", {})
        row = {}

        # Map fields
        for src_f, dst_f in field_map.items():
            if src_f in props:
                row[dst_f] = props[src_f]

        # Coordinates
        if county == "St. Charles":
            # STC has lat/lon embedded
            try:
                row["LATITUDE"]  = float(props.get("latitude") or 0) or None
                row["LONGITUDE"] = float(props.get("longitude") or 0) or None
            except (TypeError, ValueError):
                row["LATITUDE"] = row["LONGITUDE"] = None
        elif geom and geom.get("coordinates"):
            try:
                coords = geom["coordinates"]
                if geom.get("type") == "Point":
                    row["LONGITUDE"] = coords[0]
                    row["LATITUDE"]  = coords[1]
                else:
                    ring = coords[0]
                    if ring and isinstance(ring[0], list):
                        row["LONGITUDE"] = sum(c[0] for c in ring) / len(ring)
                        row["LATITUDE"]  = sum(c[1] for c in ring) / len(ring)
            except Exception:
                row["LATITUDE"] = row["LONGITUDE"] = None

        # STC: parse mailing address string into components
        if county == "St. Charles" and "OWNER_MAILING" in row:
            addr = str(row.get("OWNER_MAILING", ""))
            parts_addr = [p.strip() for p in addr.split(",")]
            row["OWNER_ADDRESS"] = parts_addr[0] if parts_addr else ""
            city_state = parts_addr[1] if len(parts_addr) > 1 else ""
            cs = city_state.strip().rsplit(" ", 1)
            row["OWNER_CITY"]  = cs[0] if len(cs) > 1 else city_state
            row["OWNER_STATE"] = cs[1] if len(cs) > 1 else "MO"
            row["OWNER_ZIP"]   = parts_addr[2].strip() if len(parts_addr) > 2 else ""

        # STC: combine land values
        if county == "St. Charles":
            if not row.get("LAND_VALUE") or float(row.get("LAND_VALUE") or 0) == 0:
                row["LAND_VALUE"] = props.get("CommercialLandValue", 0) or 0
            if not row.get("IMPROVEMENT_VALUE") or \
               float(row.get("IMPROVEMENT_VALUE") or 0) == 0:
                row["IMPROVEMENT_VALUE"] = \
                    props.get("CommercialImprovementValue", 0) or 0

        row["COUNTY"] = county
        rows.append(row)

    df = pd.DataFrame(rows)
    return _standardize(df)


# ── Standardize ───────────────────────────────────────────────────────────
def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    import datetime

    for col in ["ACRES","LAND_VALUE","IMPROVEMENT_VALUE","TOTAL_VALUE",
                "YEAR_BUILT","BUILDING_SQFT","LEAD_SCORE","DISTRESS_SCORE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "SQFT" not in df.columns:
        df["SQFT"] = df.get("ACRES", pd.Series()).fillna(0) * 43560

    if "LOT_WIDTH" not in df.columns and "LOT_DIM" in df.columns:
        def pw(dim):
            if pd.isna(dim): return None
            m = re.search(r"^(\d+)", str(dim).replace(" ",""))
            return int(m.group(1)) if m and int(m.group(1)) > 0 else None
        df["LOT_WIDTH"] = df["LOT_DIM"].apply(pw)

    if "STRUCTURE_AGE" not in df.columns and "YEAR_BUILT" in df.columns:
        yr = datetime.date.today().year
        df["STRUCTURE_AGE"] = yr - df["YEAR_BUILT"]
        df.loc[df["STRUCTURE_AGE"] < 0, "STRUCTURE_AGE"] = np.nan
        df.loc[df["STRUCTURE_AGE"] > 150, "STRUCTURE_AGE"] = np.nan

    for col in ["IS_VACANT","ABSENTEE_OWNER","NON_OWNER_OCCUPIED",
                "MULTI_PARCEL_OWNER","OLD_STRUCTURE","IN_FLOOD_ZONE",
                "NEAR_FLOOD_ZONE","IS_ROCKWOOD","IS_COMMERCIAL",
                "HIGH_TAX_BURDEN"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    if "OPPORTUNITY_TYPE" not in df.columns:
        def classify(row):
            imp = row.get("IMPROVEMENT_VALUE", 0) or 0
            if imp == 0: return "Vacant Land"
            if imp <= 150000: return "Teardown Candidate"
            return "Large Lot"
        df["OPPORTUNITY_TYPE"] = df.apply(classify, axis=1)

    if "LEAD_SCORE" in df.columns:
        df["LEAD_TIER"] = df["LEAD_SCORE"].apply(
            lambda s: "🔥 Hot" if s >= 70 else "⭐ Warm" if s >= 50
                      else "🌡️ Cool" if s >= 30 else "❄️ Cold"
        )
    if "DISTRESS_SCORE" in df.columns:
        df["DISTRESS_TIER"] = df["DISTRESS_SCORE"].apply(
            lambda s: "🚨 High" if s >= 50 else "⚠️ Medium" if s >= 30
                      else "📋 Low" if s >= 10 else "➖ None"
        )

    return df


# ── Apply client filters ──────────────────────────────────────────────────
def apply_client_filters(df: pd.DataFrame, criteria: dict) -> pd.DataFrame:
    if df.empty or not criteria:
        return df

    mask = pd.Series(True, index=df.index)

    geo = criteria.get("geography", {})
    if geo.get("school_districts") and "SCHOOL_DISTRICT" in df.columns:
        mask &= df["SCHOOL_DISTRICT"].str.upper().apply(
            lambda sd: any(
                t.upper() in str(sd)
                for t in geo["school_districts"]
                if t != "ALL"
            )
        )

    lot = criteria.get("lot", {})
    if lot.get("min_acres") and "ACRES" in df.columns:
        mask &= df["ACRES"].fillna(0) >= lot["min_acres"]
    if lot.get("min_lot_width_ft") and "LOT_WIDTH" in df.columns:
        mask &= (df["LOT_WIDTH"] >= lot["min_lot_width_ft"]) | \
                df["LOT_WIDTH"].isna()

    price = criteria.get("price", {})
    if price and "LAND_VALUE" in df.columns:
        land = df["LAND_VALUE"].fillna(0)
        acres = df["ACRES"].fillna(0)

        # Minimum land value — exclude $0 data errors
        if price.get("min_land_value"):
            mask &= land >= price["min_land_value"]

        # Hard dollar cap
        if price.get("max_land_value"):
            mask &= land <= price["max_land_value"]

        # Per-acre cap (scales with lot size)
        if price.get("max_per_acre"):
            no_cap_acres = price.get("no_cap_above_acres", 2.0)
            per_acre     = price["max_per_acre"]
            price_cap = acres.apply(
                lambda a: 999_999_999 if a >= no_cap_acres
                          else a * per_acre if a > 0 else per_acre * 0.25
            )
            mask &= land <= price_cap

    deal_types = criteria.get("deal_types", [])
    if deal_types and "OPPORTUNITY_TYPE" in df.columns:
        mask &= df["OPPORTUNITY_TYPE"].isin(deal_types)

    scoring = criteria.get("scoring", {})
    if scoring.get("min_lead_score") and "LEAD_SCORE" in df.columns:
        mask &= df["LEAD_SCORE"].fillna(0) >= scoring["min_lead_score"]
    if scoring.get("exclude_flood_zone") and "IN_FLOOD_ZONE" in df.columns:
        mask &= ~df["IN_FLOOD_ZONE"].fillna(False)

    return df[mask].copy()
