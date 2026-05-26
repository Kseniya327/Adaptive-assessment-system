import json
import os
import networkx as nx
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from .config import SQLITE_PATH, GRAPH_JSON_PATH

# ---------- Граф NetworkX ----------
def load_graph():
    if os.path.exists(GRAPH_JSON_PATH):
        with open(GRAPH_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return nx.node_link_graph(data)
    else:
        return nx.DiGraph()

def save_graph(graph):
    data = nx.node_link_data(graph)
    with open(GRAPH_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

graph = load_graph()

# ---------- SQLAlchemy ----------
engine = create_engine(f"sqlite:///{SQLITE_PATH}", echo=False)
Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, index=True)
    name = Column(String)

class Attempt(Base):
    __tablename__ = "attempts"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), index=True)
    question_id = Column(String)
    concept = Column(String)
    correct = Column(Boolean)
    answer_text = Column(String)
    time_spent = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ScheduledTest(Base):
    __tablename__ = "scheduled_tests"
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    concept_filter = Column(String, nullable=True)
    description = Column(String)

# Новая таблица для жалоб
class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), index=True)
    question_id = Column(String)          # ID вопроса (например, def_q_... или agg_q_...)
    question_type = Column(String)        # 'definition', 'aggregation', 'composition', 'association', 'realization'
    concept_id = Column(String)           # ID концепта, к которому относится вопрос
    target_concept_id = Column(String, nullable=True)  # для бинарных отношений
    student_answer = Column(String)       # что ответил студент (может быть "ЖАЛОБА" или текст)
    correct_answer = Column(String)       # правильный ответ (на момент жалобы)
    question_text = Column(String)        # текст вопроса
    status = Column(String, default='pending')  # pending, resolved, rejected
    resolved_answer = Column(String, nullable=True)  # не используется, оставим
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class FixedQuestion(Base):
    __tablename__ = "fixed_questions"
    id = Column(Integer, primary_key=True)
    concept_id = Column(String)
    relation_type = Column(String)
    target_concept_id = Column(String, nullable=True)
    fixed_text = Column(String)
    fixed_answer = Column(String)
    fixed_options = Column(String)   # JSON-строка с вариантами ответов

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)