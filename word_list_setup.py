import requests

link = "http://www.kilgarriff.co.uk/BNClists/lemma.al"

def do_word_list_setup(persister):
    resp = requests.get(link)
    data = resp.text
    for word in data.split('\n')[:-1]:
        print(word)
        _, freq, lemma, pos = word.split(' ')
        persister.update_corpus_freq(lemma, int(freq))
