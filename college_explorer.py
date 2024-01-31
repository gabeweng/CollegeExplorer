import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import pydeck as pdk

st.set_page_config(layout="wide")
ver = 'v1.2'
def csv_to_dict(file_path):
    result_dict = {"cip.title":"Major","cip.earnings.highest.3_yr.overall_median_earnings":"MedianEarning",
                   "cip.counts.ipeds_awards1":"MajorPopulation","admission_rate.overall":"AdmitRate",
                   "net_price.income.110001-plus":"NetPrice", "10_yrs_after_entry.mean_earnings":"10YrEarning"}
    try:
        df = pd.read_csv(file_path)
        result_dict = dict(zip(df["code"], df["display"]))
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    
    return result_dict
    
def rename_and_keep_columns(dataframe, column_mapping,all_columns=False):
    
    dataframe.rename(columns=column_mapping, inplace=True)
    
    if not all_columns:
        include_cols = ['name','size','city','state','zip','region_id','locale','lon','lat']
        columns_to_keep = list(column_mapping.values()) + include_cols
        # dataframe = dataframe[columns_to_keep]
        dataframe.drop(columns=dataframe.columns.difference(columns_to_keep), inplace=True)
    
    return dataframe

@st.cache_data
def load_data():
    try:
        print("Load colleges from local")
        df = pd.read_csv("reportcard.csv",index_col=0)
    except FileNotFoundError:
        print("Load colleges from github")
        df = pd.read_csv("https://raw.githubusercontent.com/LastMileNow/opendata/main/reportcard.csv",index_col=0)
    try:
        print("Load majors from local")
        df_majors = pd.read_csv("reportcard_major.csv",index_col=0)
    except FileNotFoundError:
        print("Load majors from github")
        df_majors = pd.read_csv("https://raw.githubusercontent.com/LastMileNow/opendata/main/reportcard_major.csv",index_col=0)

    data_dict = csv_to_dict('https://raw.githubusercontent.com/LastMileNow/opendata/main/show_col.csv')
    majors = list(df_majors['cip.title'].unique())
    titles = list(df_majors['cip.credential.title'].unique())
    
    return df,df_majors,titles,majors,data_dict

df_college,df_majors,titles,majors,data_dict = load_data()

numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
st.title(f"College Explorer {ver}")
major = st.multiselect('Majors', majors, default=['Computer Science.','Computer and Information Sciences, General.',
    'Finance and Financial Management Services.','Business Administration, Management and Operations.','Economics.'])

st.sidebar.write(f"{ver} by [Darren](https://github.com/darrentweng) and [Gabe](https://github.com/gabeweng)")
all_columns = st.sidebar.checkbox('All Columns')
title = st.sidebar.selectbox('Degree', titles, index=0)

if major == []:
    df = df_college
    default_cols = ['name','size','city','state','zip','region_id','AdmitRate','10YrEarning']
    default_bubble_col = 'size'
    default_earning_col = '10YrEarning'
    cat_idx = 0
else:
    df = df_college.merge(df_majors[(df_majors['cip.title'].isin(major)) & (df_majors['cip.credential.title']==title)], left_on='id', right_on='cip.unit_id')
    default_cols = ['name','AdmitRate','Major','MedianEarning','MajorPopulation']
    default_bubble_col = 'MajorPopulation'
    default_earning_col = 'MedianEarning'
    cat_idx = 2

rename_and_keep_columns(df, data_dict,all_columns)

cols_all = list(df.columns.values)
cols = list(df.select_dtypes(include=numerics).columns.values)
cols_nan = list(df.select_dtypes(exclude=numerics).columns.values)

option = st.sidebar.radio('College Search', ('Table + Scatter', 'Scatter Only','Table + Map', 'Map Only','Pair-Plot'))

if option == 'Pair-Plot':
    cat = st.sidebar.selectbox('Category', ['region_id','locale','Major'], index=cat_idx)
    columns = st.multiselect('Columns', cols, default=['AdmitRate','NetPrice','attendance.academic_year'])

    all_col = columns.copy()# append a category column. this is not in the columns list, so we need to add it
    all_col.append(cat)     # to a copy of list so multiselect won't complain about the item not in list
    fig = sns.pairplot(df[all_col], hue=cat)
    st.pyplot(fig)

else:
    # Filters: 1 & 2 are ranges, 3 is a partial string search.

    fil1 = st.sidebar.selectbox('Filter 1', cols, index=cols.index("AdmitRate"))
    txt1 = st.sidebar.text_input('Range 1','0.0-1.0')

    fil2 = st.sidebar.selectbox('Filter 2', cols, index=cols.index("size"))
    txt2 = st.sidebar.text_input('Range 2','1000-200000')

    fil3 = st.sidebar.selectbox('Filter 3', cols_nan, index=cols_nan.index("name"))
    txt3 = st.sidebar.text_input('Partial Name','')

    cond = df['name'].notna()
    if txt1 != '':
        try :
            val1 = [float(x) for x in txt1.split('-')]
        except:
            st.sidebar.write("Error parsing "+txt1)
            val1 = [0,100000]
        cond = (df[fil1]>=val1[0]) & (df[fil1]<=val1[1])

    if txt2 != '':
        try :
            val2 = [float(x) for x in txt2.split('-')]
        except:
            st.sidebar.write("Error parsing "+txt2)
            val2 = [0,100000]
        cond = cond & (df[fil2]>=val2[0]) & (df[fil2]<=val2[1])

    if txt3 != '':
        cond = cond & (df[fil3].str.contains(txt3,case=False))

    df = df[cond]
    
    if 'Scatter' in option:
        xcol = st.sidebar.selectbox('X-Axis', cols, index=cols.index("AdmitRate"))
        ycol = st.sidebar.selectbox('Y-Axis', cols, index=cols.index(default_earning_col))
        cat = st.sidebar.selectbox('Category', ['region_id','locale','Major'], index=cat_idx)
        bubble_col = st.sidebar.selectbox('Bubble Size', cols, index=cols.index(default_bubble_col))
    else:
        bubble_col = st.sidebar.selectbox('Bubble Size', cols, index=cols.index(default_bubble_col))
        defaultval='1'
        if 'Pct' in bubble_col:
            defaultval='100000'
        bubble_factor = st.sidebar.text_input(bubble_col+" * factor",defaultval)
        try :
            bubble_factor = float(bubble_factor)
        except:
            st.sidebar.write("Error parsing "+bubble_factor)
            bubble_factor = 1

    if 'Table' in option:
        columns = st.multiselect('Columns', cols_all,default=default_cols)
        
        tbl = df[columns]
        st.header("Selected Colleges (#:"+str(tbl.shape[0])+")")
        st.dataframe(tbl,use_container_width=True) # , width=1200

    if 'Scatter' in option:
        plot = df[["name",xcol,ycol,bubble_col,cat]].dropna()
        ## https://plotly.com/python/linear-fits/
        fig = px.scatter(plot, x=xcol, y=ycol, hover_data=['name'],size=bubble_col,color=cat,height=600, trendline="ols") 
        st.plotly_chart(fig, use_container_width=True)
    else:
        mapdf = df[['name','lon','lat',bubble_col]].dropna(thresh=4)

        # https://docs.streamlit.io/en/stable/api.html?highlight=pydeck_chart
        st.pydeck_chart( 
            pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9',
                layers=[
                    # rename the target column to 'size' for the scatterplot layer 
                    pdk.Layer("ScatterplotLayer", data=mapdf.rename(columns = {bubble_col:'size'}), get_position='[lon, lat]',
                    get_fill_color="[200, 30, 0, 160]",  get_radius='size'+"*"+str(bubble_factor), 
                    pickable=True, opacity=0.8, stroked=False, filled=True, wireframe=True,
                    )],
                initial_view_state=pdk.ViewState(longitude=-95.324441, latitude=39.54636, zoom=4, min_zoom=2, max_zoom=15, height=800),
                tooltip={"html": "<b>{name}</b>: {size}"}
            ), 
            use_container_width=True)
