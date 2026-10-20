# ============================================================
# THAMIZHAGA VAANILAI - TAMIL NADU DISTRICT RAINFALL STATUS
# Streamlit app. District-name attribute: dtname
# ============================================================

import os
import zipfile
import tempfile
from io import BytesIO
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import requests

st.set_page_config(
    page_title="Tamil Nadu District Rainfall Status",
    page_icon="🌧️",
    layout="wide",
)

st.title("🌧️ தமிழக வானிலை")
st.subheader("Tamil Nadu District Rainfall Status Map")
st.caption("Select a district and manually assign its rainfall status.")

CATEGORIES = {
    "No Status": {"color": "#E8E8E8"},
    "Very Heavy Rain": {"color": "#FF8C00"},
    "Heavy Rain": {"color": "#FF0000"},
    "Moderate Rain": {"color": "#FFFF00"},
    "Light Rain": {"color": "#87CEFA"},
}

# Optional: paste a DIRECT raw GeoJSON URL or direct ZIP download URL here.
# A GitHub repository webpage URL is not a direct data URL.
SHAPE_SOURCE_URL = ""

def read_boundary(uploaded_file, source_url):
    """Read a shapefile ZIP or GeoJSON from upload or direct URL."""
    temp_dir = None

    if uploaded_file is not None:
        raw = uploaded_file.getvalue()
    elif source_url.strip():
        response = requests.get(source_url.strip(), timeout=90)
        response.raise_for_status()
        raw = response.content
    else:
        raise ValueError(
            "Upload a ZIP containing the shapefile components "
            "(.shp, .shx, .dbf, preferably .prj), or configure "
            "SHAPE_SOURCE_URL near the top of app.py."
        )

    try:
        if zipfile.is_zipfile(BytesIO(raw)):
            temp_dir = tempfile.mkdtemp(prefix="tn_districts_")
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                # Prevent unsafe archive paths from being extracted.
                root = Path(temp_dir).resolve()
                for member in archive.infolist():
                    target = (root / member.filename).resolve()
                    if root not in target.parents and target != root:
                        raise ValueError("Unsafe path found in ZIP archive.")
                archive.extractall(temp_dir)

            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if not shp_files:
                raise ValueError("No .shp file was found inside the ZIP.")
            preferred = [
                path for path in shp_files
                if "district" in path.stem.lower()
            ]
            shp_path = preferred[0] if preferred else shp_files[0]
            gdf = gpd.read_file(str(shp_path))
        else:
            # Supports GeoJSON and other vector formats readable by GeoPandas.
            gdf = gpd.read_file(BytesIO(raw))

        if gdf.empty:
            raise ValueError("The boundary file contains no features.")

        if "dtname" not in gdf.columns:
            raise ValueError(
                "The required district-name field 'dtname' was not found. "
                "Available fields: " + ", ".join(map(str, gdf.columns))
            )

        if gdf.crs is None:
            # Assumes source coordinates are longitude/latitude only when CRS
            # metadata is absent. Confirm this for your dataset if necessary.
            gdf = gdf.set_crs("EPSG:4326")

        gdf = gdf.to_crs("EPSG:4326")
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        gdf["geometry"] = gdf.geometry.make_valid()
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        gdf["__district_name"] = gdf["dtname"].astype(str).str.strip()
        gdf = gdf[
            gdf["__district_name"].ne("")
            & gdf["__district_name"].ne("nan")
        ].copy()

        if gdf.empty:
            raise ValueError("No valid district polygons were found.")

        # Combine multiple polygon parts/features that share a district name.
        gdf = gdf[["__district_name", "geometry"]].dissolve(
            by="__district_name", as_index=False
        )
        return gdf
    finally:
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

st.sidebar.header("District boundary")
st.sidebar.markdown(
    "[Your GitHub shapefile repository](https://github.com/"
    "thamizhagavaanilai-hub/tamil-nadu-shape-file)"
)
st.sidebar.write(
    "Upload a ZIP containing the shapefile components below, "
    "or configure a direct download URL in app.py."
)

uploaded_boundary = st.sidebar.file_uploader(
    "Upload district shapefile ZIP or GeoJSON",
    type=["zip", "geojson", "json"],
    help="For a shapefile, include .shp, .shx and .dbf in the ZIP."
)

try:
    districts = read_boundary(uploaded_boundary, SHAPE_SOURCE_URL)
except Exception as exc:
    st.info(
        "To start, upload your district boundary ZIP using the sidebar. "
        "Your shapefile must contain a district-name attribute called dtname."
    )
    st.error(f"Could not load district boundaries: {exc}")
    st.stop()

district_names = sorted(districts["__district_name"].unique().tolist())
if not district_names:
    st.error("No district names found in the dtname field.")
    st.stop()

if "district_statuses" not in st.session_state:
    st.session_state.district_statuses = {}
if "selected_district" not in st.session_state:
    st.session_state.selected_district = district_names[0]

# Keep selections valid if the boundary file changes.
st.session_state.district_statuses = {
    name: status
    for name, status in st.session_state.district_statuses.items()
    if name in district_names and status in CATEGORIES
}
if st.session_state.selected_district not in district_names:
    st.session_state.selected_district = district_names[0]

def make_map(gdf, statuses):
    map_df = gdf.copy()
    map_df["Rainfall Status"] = (
        map_df["__district_name"].map(statuses).fillna("No Status")
    )
    geojson = map_df.__geo_interface__
    fig = px.choropleth(
        map_df,
        geojson=geojson,
        locations=map_df.index,
        featureidkey="id",
        color="Rainfall Status",
        color_discrete_map={
            key: value["color"] for key, value in CATEGORIES.items()
        },
        hover_name="__district_name",
        hover_data={"Rainfall Status": True, "__district_name": False},
    )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="white")
    fig.update_traces(marker_line_color="#333333", marker_line_width=0.8)
    fig.update_layout(
        height=650,
        margin=dict(l=5, r=5, t=50, b=5),
        title={"text": "Tamil Nadu District Rainfall Status", "x": 0.5},
        legend_title_text="Rainfall Status",
    )
    return fig

st.subheader("1. District map")
st.caption("Use the map hover to identify a district, then select it below.")
st.plotly_chart(
    make_map(districts, st.session_state.district_statuses),
    use_container_width=True,
    key="district_status_map",
)

selected_district = st.selectbox(
    "2. Select district",
    district_names,
    index=district_names.index(st.session_state.selected_district),
)
st.session_state.selected_district = selected_district

current_status = st.session_state.district_statuses.get(
    selected_district, "No Status"
)
status_options = list(CATEGORIES.keys())
chosen_status = st.radio(
    "3. Choose rainfall status",
    status_options,
    index=status_options.index(current_status),
    format_func=lambda status: (
        f"{status} — {CATEGORIES[status]['color']}"
    ),
)
chosen_colour = CATEGORIES[chosen_status]["color"]
st.markdown(
    f"""<div style="background:{chosen_colour};color:#111;padding:14px;
    border:1px solid #555;border-radius:8px;font-weight:700;text-align:center">
    Selected: {selected_district} • {chosen_status}</div>""",
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    if st.button("✅ Update district status", type="primary", use_container_width=True):
        if chosen_status == "No Status":
            st.session_state.district_statuses.pop(selected_district, None)
        else:
            st.session_state.district_statuses[selected_district] = chosen_status
        st.rerun()
with c2:
    if st.button("↩️ Clear this district", use_container_width=True):
        st.session_state.district_statuses.pop(selected_district, None)
        st.rerun()

st.divider()
st.subheader("4. District status summary")
statuses = st.session_state.district_statuses
assigned_count = len(statuses)
m1, m2, m3 = st.columns(3)
m1.metric("Total districts", len(district_names))
m2.metric("Updated districts", assigned_count)
m3.metric("Not assigned", len(district_names) - assigned_count)

count_cols = st.columns(2)
for i, category in enumerate(status_options):
    with count_cols[i % 2]:
        st.metric(category, sum(value == category for value in statuses.values()))

if statuses:
    summary_df = pd.DataFrame(
        [
            {
                "District": district,
                "Rainfall Status": status,
                "Colour": CATEGORIES[status]["color"],
            }
            for district, status in statuses.items()
        ]
    ).sort_values(["Rainfall Status", "District"])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download status summary (CSV)",
        data=summary_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="Tamil_Nadu_Rainfall_Status.csv",
        mime="text/csv",
    )
else:
    st.caption("No district status has been assigned yet.")

st.divider()
st.subheader("5. Generate final image")
image_title = st.text_input(
    "Image title", "TAMIL NADU DISTRICT RAINFALL STATUS"
)

if st.button("🖼️ Generate final image", type="primary"):
    try:
        plot_df = districts.copy()
        plot_df["Rainfall Status"] = (
            plot_df["__district_name"].map(statuses).fillna("No Status")
        )
        plot_df["Colour"] = plot_df["Rainfall Status"].map(
            lambda status: CATEGORIES[status]["color"]
        )

        fig, ax = plt.subplots(figsize=(10, 12), dpi=200)
        plot_df.plot(
            ax=ax,
            color=plot_df["Colour"],
            edgecolor="#333333",
            linewidth=0.6,
        )

        for _, row in plot_df.iterrows():
            point = row.geometry.representative_point()
            ax.text(
                point.x, point.y, row["__district_name"],
                ha="center", va="center", fontsize=5.5,
                fontweight="bold", color="black",
            )

        legend_items = [
            mpatches.Patch(
                facecolor=CATEGORIES[category]["color"],
                edgecolor="#333333",
                label=category,
            )
            for category in status_options
        ]
        ax.legend(
            handles=legend_items,
            title="Rainfall Status",
            loc="lower left",
            fontsize=8,
            title_fontsize=9,
            frameon=True,
        )
        ax.set_title(image_title, fontsize=15, fontweight="bold", pad=18)
        ax.set_axis_off()
        fig.tight_layout()

        image_buffer = BytesIO()
        fig.savefig(
            image_buffer, format="png", dpi=300,
            bbox_inches="tight", facecolor="white",
        )
        plt.close(fig)
        png_bytes = image_buffer.getvalue()

        st.image(
            png_bytes,
            caption="Generated district rainfall status map",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Download image (PNG)",
            data=png_bytes,
            file_name="Tamil_Nadu_District_Rainfall_Status.png",
            mime="image/png",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"Image generation failed: {exc}")

st.caption(
    "Colour key: Very Heavy Rain = Orange • Heavy Rain = Red • "
    "Moderate Rain = Yellow • Light Rain = Light blue. "
    "Statuses are manually assigned and are not independently verified "
    "rainfall observations. Statuses are held in the current session only."
)
