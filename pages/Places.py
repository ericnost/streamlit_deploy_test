import streamlit as st
from npri import npri
from streamlit_folium import st_folium
import folium # installed from npri
import altair
from copy import deepcopy
import requests

substances = ["Carbon monoxide",
            "Sulphur dioxide",
            "Ammonia (total)",
            "PM10 - Particulate Matter <= 10 Micrometers",
            "PM2.5 - Particulate Matter <= 2.5 Micrometers",
            "Nitrogen oxides (expressed as nitrogen dioxide)",
            "Volatile Organic Compounds (Total)"
            ]
times = ["Most Recent", "Past 5 Years", "Past 15 Years", "All Years"]
cimd = {"Residential instability Scores": ["Residential Instability Scores", "the tendency of neighbourhood inhabitants to fluctuate over time, taking into consideration both housing and familial characteristics"],
        "Economic dependency Scores": ["Economic Dependency Scores", "to reliance on the workforce, or a dependence on sources of income other than employment income"], 
        "Ethno-cultural composition Scores": ["Ethnocultural Composition Scores", "the community make-up of immigrant populations, and at the national-level, for example, takes into consideration indicators such as ... the proportion of the population who self-identified as visible minority..."], 
        "Situational vulnerability Scores": ["Situational Vulnerability Scores", "variations in socio-demographic conditions in the areas of housing and education, while taking into account other demographic characteristics"]}    

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

@st.cache_data 
def get_context(list_of_ids):
    try:
        print("getting data...")
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select "NpriID", "median_instability_2021", geom from npri_exporter_table where "NpriID" in ({});'.format(list_of_ids))
        return data
    except:
        print("Couldn't get data")

# PAGE LAYOUT
top = st.container()
left, middle = top.columns([.15,.85])
left.markdown("## Places")
middle.markdown("This page provides more information about facilities in a given place reporting releases of regulated substances to the National Pollutant Release Inventory")
middle.warning("These numbers are facility self-reported estimates compiled by Environment and Climate Change Canada. Please see here for more information about how to interpet NPRI data: https://www.canada.ca/en/environment-climate-change/services/national-pollutant-release-inventory/using-interpreting-data.html")

col1, col2 = st.columns([0.4, 0.6])

# SELECTIONS
## Select FSA
idx = 0
if "fsa" in st.query_params.keys():
    if st.query_params["fsa"].upper() in list(fsas["ForwardSortationArea"].unique()):
        idx = list(fsas["ForwardSortationArea"].unique()).index(st.query_params["fsa"].upper())
    else:
        st.query_params["fsa"] = list(fsas["ForwardSortationArea"].unique())[0]
else:
    st.query_params["fsa"] = list(fsas["ForwardSortationArea"].unique())[0]
def change_fsa_url():
    st.query_params["fsa"] = st.session_state.fsa
select_fsa  = col2.selectbox(
    "### **1. Select an FSA**",
    list(fsas["ForwardSortationArea"].unique()),
    index = idx,
    help = "Forward Sortation Areas are the first three numbers/letters of a postal code, e.g. N1E",
    on_change=change_fsa_url,
    key="fsa"
)

col2a, col2b = col2.columns(2)

## Select substance
idx = 0
if "substance" in st.query_params.keys():
    if st.query_params["substance"].lower() in [s.lower() for s in substances]:
        idx = [s.lower() for s in substances].index(st.query_params["substance"].lower())
    else:
        st.query_params["substance"] = substances[0]
else:
    st.query_params["substance"] = substances[0]
def change_sub_url():
    st.query_params["substance"] = st.session_state.substance
select_substance  = col2a.selectbox( #multiselect
    "### **2. Select a Criteria Air Contaminant**",
    substances,
    index=idx,
    help = "Criteria Air Contaminants are the most common air pollutants in Canada by weight. See here: https://www.canada.ca/en/environment-climate-change/services/air-pollution/pollutants/common-contaminants.html",
    on_change = change_sub_url,
    key="substance"
)
## Get health information
url = "https://www.canada.ca/en/health-canada/services/chemical-substances/fact-sheets/chemicals-glance/{}.html".format(select_substance.lower().replace(" ", "-"))
page = requests.get(url)
if page.status_code == 200:
    health = "Learn more about "+select_substance+" here: "+ url
else:
    health = "Unable to retrieve information about the health effects of "+select_substance+" at this time. Try searching: https://www.canada.ca/en/health-canada/services/chemical-substances/fact-sheets/chemicals-glance/"
col2a.info(health, icon="ℹ️")

## Select time
idx = 0
if "timeframe" in st.query_params.keys():
    if st.query_params["timeframe"].lower() in [t.lower() for t in times]:
        idx = [t.lower() for t in times].index(st.query_params["timeframe"].lower())
    else:
        st.query_params["timeframe"] = times[0]
else:
    st.query_params["timeframe"] = times[0]
def change_times_url():
    st.query_params["timeframe"] = st.session_state.time
select_time  = col2a.selectbox(
    "### **3. Select a timeframe**",
    times,
    index=idx, 
    help = "NPRI began in 1993, but some substances were only added to the list later.",
    on_change=change_times_url,
    key="time"
)


# GET DATA
places = get_places(select_fsa)
this_fsa = get_this_fsa(select_fsa)
#st.write(places.data)
dauids = list(places.data.index.unique())
facilities = get_facilities(dauids)
#st.write(facilities.data)

# Process data
select_measure = select_substance + " - " + select_time
min = facilities.data[select_measure].min()
max = facilities.data[select_measure].max()
filter_fac = col2a.slider(
    "### **4. Filter the facilities releasing "+ select_substance +" in this range (tonnes):**",
    min-.01, max+.01, (min, max)
    )
filtered = deepcopy(facilities)
filtered.working_data = filtered.working_data.loc[(filtered.working_data[select_measure]>=filter_fac[0]) & (filtered.working_data[select_measure]<=filter_fac[1])]
#st.write(filtered)

# Chart data
col2b.markdown("### {} | {} | {} ".format(
    select_fsa, 
    select_measure,
    str(round(filter_fac[0],2)) + "-" + str(round(filter_fac[1],2)) + " tonnes",
    )
) 

to_chart = filtered.working_data.reset_index()[["NpriID", select_measure]]
to_chart["NpriID"] = to_chart["NpriID"].astype(str)
col2b.markdown("#### Top 10 Facilities ({} total)".format(str(to_chart.shape[0])))
col2b.altair_chart(
    altair.Chart(to_chart.sort_values(by=select_measure, ascending=False).head(10)).mark_bar().encode(
        x=altair.X(select_measure),
        y=altair.Y("NpriID" ).sort('-x')
    )
)
# Industries
toptenind = filtered.working_data.reset_index().loc[~filtered.working_data.reset_index()[select_measure].isna()].groupby(by="NAICSTitleEn")[[select_measure]].sum()
col2b.markdown("#### Top 10 Industries ({} total)".format(str(toptenind.shape[0])))
toptenind = toptenind.reset_index().sort_values(by=select_measure, ascending=False).head(10)
col2b.altair_chart(
    altair.Chart(toptenind).mark_bar().encode(
        x=altair.X(select_measure),
        y=altair.Y("NAICSTitleEn" ).sort('-x')
    )
)

# PLACES
select_attribute_place = col2a.selectbox(
    "### **5. Select a Census indicator of 'deprivation' to display**",
    cimd.keys(),
    help =  "".join(s[0] + " " + s[1] + ". " for s in cimd.values()) + "See here: https://www150.statcan.gc.ca/n1/pub/45-20-0001/452000012023002-eng.htm"
)
#col2a.info(cimd[select_attribute_place][0] + " refers to " + cimd[select_attribute_place][1] + ".",icon="ℹ️")
min = places.data[select_attribute_place].min()
max = places.data[select_attribute_place].max()
filter_place = col2a.slider(
    "### **6. Focus on Census Dissemination Areas with " + select_attribute_place + " in this range:**",
    min, max, (min, max)
    )
filtered_places = deepcopy(places)
filtered_places.working_data = filtered_places.working_data.loc[(filtered_places.working_data[select_attribute_place]>=filter_place[0]) & (filtered_places.working_data[select_attribute_place]<=filter_place[1])]
#st.write(filtered)

# Scatter plot
x = select_substance + " - Allocated"
y = select_attribute_place
col2b.markdown("#### Characteristics of Dissemination Areas")
col2b.info("Here, releases of "+select_substance+" are 'allocated' across the Census Dissemination Areas that are within 5 km of polluting facilities, based on how much each Dissemination Area intersects with that buffer",icon="ℹ️")
col2b.scatter_chart(filtered_places.working_data.reset_index(), x=x, y=y)

# CIMD
#x, y = col2a.columns([.5,.5])
col2a.metric("Median of "+cimd[select_attribute_place][0]+ " in all Dissemination Areas intersecting with this FSA", round(filtered_places.working_data[select_attribute_place].median(),2))
col2a.metric("Max of "+cimd[select_attribute_place][0]+ " in all Dissemination Areas intersecting with this FSA", round(filtered_places.working_data[select_attribute_place].max(),2)) 


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