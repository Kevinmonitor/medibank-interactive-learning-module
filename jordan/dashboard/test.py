import html
import numpy
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

# you have to run it in the dashboard folder

data1 = pd.read_csv('teststats2.csv')
data2 = pd.read_csv('teststats2.csv')
data2['VALUE2']=data2['VALUE']%2500
data2['VALUE3']=data2['VALUE']%3500
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

# https://docs.streamlit.io/develop/api-reference/layout/st.container
def stat(value:float,ceiling:float,text):
    value = value / ceiling
    print(ceiling)
    with st.container(border=True):
        st.subheader(f'{value*100}%')
        st.text(text)

table(data1)
table(data2)
with st.container(horizontal=True):
    stat(pd.to_numeric(data1.loc[2,'VALUE']),data1['VALUE'].sum(),'VALUE1')
    #https://stackoverflow.com/questions/40804706/sum-all-columns-in-a-pandas-dataframe-where-there-are-non-numeric-values
    stat(pd.to_numeric(data2.iloc[2,3]),pd.to_numeric(data2.iloc[2],errors='coerce').sum(numeric_only=True),f"{data2.iloc[2,0]} is {data2.columns.to_list()[3]}")


with st.container(horizontal=True):

    st.bar_chart(data1,x='METRIC')
    #https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
    st.plotly_chart(px.pie(data1,names='METRIC',values='VALUE'))
with st.container(horizontal=True):
    st.bar_chart(data2,x='METRIC',stack=False)
    st.area_chart(data1,x='METRIC')
with st.container(horizontal=True):
    st.line_chart(data2,x='METRIC')
    columns = data2.columns.tolist()
    count = len(columns)
    #https://community.plotly.com/t/make-double-donut-plots-or-donut-plot-with-subgroups/13755/3
    dat = [
                go.Pie(hole=(i/count), values=data2[columns[i]],labels=data2['METRIC'],domain={
                    'x':[1-((i+1)/count),((i+1)/count)], 'y':[1-((i+1)/count),((i+1)/count)]
                }
                )
                for i in range(0,count)
            ]
    st.plotly_chart(
        go.Figure(
            data=dat
        )
    )
