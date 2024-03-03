import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    try:
        print("Load colleges from local")
        showDF= pd.read_csv("show_col.csv",index_col=0)
    except FileNotFoundError:
        print("Load colleges from github")
        showDF = pd.read_csv('https://raw.githubusercontent.com/LastMileNow/opendata/main/show_col.csv',index_col=0)
    try:
        print("Load majors from local")
        dictDF= pd.read_csv("dict.csv",index_col=0)
    except FileNotFoundError:
        print("Load majors from github")
        dictDF = pd.read_csv("https://raw.githubusercontent.com/LastMileNow/opendata/main/dict.csv",index_col=0)

    return showDF, dictDF

showDF, dictDF = load_data()

st.dataframe(showDF,use_container_width=True) 
st.dataframe(dictDF,use_container_width=True) 