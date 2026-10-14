import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

from utils import (
    apply_plotly_theme
)

# sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# from utils import (
#     load_csv
# )

# style

data = pd.DataFrame({
    "Product": ["A", "B", "C"],
    "Sales": [120, 180, 150]
})

sample_data = pd.read_csv("../../jordan/dashboard/test2.csv")

# module usage rate

# myth v.s. fact quiz answers

# create a dataframe measuring the number of correct answers for each question

st.title('Module Highlights')

questions = ["question0", "question1", "question2", "question3", "question4", "question5", "question6", "question7", "question8", "question9"]
question_key = [""]
question_answer_counts_df = pd.DataFrame(columns=["Question", "Correct Answers"])

modules = ["module0", "module1", "module2", "module3", "module4", "module5", "module6", "module7"]
module_usage_counts_df = pd.DataFrame(columns=["Module", "Students Accessed"])

for i in questions:
    # create row
    new_row = pd.DataFrame({"Question": [i], "Correct Answers": [(sample_data[i] >= 1).sum()]})
    question_answer_counts_df = pd.concat([question_answer_counts_df, new_row], ignore_index=True)

for i in modules:
    # create row
    new_row = pd.DataFrame({"Module": [i], "Students Accessed": [(sample_data[i] >= 1).sum()]})
    module_usage_counts_df = pd.concat([module_usage_counts_df, new_row], ignore_index=True)

col1, col2 = st.columns(2, gap="small")

st.set_page_config(page_title="Module Highlights", layout="wide")

with col1:

    with st.container(border=True):

        st.subheader("Overall Quiz Performances")

        # st.bar_chart(data=question_answer_counts_df, x='Question', y='Correct Answers', x_label='Question', y_label='Correct Answerers', color='blue', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

        fig = px.bar(question_answer_counts_df, x='Question', y='Correct Answers', color="Question")
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")
        # fig.show()

        # st.markdown("Generally, most students answered all questions equally correctly. This shows us that the module is working well in communicating basic OSHC knowledge.", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

with col2:

    with st.container(border=True):

        st.subheader("Module Usage")

        fig = px.bar(module_usage_counts_df, x='Module', y='Students Accessed', color="Module")
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")

        # st.bar_chart(data=module_usage_counts_df, x='Module', y='Students Accessed', x_label='Module', y_label='Number of Users', color='violet', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

# module completion rate

# key word frequency