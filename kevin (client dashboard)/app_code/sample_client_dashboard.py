import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os


data = pd.DataFrame({
    "Product": ["A", "B", "C"],
    "Sales": [120, 180, 150]
})

def data_path(filename):
    """Return the full path to a file in the data/sample directory."""
    return os.path.join(os.path.dirname(__file__), "../data/sample", filename)


def load_csv(filename):
    """Load a CSV from the data/ directory. Returns None if file doesn't exist."""
    path = data_path(filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

sample_data = load_csv("sample_module_user_list.csv")

st.bar_chart(sample_data, x="ok m0q1", y="ok m0q2")