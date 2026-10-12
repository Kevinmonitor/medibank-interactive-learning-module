import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import (
    load_csv
)

data = pd.DataFrame({
    "Product": ["A", "B", "C"],
    "Sales": [120, 180, 150]
})

sample_data = load_csv("sample_module_user_list.csv")

st.bar_chart(sample_data, x="ok m0q1", y="ok m0q2")