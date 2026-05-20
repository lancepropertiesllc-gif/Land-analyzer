# 🏗️ Land Finder — Streamlit Dashboard

Multi-client builder intelligence platform for off-market land acquisition.

---

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

**Default login:**
- Account: Consultant View → Password: `admin2024`
- Account: Ballwin Builder → Password: `builder2024`

**Change passwords** in `config/clients.yaml` before sharing with anyone.

---

## Deploy to Streamlit Cloud (Free, Public URL)

1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click Deploy

Your dashboard will be live at `https://yourapp.streamlit.app`

**Add secrets** (passwords, API keys) in Streamlit Cloud → Settings → Secrets:
```toml
[clients]
consultant_password = "your_real_password"
builder_a_password  = "builder_real_password"
```

---

## Adding a New Client

Edit `config/clients.yaml` and copy the `builder_a` block:

```yaml
clients:
  builder_b:
    name: "Chesterfield Builder"
    password: "their_password"
    role: "client"
    color: "#047857"          # Green brand color
    criteria:
      geography:
        municipality: "Chesterfield"
        zips: ["63005", "63017"]
        school_districts: ["PARKWAY"]
      lot:
        min_acres: 0.5
        min_lot_width_ft: 75
      price:
        max_land_value_per_acre: 200000
        no_cap_above_acres: 2.0
      deal_types: ["Vacant Land", "Teardown Candidate"]
      scoring:
        min_lead_score: 40
        exclude_flood_zone: true
    contact:
      name: "Builder B Name"
      company: "Builder B LLC"
```

Save the file and restart the app. The new client appears on the login screen immediately.

---

## Loading Data

### Option 1 — Upload CSV
- Run your Colab notebooks
- Download `private_leads.csv`
- Upload via the sidebar "Upload CSV" option

### Option 2 — Google Drive
- Save `private_leads.csv` to Google Drive
- Right-click → Share → "Anyone with the link" → Viewer
- Copy the share link
- Paste it in the sidebar "Google Drive Link" field

### Option 3 — Live GIS Pull
- Enter municipality and school district
- Click "Pull Live Data"
- Fresh data pulled directly from STL County GIS (~30 seconds)

---

## File Structure

```
ballwin_streamlit/
├── app.py                  # Main entry point
├── requirements.txt
├── config/
│   └── clients.yaml        # Client profiles and passwords
├── utils/
│   ├── auth.py             # Login and session management
│   └── data_loader.py      # CSV, Drive, and GIS data loading
├── components/
│   └── map_builder.py      # Folium map construction
└── pages/
    ├── overview.py         # KPIs and charts
    ├── map_view.py         # Interactive map
    ├── lead_table.py       # Sortable lead table
    └── criteria.py         # Live filter adjustment
```

---

## Updating Your Data

Run Notebooks 01-03 weekly in Google Colab, then either:
- Re-upload the CSV to the dashboard, or
- Overwrite the file in Google Drive (link stays the same), or
- Click "Pull Live Data" for a fresh pull from STL County

---

## Roadmap

- [ ] MARIS MLS API connector (once credentials available)
- [ ] Letter generation from inside the dashboard
- [ ] Email notification when new hot leads appear
- [ ] Multi-county support (St. Charles, Jefferson, etc.)
- [ ] Saved search alerts
