import math
from datetime import datetime, timedelta

import pymongo
from pymongo.database import Database

from entities import WordInSentence, UsageStatisticRecord, POSUsageStatistic

class Persister:

    statistic_records = 'usage_statistic_records'
    inputs = 'inputs'

    @classmethod
    def next_level_reps(cls, level):
        return 3*(level+1)

    @classmethod
    def level_delays(cls, level):
        return timedelta(days=2**(level-1))

    def __init__(self, db: Database):
        self.db = db
        db[Persister.statistic_records].create_index([('lemma', pymongo.ASCENDING)])

    def process_leveling(self, rec: UsageStatisticRecord, now):
        if rec.n_used >= Persister.next_level_reps(rec.memory_level):
            rec.last_level_achieved = now
            rec.memory_level += 1
            rec.next_level_reminder = now + Persister.level_delays(rec.memory_level)

    def save_input(self, text):
        self.db[Persister.inputs].insert_one({'dt': datetime.now(), 'text': text})

    def update_statistics(self, wd: WordInSentence):
        existing = self.db[Persister.statistic_records].find_one({'lemma': wd.lemma})
        now = datetime.utcnow()
        if existing:
            rec: UsageStatisticRecord = UsageStatisticRecord.parse_obj(existing)
        else:
            rec: UsageStatisticRecord = UsageStatisticRecord(lemma=wd.lemma)

        rec.last_used = now
        rec.n_used += 1

        self.process_leveling(rec, now)

        pos_rec = next((r for r in rec.parts_of_speech if r.pos == wd.pos), None)
        if pos_rec is None:
            pos_rec = POSUsageStatistic(pos=wd.pos)
            rec.parts_of_speech.append(pos_rec)

        pos_rec.last_used = now
        pos_rec.n_used += 1

        self.db[Persister.statistic_records].update_one({'lemma': wd.lemma}, {'$set': rec.dict()}, upsert=True)

    def get_recommended(self):
        now = datetime.utcnow()
        stale = self.db[Persister.statistic_records].find_one({'next_level_reminder': {'$lt': now}, 'ignored': {'$ne': True}},
                                                              sort=[('next_level_reminder', pymongo.ASCENDING)])
        if stale is not None:
            return stale['lemma']
        new_one = self.db[Persister.statistic_records].find_one({'memory_level': 0, 'ignored': {'$ne': True}},
                                                                sort=[('corpus_frequency', pymongo.DESCENDING)])
        if new_one is not None:
            return new_one['lemma']
        return '???'

    def toggle_ignore(self, lemma):
        rec = self.db[Persister.statistic_records].find_one({'lemma': lemma})
        if rec is None: return None
        record: UsageStatisticRecord = UsageStatisticRecord.parse_obj(rec)
        new_state = not record.ignored
        record.ignored = new_state
        self.db[Persister.statistic_records].update_one({'lemma': lemma}, {'$set': record.dict()})
        return new_state

    def update_corpus_freq(self, lemma, freq):
        rec = self.db[Persister.statistic_records].find_one({'lemma': lemma})
        if rec is None:
            record = UsageStatisticRecord(lemma=lemma)
        else:
            record = UsageStatisticRecord.parse_obj(rec)

        record.corpus_frequency = freq
        self.db[Persister.statistic_records].update_one({'lemma': lemma}, {'$set': record.dict()}, upsert=True)