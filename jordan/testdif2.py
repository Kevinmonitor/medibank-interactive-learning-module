import difflib
import re
import regex
from tqdm import tqdm
from unidiff import PatchSet # type: ignore
from unidiff.patch import Line, Hunk

# https://docs.python.org/3/library/difflib.html
file1 = open('output.txt', encoding='utf-8').read()
file2 = open('output2.txt', encoding='utf-8').read()

# https://stackoverflow.com/questions/17904097/python-difference-between-two-strings
diff = difflib.ndiff(file1, file2)
print(len(file1))
print(len(file2))
o = ''
print('This may take some time!')
l = len(file1) + (len(file1)-len(file2))
lines = list(enumerate(tqdm(diff,'Enumerating diff... (approx)',l)))
engaged = ' '
for i,s in tqdm(lines,'Iterating diff...'):
    flag = s[0]
    change = s[-1]
    if flag != engaged:
        if engaged != ' ':
            o += f'}}'
        if flag != ' ':
            o+= f'{flag}{{'
    if change == '\n': o+= '\\n'
    if not (change == '\n' and flag == '-'): o+= change
    engaged = flag
print(o)

            