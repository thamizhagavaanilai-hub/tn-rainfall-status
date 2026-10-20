# Thamizhaga Vaanilai — Tamil Nadu District Rainfall Status

A Streamlit application to assign rainfall-status colours to Tamil Nadu district polygons.

## Colour scheme

- Very Heavy Rain: Orange (`#FF8C00`)
- Heavy Rain: Red (`#FF0000`)
- Moderate Rain: Yellow (`#FFFF00`)
- Light Rain: Light blue (`#87CEFA`)
- No Status: Light grey (`#E8E8E8`)

## District field

The app expects the district-name attribute to be exactly `dtname`.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run:

   ```bash
   streamlit run app.py
   ```

5. In the sidebar, upload a ZIP containing the shapefile components (`.shp`, `.shx`, `.dbf`, and preferably `.prj`), or a GeoJSON file.

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository and upload `app.py`, `requirements.txt`, and `README.md`.
2. Open https://share.streamlit.io/ and sign in with GitHub.
3. Create an app using your repository, branch `main`, and main file `app.py`.
4. Deploy. Upload your district ZIP in the app sidebar.

### Optional automatic boundary download

At the top of `app.py`, set `SHAPE_SOURCE_URL` to a *direct* downloadable ZIP URL or raw GeoJSON URL. Do not use the normal GitHub repository page URL. If you use a direct URL, the app can load the boundaries without requiring each visitor to upload them.

## Important notes

- The app checks for `dtname`; the name is case-sensitive.
- If the shapefile has no CRS metadata, the app assumes EPSG:4326. Confirm the source CRS before using this assumption.
- Statuses are stored in Streamlit session state only. They are not a shared permanent database and may reset when a session restarts.
- The app records manually assigned statuses; it does not automatically measure or verify rainfall.
