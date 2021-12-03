# pip install -U spacy
# python -m spacy download en_core_web_sm
import json
import os
from collections import Counter, defaultdict

import spacy
from idiomatch import Idiomatcher
from lemminflect import getInflection, getAllInflections, getAllInflectionsOOV
# getAllLemmas('watches')
# {'NOUN': ('watch',), 'VERB': ('watch',)}
from entities import WordInSentence, UsageStatisticRecord


class SentenceSplitter:
    def __init__(self, extract_idioms = False):
        self.nlp = spacy.load("en_core_web_sm")
        self.extract_idioms = extract_idioms
        self.idiomatcher = None
        if self.extract_idioms:
            Idiomatcher.from_pretrained(self.nlp)

    def process(self, sentence):
        usages = []
        tokens = self.nlp(sentence)
        for token in tokens:
            if  token.pos_ == 'PUNCT':
                continue
            usages.append(WordInSentence(lemma=token.lemma_.lower(), pos=token.pos_, word=str(token).lower()))
        if self.extract_idioms:
            pass
            # idioms = set()
            # for match in idiomatcher.identify(tokens):
            #     idioms.add(match['idiom'])

        return usages

    def lemmatize_google_word(self, word):
        word = word.split('_')[0]
        tokens = self.nlp(word)
        return tokens[0].lemma_

    def convert_google_freq_to_lemma_freq(self, path):
        lemma_freq = defaultdict(lambda: 0)
        with open(path, 'r') as f:
            data = json.load(f)
        for wd in data:
            lemma = self.lemmatize_google_word(wd[0])
            lemma_freq[lemma] = max(lemma_freq[lemma], wd[1])
        return lemma_freq



if __name__ == '__main__':
    #update frec records
    #TODO move it somewhere
    import pymongo
    from dotenv import load_dotenv

    load_dotenv('debug.env')
    DB_NAME = os.getenv('DB_NAME')
    DB_ADDRESS = os.getenv('DB_ADDRESS')
    client = pymongo.MongoClient(DB_ADDRESS)
    db = client[DB_NAME]
    splitter = SentenceSplitter()

    google_freq_path = r'C:\PROJECTS\google-ngram-word-frequency-lists\wordlist-eng-n10000-y1950-2000.json'
    freqs = splitter.convert_google_freq_to_lemma_freq(google_freq_path)
    for lemma, freq in freqs.items():
        existing = db['usage_statistic_records'].find_one({'lemma': lemma})
        if existing is not None:
            rec = UsageStatisticRecord.parse_obj(existing)
        else:
            rec = UsageStatisticRecord(lemma = lemma)
        rec.corpus_frequency = freq
        db['usage_statistic_records'].update_one({'lemma': lemma}, {'$set': rec.dict()}, upsert=True)
