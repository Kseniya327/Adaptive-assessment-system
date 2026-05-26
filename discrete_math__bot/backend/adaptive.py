from .database import SessionLocal, Student, Attempt
from .ontology import get_all_sections, get_concepts_by_section, get_knowledge_gaps_by_section, get_student_section_performance
import random

def get_student_concept_performance(vk_id: int, concept_name: str):
    """Возвращает (точность, количество попыток) по концепту."""
    session = SessionLocal()
    student = session.query(Student).filter_by(vk_id=vk_id).first()
    if not student:
        session.close()
        return 0.0, 0
    attempts = session.query(Attempt).filter_by(student_id=student.id, concept=concept_name).all()
    total = len(attempts)
    if total == 0:
        session.close()
        return 0.0, 0
    correct = sum(1 for a in attempts if a.correct)
    session.close()
    return correct / total, total

def choose_next_section(vk_id: int):
    """Выбирает следующий раздел: сначала пробелы, затем наихудшая точность."""
    gaps = get_knowledge_gaps_by_section(vk_id)
    if gaps:
        return gaps[0]
    sections = get_all_sections()
    best = None
    best_acc = 1.0
    for s in sections:
        acc, _ = get_student_section_performance(vk_id, s["id"])
        if acc < best_acc:
            best_acc = acc
            best = s["id"]
    return best if best else sections[0]["id"]

def choose_next_concept(vk_id: int, section_id: str):
    """Выбирает концепт в разделе: тот, по которому у студента наименьшая точность."""
    concepts = get_concepts_by_section(section_id)
    if not concepts:
        return None
    session = SessionLocal()
    student = session.query(Student).filter_by(vk_id=vk_id).first()
    if not student:
        session.close()
        return concepts[0]
    attempts = session.query(Attempt).filter_by(student_id=student.id, section=section_id).all()
    concept_stats = {}
    for c in concepts:
        c_attempts = [a for a in attempts if a.concept == c["name"]]
        total = len(c_attempts)
        if total == 0:
            concept_stats[c["id"]] = 0.0
        else:
            correct = sum(1 for a in c_attempts if a.correct)
            concept_stats[c["id"]] = correct / total
    session.close()
    worst = min(concept_stats, key=concept_stats.get)
    for c in concepts:
        if c["id"] == worst:
            return c
    return concepts[0]

def choose_difficulty(vk_id: int, section_id: str) -> int:
    """
    Адаптивный выбор сложности вопроса на основе точности студента по данному разделу.
    Точность < 0.3 -> сложность 1
    точность 0.3-0.6 -> сложность 2
    точность 0.6-0.8 -> сложность 3
    точность > 0.8 -> сложность 4
    Если попыток меньше 2, возвращает 1.
    """
    acc, attempts = get_student_section_performance(vk_id, section_id)
    if attempts < 2:
        return 1
    if acc < 0.3:
        return 1
    elif acc < 0.6:
        return 2
    elif acc < 0.8:
        return 3
    else:
        return 4