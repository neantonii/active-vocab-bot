from typing import List, Optional

from pydantic import BaseModel, Field
from datetime import datetime


class WordInSentence (BaseModel):
    lemma: str = Field(...)
    pos: str = Field(...)
    word: str = Field(...)

    def __hash__(self):
        return hash(repr(self))

class UsageStatistic(BaseModel):
    first_used: Optional[datetime] = Field(None)
    last_used: Optional[datetime] = Field(None)
    n_used: int = Field(0)

class POSUsageStatistic(UsageStatistic):
    pos: str = Field(...)

class UsageStatisticRecord(UsageStatistic):
    lemma: str = Field(...)
    memory_level: int = Field(0)
    corpus_frequency: float = Field(0)
    last_level_achieved: Optional[datetime] = Field(None)
    next_level_reminder: Optional[datetime] = Field(None)
    parts_of_speech: List[POSUsageStatistic] = Field([])
    ignored: Optional[bool] = Field(False)

class UserSettings(BaseModel):
    user_id: int = Field(...)
    start_skip: int = Field(500)


