import html
import plotly.express as px
import pandas as pd
import streamlit as st
data1 = pd.read_csv('teststats2.csv')
data2 = pd.read_csv('teststats2.csv')
data2['VALUE2']=data2['VALUE']*1.1
data2['VALUE3']=data2['VALUE2']*1.1
#https://stackoverflow.com/questions/16476924/how-can-i-iterate-over-rows-in-a-pandas-dataframe
def table(dataframe: pd.DataFrame):
    markdown = ''
    markdown += '<table><tr>'
    for i in dataframe.columns:
        markdown += f'<th>{i}</th>'
    markdown += '</tr>'
    for n, j in dataframe.iterrows():
        markdown += '<tr>'
        for i in dataframe.columns:
            markdown += f'<td>{j[i]}</td>'
        markdown += '</tr>'
    markdown += '</table>'
    st.html(markdown)

st.html('<style>' \
'table, td {' \
'border: solid thin black;' \
'}' \
'</style>')

table(data1)
table(data2)

st.bar_chart(data1,x='METRIC')
#https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
st.plotly_chart(px.pie(data1,names='METRIC',values='VALUE'))
st.bar_chart(data2,x='METRIC',stack=False)
