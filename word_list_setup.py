import os

import pymongo
from dotenv import load_dotenv
import requests

from persistence import Persister

link = "http://www.kilgarriff.co.uk/BNClists/lemma.al"

if __name__ == '__main__':
    load_dotenv('debug.env')

    DB_NAME = os.getenv('DB_NAME')
    DB_ADDRESS = os.getenv('DB_ADDRESS')

    client = pymongo.MongoClient(DB_ADDRESS)
    db = client[DB_NAME]
    persister = Persister(db)

    resp = requests.get(link)
    data = resp.text
    for word in data.split('\n')[:-1]:
        print(word)
        _, freq, lemma, pos = word.split(' ')
        persister.update_corpus_freq(lemma, int(freq))
