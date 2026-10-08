import re

import regex


file1 = open('output.txt','r',encoding='utf-8')
file2 = open('output2.txt','w',encoding='utf-8')

content = file1.read()
content = regex.sub('(?<=[a-z,; .]+)\n(?=[a-z,;. ]{2,})',' ', content,flags=regex.IGNORECASE)
content = re.sub(r'\<[^>]+\>','', content)
file2.write(content)
file2.close()