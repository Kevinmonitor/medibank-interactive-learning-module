import random

# File to output
path = 'sample_module_user_list.csv'
# Modules
# https://regexr.com/ (?<=id=")[^ ]+(?=")
# file:///C:/Users/jorda/source/python/uni/medibank-interactive-learning-module/Tala/pages/1_Question.py
modules = ["homesick","hospital","sick","medication","find_provider","comprehensive_oshc","make_claim","just_learning"]
# Questions
# https://regexr.com/ (?<="key": ")[^ ]+(?=")
# file:///C:/Users/jorda/source/python/uni/medibank-interactive-learning-module/Tala/pages/Test_Knowledge.py
questions = ["pays_all","gp_rate","glasses","claim_now","rx_free","psych_hosp","cosmetic","ivf","counselling","ambulance"]
# Number of rows
rows = 0

map = {"pays_all":"comprehensive_oshc",
       "gp_rate":"make_claim",
       "glasses":"comprehensive_oshc",
       "claim_now":"make_claim",
       "rx_free":"medication",
       "psych_hosp":"homesick",
       "cosmetic":"medication",
       "ivf":"coverage_guide",
       "counselling":"homesick",
       "ambulance":"sick",
       }

# header - id, modules, answers
o = 'id,'
o += ','.join([f'm_{i}' for i in modules]) + ','
o += ','.join([f'q_{i}' for i in questions]) + '\n'
# for each row
for i in range(0,rows):
    # generate id
    id = str(random.randint(12345679,20000000))
    # generate modules done
    clicked = [random.choice([1,1,0]) for _ in range(0,len(modules))]
    print(clicked)
    # generate correct answers
    correct = [random.choice([1,1,0]) for _ in range(0,len(questions))]
    # bring together
    results = [j for i in [[id],clicked,correct] for j in i]
    print(results)
    #post!
    o += ','.join([str(i) for i in results]) + '\n'

# save!
open(path,'w').write(o.strip())