import streamlit as st
from ECHO_modules import get_echo_data

try:
    data = get_echo_data('select * from "ECHO_EXPORTER" limit 5')
    st.dataframe(data)
except:
    st.write("There's an error here!")