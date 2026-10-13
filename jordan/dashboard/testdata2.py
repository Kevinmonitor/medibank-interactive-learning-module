import random

# File to output
path = 'test2.csv'
# Number of modules
modules = 8
# Number of questions
questions = 10
# Number of rows
rows = 50
# header - id, modules, answers
o = 'id,'

# add fields as needed

o += ','.join([f'module{i}' for i in range(0,modules)]) + ','
o += ','.join([f'question{i}' for i in range(0,questions)]) + '\n'
# for each row
for i in range(0,rows):
    # generate id
    id = str(random.randint(12345679,20000000))

    # add fields as needed

    # generate modules done
    clicked = [random.choice([1,1,0]) for _ in range(0,modules)]
    print(clicked)
    # generate correct answers
    correct = [random.choice([1,1,0]) for _ in range(0,questions)]
    # bring together
    results = [j for i in [[id],clicked,correct] for j in i]
    print(results)
    #post!
    o += ','.join([str(i) for i in results]) + '\n'

# save!
open(path,'w').write(o.strip())
