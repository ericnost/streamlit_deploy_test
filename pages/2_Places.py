import streamlit as st
from npri import npri
from streamlit_folium import st_folium
import folium # installed from npri
import altair
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Overview")
st.markdown("# Places")

if st.button("Overview"):
    st.switch_page("pages/1_Overview.py")

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
def get_this_fsa(fsa):
    """
    Load geometry of FSA for mapping purposes (need to add FSA shapes to Google db)
    """
    try:
        print("getting data...")
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select * from from lfsa.... where X = \''+fsa+'\';')
        return data
    except:
        print("Couldn't get data")

@st.cache_data
def get_fsas():
    try:
        print("getting data...")
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
        print("getting data...")
        data = npri.Places(place=fsa)
        return data
    except:
        print("Couldn't get data")

@st.cache_data
def get_facilities(dauids):
    """
    dauids -- list: DAUIDs that intersect the selected FSA 
    """
    #st.write(dauids)
    try:
        print("getting data...")
        data = npri.Facilities(within=dauids)
        return data
    except:
        print("Couldn't get data")
   
def get_context(list_of_ids):
    try:
        print("getting data...")
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

# Get data
places = get_places(select_fsa)
this_fsa = get_this_fsa(select_fsa)
#st.write(places.data)
dauids = list(places.data.index.unique())
facilities = get_facilities(dauids)
#st.write(facilities.data)
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
col2a, col2b = col2.columns(2)
col2a.markdown("## Select a measure")
select_substance  = col2a.selectbox(
    "Select substance",
    substances,  
)

select_time  = col2a.selectbox(
    "Select a timeframe",
    times,   
)

select_measure = select_substance + " - " + select_time

min = facilities.data[select_measure].min()
max = facilities.data[select_measure].max()
filter_fac = col2a.slider(
    "Which facilities do you want to focus on?",
    min, max, (min, max)
    )
filtered = deepcopy(facilities)
filtered.working_data = filtered.working_data.loc[(filtered.working_data[select_measure]>=filter_fac[0]) & (filtered.working_data[select_measure]<=filter_fac[1])]
#st.write(filtered)

to_chart = filtered.working_data.reset_index()[["NpriID", select_measure]].sort_values(by=select_measure, ascending=False).head(10)
to_chart["NpriID"] = to_chart["NpriID"].astype(str)
col2b.altair_chart(
    altair.Chart(to_chart).mark_bar().encode(
        x=altair.X(select_measure),
        y=altair.Y("NpriID" ).sort('-x')
    )
)
# Industries
toptenind = filtered.working_data.reset_index().loc[~filtered.working_data.reset_index()[select_measure].isna()].groupby(by="NAICSTitleEn")[["NpriID"]].nunique().sort_values(by="NpriID", ascending=False).head(10)
col2b.altair_chart(
    altair.Chart(toptenind.reset_index()).mark_bar().encode(
        x=altair.X("NpriID"),
        y=altair.Y("NAICSTitleEn" ).sort('-x')
    )
)

# PLACES
col2a.markdown("## Select a CIMD score")
select_attribute_place = col2a.selectbox(
    "Select attribute",
    list(places.data.columns),
)
min = places.data[select_attribute_place].min()
max = places.data[select_attribute_place].max()
filter_place = col2a.slider(
    "Which places do you want to focus on?",
    min, max, (min, max)
    )
filtered_places = deepcopy(places)
filtered_places.working_data = filtered_places.working_data.loc[(filtered_places.working_data[select_attribute_place]>=filter_place[0]) & (filtered_places.working_data[select_attribute_place]<=filter_place[1])]
#st.write(filtered)

# Scatter plot
x = select_measure #select_substance + " - Allocated"
y = select_attribute_place
chart_data = filtered_places.working_data.reset_index()[[x,y]]
col2b.scatter_chart(filtered_places.working_data.reset_index(), x=x, y=y)



# CIMD
## median, max, distribution
col2a.metric(select_attribute_place + " median:", filtered_places.working_data[select_attribute_place].median())
col2a.metric(select_attribute_place + " max:", filtered_places.working_data[select_attribute_place].max())

# Map
filtered.get_features(select_measure)
filtered_places.get_features(select_attribute_place)
lat = (filtered_places.features[select_attribute_place][0].get_bounds()[1][0] + filtered_places.features[select_attribute_place][0].get_bounds()[0][0]) / 2
long = (filtered_places.features[select_attribute_place][0].get_bounds()[1][1] + filtered_places.features[select_attribute_place][0].get_bounds()[0][1]) / 2

m = folium.Map(tiles="cartodb positron", zoom_start = 12, location=(lat,long))
fg = folium.FeatureGroup()


for da in filtered_places.features[select_attribute_place]:
    fg.add_child(da)
for marker in filtered.features[select_measure]:
    fg.add_child(marker)


with col1:
    st_folium(
        m,
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )