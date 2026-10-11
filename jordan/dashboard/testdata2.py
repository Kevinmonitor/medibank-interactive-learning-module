import random

# File to output
path = 'test2.csv'
questions = [6,5,6,4,5,6,4]
# Number of rows
rows = 50


length = len(questions)
# header - id, modules, answers
o = 'id,'+ ','.join([f'did m{i}' for i in range(0,length)])+','+','.join([f'ok m{i}q{j}' for i in range(0,length) for j in range(0,questions[i])]) + '\n'
# for each row
for i in range(0,rows):
    # generate id
    id = str(random.randint(11111111,20000000))
    # generate modules done
    clicked = [random.choice([1,1,0]) for _ in range(0,length)]
    print(clicked)
    # generate correct answers
    results = []
    for i in range(0,length):
        # if module was skipped, fill with nothing
        if clicked[i] == 0:
           for j in range(0,questions[i]):
                results.append(None)
        else:
           for j in range(0,questions[i]):
                results.append(random.choice([1,1,0]))
    print(results)
    #post
    o += id + ',' + ','.join([str(i) for i in clicked]) + ',' + ','.join(['' if i is None else str(i) for i in results]) + '\n'

# save!
open(path,'w').write(o.strip())
