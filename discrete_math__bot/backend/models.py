from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Модели для работы с API
class AttemptCreate(BaseModel):
    vk_id: int
    question_id: str
    answer: str
    time_spent: float
    correct_answer: str   
    concept: str

class AttemptResponse(BaseModel):
    correct: bool
    correct_answer: str
    score_delta: float

class StudentStats(BaseModel):
    vk_id: int
    name: str
    total_attempts: int
    accuracy: float
    overall_score: float
    concept_gaps: List[str]

class ScheduledTestCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    concept_filter: Optional[str] = None
    description: Optional[str] = None

# Модели для онтологии (Concept и Question)
class Concept(BaseModel):
    name: str

class Question(BaseModel):
    id: str
    text: str
    answer: str
    difficulty: int
    concept: str