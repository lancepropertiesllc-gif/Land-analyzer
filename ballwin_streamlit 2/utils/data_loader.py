"""
utils/data_loader.py — Load leads from CSV upload, Google Drive, or live GIS pull
"""
import io
import re
import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path


STL_PARCEL_URL = (
    "https://maps.stlouisco.com/hosting/rest/services"
    "/Accela/Accela_Parcels/FeatureServer/0/query"
)
HEADERS = {"User-Agent": "LandFinder/1.0 (Streamlit dashboard)"}


# ── CSV Upload ────────────────────────────────────────────────────────────────

def load_from_upload(uploaded_file) -> pd.DataFrame:
    """Load leads from an uploaded CSV file."""
    try:
        df = pd.read_csv(uploaded_file)
        return _standardize(df)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()


# ── Google Drive ──────────────────────────────────────────────────────────────

def load_from_drive(share_url: str) -> pd.DataFrame:
    """
    Load CSV from a Google Drive share link.
    Converts share URL to direct download URL automatically.
    """
    try:
        # Convert share URL to direct download
        file_id = None
        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]
        for pat in patterns:
            m = re.search(pat, share_url)
            if m:
                file_id = m.group(1)
                break

        if not file_id:
            st.error("Could not extract file ID from Google Drive URL")
            return pd.DataFrame()

        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = requests.get(download_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text))
        return _standardize(df)

    except Exception as e:
        st.error(f"Google Drive load failed: {e}")
        return pd.DataFrame()


# ── Live GIS Pull ─────────────────────────────────────────────────────────────

def load_from_gis(
    municipality: str = "Ballwin",
    school_district: str = "ROCKWOOD",
    progress_callback=None,
) -> pd.DataFrame:
    """
    Pull fresh parcel data directly from STL County GIS.
    Takes 20-30 seconds for Ballwin.
    """
    import re as _re

    where = f"MUNICIPALITY = '{municipality}'"
    if school_district:
        where += f" AND SCHOOL_DISTRICT = '{school_district}'"

    FIELDS = [
        "LOCATOR","OWNER_NAME","OWN_ADD","OWN_CITY","OWN_STATE","OWN_ZIP",
        "PROP_ADD","PROP_ZIP","MUNICIPALITY","ACRES","APPLANDVAL","APPIMPVAL",
        "TOTAPVAL","ASSTLANDVAL","ASSTIMPVAL","TOTASSMT","ZONING","MUNI_ZONING",
        "LUC","LANDUSE2","LUCODE","PROPCLASS","YEARBLT","RESQFT",
        "RECDATEDAILY","DEEDTYPE","SCHOOL_DISTRICT","LOTDIM","SUBDIVISION",
        "NBHD","TAXCODE","TENURE","CODE_ENFORCEMENT_DISTRICT",
    ]

    all_features = []
    offset = 0
    page_size = 1000

    while True:
        params = {
            "where":             where,
            "outFields":         ",".join(FIELDS),
            "returnGeometry":    "true",
            "outSR":             "4326",
            "f":                 "geojson",
            "resultOffset":      offset,
            "resultRecordCount": page_size,
        }
        try:
            r = requests.get(STL_PARCEL_URL, params=params,
                             headers=HEADERS, timeout=45)
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

    # Parse features into DataFrame
    rows = []
    for feat in all_features:
        props = feat.get("properties") or feat.get("attributes", {})
        geom  = feat.get("geometry", {})
        if geom and geom.get("type") == "Point":
            props["LONGITUDE"] = geom["coordinates"][0]
            props["LATITUDE"]  = geom["coordinates"][1]
        elif geom and geom.get("coordinates"):
            # Polygon centroid approximation
            try:
                coords = geom["coordinates"][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                props["LONGITUDE"] = sum(lons) / len(lons)
                props["LATITUDE"]  = sum(lats) / len(lats)
            except Exception:
                props["LONGITUDE"] = None
                props["LATITUDE"]  = None
        rows.append(props)

    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "LOCATOR": "PARCEL_ID", "OWNER_NAME": "OWNER_NAME",
        "OWN_ADD": "OWNER_ADDRESS", "OWN_CITY": "OWNER_CITY",
        "OWN_STATE": "OWNER_STATE", "OWN_ZIP": "OWNER_ZIP",
        "PROP_ADD": "SITUS_ADDRESS", "PROP_ZIP": "SITUS_ZIP",
        "MUNICIPALITY": "SITUS_CITY", "APPLANDVAL": "LAND_VALUE",
        "APPIMPVAL": "IMPROVEMENT_VALUE", "TOTAPVAL": "TOTAL_VALUE",
        "TOTASSMT": "ASSESSED_TOTAL", "LUC": "LAND_USE_CODE",
        "LANDUSE2": "LAND_USE_DESC", "PROPCLASS": "PROPERTY_CLASS",
        "YEARBLT": "YEAR_BUILT", "RESQFT": "BUILDING_SQFT",
        "RECDATEDAILY": "LAST_SALE_DATE", "DEEDTYPE": "DEED_TYPE",
        "LOTDIM": "LOT_DIM",
    })
    return _standardize(df)


# ── Standardize & enrich ──────────────────────────────────────────────────────

def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all required columns exist and are correctly typed."""
    import datetime, re

    # Numeric coercions
    for col in ["ACRES","LAND_VALUE","IMPROVEMENT_VALUE","TOTAL_VALUE",
                "YEAR_BUILT","BUILDING_SQFT","LEAD_SCORE","DISTRESS_SCORE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derive SQFT
    if "SQFT" not in df.columns or df.get("SQFT", pd.Series()).isna().all():
        df["SQFT"] = df.get("ACRES", pd.Series()).fillna(0) * 43560

    # Derive lot width from LOT_DIM if not present
    if "LOT_WIDTH" not in df.columns and "LOT_DIM" in df.columns:
        def parse_width(dim):
            if pd.isna(dim): return None
            m = re.search(r"^(\d+)", str(dim).replace(" ",""))
            return int(m.group(1)) if m else None
        df["LOT_WIDTH"] = df["LOT_DIM"].apply(parse_width)

    # Structure age
    if "STRUCTURE_AGE" not in df.columns and "YEAR_BUILT" in df.columns:
        yr = datetime.date.today().year
        df["STRUCTURE_AGE"] = yr - df["YEAR_BUILT"]
        df.loc[df["STRUCTURE_AGE"] < 0,   "STRUCTURE_AGE"] = np.nan
        df.loc[df["STRUCTURE_AGE"] > 150, "STRUCTURE_AGE"] = np.nan

    # Boolean coercions
    for col in ["IS_VACANT","ABSENTEE_OWNER","NON_OWNER_OCCUPIED",
                "MULTI_PARCEL_OWNER","OLD_STRUCTURE","IN_FLOOD_ZONE",
                "NEAR_FLOOD_ZONE","IS_ROCKWOOD","IS_COMMERCIAL","HIGH_TAX_BURDEN"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    # Opportunity type default
    if "OPPORTUNITY_TYPE" not in df.columns:
        def classify(row):
            imp = row.get("IMPROVEMENT_VALUE", 0) or 0
            if imp == 0: return "Vacant Land"
            if imp <= 150000: return "Teardown Candidate"
            return "Large Lot"
        df["OPPORTUNITY_TYPE"] = df.apply(classify, axis=1)

    # Score tiers
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


def apply_client_filters(df: pd.DataFrame, criteria: dict) -> pd.DataFrame:
    """Apply a client's saved criteria to filter a leads DataFrame."""
    if df.empty or not criteria:
        return df

    mask = pd.Series(True, index=df.index)

    # Geography
    geo = criteria.get("geography", {})
    if geo.get("school_districts") and "SCHOOL_DISTRICT" in df.columns:
        mask &= df["SCHOOL_DISTRICT"].str.upper().isin(
            [s.upper() for s in geo["school_districts"]]
        )

    # Lot size
    lot = criteria.get("lot", {})
    if lot.get("min_acres") and "ACRES" in df.columns:
        mask &= df["ACRES"].fillna(0) >= lot["min_acres"]
    if lot.get("min_lot_width_ft") and "LOT_WIDTH" in df.columns:
        mask &= (df["LOT_WIDTH"] >= lot["min_lot_width_ft"]) | df["LOT_WIDTH"].isna()

    # Price cap
    price = criteria.get("price", {})
    if price.get("max_land_value_per_acre") and "LAND_VALUE" in df.columns:
        no_cap_acres = price.get("no_cap_above_acres", 2.0)
        per_acre_cap = price["max_land_value_per_acre"]
        price_cap = df["ACRES"].apply(
            lambda a: 999999999 if (a or 0) >= no_cap_acres
                      else max(250000, (a or 0) * per_acre_cap)
        )
        mask &= df["LAND_VALUE"].fillna(0) <= price_cap

    # Deal types
    deal_types = criteria.get("deal_types", [])
    if deal_types and "OPPORTUNITY_TYPE" in df.columns:
        mask &= df["OPPORTUNITY_TYPE"].isin(deal_types)

    # Scoring thresholds
    scoring = criteria.get("scoring", {})
    if scoring.get("min_lead_score") and "LEAD_SCORE" in df.columns:
        mask &= df["LEAD_SCORE"].fillna(0) >= scoring["min_lead_score"]
    if scoring.get("exclude_flood_zone") and "IN_FLOOD_ZONE" in df.columns:
        mask &= ~df["IN_FLOOD_ZONE"].fillna(False)

    return df[mask].copy()
