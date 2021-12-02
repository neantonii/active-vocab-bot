import random
from datetime import datetime, timedelta

import pymongo
from pymongo.database import Database

from entities import WordInSentence, UsageStatisticRecord, POSUsageStatistic, UserSettings

class Persister:
    NO_WORD = '???'
    randomness = 10

    @classmethod
    def next_level_reps(cls, level):
        return 3*(level+1)

    @classmethod
    def level_delays(cls, level):
        return timedelta(days=2**(level-1))

    def __init__(self, db: Database, user_id, start_skip=500):
        self.statistic_records_col = str(user_id) + '_usage_statistic_records'
        self.inputs_col = str(user_id) + '_inputs'
        self.settings_col = str(user_id) + '_settings'
        self.user_id = user_id
        self.db = db
        self.last_recommended = Persister.NO_WORD

        self.settings = self.db[self.settings_col].find_one()
        if self.settings is not None:
            self.settings = UserSettings.parse_obj(self.settings)
        else:
            self.settings = UserSettings(user_id = self.user_id, start_skip=start_skip)
            self.db[self.settings_col].update_one({'user_id': self.user_id}, {'$set': self.settings.dict()}, upsert=True)

        db[self.statistic_records_col].create_index([('lemma', pymongo.ASCENDING)])
        self.total_learned = db[self.statistic_records_col].count_documents({'memory_level': {'$ne': 0}})

    def process_leveling(self, rec: UsageStatisticRecord, now):
        if rec.n_used >= Persister.next_level_reps(rec.memory_level):
            rec.last_level_achieved = now
            rec.memory_level += 1
            rec.next_level_reminder = now + Persister.level_delays(rec.memory_level)
            if rec.memory_level == 1:
                self.total_learned += 1

    def save_input(self, text):
        self.db[self.inputs_col].insert_one({'dt': datetime.now(), 'text': text})

    def update_statistics(self, wd: WordInSentence):
        existing = self.db[self.statistic_records_col].find_one({'lemma': wd.word})
        if existing is None:
            existing = self.db[self.statistic_records_col].find_one({'lemma': wd.lemma})
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

        self.db[self.statistic_records_col].update_one({'lemma': wd.lemma}, {'$set': rec.dict()}, upsert=True)


    def get_stale(self, now, freq_thresh = None):
        filter = {'next_level_reminder': {'$lt': now}, 'ignored': {'$ne': True}}
        if freq_thresh is not None: filter['corpus_frequency'] = {'$lte': freq_thresh}
        stales = self.db[self.statistic_records_col].find( filter, sort=[('next_level_reminder', pymongo.ASCENDING)],
                                                           limit=Persister.randomness)
        stales = list(stales)
        if len(stales) == 0:
            return None
        print(f'[{freq_thresh}] selecting at random a stale word from {[s["lemma"] for s in stales]}')
        return random.choice(stales)

    def get_new(self, freq_thresh = None):
        filter = {'memory_level': 0, 'ignored': {'$ne': True}}
        if freq_thresh is not None: filter['corpus_frequency'] = {'$lte': freq_thresh}
        new_ones = self.db[self.statistic_records_col].find(filter, sort=[('corpus_frequency', pymongo.DESCENDING)],
                                                            limit=Persister.randomness)
        new_ones = list(new_ones)
        if len(new_ones) == 0:
            return None
        print(f'[{freq_thresh}] selecting at random a new word from {[s["lemma"] for s in new_ones]}')
        return random.choice(new_ones)

    def get_recommended(self):
        now = datetime.utcnow()
        use_skipped_chance = 0.5 * min(self.total_learned / self.settings.start_skip, 1)
        repeat_stale_chance = .7

        freq_thresh = self.db[self.statistic_records_col].find_one({},
                                                                   sort=[('corpus_frequency', pymongo.DESCENDING)],
                                                                   skip=self.settings.start_skip)
        if freq_thresh is None:
            use_skipped_chance = 1
            freq_thresh = 0
        else:
            freq_thresh = freq_thresh['corpus_frequency']

        def use(res):
            self.last_recommended = res['lemma']
            return self.last_recommended

        if random.random() < repeat_stale_chance:
            if random.random() < use_skipped_chance:
                res = self.get_stale(now)
                if res is not None: return use(res)
            res = self.get_stale(now, freq_thresh)
            if res is not None: return use(res)
        if random.random() < use_skipped_chance:
            res = self.get_new()
            if res is not None: return use(res)
        res = self.get_new(freq_thresh)
        if res is not None: return use(res)

        self.last_recommended = Persister.NO_WORD
        return Persister.NO_WORD

    def toggle_ignore(self, lemma):
        rec = self.db[self.statistic_records_col].find_one({'lemma': lemma})
        if rec is None: return None
        record: UsageStatisticRecord = UsageStatisticRecord.parse_obj(rec)
        new_state = not record.ignored
        record.ignored = new_state
        self.db[self.statistic_records_col].update_one({'lemma': lemma}, {'$set': record.dict()})
        return new_state

    def update_corpus_freq(self, lemma, freq):
        rec = self.db[self.statistic_records_col].find_one({'lemma': lemma})
        if rec is None:
            record = UsageStatisticRecord(lemma=lemma)
        else:
            record = UsageStatisticRecord.parse_obj(rec)

        record.corpus_frequency = freq
        self.db[self.statistic_records_col].update_one({'lemma': lemma}, {'$set': record.dict()}, upsert=True)

    def update_settings(self, start_skip=None):
        if start_skip is not None:
            self.settings.start_skip = start_skip
        self.db[self.settings_col].update_one({'user_id': self.user_id}, {'$set': self.settings.dict()})

