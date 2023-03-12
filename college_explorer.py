import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import pydeck as pdk

st.set_page_config(layout="wide")
ver = 'v1.0'

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

    majors = list(df_majors['cip.title'].unique())
    titles = list(df_majors['cip.credential.title'].unique())
    return df,df_majors,titles,majors

df_college,df_majors,titles,majors = load_data()

numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
st.title('College Explorer {ver}')
major = st.multiselect('Majors', majors, default=['Computer Science.','Computer and Information Sciences, General.',
    'Finance and Financial Management Services.','Business Administration, Management and Operations.','Economics.'])

st.sidebar.write(f"{ver} by [Darren](https://github.com/darrentweng) and [Gabe](https://github.com/gabeweng)")
title = st.sidebar.selectbox('Degree', titles, index=0)
if major == []:
    df = df_college
    default_cols = ['name','size','city','state','zip','region_id','admission_rate.overall','10_yrs_after_entry.mean_earnings']
    default_bubble_col = 'size'
    default_earning_col = '10_yrs_after_entry.mean_earnings'
    cat_idx = 0
else:
    df = df_college.merge(df_majors[(df_majors['cip.title'].isin(major)) & (df_majors['cip.credential.title']==title)], left_on='id', right_on='cip.unit_id')
    default_cols = ['name','admission_rate.overall','cip.title','cip.earnings.highest.3_yr.overall_median_earnings',
                   'cip.counts.ipeds_awards1']
    default_bubble_col = 'cip.counts.ipeds_awards1'
    # df.rename(columns = {'cip.counts.ipeds_awards1':'major_population'}, inplace = True)
    default_earning_col = 'cip.earnings.highest.3_yr.overall_median_earnings'
    cat_idx = 2

cols_all = list(df.columns.values)
cols = list(df.select_dtypes(include=numerics).columns.values)
cols_nan = list(df.select_dtypes(exclude=numerics).columns.values)

option = st.sidebar.radio('College Search', ('Table + Scatter', 'Scatter Only','Table + Map', 'Map Only','Pair-Plot'))

if option == 'Pair-Plot':
    cat = st.sidebar.selectbox('Category', ['region_id','locale','cip.title'], index=cat_idx)
    columns = st.multiselect('Columns', cols, default=['admission_rate.overall','net_price.income.110001-plus','attendance.academic_year'])

    all_col = columns.copy()# append a category column. this is not in the columns list, so we need to add it
    all_col.append(cat)     # to a copy of list so multiselect won't complain about the item not in list
    fig = sns.pairplot(df[all_col], hue=cat)
    st.pyplot(fig)

else:
    # Filters: 1 & 2 are ranges, 3 is a partial string search.
    fil1 = st.sidebar.selectbox('Filter 1', cols, index=cols.index("admission_rate.overall"))
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
        xcol = st.sidebar.selectbox('X-Axis', cols, index=cols.index("admission_rate.overall"))
        ycol = st.sidebar.selectbox('Y-Axis', cols, index=cols.index(default_earning_col))
        cat = st.sidebar.selectbox('Category', ['region_id','locale','cip.title'], index=cat_idx)
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
