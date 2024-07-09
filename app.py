import streamlit as st

st.set_page_config(layout="wide")

pg = st.navigation([st.Page("pages/Background.py", title="Home"), st.Page("pages/Overview.py", title="Overview"), st.Page("pages/Places.py", title="Places")], position="hidden")


top = st.container()
c1,c2,c3 = top.columns(3)
#top.markdown("Click here to focus on releases in a specific area: ")
c1.page_link("pages/Background.py", label="Home", icon="🏠")
c2.page_link("pages/Overview.py", label="Overview", icon="🌎")
c3.page_link("pages/Places.py", label="Places", icon="🗺️")

pg.run()


