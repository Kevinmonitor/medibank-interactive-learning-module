import pandas as pd
# open a CSV file
#https://stackoverflow.com/questions/61171223/how-can-i-read-in-row-names-as-they-were-originally-using-pandas-read-csv
def get_data(file: str):
    return pd.read_csv(file, index_col=0)

# save a CSV file
def save_data(file: str, dataFrame: pd.DataFrame):
    dataFrame.to_csv(file)
    print(f'Saved data to {file}!')

# return a cell value
# https://stackoverflow.com/questions/16729574/how-can-i-get-a-value-from-a-cell-of-a-dataframe
def get_cell(dataFrame: pd.DataFrame,id:int,field:str):
    return dataFrame.loc[id][field]

# set a cell value
def set_cell(dataFrame: pd.DataFrame,id:int,field:str,value,force:bool=False):
    if not field in dataFrame.columns.tolist():
        if not force:
            raise KeyError(field)
        else:
            print(f'Created field {field}!')
    dataFrame.loc[id,field] = value

# add a blank row, force to add even though it exists (will wipe row!)
# https://stackoverflow.com/questions/10715965/create-a-pandas-dataframe-by-appending-one-row-at-a-time
def add_row(dataFrame: pd.DataFrame, id:int, force: bool = False):
    if id in dataFrame.index:
        if (not force): raise ValueError('Index exists and not forced: ' + str(id)) # the key exists!
        else: print(f"Overwriting {id}!")
    dataFrame.loc[id] = [0 for _ in dataFrame.columns]

# get a row (as Series)
def get_row(dataFrame: pd.DataFrame, id:int):
    return dataFrame.loc[id]

# set many certain cell values in a row according to a dictionary or list
def set_many_cells(dataFrame: pd.DataFrame, id:int, values: dict | list):
    if isinstance(values, dict): # if values is dictionary
        for i,j in values.items(): # check if keys exist
            if not i in dataFrame.columns.to_list(): raise KeyError(i) # the key does not exist!
        for i,j in values.items(): # populate values
            set_cell(dataFrame, id, i, j)
    else: # if values is list
        # check if values is <= table width
        if len(values) > len(dataFrame.columns): raise ValueError('Values list is too long')
        for i in range(0,len(values)): # populate values
            set_cell(dataFrame, id, dataFrame.columns[i],values[i])



# open, set cell value, close
def get_set_save(file: str, id: int, field: str, value):
    data = get_data(file)
    set_cell(data,id,field,value)
    save_data(file,data)

# open, add row, [add values,] close
def get_add_save(file: str, id: int, values: dict | list = {}, force : bool = False):
    data = get_data(file)
    add_row(data,id,force)
    set_many_cells(data,id,values)
    save_data(file,data)