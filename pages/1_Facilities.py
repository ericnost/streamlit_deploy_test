import streamlit as st
from npri import npri
import pandas # installed from npri
import folium # installed from npri
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Facilities")
st.markdown("# Facilities")

@st.cache_data
def get_data():
    fac = npri.Facilities(across = "ON") # Eventually, will be able to directly query Facilities via substances...That might help with markers too because then we can just pass the Folium map generated by npri into st_folium?
    data = fac.data
    data.reset_index(inplace=True) # Expose NpriID
    return fac,data
fac, data = get_data()
#st.write(data) # Debugging
substances = ["Carbon monoxide",
            "Sulphur dioxide",
            "Ammonia (total)",
            "PM10 - Particulate Matter <= 10 Micrometers",
            "PM2.5 - Particulate Matter <= 2.5 Micrometers",
            "Nitrogen oxides (expressed as nitrogen dioxide)",
            "Volatile Organic Compounds (Total)"
            ] # Eventually should include other kinds of measures.... How to keep track of these?

col1, col2 = st.columns([0.6, 0.4])

col2.markdown("## Select a pollutant")
select_substances = col2.selectbox(
    label = "Which criteria air contaminants do you want to focus on?",
    options = substances,
    label_visibility = "hidden"
)

# Prep data
chart_data = data.loc[~data[select_substances].isna()] # Don't show nulls? :( Or show them as other kinds of markers!
chart_data = chart_data.sort_values(by=select_substances, ascending = False)

# Prep map data
m = folium.Map(tiles="cartodb positron")
chart_data['quantile'] = pandas.qcut(chart_data[select_substances], 4, labels=False)
chart_data.to_crs(4326, inplace=True)
markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
      popup=folium.Popup(str(mark["NpriID"])+'<br><b>Substances:</b> '+mark["Substances"]+'<br><b>Years Active:</b> '+str(mark["NumberOfActiveYears"])+'<br><b>Industry:</b> '+mark["NAICSTitleEn"]),
      radius=(mark["quantile"] * 5) + 3, fill_color="orange", stroke="None") for index, mark in chart_data.iterrows() if not mark.geometry.is_empty]
# Proportional scaling of data. According to Streamlit, "The size of the circles representing each point, in meters." (!!!)
fg = folium.FeatureGroup(name="Facilities")
for marker in markers:
    fg.add_child(marker)

#bounds = m.get_bounds() # Currently does not work. Follow: https://github.com/randyzwitch/streamlit-folium/issues/152
#m.fit_bounds(bounds)

with col1:
    st_folium(
        m, #fac.show_data_map(attribute="NumberOfSubstances")
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )

#col1.bar_chart(chart_data, x = "NpriID", y = select_substances) # Would need Altair for an effective (sorted) bar chart

col2.markdown("## Top ten facilities: " + select_substances)

col2.dataframe(chart_data[["NpriID", select_substances]].head(10)) # Add more info here

x, y = col2.columns(2)
x.metric("Median % Visible Minority", chart_data[["median_1684"]].median()) # Will be replaced with CIMD soon. Also need to explain median median.
y.metric("Max % Visible Minority", chart_data[["median_1684"]].max()) # Will be replaced with CIMD soon. Also need to explain max median.
a, b = col2.columns(2)
a.metric("Median Number of Years These Facilities Have Been Active", chart_data[["NumberOfActiveYears"]].median())
b.metric("Median Number of Substances These Facilities Reported in 2022", chart_data[["NumberOfSubstances"]].median())