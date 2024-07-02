import streamlit as st
from npri import npri
import pandas # installed from npri
import folium # installed from npri
from streamlit_folium import st_folium
import geopandas
import altair

st.set_page_config(layout="wide", page_title="Overview")
st.markdown("# Overview")

if st.button("Places"):
    st.switch_page("pages/2_Places.py")

times = [year for year in range(1993,2023)]

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

cimd = {"median_instability_2021": "Residential Instability Scores across Dissemination Areas within 5km of these Facilities", "median_dependency_2021": "Economic Dependency Scores across Dissemination Areas within 5km of these Facilities", "median_composition_2021": "Ethnocultural Composition Scores across Dissemination Areas within 5km of these Facilities", "median_vulnerability_2021": "Situational Vulnerability Scores across Dissemination Areas within 5km of these Facilities"}    
def get_context(list_of_ids):
    try:
        data, url, report_url = npri.get_npri_data(view=None, endpoint="sql", 
                                           sql = 'select "NpriID", "NAICSTitleEn", "median_instability_2021", "median_dependency_2021", "median_composition_2021", "median_vulnerability_2021", geom from npri_exporter_table where "NpriID" in ({});'.format(list_of_ids))
        return data
    except:
        print("Couldn't get data")

# PAGE LAYOUT
col1, col2 = st.columns([0.4, 0.6])

col2.markdown("## Select up to 3 pollutants")
select_substances  = col2.multiselect(
    "Select pollutant(s)",
    list(substances["Substance"].unique()),
    list(substances["Substance"].unique())[0],
    max_selections = 3
)

col2.markdown("## Select a timeframe")
select_times = col2.slider(
    "Which timeframe do you want to focus on?",
    1993, 2023, (2013, 2023),
    step = 1)

# Get data
records = get_records(select_substances, select_times)

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

# Aggregate by industry
ind = records.join(context[["NAICSTitleEn"]])
ind = ind.groupby(by=["NAICSTitleEn", "Substance"])[["SumInTonnes"]].sum().reset_index()
ind.set_index("NAICSTitleEn", inplace=True)

# Prep map
m = folium.Map(tiles="cartodb positron", zoom_start = 3, location=(65,-110))
fg = folium.FeatureGroup(name="Facilities")

all_fac = []
markers = []

for i,s in enumerate(select_substances):
    if i == 0:
        sub0 = aggregate.loc[aggregate["Substance"]==s]
        sub0ind = ind.loc[ind["Substance"]==s]
        col2.markdown("## Top ten facilities: {}, ".format(s) + str(select_times[0]) + "-" + str(select_times[1]))
        toptentotal = sub0.sort_values(by="SumInTonnes", ascending=False).head(10)
        #col2.dataframe(toptentotal) # Add more info here or do altair chart
        toptentotal.reset_index(inplace=True)
        toptentotal["NpriID"] = toptentotal["NpriID"].astype(str)
        col2.altair_chart(
            altair.Chart(toptentotal).mark_bar().encode(
                x=altair.X("SumInTonnes"),
                y=altair.Y("NpriID" ).sort('-x')
            )
        )
        col2.markdown("## Top ten industries: {}, ".format(s) + str(select_times[0]) + "-" + str(select_times[1]))
        toptenind = sub0ind.sort_values(by="SumInTonnes", ascending=False).head(10)
        #col2.dataframe(toptenind) # Add more info here or do altair chart
        toptenind.reset_index(inplace=True)
        col2.altair_chart(
            altair.Chart(toptenind).mark_bar().encode(
                x=altair.X("SumInTonnes"),
                y=altair.Y("NAICSTitleEn" ).sort('-x')
            )
        )
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

with col1:
    st_folium(
        m,
        feature_group_to_add=fg,
        returned_objects=[],
        use_container_width=True
    )
    #st.warning('There are '+str(nodata)+' facilities without records on '+selector+' and an additional '+str(unmappable)+' that cannot be mapped', icon="⚠️")

# CIMD
x, y = col1.columns(2)
from functools import reduce
all_fac = reduce(lambda x, y: pandas.merge(x, y, on = 'NpriID'), all_fac)
all_fac = list(all_fac.index.unique())
st.write(cimd)
for metric in cimd.keys():
    st.write(metric)
    x.metric("Median of "+cimd[metric], round(context.loc[context.index.isin(all_fac)][[metric]].median(),2)) # Need to explain median median.
    x.metric("Max of "+cimd[metric], round(context.loc[context.index.isin(all_fac)][[metric]].max(),2)) # Need to explain max median.
    y.info('TBD: Explain median of median and compare to national residential instability', icon="ℹ️")
