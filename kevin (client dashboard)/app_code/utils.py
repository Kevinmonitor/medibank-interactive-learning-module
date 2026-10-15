import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

# def data_path(filename):
#     """Return the full path to a file in the data/ directory."""
#     return os.path.join(os.path.dirname(__file__), "data", filename)

# def load_csv(filename):
#     """Load a CSV from the data/ directory. Returns None if file doesn't exist."""
#     path = data_path(filename)
#     if os.path.exists(path):
#         return pd.read_csv(path)
#     return None

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#090909", family="Segoe UI, sans-serif"),
    xaxis=dict(gridcolor="rgba(100,100,100,0.2)", zerolinecolor="rgba(100,100,100,0.2)"),
    yaxis=dict(gridcolor="rgba(100,100,100,0.2)", zerolinecolor="rgba(100,100,100,0.2)"),
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)

def apply_plotly_theme(fig):
    """Apply the dashboard theme to any plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig

def randomise_module_completion(data, rowCount):
    # select x random rows from the sample data
    random_sample = data.sample(n=rowCount, random_state=1)
    # set all module columns to true
    random_sample.loc[:, "module0":"module7"] = 1
    return random_sample