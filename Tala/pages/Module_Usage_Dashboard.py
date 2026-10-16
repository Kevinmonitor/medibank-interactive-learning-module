# final version: Module_Usage_Dashboard.py

# """Module usage analytics dashboard (administrators only).
# shows usage of cards and question answers using sample_module_user_list.csv.
# """

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

from utils import (
    apply_plotly_theme,
    randomise_module_completion,
    randomise_quiz_completion
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

sample_data = pd.read_csv("data/sample_module_user_list.csv")


####

#### ----------------------------------------------------------

#### CREATE DATAFRAMES

#### ----------------------------------------------------------

####

st.title('Module Highlights')

questions = ["question0", "question1", "question2", "question3", "question4", "question5", "question6", "question7", "question8", "question9"]

questions_true = ["q_pays_all","q_gp_rate","q_glasses","q_claim_now","q_rx_free","q_psych_hosp","q_cosmetic","q_ivf","q_counselling","q_ambulance"]
questions_true_key = ["OSHC Pays All (Myth)", "100% MBS Fee (Myth)", "New Glasses (Myth)", "Claim Instantly (Myth)", "Free Prescriptions (Myth)", "Psychiatric Services (Fact)", "Cosmetic Treatments (Myth)", "Reproductive Services (Comprehensive-only)", "Counseling (Fact)", "Comprehensive OSHC Ambulance (Fact)"]

question_answer_counts_df = pd.DataFrame(columns=["Question", "Correct Answers"])

modules = ["module0", "module1", "module2", "module3", "module4", "module5", "module6", "module7"]

modules_true = ["m_homesick","m_hospital","m_sick","m_medication","m_find_provider","m_comprehensive_oshc","m_make_claim","m_just_learning"] # we have actual names
modules_true_key = ["Homesickness", "Hospital Help", "Sickness Help", "Medication Help", "Provider Search", "Comprehensive OSHC", "Making Claims", "General Learning"]

module_usage_counts_df = pd.DataFrame(columns=["Module", "Students Accessed"])



for i in questions_true:
    # create row
    new_row = pd.DataFrame({"Question": [i], "Correct Answers": [(sample_data[i] >= 1).sum()]})
    question_answer_counts_df = pd.concat([question_answer_counts_df, new_row], ignore_index=True)

for i in modules_true:
    # create row
    new_row = pd.DataFrame({"Module": [i], "Students Accessed": [(sample_data[i] >= 1).sum()]})
    module_usage_counts_df = pd.concat([module_usage_counts_df, new_row], ignore_index=True)


# module completion rate

# completion here refers to: all cards have been accessed at least once
module_completion_df = pd.DataFrame(columns=["Account ID", "Number of Cards Completed", "Module Complete", "Number of Correct Answers", "Quiz Complete"])


# RANDOMISATION

# randomised sample

randomised_module_completion_sample = randomise_module_completion(sample_data, 145)
sample_data.update(randomised_module_completion_sample)

randomised_quiz_completion_sample = randomise_quiz_completion(sample_data, 110)
sample_data.update(randomised_quiz_completion_sample)

# END OF RANDOMISATION

# Sum the values along axis 1 (rows)
sample_data["Total Cards Completed"] = sample_data[modules_true].sum(axis=1)
sample_data["Total Questions Completed"] = sample_data[questions_true].sum(axis=1)

for index, row in sample_data.iterrows():
    # create row
    # there are 8 modules
    completion_check = False
    quiz_check = False
    if row['Total Cards Completed'] >= 8:
        completion_check = True
    if row['Total Questions Completed'] >= 10:
        quiz_check = True
    new_row = pd.DataFrame(
        {"Account ID": [row['id']], 
         "Number of Cards Completed": [row['Total Cards Completed']], 
         "Module Complete": [completion_check],
         "Number of Correct Answers": [row['Total Questions Completed']],
         "Quiz Complete": [quiz_check]
        })
    module_completion_df = pd.concat([module_completion_df, new_row], ignore_index=True)


####


#### ----------------------------------------------------------

#### OVERALL USAGE

#### ----------------------------------------------------------


####

labels = {True: 'Completed', False: 'Incomplete'}
labels_quiz = {True: 'Perfect', False: 'Imperfect'}
module_completion_df['Module Complete'] = module_completion_df['Module Complete'].map(labels)
module_completion_df['Quiz Complete'] = module_completion_df['Quiz Complete'].map(labels_quiz)

total = sample_data.shape[0]
completion_rate = module_completion_df['Module Complete'].eq('Completed').mean()
quiz_perfect_rate = module_completion_df['Quiz Complete'].eq('Perfect').mean()

# full completion: all cards accessed AND all questions completed

full_completion_rate = ( module_completion_df.loc[(module_completion_df['Module Complete'] == "Completed") & (module_completion_df['Quiz Complete'] == "Perfect")].shape[0] / module_completion_df.shape[0] )

# Inject CSS to flip the order of label and value in metrics
# "div.st-emotion-cache-ocy457.eozy2n81" is hardcoded... oops. to-do: find a more elegant solution

st.markdown(
    """
    <style>

    [data-testid="stMetricValue"] p {
        font-size: 4rem;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 1.5rem;
        overflow-wrap: break-word;
        white-space: normal;
        overflow: visible;
        text-overflow: clip;    
    }

    div.st-emotion-cache-ocy457.eozy2n81 {
        display: flex;
        flex-direction: column-reverse;
        font-weight: bold;
        height: auto;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("students have viewed the module.", total, border=True, help="This refers to logging into the module at least once.")
m2.metric("of students have accessed all cards.", completion_rate, format="percent", border=True)
m3.metric("of students have answered all questions correctly in the Myth v.s Fact knowledge quiz.", quiz_perfect_rate, format="percent", border=True)
m4.metric("**of students have fully completed the module.**", full_completion_rate, format="percent", border=True, help="This refers to getting all questions correct and accessing all cards in the module.")


####


#### ----------------------------------------------------------

#### QUIZ AND MODULE USAGE

#### ----------------------------------------------------------


####


col1, col2 = st.columns(2, gap="small")

st.set_page_config(page_title="Module Highlights", layout="wide")

# map modules to names

question_dict = dict(zip(questions_true, questions_true_key))
module_dict = dict(zip(modules_true, modules_true_key))

question_answer_counts_df['Question'] = question_answer_counts_df['Question'].map(question_dict)
module_usage_counts_df['Module'] = module_usage_counts_df['Module'].map(module_dict)






with col1:

    with st.container(border=True):

        st.subheader("Overall Quiz Performances")
        st.markdown("This data shows how students performed on each question of the Myth v.s Fact Knowledge Quiz.\n\nHaving information on questions or topics that students struggled with (or succeeded on) the most helps us *rework the cards and information being communicated.*", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

        # st.bar_chart(data=question_answer_counts_df, x='Question', y='Correct Answers', x_label='Question', y_label='Correct Answerers', color='blue', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

        fig = px.bar(question_answer_counts_df, x='Question', y='Correct Answers', color="Question")
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")
        # fig.show()

with col2:

    with st.container(border=True):

        st.subheader("Card Access")
        st.markdown("This data shows how many students accessed each card within the learning module.\n\nNot all students actually read every card - if a card is particularly under-utilised, *it may suggest a lack of interest in that topic.*", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

        fig = px.bar(module_usage_counts_df, x='Module', y='Students Accessed', color="Module")
        st.plotly_chart(apply_plotly_theme(fig), width="stretch")

        # st.bar_chart(data=module_usage_counts_df, x='Module', y='Students Accessed', x_label='Module', y_label='Number of Users', color='violet', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

# col3, col4 = st.columns(2, gap="small")

# with col3:

#     with st.container(border=True):

#         st.subheader("Module Completion Rate")
#         st.markdown("This data shows how many students (out of our total userbase) finished the module.\n\nThis refers to viewing every card in the module.", unsafe_allow_html=False, help=None, width="auto", text_alignment="left")

#         # st.bar_chart(data=question_answer_counts_df, x='Question', y='Correct Answers', x_label='Question', y_label='Correct Answerers', color='blue', horizontal=False, sort=True, stack=None, width="stretch", height="content", use_container_width=None)

#         labels = {True: 'Completed', False: 'Incomplete'}
#         module_completion_df['Module Complete'] = module_completion_df['Module Complete'].map(labels)

#         fig = px.pie(module_completion_df, names='Module Complete', hole = 0.5,

#                     color_discrete_sequence=["cornflowerblue", "coral"]

#                     )
#         fig.update_layout(font=dict(size=25), 
#                           legend=dict
#                             (
#                             font=dict(size= 20)
#                             )
#                         )
#         st.plotly_chart(apply_plotly_theme(fig), width="stretch")

# with col4:

#     with st.container(border=True):

#         st.html("<p><span style='text-decoration: line-through double red;'>{{len(sample_data.index)}}</span></p>", width="stretch", unsafe_allow_javascript=False)

#         pass

# key word frequency