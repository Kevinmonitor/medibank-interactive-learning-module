import random
# Ratings by weight of each rating
ratings = [1,2,2,3,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5]
# File to output
path = 'test.csv'
# Number of rows
rows = 10

# header
o = "Account ID,Initial Cover,Health,Homesickness,VISITING A DOCTOR,VISITING A HOSPITAL,CALLING AN EMERGENCY,PAYING HOSPITAL BILLS\n"
# for eac row
for i in range(0,rows):
    # randomise ID and ratings
    id = str(random.randint(11111111,20000000))
    cover = random.choice(ratings)
    health = random.choice(ratings)
    homesick = random.choice(ratings)
    choices = []
    answers = ()
    # while answers are blank
    while sum(choices) == 0:
        # randomly generate indices
        for i in range(0,3):
            choices.append(random.randint(-4,random.choice(ratings)))
        # trim the out of range answers
        choices = [(-1 if i > 4 or i < 0 else i) for i in choices]
        print(choices)
        # generate the answers using the random indices
        answers = [str(i) for i in
                   (1 if 0 in choices else 0,
                   1 if 1 in choices else 0,
                   1 if 2 in choices else 0,
                   1 if 3 in choices else 0,
                   1 if 4 in choices else 0)]
    # post the row!
    line = f"{id},{cover},{health},{homesick},{','.join(answers)}\n"
    print(line)
    o+=line

# save!
open(path,'w').write(o.strip())
