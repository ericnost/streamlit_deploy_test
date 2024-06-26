import streamlit as st
from npri import npri
import pandas # installed from npri
import folium # installed from npri
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Places")
st.markdown("# Places")

@st.cache_data
def get_data():
    try:
        fac = npri.Places(across=["ON"]) #near=[43.54, -80.25]
        data = fac.data
        data.reset_index(inplace=True) # Expose ID
        return fac,data
    except:
        print("Couldn't get data")
fac,data = get_data()

#st.write(data)

substances = ["total_co_2022",
            "total_pm10_2022",
            "total_so2_2022",
            "total_ammonia_2022",
            "total_pm25_2022"
            ] # Eventually these should be EJScreen-like metrics (see Kelly Evans's work).... 

col1, col2 = st.columns([0.6, 0.4])

col2.markdown("## Select a measure")
select_substances = col2.selectbox(
    label = "Which criteria air contaminants do you want to focus on?",
    options = substances,
    label_visibility = "hidden"
)

chart_data = data#.loc[~data[select_substances].isna()] # Don't show nulls? :(
chart_data = chart_data.sort_values(by=select_substances, ascending = False)

# Prep map data
m = folium.Map(tiles="cartodb positron")

# Create GeoJson
fg = folium.FeatureGroup(name="Facilities")
layer = folium.GeoJson(fac.data.loc[fac.data[select_substances] >= 0]) #.filters(attribute=select_substances, operator=">=", value=0)) # Illustrates Streamlit Folium dynamic render
fg.add_child(layer)

with col1:
    st_folium(
        m,
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )

col2.markdown("## Top ten neighbourhoods: " + select_substances)

col2.dataframe(chart_data[["dauid", select_substances]].head(10)) # Add more info here

col2.scatter_chart(
    chart_data,
    x=select_substances,
    y='C10_RATE_TOTAL'
)