import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

# sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# from utils import (
#     load_csv
# )

data = pd.DataFrame({
    "Product": ["A", "B", "C"],
    "Sales": [120, 180, 150]
})

sample_data = pd.read_csv("../../jordan/dashboard/test2.csv")

# module usage rate

# myth v.s. fact quiz answers

# create a dataframe measuring the number of correct answers for each question

questions = ["question0", "question1", "question2", "question3", "question4", "question5", "question6", "question7", "question8", "question9"]
question_answer_counts_df = pd.DataFrame(columns=["Question", "Correct Answers"])

for i in questions:
    # create row
    new_row = pd.DataFrame({"Question": [i], "Correct Answers": [(sample_data[i] >= 1).sum()]})
    question_answer_counts_df = pd.concat([question_answer_counts_df, new_row], ignore_index=True)

st.bar_chart(data=question_answer_counts_df, x='Question', y='Correct Answers', x_label='Question', y_label='Correct Answerers', color=None, horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

st.title("Overall Quiz Performances", anchor=None, help=None, width="stretch", text_alignment="left")
st.markdown("Generally, most students answered all questions equally correctly. This shows us that the module is working well in communicating basic OSHC knowledge.", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

# module completion rate

# key word frequency