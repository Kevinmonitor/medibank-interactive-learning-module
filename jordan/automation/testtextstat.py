import textstat

print('< for return')
while True:
    text = ''
    inp = ''
    while inp != '<':
        inp = input('>')
        if inp != '<':
            text += inp + '\n'
    print(textstat.textstat.text_standard(text))
    print(textstat.textstat.difficult_words_list(text))
    print(textstat.textstat.flesch_reading_ease(text))
    print(textstat.textstat.dale_chall_readability_score(text))
