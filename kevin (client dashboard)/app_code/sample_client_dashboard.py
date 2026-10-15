import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

from utils import (
    apply_plotly_theme,
    randomise_module_completion
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
        st.markdown("This data shows how students performed on each question of the Myth v.s Fact Knowledge Quiz.\n\nHaving information on questions or topics that students struggled with (or succeeded on) the most helps us rework the cards and information being communicated.", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

        # st.bar_chart(data=question_answer_counts_df, x='Question', y='Correct Answers', x_label='Question', y_label='Correct Answerers', color='blue', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

        fig = px.bar(question_answer_counts_df, x='Question', y='Correct Answers', color="Question")
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")
        # fig.show()

with col2:

    with st.container(border=True):

        st.subheader("Card Access")
        st.markdown("This data shows how many students accessed each card within the learning module.\n\nNot all students actually read every card - if a card is particularly under-utilised, it may suggest a lack of interest in that topic.", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

        fig = px.bar(module_usage_counts_df, x='Module', y='Students Accessed', color="Module")
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")

        # st.bar_chart(data=module_usage_counts_df, x='Module', y='Students Accessed', x_label='Module', y_label='Number of Users', color='violet', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

# module completion rate

# completion here refers to: all cards have been accessed at least once
module_completion_df = pd.DataFrame(columns=["Account ID", "Number of Cards Completed", "Module Complete"])

# List of target column names
module_cols = [f"module{i}" for i in range(8)]

# RANDOMISATION

# randomised sample

randomised_module_completion_sample = randomise_module_completion(sample_data, 35)

sample_data.update(randomised_module_completion_sample)

# END OF RANDOMISATION

# Sum the values along axis 1 (rows)
sample_data["Total Cards Completed"] = sample_data[module_cols].sum(axis=1)

for index, row in sample_data.iterrows():
    # create row
    # there are 8 modules
    completion_check = False
    if row['Total Cards Completed'] >= 8:
        completion_check = True
    new_row = pd.DataFrame({"Account ID": [row['id']], "Number of Cards Completed": [row['Total Cards Completed']], "Module Complete": [completion_check]})
    module_completion_df = pd.concat([module_completion_df, new_row], ignore_index=True)

col3, col4 = st.columns(2, gap="small")

with col3:

    with st.container(border=True):

        st.subheader("Module Completion Rate")
        st.markdown("This data shows how many students (out of our total userbase) finished the module.\n\nThis refers to viewing every card in the module.", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

        # st.bar_chart(data=question_answer_counts_df, x='Question', y='Correct Answers', x_label='Question', y_label='Correct Answerers', color='blue', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

        labels = {True: 'Completed', False: 'Incomplete'}
        module_completion_df['Module Complete'] = module_completion_df['Module Complete'].map(labels)

        fig = px.pie(module_completion_df, names='Module Complete', hole = 0.5,

                    color_discrete_sequence=["cornflowerblue", "coral"]

                    )
        fig.update_layout(font=dict(size=25), 
                          legend=dict
                            (
                            font=dict(size= 20)
                            )
                        )
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")

# key word frequency