import enchant
import requests
import spacy

link = "http://www.kilgarriff.co.uk/BNClists/lemma.al"
link2 = 'http://corpus.leeds.ac.uk/frqc/internet-en.num'

dic_gb = enchant.Dict("en_GB")
dic_us = enchant.Dict("en_US")

nlp = spacy.load("en_core_web_sm")

def check(word:str):
    ents = nlp(word.capitalize()).ents
    if len(ents) > 0 and ents[0].label_ == 'PERSON':
        return False
    return dic_gb.check(word) or dic_us.check(word) or dic_gb.check(word.capitalize()) or dic_us.check(word.capitalize())

def do_word_list_setup_british(persister):
    resp = requests.get(link)
    data = resp.text
    for word in data.split('\n')[:-1]:
        print(word)
        _, freq, lemma, pos = word.split(' ')
        persister.update_corpus_freq(lemma, int(freq))

def do_word_list_setup_internet(persister):
    resp = requests.get(link2)
    data = resp.text
    for word in data.split('\n')[4:-1]:
        # print(word)
        _, freq, lemma = word.split(' ')
        if check(lemma):
            persister.update_corpus_freq(lemma, float(freq))
        else:
            print(lemma)


if __name__ == '__main__':
    print(check('iii'))