import random

# File to output
path = 'sample_module_user_list.csv'
questions = [6,5,6,4,5,6,4]
# Number of rows
rows = 50

# create an empty dataframe with certain columns: account ID (randomised beyond 12345678), module accessed (homesick / hospital / sick / medication / health provider / comprehensive / claim), questions answered correctly ( pays_all, gp_rate, glasses, claim_now, rx_free, psych_hosp, cosmetic, ivf, counseling, ambulance )