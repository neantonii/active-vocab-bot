import math
from datetime import datetime, timedelta

import pymongo
from pymongo.database import Database

from entities import WordInSentence, UsageStatisticRecord, POSUsageStatistic

class Persister:

    statistic_records = 'usage_statistic_records'

    next_level_reps = [3, 6, 9, 12, 15, 18, 21, math.inf] #if we now are on lvl l, we need next_level_reps to go to the next one
    level_delays = [None, timedelta(days=1), timedelta(days=2), timedelta(days=4), timedelta(days=8), timedelta(days=16), timedelta(days=32), timedelta(days=64)] #if we just got lvl l, set notification delay to level_delays[l]
    assert len(next_level_reps) == len(level_delays)

    def __init__(self, db: Database):
        self.db = db
        db[Persister.statistic_records].create_index([('lemma', pymongo.ASCENDING)])

    def process_leveling(self, rec: UsageStatisticRecord, now):
        if rec.n_used >= Persister.next_level_reps[rec.memory_level]:
            rec.last_level_achieved = now
            rec.memory_level += 1
            rec.next_level_reminder = now + Persister.level_delays[rec.memory_level]


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
        fresh = self.db[Persister.statistic_records].find_one({'next_level_reminder': {'$lt': now}}, sort=[('next_level_reminder', pymongo.ASCENDING)])
        if fresh is not None:
            return fresh['lemma']
        new_one = self.db[Persister.statistic_records].find_one({'memory_level': 0}, sort=[('corpus_frequency', pymongo.DESCENDING)])
        if new_one is not None:
            return new_one['lemma']
        return '???'