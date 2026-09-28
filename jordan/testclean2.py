import io
import nltk
import textcleaner
from nltk.corpus import stopwords

nltk.download('punkt_tab')
nltk.download('maxent_ne_chunker_tab')
nltk.download('averaged_perceptron_tagger_eng')


name = r'C:\Users\jorda\OneDrive\Documents\2026\COS70008-Tec\ACS_Ethics_Case_Studies_v2.1-1.pdf'

print('Reading input.txt')
file = io.open('input.txt', 'r', encoding='utf-8')
lines = '\n\n'.join(file.readlines())

tokens = nltk.word_tokenize(lines)
#https://www.geeksforgeeks.org/nlp/removing-stop-words-nltk-python/
stops = set(stopwords.words('english'))
tokens = [word for word in tokens if word not in stops]
print(tokens)
#https://www.nltk.org/book/ch05.html
tags = nltk.pos_tag(tokens)
print(tags)
#https://www.nltk.org/api/nltk.chunk.html
chunks = nltk.chunk.ne_chunk(tags,False)
print(chunks)
