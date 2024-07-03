import streamlit as st
from npri import npri
import pandas # installed from npri
import folium # installed from npri
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Overview")
st.markdown("# Overview")

substances = ["Carbon monoxide",
            "Sulphur dioxide",
            "Ammonia (total)",
            "PM10 - Particulate Matter <= 10 Micrometers",
            "PM2.5 - Particulate Matter <= 2.5 Micrometers",
            "Nitrogen oxides (expressed as nitrogen dioxide)",
            "Volatile Organic Compounds (Total)"
            ]
times = ["Most Recent", "Past 5 Years", "Past 15 Years", "All Years"]

@st.cache_data
def get_data(substance):
    try:
        fac = npri.Facilities(substances=[substance]) 
        data = fac.data
        data.reset_index(inplace=True) # Expose NpriID
        return fac,data
    except:
        print("Couldn't get data")

# PAGE LAYOUT
col1, col2 = st.columns([0.6, 0.4])

col2.markdown("## Select a pollutant")
select_substances = col2.selectbox(
    label = "Which criteria air contaminants do you want to focus on?",
    options = substances,
    label_visibility = "hidden"
)
fac, data = get_data(substance=select_substances)
#st.write(data) # Debugging

col2.markdown("## Select a timeframe")
select_times = col2.selectbox(
    label = "Which timeframe do you want to focus on?",
    options = times,
    label_visibility = "hidden" # Figure out to prevent this from re-firing the get_data call...
)

# Prep data
selector = select_substances + " - " + select_times
nodata = len(data.loc[data[selector].isna()])
chart_data = data.loc[~data[selector].isna()] # Don't show nulls? :( Or show them as other kinds of markers!
unmappable = len(chart_data.loc[chart_data.geometry.is_empty])
chart_data = chart_data[~chart_data.geometry.is_empty] # Can't show empty geometries (why are these here?)
chart_data = chart_data.sort_values(by=selector, ascending = False)


# Prep map data
m = folium.Map(tiles="cartodb positron")
chart_data['quantile'] = pandas.qcut(chart_data[selector], 4, labels=False)
chart_data.to_crs(4326, inplace=True)

markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
        popup=folium.Popup(
            str(mark["NpriID"])+'<br><b>'+selector+':</b> '+str(mark[selector])+'<br><b>Industry:</b> '+mark["NAICSTitleEn"]
            ),
        radius=(mark["quantile"] * 5) + 3, fill_color="orange", stroke="None", weight=.5
        ) for index, mark in chart_data.iterrows() if mark.geometry is not None
        ]
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
    st.warning('There are '+str(nodata)+' facilities without records on '+selector+' and an additional '+str(unmappable)+' that cannot be mapped', icon="⚠️")

col1.bar_chart(chart_data, x = "NpriID", y = selector) # Would need Altair for an effective (sorted) bar chart

col2.markdown("## Top ten facilities: " + selector)
col2.dataframe(chart_data[["NpriID", selector]].head(10)) # Add more info here

x, y = col2.columns(2)
x.metric("Median Residential Instability Score", round(chart_data[["median_instability_2021"]].median(),2)) # Need to explain median median.
x.info('Explain median of median and compare to national residential instability', icon="ℹ️")
# OTHER METRICS HERE
y.metric("Max Residential Instability Score", round(chart_data[["median_instability_2021"]].max(),2)) # Need to explain max median.
y.info('Explain median of median and compare to national residential instability', icon="ℹ️")

a, b = col2.columns(2)
# Top 10 industries
a.markdown("## Top ten industries: " + selector)
a.dataframe(chart_data.groupby(by="NAICSTitleEn")[["NpriID"]].nunique().sort_values(by="NpriID", ascending=False).head(10))
#a.metric("Median Number of Years These Facilities Have Been Active", chart_data[["NumberOfActiveYears"]].median())
#b.metric("Median Number of Substances These Facilities Reported in 2022", chart_data[["NumberOfSubstances"]].median())