import json
from typing import Literal
from dataentry import add_row, get_data, get_row, save_data, set_cell

# simplified dataentry api for answering questions and data

Done = Literal[0,1]
data = '../../sample_module_user_list.csv'

def start(user):
    table = get_data(data)
    try:
        row = get_row(table,user)
    except KeyError:
        row = add_row(table,user)
    return table,row

def edit(user,name,value:Done):
    table,row = start(user)
    set_cell(table,user,name,value)
    save_data(data,table)

def done_module(user,name):
    edit(user,'m_'+name,1)

def set_question(user,name,right:Done):
    edit(user,'q_'+name,right)


