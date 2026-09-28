import re

import pdfplumber

from Pydirext import start

n = r'C:\Users\jorda\OneDrive\Documents\2026\COS70008-Tec\ACS_Ethics_Case_Studies_v2.1-1.pdf'




def print_data(file, text, root=0, prev=0):
    s = ' '*root
    print(f'{s}Extracting data ({type(text)}:{len(text)})')
    n = 0
    for i in text:
        # if the row is a sub-matrix
        if type(i) is list:
            print(f'{s}Matrix')
            # if on the 2nd layer of the matrix and the previous width does not match the current width
            if root == 1 and prev != len(i):
                # we are at the head, print the head of the table
                sep = ("┌", "┬")
                m = 0
                for _ in i:
                    m += 1
                    left_of_table = m == 1 # choose the seperator to use based on if the cursor is on the left or the middle
                    num = 0 if left_of_table else 1
                    file.write(sep[num] + ('─' * 60)) # print the seperator followed by a vertical seperator
                file.write("┐" + '\n')
            prev = len(i)
            # print the row
            print_data(file, i, root + 1, prev)
            n += 1
            # if on the 2nd layer of the matrix
            if root == 1:
                # print the seperator
                bottom_of_table = n == len(text)
                sep = ("└","┴","┘") if bottom_of_table else ("├","┼","┤")
                m = 0
                for _ in i:
                    m += 1
                    left_of_table = m == 1 # choose the seperator to use based on if the cursor is on the left or the middle
                    num = 0 if left_of_table else 1
                    file.write(sep[num] + ('─' * 60)) # print the seperator followed by a vertical seperator
                file.write(sep[2] + '\n')
        else:
            # print a separator followed by the datum
            i = str(i).replace('\n', ' \\n ')
            file.write(f"│{i:<60}")
    if root == 0: # if on the 1st layer
        file.write('\n\n---------------\n\n')
    else:
        # if printing a row
        if all(type(i) is str for i in text):
            # print a row end
            file.write('|')
        file.write('\n')
    print(f'{s}End of data ({type(text)}:{len(text)})')

def save(text):
    file = open('output.txt', 'w', encoding="utf-8")
    try:
        print(f'Extracting text')
        file.writelines(text)
    except TypeError:
        for i in text:
            if type(i) is str:
                file.write(i+"\n")
                continue
            print(f'Attempting extract table')
            print_data(file, i)
    file.close()
    start('output.txt') # type: ignore


while True:
    name = input('>')
    r = re.match('^(?P<mode>(tables )?(text )?)(?P<name>.*)', name)
    if r is None: continue
    mode = r.group('mode').strip()
    if mode is None: mode = 'text'
    name = r.group('name')
    if name == '': name = n
    with pdfplumber.open(name) as pdf:
        print(f'Printing {name}')
        o = []
        for page in pdf.pages:
            o.append(str(page))
            print(f'Extracting {mode}(s) from {page}')
            if 'text' in mode:
                o.append(page.extract_text() + '\n\n---------------\n\n')
            if 'table' in mode:
                    o.append(page.extract_tables())
        save(o)
