import streamlit as st
from npri import npri
import pandas # installed from npri
import folium # installed from npri
from streamlit_folium import st_folium
import geopandas
import altair
import requests

st.set_page_config(layout="wide", page_title="Overview")

@st.cache_data
def get_substances():
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select distinct "Substance" from npri_reports_full_table;') 
        return data
    except:
        print("Couldn't get data")
substances = get_substances()

@st.cache_data
def get_records(substance, years):
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select "NpriID", "Substance", "ReportYear", "SumInTonnes" from npri_reports_full_table where "ReportYear" >= '+str(years[0])+' and "ReportYear" <= '+str(years[1])+' and lower("Substance") in ({})'.format(','.join('\''+s.lower()+'\'' for s in substance)) 
                                           )
        return data
    except:
        print("Couldn't get data")

cimd = {"median_instability_2021": ["Residential Instability Scores", "the tendency of neighbourhood inhabitants to fluctuate over time, taking into consideration both housing and familial characteristics"],
        "median_dependency_2021": ["Economic Dependency Scores", "to reliance on the workforce, or a dependence on sources of income other than employment income"], 
        "median_composition_2021": ["Ethnocultural Composition Scores", "the community make-up of immigrant populations, and at the national-level, for example, takes into consideration indicators such as ... the proportion of the population who self-identified as visible minority..."], 
        "median_vulnerability_2021": ["Situational Vulnerability Scores", "variations in socio-demographic conditions in the areas of housing and education, while taking into account other demographic characteristics"]}    
def get_context(list_of_ids):
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select "NpriID", "NAICSTitleEn", "median_instability_2021", "median_dependency_2021", "median_composition_2021", "median_vulnerability_2021", geom from npri_exporter_table where "NpriID" in ({});'.format(list_of_ids))
        return data
    except:
        print("Couldn't get data")

# PAGE LAYOUT
top = st.container()
left, middle, right = top.columns([.15,.6, .25])
left.markdown("# Overview")
middle.markdown("This page provides an overview of facilities reporting releases of regulated substances to the National Pollutant Release Inventory")
middle.warning("These numbers are facility self-reported estimates compiled by Environment and Climate Change Canada. Please see here for more information about how to interpet NPRI data: https://www.canada.ca/en/environment-climate-change/services/national-pollutant-release-inventory/using-interpreting-data.html")
right.markdown("Click here to focus on releases in a specific area: ")
if right.button("Places"):
    st.switch_page("pages/2_Places.py")

col1, col2 = st.columns([0.4, 0.6])
col2a, col2b = col2.columns(2)
select_substances  = col2a.selectbox( #multiselect
    "### **1. Select a pollutant**",
    list(substances["Substance"].unique()),
    help = "See more about which substances are required to be reported on and in what amounts here: https://www.canada.ca/en/environment-climate-change/services/national-pollutant-release-inventory/substances-list/threshold.html"
)
## Get health information
url = "https://www.canada.ca/en/health-canada/services/chemical-substances/fact-sheets/chemicals-glance/{}.html".format(select_substances.lower().replace(" ", "-"))
page = requests.get(url)
if page.status_code == 200:
    health = "Learn more about "+select_substances+" here: "+ url
else:
    health = "Unable to retrieve information about the health effects of  "+select_substances+" at this time. Try searching: https://www.canada.ca/en/health-canada/services/chemical-substances/fact-sheets/chemicals-glance/"
col2a.info(health, icon="ℹ️")

times = [year for year in range(1993,2022)]
select_times = col2a.slider(
    "### **2. Select a timeframe to focus on**",
    1993, 2022, (2013, 2022),
    step = 1,
    help = "NPRI began in 1993, but some substances were only added to the list later.")

## Get data
records = get_records([select_substances], select_times)

## Prep data
ids = list(records["NpriID"].unique())
list_of_ids = ""
for id in ids:
    list_of_ids += str(id) + ","
list_of_ids = list_of_ids[:-1]
context = get_context(list_of_ids)
try:
    context['geometry'] = geopandas.GeoSeries.from_wkb(context['geom'])
    context.drop("geom", axis=1, inplace=True)
    context.set_index("NpriID", inplace=True)
except: # No facilities found
    st.error("Something went wrong - it may be that there are no facilities that reported "+select_substances+" for this timeframe. In some cases, there may be too many facilities for us to display. Try selecting a different range of years.")
    st.stop()

## Aggregate by NpriID
aggregate = records.groupby(by=["NpriID", "Substance"])[["SumInTonnes"]].sum().reset_index()
aggregate.set_index("NpriID", inplace=True)

## Facility filter
select_facs = col2a.slider(
    "### **3. Filter the facilities releasing "+ select_substances +" in this range (tonnes):**",
    aggregate["SumInTonnes"].min()-.01, aggregate["SumInTonnes"].max()+.01, (aggregate["SumInTonnes"].min(), aggregate["SumInTonnes"].max()))
aggregate = aggregate.loc[(aggregate["SumInTonnes"]>=select_facs[0]) & (aggregate["SumInTonnes"]<=select_facs[1])]

## Calculate industry metrics
ind = aggregate.join(context[["NAICSTitleEn"]])
ind = ind.groupby(by=["NAICSTitleEn", "Substance"])[["SumInTonnes"]].sum().reset_index()
ind.set_index("NAICSTitleEn", inplace=True)

## Facilities
col2b.markdown("### {} | {} | {}".format(
    select_substances, 
    str(select_times[0]) + "-" + str(select_times[1]),
    str(round(select_facs[0],2)) + "-" + str(round(select_facs[1],2)) + " tonnes",
    )
) 
col2b.markdown("#### Top 10 Facilities ({} total)".format(str(aggregate.shape[0])))
toptentotal = aggregate.sort_values(by="SumInTonnes", ascending=False).head(10)
toptentotal.reset_index(inplace=True)
toptentotal["NpriID"] = toptentotal["NpriID"].astype(str)
col2b.altair_chart(
    altair.Chart(toptentotal).mark_bar().encode(
        x=altair.X("SumInTonnes"),
        y=altair.Y("NpriID" ).sort('-x')
    )
)
## Industries 
col2b.markdown("#### Top 10 Industries ({} total)".format(str(ind.shape[0])))
toptenind = ind.sort_values(by="SumInTonnes", ascending=False).head(10)

toptenind.reset_index(inplace=True)
col2b.altair_chart(
    altair.Chart(toptenind).mark_bar().encode(
        x=altair.X("SumInTonnes"),
        y=altair.Y("NAICSTitleEn" ).sort('-x')
    )
)

# Prep map
m = folium.Map(tiles="cartodb positron", zoom_start = 4, location=(60,-100))
fg = folium.FeatureGroup(name="Facilities")

markers = []

## Markers
aggregate['quantile'] = pandas.qcut(aggregate["SumInTonnes"], 4, labels=False, duplicates="drop") #duplicates drop to handle single facility
aggregate.loc[aggregate['quantile'].isna(),'quantile'] = 3 # Deafult marker size
to_mark = aggregate.join(context, how="left")
to_mark = geopandas.GeoDataFrame(to_mark, crs=3347)   
to_mark.to_crs(4326, inplace=True)
to_mark.set_geometry("geometry", inplace=True)
markers.extend([folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
    popup=folium.Popup(
        '<b>NPRI ID: </b>'+str(index)+
        '<br><b>Industry:</b> {}'.format(mark["NAICSTitleEn"])+
        '<br><b>{}:</b> '.format(select_substances)+str(mark["SumInTonnes"])+
        "<br><b>Median Residential Instability Score: </b>'"+str(mark["median_instability_2021"]) +
        "<br><b>Median Economic Dependency Score: </b>'"+str(mark["median_dependency_2021"]) +
        "<br><b>Median Ethnocultural Composition Score: </b>'"+str(mark["median_composition_2021"]) +
        "<br><b>Median Situational Vulnerability Score: </b>'"+str(mark["median_vulnerability_2021"])
    ),
    radius=(mark["quantile"] * 5) + 3, fill_color="#FFA500", weight=.5, fill_opacity=0.75
    ) for index, mark in to_mark.iterrows() if mark.geometry is not None
])
## Bar chart
col2b.markdown("#### Totals over time")
col2b.bar_chart(records.loc[(records["Substance"]==select_substances) & records["NpriID"].isin(list(aggregate.index))][["ReportYear", "SumInTonnes"]].sort_values(by="SumInTonnes"), x = "ReportYear", y="SumInTonnes", color="#FFA500")

# Make larger markers appear in the back so as to not obscure small markers
markers.sort(key=lambda x: x.options["radius"], reverse=True)
for marker in markers:
    fg.add_child(marker)

with col1:
    st_folium(
        m,
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )
    #st.warning('There are '+str(nodata)+' facilities without records on '+selector+' and an additional '+str(unmappable)+' that cannot be mapped', icon="⚠️")

# CIMD
col2a.markdown("#### 2021 Canadian Index of Multiple Deprivation")
for metric in cimd.keys():
    #col2a.metric("Median of "+cimd[metric][0], 
    #        round(context.loc[context.index.isin(list(aggregate.index))][[metric]].median(),2),
    #        help = cimd[metric][0] + " refers to " + cimd[metric][1] + "as measured across Census Dissemination Areas within 5km of #these facilities."
    #        )
    col2a.metric("Max of "+cimd[metric][0], 
            round(context.loc[context.index.isin(list(aggregate.index))][[metric]].max(),2),
            help = cimd[metric][0] + " refers to " + cimd[metric][1] + "as measured across Census Dissemination Areas within 5km of these facilities. See here: https://www150.statcan.gc.ca/n1/pub/45-20-0001/452000012023002-eng.htm"
            )
