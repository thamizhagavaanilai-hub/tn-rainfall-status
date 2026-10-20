# ============================================================
# THAMIZHAGA VAANILAI - TAMIL NADU DISTRICT RAINFALL STATUS
# Automatically loads district boundaries from GitHub.
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
import matplotlib.font_manager as fm
import requests

st.set_page_config(
    page_title="தமிழக வானிலை - மாவட்ட மழை நிலை",
    page_icon="🌧️",
    layout="wide",
)

# Public ZIP stored in your GitHub repository.
SHAPE_SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "thamizhagavaanilai-hub/tamil-nadu-shape-file/main/tnshp.zip"
)

# Tamil-capable font from Google's Noto Sans Tamil project.
TAMIL_FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstamil/"
    "NotoSansTamil%5Bwdth%2Cwght%5D.ttf"
)
FONT_CACHE = Path(tempfile.gettempdir()) / "NotoSansTamil.ttf"


def get_tamil_font():
    """Download/register a Tamil font for labels and legends."""
    try:
        if not FONT_CACHE.exists() or FONT_CACHE.stat().st_size < 1000:
            response = requests.get(TAMIL_FONT_URL, timeout=30)
            response.raise_for_status()
            FONT_CACHE.write_bytes(response.content)
        return fm.FontProperties(fname=str(FONT_CACHE))
    except Exception:
        # Browser UI still uses the device's Tamil font if font download fails.
        return fm.FontProperties(family="sans-serif")


TAMIL_FONT = get_tamil_font()

st.title("🌧️ தமிழக வானிலை")
st.subheader("தமிழ்நாடு மாவட்ட மழை நிலை வரைபடம்")
st.caption("மாவட்டங்களைத் தேர்வு செய்து, ஒரே முறையில் மழை நிலையைப் புதுப்பிக்கலாம்.")

# Internal keys are stable English strings; users see Tamil labels.
CATEGORIES = {
    "No Status": {
        "ta": "நிலை குறிப்பிடப்படவில்லை",
        "color": "#E8E8E8",
    },
    "Very Heavy Rain": {
        "ta": "மிக கனமழை",
        "color": "#FF8C00",
    },
    "Heavy Rain": {
        "ta": "கனமழை",
        "color": "#FF0000",
    },
    "Moderate Rain": {
        "ta": "மிதமான மழை",
        "color": "#FFFF00",
    },
    "Light Rain": {
        "ta": "லேசான மழை",
        "color": "#87CEFA",
    },
}


@st.cache_data(show_spinner="GitHub-இலிருந்து மாவட்ட எல்லைகள் ஏற்றப்படுகின்றன...")
def load_boundaries(source_url):
    """Load the shapefile/GeoJSON ZIP directly from GitHub; no user upload needed."""
    response = requests.get(source_url, timeout=90)
    response.raise_for_status()
    raw = response.content
    temp_dir = tempfile.mkdtemp(prefix="tn_districts_")
    try:
        if zipfile.is_zipfile(BytesIO(raw)):
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                root = Path(temp_dir).resolve()
                for member in archive.infolist():
                    target = (root / member.filename).resolve()
                    if root not in target.parents and target != root:
                        raise ValueError("Unsafe path found in ZIP archive.")
                archive.extractall(temp_dir)

            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if shp_files:
                preferred = [p for p in shp_files if "district" in p.stem.lower()]
                gdf = gpd.read_file(str(preferred[0] if preferred else shp_files[0]))
            else:
                geojson_files = list(Path(temp_dir).rglob("*.geojson"))
                json_files = list(Path(temp_dir).rglob("*.json"))
                candidates = geojson_files or json_files
                if not candidates:
                    raise ValueError("GitHub tnshp.zip contains no .shp or GeoJSON file.")
                gdf = gpd.read_file(str(candidates[0]))
        else:
            gdf = gpd.read_file(BytesIO(raw))

        if gdf.empty:
            raise ValueError("The boundary file contains no features.")

        # Prefer dtname, but accept common district-name fields as a fallback.
        candidates = [
            "dtname", "DISTRICT", "District", "district", "DIST_NAME",
            "district_n", "NAME_2", "dt_name", "name"
        ]
        name_field = next((c for c in candidates if c in gdf.columns), None)
        if name_field is None:
            raise ValueError(
                "District-name field not found. Fields available: "
                + ", ".join(map(str, gdf.columns))
            )

        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        gdf = gdf.to_crs("EPSG:4326")
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        gdf["geometry"] = gdf.geometry.make_valid()
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
        gdf["__district_name"] = gdf[name_field].astype(str).str.strip()
        gdf = gdf[
            gdf["__district_name"].ne("")
            & gdf["__district_name"].ne("nan")
        ].copy()
        if gdf.empty:
            raise ValueError("No valid district polygons were found.")

        return gdf[["__district_name", "geometry"]].dissolve(
            by="__district_name", as_index=False
        )
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


try:
    districts = load_boundaries(SHAPE_SOURCE_URL)
except Exception as exc:
    st.error("GitHub-இலிருந்து மாவட்ட எல்லைகளை ஏற்ற முடியவில்லை.")
    st.code(str(exc))
    st.info(
        "GitHub repository-யில் tnshp.zip உள்ளது என்பதைச் சரிபார்க்கவும். "
        "ZIP-க்குள் .shp, .shx, .dbf மற்றும் .prj கோப்புகள் இருக்க வேண்டும்."
    )
    st.stop()

district_names = sorted(districts["__district_name"].unique().tolist())
if not district_names:
    st.error("மாவட்டப் பெயர்கள் கிடைக்கவில்லை.")
    st.stop()

if "district_statuses" not in st.session_state:
    st.session_state.district_statuses = {}
if "checked_districts" not in st.session_state:
    st.session_state.checked_districts = []

# Keep saved state valid if the boundary data changes.
st.session_state.district_statuses = {
    name: status
    for name, status in st.session_state.district_statuses.items()
    if name in district_names and status in CATEGORIES
}
st.session_state.checked_districts = [
    name for name in st.session_state.checked_districts if name in district_names
]


def make_map(gdf, statuses):
    map_df = gdf.copy()
    map_df["Rainfall Status"] = (
        map_df["__district_name"].map(statuses).fillna("No Status")
    )
    map_df["Tamil Status"] = map_df["Rainfall Status"].map(
        lambda x: CATEGORIES[x]["ta"]
    )
    fig = px.choropleth(
        map_df,
        geojson=map_df.__geo_interface__,
        locations=map_df.index,
        featureidkey="id",
        color="Rainfall Status",
        color_discrete_map={k: v["color"] for k, v in CATEGORIES.items()},
        hover_name="__district_name",
        hover_data={"Tamil Status": True, "Rainfall Status": False,
                    "__district_name": False},
        category_orders={"Rainfall Status": list(CATEGORIES.keys())},
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="#FFFFFF",
        showland=True,
        landcolor="#FFFFFF",
        showocean=True,
        oceancolor="#FFFFFF",
        showlakes=True,
        lakecolor="#FFFFFF",
    )
    fig.update_traces(marker_line_color="#333333", marker_line_width=0.8)
    fig.update_layout(
        height=650,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=5, r=5, t=45, b=5),
        title={"text": "தமிழ்நாடு மாவட்ட மழை நிலை", "x": 0.5},
        legend_title_text="மழை நிலை",
        font={"family": "Noto Sans Tamil, Noto Sans, sans-serif", "color": "#111111"},
    )
    return fig


st.subheader("1. மாவட்ட வரைபடம்")
st.caption("மாவட்டத்தின் பெயரை வரைபடத்தில் பார்த்து, கீழே உள்ள பட்டியலில் டிக் செய்யவும்.")
st.plotly_chart(
    make_map(districts, st.session_state.district_statuses),
    use_container_width=True,
    key="district_status_map",
)

st.subheader("2. புதுப்பிக்க வேண்டிய மாவட்டங்களைத் தேர்வு செய்யவும்")
top1, top2 = st.columns(2)
with top1:
    if st.button("☑️ அனைத்து மாவட்டங்களையும் தேர்வு செய்", use_container_width=True):
        st.session_state.checked_districts = district_names.copy()
        st.rerun()
with top2:
    if st.button("⬜ தேர்வுகளை நீக்கு", use_container_width=True):
        st.session_state.checked_districts = []
        st.rerun()

# Checkboxes are arranged in columns; multiple districts can be selected at once.
checkbox_cols = st.columns(3)
checked_now = []
for i, district in enumerate(district_names):
    with checkbox_cols[i % 3]:
        if st.checkbox(
            district,
            value=district in st.session_state.checked_districts,
            key=f"district_check_{district}",
        ):
            checked_now.append(district)
st.session_state.checked_districts = checked_now

st.caption(f"தேர்வு செய்யப்பட்ட மாவட்டங்கள்: {len(checked_now)} / {len(district_names)}")

st.subheader("3. தேர்வு செய்யப்பட்ட மாவட்டங்களுக்கு மழை நிலையை அமைக்கவும்")
status_options = list(CATEGORIES.keys())
chosen_status = st.selectbox(
    "மழை நிலை",
    status_options,
    format_func=lambda status: CATEGORIES[status]["ta"],
    index=1,
)
chosen_colour = CATEGORIES[chosen_status]["color"]
st.markdown(
    f"""<div style="background:{chosen_colour};color:#111;padding:12px;
    border:1px solid #555;border-radius:8px;font-weight:700;text-align:center">
    தேர்ந்தெடுத்த நிலை: {CATEGORIES[chosen_status]['ta']}</div>""",
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    if st.button("✅ தேர்வு செய்த மாவட்டங்களைப் புதுப்பி", type="primary",
                 use_container_width=True):
        if not checked_now:
            st.warning("முதலில் குறைந்தது ஒரு மாவட்டத்தையாவது டிக் செய்யவும்.")
        else:
            for name in checked_now:
                if chosen_status == "No Status":
                    st.session_state.district_statuses.pop(name, None)
                else:
                    st.session_state.district_statuses[name] = chosen_status
            st.success(f"{len(checked_now)} மாவட்டங்கள் புதுப்பிக்கப்பட்டன.")
            st.rerun()
with c2:
    if st.button("↩️ தேர்வு செய்த மாவட்டங்களின் நிலையை நீக்கு",
                 use_container_width=True):
        for name in checked_now:
            st.session_state.district_statuses.pop(name, None)
        st.rerun()

st.divider()
st.subheader("4. மாவட்ட நிலைச் சுருக்கம்")
statuses = st.session_state.district_statuses
assigned_count = len(statuses)
m1, m2, m3 = st.columns(3)
m1.metric("மொத்த மாவட்டங்கள்", len(district_names))
m2.metric("புதுப்பிக்கப்பட்ட மாவட்டங்கள்", assigned_count)
m3.metric("நிலை அமைக்கப்படாதவை", len(district_names) - assigned_count)

count_cols = st.columns(2)
for i, category in enumerate(status_options):
    with count_cols[i % 2]:
        st.metric(
            CATEGORIES[category]["ta"],
            sum(value == category for value in statuses.values()),
        )

if statuses:
    summary_df = pd.DataFrame([
        {
            "மாவட்டம்": district,
            "மழை நிலை": CATEGORIES[status]["ta"],
            "Rainfall Status (English)": status,
            "நிறம்": CATEGORIES[status]["color"],
        }
        for district, status in statuses.items()
    ]).sort_values(["மழை நிலை", "மாவட்டம்"])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ நிலைச் சுருக்கத்தை CSV ஆகப் பதிவிறக்கு",
        data=summary_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="Tamil_Nadu_Rainfall_Status.csv",
        mime="text/csv",
    )
else:
    st.caption("இதுவரை எந்த மாவட்டத்திற்கும் மழை நிலை அமைக்கப்படவில்லை.")

st.divider()
st.subheader("5. இறுதி வரைபடத்தைப் பதிவிறக்கவும்")
image_title = st.text_input("வரைபடத் தலைப்பு", "தமிழ்நாடு மாவட்ட மழை நிலை")

if st.button("🖼️ இறுதி வரைபடத்தை உருவாக்கு", type="primary"):
    try:
        plot_df = districts.copy()
        plot_df["Rainfall Status"] = (
            plot_df["__district_name"].map(statuses).fillna("No Status")
        )
        plot_df["Colour"] = plot_df["Rainfall Status"].map(
            lambda status: CATEGORIES[status]["color"]
        )

        # A4 portrait layout with a dedicated right-hand legend panel.
        # This keeps the legend completely outside the Tamil Nadu polygon.
        fig = plt.figure(figsize=(8.27, 11.69), dpi=300, facecolor="#FFFFFF")
        ax = fig.add_axes([0.035, 0.075, 0.68, 0.82])
        legend_ax = fig.add_axes([0.735, 0.22, 0.235, 0.48])
        legend_ax.set_axis_off()
        ax.set_facecolor("#FFFFFF")

        plot_df.plot(
            ax=ax,
            color=plot_df["Colour"],
            edgecolor="#343A40",
            linewidth=0.75,
            antialiased=True,
        )

        # Use representative points so labels remain inside multipart districts.
        # Add a subtle white halo to improve readability over all fill colours.
        import matplotlib.patheffects as path_effects

        for _, row in plot_df.iterrows():
            point = row.geometry.representative_point()
            label = ax.text(
                point.x,
                point.y,
                row["__district_name"],
                ha="center",
                va="center",
                fontsize=7.2,
                fontweight="bold",
                color="#161616",
                fontproperties=TAMIL_FONT,
                zorder=5,
                clip_on=True,
            )
            label.set_path_effects([
                path_effects.Stroke(linewidth=1.5, foreground="white"),
                path_effects.Normal(),
            ])

        legend_items = [
            mpatches.Patch(
                facecolor=CATEGORIES[category]["color"],
                edgecolor="#343A40",
                linewidth=0.8,
                label=CATEGORIES[category]["ta"],
            )
            for category in status_options
        ]
        legend_ax.legend(
            handles=legend_items,
            title="மழை நிலை",
            loc="upper left",
            fontsize=10,
            title_fontsize=11,
            prop=TAMIL_FONT,
            frameon=True,
            fancybox=False,
            framealpha=1,
            facecolor="#FFFFFF",
            edgecolor="#B8C0C8",
            borderpad=1.2,
            labelspacing=1.25,
            handlelength=1.8,
            handleheight=1.1,
        )
        legend_ax.text(
            0.02, 0.02,
            "தமிழ்நாடு மாவட்டங்கள்",
            transform=legend_ax.transAxes,
            ha="left", va="bottom",
            fontsize=8, color="#59636E",
            fontproperties=TAMIL_FONT,
        )

        fig.suptitle(
            image_title,
            x=0.49,
            y=0.965,
            fontsize=17,
            fontweight="bold",
            fontproperties=TAMIL_FONT,
            color="#17212B",
        )
        fig.text(
            0.49, 0.935,
            "மாவட்ட வாரியான மழை நிலை",
            ha="center", va="center",
            fontsize=10,
            fontproperties=TAMIL_FONT,
            color="#59636E",
        )
        ax.set_axis_off()
        ax.set_aspect("equal")

        image_buffer = BytesIO()
        fig.savefig(
            image_buffer,
            format="png",
            dpi=300,
            facecolor="#FFFFFF",
            pil_kwargs={"optimize": True},
        )
        plt.close(fig)
        image_bytes = image_buffer.getvalue()

        st.image(image_bytes, caption="தமிழ்நாடு மாவட்ட மழை நிலை வரைபடம்",
                 use_container_width=True)
        st.download_button(
            "⬇️ வரைபடத்தை PNG ஆகப் பதிவிறக்கு",
            data=image_bytes,
            file_name="Tamil_Nadu_District_Rainfall_Status.png",
            mime="image/png",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"வரைபடத்தை உருவாக்க முடியவில்லை: {exc}")

st.caption(
    "மிக கனமழை = ஆரஞ்சு • கனமழை = சிவப்பு • "
    "மிதமான மழை = மஞ்சள் • லேசான மழை = வெளிர் நீலம். "
    "இந்த நிலைகள் பயனரால் அமைக்கப்படுகின்றன; நேரடி மழை அளவீடுகள் அல்ல. "
    "தற்போதைய அமர்வில் மட்டும் நிலைகள் சேமிக்கப்படும்."
)
