import streamlit as st
from npri import npri
import pandas # installed from npri
import folium # installed from npri
from streamlit_folium import st_folium
import geopandas

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
times = [year for year in range(1993,2023)]

@st.cache_data
def get_substances():
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select distinct "Substance" from npri_reports_full_table;') # need to enable multi-substance select....
        return data
    except:
        print("Couldn't get data")
substances = get_substances()

@st.cache_data
def get_fsas():
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select distinct "ForwardSortationArea" from npri_exporter_table;')
        return data
    except:
        print("Couldn't get data")
fsas = get_fsas()

@st.cache_data
def get_places(fsa):
    """
    fsa -- str: selected FSA
    """
    fsa = [fsa]
    try:
        data = npri.Places(place=fsa)
        return data
    except:
        print("Couldn't get data")

@st.cache_data
def get_facilities(dauids):
    """
    dauids -- list: DAUIDs that intersect the selected FSA 
    """
    st.write(dauids)
    try:
        data = npri.Facilities(within=dauids)
        return data
    except:
        print("Couldn't get data")
   
def get_context(list_of_ids):
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select "NpriID", "median_instability_2021", geom from npri_exporter_table where "NpriID" in ({});'.format(list_of_ids))
        return data
    except:
        print("Couldn't get data")

# PAGE LAYOUT
col1, col2 = st.columns([0.4, 0.6])

col2.markdown("## Select an FSA")
select_fsa  = col2.selectbox(
    "Select FSA",
    ["N1E"]#list(fsas["ForwardSortationArea"].unique()),
    
)
places = get_places(select_fsa)
st.write(places.data)
dauids = list(places.data.index.unique())
facilities = get_facilities(dauids)
st.write(facilities.data)
"""

# Get data
records = get_records(facilities, select_times)

# Prep data
ids = list(records["NpriID"].unique())
list_of_ids = ""
for id in ids:
    list_of_ids += str(id) + ","
list_of_ids = list_of_ids[:-1]
context = get_context(list_of_ids)
context['geometry'] = geopandas.GeoSeries.from_wkb(context['geom'])
context.drop("geom", axis=1, inplace=True)
context.set_index("NpriID", inplace=True)

# Aggregate by NpriID
aggregate = records.groupby(by=["NpriID", "Substance"])[["SumInTonnes"]].sum().reset_index()
aggregate.set_index("NpriID", inplace=True)
"""
# Prep map
col2.markdown("## Select an attribute of facilities")
select_attribute_fac  = col2.selectbox(
    "Select attribute",
    list(facilities.data.columns),
    
)
col2.markdown("## Select an attribute of places")
select_attribute_place = col2.selectbox(
    "Select attribute",
    list(places.data.columns),
)

facilities.get_features(select_attribute_fac)
places.get_features(select_attribute_place)
lat = (places.features[select_attribute_place][0].get_bounds()[1][0] + places.features[select_attribute_place][0].get_bounds()[0][0]) / 2
long = (places.features[select_attribute_place][0].get_bounds()[1][1] + places.features[select_attribute_place][0].get_bounds()[0][1]) / 2

m = folium.Map(tiles="cartodb positron", zoom_start = 11, location=(lat,long))
fg = folium.FeatureGroup()


for da in places.features[select_attribute_place]:
    fg.add_child(da)
for marker in facilities.features[select_attribute_fac]:
    fg.add_child(marker)


with col1:
    st_folium(
        m,
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )

"""

all_fac = []
markers = []

for i,s in enumerate(select_substances):
    if i == 0:
        sub0 = aggregate.loc[aggregate["Substance"]==s]
        col2.markdown("## Top ten facilities: {}, ".format(s) + str(select_times[0]) + "-" + str(select_times[1]))
        toptentotal = sub0.sort_values(by="SumInTonnes", ascending=False).head(10)
        col2.dataframe(toptentotal) # Add more info here
        select_facs_0 = col2.slider(
            "Facilities releasing "+ s +" in this range:",
            sub0["SumInTonnes"].min(), sub0["SumInTonnes"].max(), (sub0["SumInTonnes"].min(), sub0["SumInTonnes"].max()))
        ## Markers
        sub0['quantile'] = pandas.qcut(sub0["SumInTonnes"], 4, labels=False)
        to_mark = sub0.join(context, how="left")
        to_mark = geopandas.GeoDataFrame(to_mark, crs=3347)   
        to_mark.to_crs(4326, inplace=True)
        to_mark.set_geometry("geometry", inplace=True)
        to_mark = to_mark.loc[(to_mark["SumInTonnes"]>=select_facs_0[0]) & (to_mark["SumInTonnes"]<=select_facs_0[1])]
        markers.extend([folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
        popup=folium.Popup(
            str(index)+'<br><b>{}:</b> '.format(s)+str(mark["SumInTonnes"])+'<br><b>CIMD - Median Residential Instability Score: </b>'+str(mark["median_instability_2021"])+''),
        radius=(mark["quantile"] * 5) + 3, fill_color="#FFA500", weight=.5, fill_opacity=0.75
        ) for index, mark in to_mark.iterrows() if mark.geometry is not None
        ])
        all_fac.append(sub0)
        col2.bar_chart(records.loc[records["Substance"]==s][["ReportYear", "SumInTonnes"]].sort_values(by="SumInTonnes"), x = "ReportYear", y="SumInTonnes", color="#FFA500")
    if i == 1:
        sub1 = aggregate.loc[aggregate["Substance"]==s]
        col2.markdown("## Top ten facilities: {}, ".format(s) + str(select_times[0]) + "-" + str(select_times[1]))
        toptentotal = sub1.sort_values(by="SumInTonnes", ascending=False).head(10)
        col2.dataframe(toptentotal)
        select_facs_1 = col2.slider(
            "Facilities releasing "+ s +" in this range:",
            sub1["SumInTonnes"].min(), sub1["SumInTonnes"].max(), (sub1["SumInTonnes"].min(), sub1["SumInTonnes"].max()))
        ## Markers
        sub1['quantile'] = pandas.qcut(sub1["SumInTonnes"], 4, labels=False)
        to_mark = sub1.join(context, how="left")
        to_mark = geopandas.GeoDataFrame(to_mark, crs=3347)   
        to_mark.to_crs(4326, inplace=True)
        to_mark.set_geometry("geometry", inplace=True)
        to_mark = to_mark.loc[(to_mark["SumInTonnes"]>=select_facs_1[0]) & (to_mark["SumInTonnes"]<=select_facs_1[1])]
        markers.extend([folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
        popup=folium.Popup(
            str(index)+'<br><b>{}:</b> '.format(s)+str(mark["SumInTonnes"])+'<br><b>CIMD - Median Residential Instability Score: </b>'+str(mark["median_instability_2021"])+''),
        radius=(mark["quantile"] * 5) + 3, fill_color="#50C878", weight=.5, fill_opacity=0.75
        ) for index, mark in to_mark.iterrows() if mark.geometry is not None
        ])
        all_fac.append(sub1)
        col2.bar_chart(records.loc[records["Substance"]==s][["ReportYear", "SumInTonnes"]].sort_values(by="SumInTonnes"), x = "ReportYear", y="SumInTonnes", color="#50C878")
    if i == 2:
        sub2 = aggregate.loc[aggregate["Substance"]==s]
        col2.markdown("## Top ten facilities: {}, ".format(s) + str(select_times[0]) + "-" + str(select_times[1]))
        toptentotal = sub2.sort_values(by="SumInTonnes", ascending=False).head(10)
        col2.dataframe(toptentotal) # Add more info here
        select_facs_2 = col2.slider(
            "Facilities releasing "+ s +" in this range:",
            sub2["SumInTonnes"].min(), sub2["SumInTonnes"].max(), (sub2["SumInTonnes"].min(), sub2["SumInTonnes"].max()))
        ## Markers
        sub2['quantile'] = pandas.qcut(sub2["SumInTonnes"], 4, labels=False)
        to_mark = sub2.join(context, how="left")
        to_mark = geopandas.GeoDataFrame(to_mark, crs=3347)   
        to_mark.to_crs(4326, inplace=True)
        to_mark.set_geometry("geometry", inplace=True)
        to_mark = to_mark.loc[(to_mark["SumInTonnes"]>=select_facs_2[0]) & (to_mark["SumInTonnes"]<=select_facs_2[1])]
        markers.extend([folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
        popup=folium.Popup(
            str(index)+'<br><b>{}:</b> '.format(s)+str(mark["SumInTonnes"])+'<br><b>CIMD - Median Residential Instability Score: </b>'+str(mark["median_instability_2021"])+''),
        radius=(mark["quantile"] * 5) + 3, fill_color="#FF5733", weight=.5, fill_opacity=0.75
        ) for index, mark in to_mark.iterrows() if mark.geometry is not None
        ])
        all_fac.append(sub2)
        col2.bar_chart(records.loc[records["Substance"]==s][["ReportYear", "SumInTonnes"]].sort_values(by="SumInTonnes"), x = "ReportYear", y="SumInTonnes", color="#FF5733")

# Make larger markers appear in the back so as to not obscure small markers
markers.sort(key=lambda x: x.options["radius"], reverse=True)
for marker in markers:
    fg.add_child(marker)

#bounds = m.get_bounds() # Currently does not work. Follow: https://github.com/randyzwitch/streamlit-folium/issues/152
#m.fit_bounds(bounds)

with col1:
    st_folium(
        m,
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )
    #st.warning('There are '+str(nodata)+' facilities without records on '+selector+' and an additional '+str(unmappable)+' that cannot be mapped', icon="⚠️")

#col1.bar_chart(chart_data, x = "NpriID", y = selector) # Would need Altair for an effective (sorted) bar chart

x, y = col1.columns(2)
from functools import reduce
all_fac = reduce(lambda x, y: pandas.merge(x, y, on = 'NpriID'), all_fac)
all_fac = list(all_fac.index.unique())
x.metric("Median Residential Instability Score", round(context.loc[context.index.isin(all_fac)][["median_instability_2021"]].median(),2)) # Need to explain median median.
x.info('Explain median of median and compare to national residential instability', icon="ℹ️")
# OTHER METRICS HERE
y.metric("Max Residential Instability Score", round(context.loc[context.index.isin(all_fac)][["median_instability_2021"]].max(),2)) # Need to explain max median.
y.info('Explain median of median and compare to national residential instability', icon="ℹ️")
"""