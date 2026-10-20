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

        fig, ax = plt.subplots(figsize=(10, 12), dpi=200, facecolor="white")
        ax.set_facecolor("white")
