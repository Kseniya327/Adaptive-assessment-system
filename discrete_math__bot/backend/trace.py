from .database import SessionLocal, Student, Attempt, graph   # добавлен graph
from .ontology import get_all_sections, get_knowledge_gaps_by_section
import numpy as np

def compute_student_stats(vk_id: int) -> dict:
    session = SessionLocal()
    student = session.query(Student).filter_by(vk_id=vk_id).first()
    if not student:
        all_sections = get_all_sections()
        return {
            "vk_id": vk_id,
            "name": "Unknown",
            "total_attempts": 0,
            "accuracy": 0.0,
            "overall_score": 0.0,
            "section_gaps": [s["id"] for s in all_sections]
        }
    attempts = session.query(Attempt).filter_by(student_id=student.id).all()
    total = len(attempts)
    if total == 0:
        gaps = [s["id"] for s in get_all_sections()]
        session.close()
        return {
            "vk_id": vk_id,
            "name": student.name,
            "total_attempts": 0,
            "accuracy": 0.0,
            "overall_score": 0.0,
            "section_gaps": gaps
        }
    correct = sum(1 for a in attempts if a.correct)
    accuracy = correct / total
    times = [a.time_spent for a in attempts]
    max_time = max(times) if times else 1.0
    avg_time = np.mean(times) if times else 0.0
    time_norm = 1 - (avg_time / max_time) if max_time > 0 else 0.0
    if len(attempts) > 1:
        correctness_bin = [1 if a.correct else 0 for a in attempts]
        std = np.std(correctness_bin)
        trace_similarity = 1 - min(1.0, std)
    else:
        trace_similarity = 0.5
    graph_position = 0.5
    overall = 0.4 * accuracy + 0.3 * time_norm + 0.2 * trace_similarity + 0.1 * graph_position
    gaps = get_knowledge_gaps_by_section(vk_id)
    session.close()
    return {
        "vk_id": vk_id,
        "name": student.name,
        "total_attempts": total,
        "accuracy": accuracy,
        "overall_score": overall,
        "section_gaps": gaps
    }

def get_attempt_history(vk_id: int):
    session = SessionLocal()
    student = session.query(Student).filter_by(vk_id=vk_id).first()
    if not student:
        return []
    attempts = session.query(Attempt).filter_by(student_id=student.id).order_by(Attempt.timestamp).all()
    history = []
    for a in attempts:
        section_id = None
        concept_id = a.concept
        # Определяем раздел по концепту через граф
        for node, data in graph.nodes(data=True):
            if data.get('type') == 'section':
                for _, target, edata in graph.out_edges(node, data=True):
                    if edata.get('relation') == 'HAS_CONCEPT' and target == concept_id:
                        section_id = node
                        break
                if section_id:
                    break
        history.append({
            "timestamp": a.timestamp.isoformat(),
            "section": section_id,
            "concept": a.concept,
            "correct": a.correct,
            "time_spent": a.time_spent
        })
    session.close()
    return history