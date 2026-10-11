import html
import numpy
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from test import table # type: ignore
st.html('<style>' \
'table, td {' \
'border: solid thin black;' \
'}' \
'</style>')
# you have to run it in the dashboard folder

data = pd.read_csv('test.csv')
data.drop(columns=['Account ID'],inplace=True)
table(data)
data2 = data.iloc[:,0:3].transpose()
#https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.eq.html#pandas.DataFrame.eq 
for i in range(1,6):
    data2[f'={i}'] = data2.eq(i).sum(axis=1)
table(data2)
data3 = data.iloc[:,-4:].transpose()
for i in range(0,2):
    data3[f'={i}'] = data3.eq(i).sum(axis=1)

# https://stackoverflow.com/questions/11285613/selecting-multiple-columns-in-a-pandas-dataframe
with st.container(horizontal=True):
    st.plotly_chart(px.bar(data2.iloc[:,-5:],barmode='group', color_discrete_map={'=1':'#F00','=2':'#F88','=3':'#BBB','=4':'#88F','=5':'#00F'}))
    st.plotly_chart(px.bar(data3.iloc[:,-2:],barmode='group', color_discrete_map={'=1':'#F00','=0':'#00F'}))
st.plotly_chart(px.pie(data, title='Respondants worried about: Visiting a doctor', names='VISITING A DOCTOR', color='VISITING A DOCTOR', color_discrete_map={0:'navy',1:'red'}))

