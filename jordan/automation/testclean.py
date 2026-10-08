import io
import re

import pdfplumber
# https://github.com/tqdm/tqdm
from tqdm import tqdm

name = r'C:\Users\jorda\OneDrive\Documents\2026\COS70008-Tec\ACS_Ethics_Case_Studies_v2.1-1.pdf'
extract = 1
lines = []

if extract == 0:
    pdf = pdfplumber.open(name)
    for i in tqdm(pdf.pages, desc=f'{name} Reading page'):
        lines.append(i.extract_text())
    file = io.open('input.txt', 'w', encoding='utf-8')
    file.writelines([i.replace('\n', ' ') + '\n' for i in lines])
    file.close()
    exit(0)
else:
    print('Reading input.txt')
    file = io.open('input.txt', 'r', encoding='utf-8')
    for i in tqdm(file.readlines(), desc=f'{name} Reading page'):
        lines.append(i)

sentences = []
splitlines = []
for _line in lines:
    page = []
    #remove abbreviations
    _line = re.sub(r'(vol|etc|no)\.', lambda x: x.group(1), _line, flags=re.IGNORECASE)

    # https://stackoverflow.com/questions/20320719/constructing-regex-pattern-to-match-sentence
    for i in re.finditer('[A-Z](?:[^.!?]|[.!?;:]\w)+?(([.!?;:](?=\s|$))|$)', _line, re.IGNORECASE):
        page.append(i.group())
    sentences.append(page)

for i in sentences:
    print(i)

for _page in sentences:
    page = []
    for _line in _page:
        words = []
        for word in _line.split(' '):
            word = word.strip()
            word = word.replace('\n', ' ')
            word = re.sub('[^\da-zA-Z\'\-]', ' ', word, )

            if word == '': continue
            for i in re.finditer('([a-z][a-z\'\-]*)|&|([\-+\d.]?[\d.]+)', word, flags=re.IGNORECASE):
                words.append(i.group())
        page.append(words)
    splitlines.append(page)

for i in splitlines:
    print(i)
