from fastapi import FastAPI, HTTPException
from .database import graph, save_graph, SessionLocal, Student, Attempt, ScheduledTest, FixedQuestion
from .trace import compute_student_stats, get_attempt_history
from .question_generator import get_next_question_for_student
from .ontology import get_all_sections, get_knowledge_gaps_by_section
from .adaptive import choose_next_section, choose_difficulty
from .models import AttemptCreate, AttemptResponse, StudentStats, ScheduledTestCreate, Concept, Question
import uuid
import json
from datetime import datetime
from .database import Complaint

app = FastAPI()

# Хранилище сессий тестов
test_sessions = {}

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/sections")
def sections():
    return get_all_sections()

@app.get("/concepts")
def concepts():
    # Возвращает все концепты (для совместимости)
    concepts_list = []
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'concept':
            concepts_list.append({"name": data.get('name')})
    return concepts_list

@app.get("/start_test/{vk_id}")
def start_test(vk_id: int):
    question = get_next_question_for_student(vk_id)
    test_sessions[vk_id] = {
        "questions_asked": 1,
        "max_questions": 10,
        "current_section": question["section"]
    }
    return {"question": question, "current": 1, "total": 10}

@app.get("/next_question/{vk_id}")
def next_question(vk_id: int):
    session = test_sessions.get(vk_id)
    if not session:
        return {"error": "Тест не начат. Нажмите 'Тест'."}
    # Проверяем, не превышен ли лимит ДО увеличения счётчика
    if session["questions_asked"] >= session["max_questions"]:
        del test_sessions[vk_id]
        return {"error": "Тест завершён. Поздравляем!"}
    # Увеличиваем счётчик заданных вопросов
    session["questions_asked"] += 1
    current_num = session["questions_asked"]
    question = get_next_question_for_student(vk_id)
    session["current_section"] = question["section"]
    return {"question": question, "current": current_num, "total": session["max_questions"]}


# backend/main.py (фрагмент)
@app.post("/attempt")
def save_attempt(attempt: AttemptCreate):
    # Убираем поиск в графе
    correct_answer = attempt.correct_answer
    concept = attempt.concept
    correct = (attempt.answer.strip().lower() == correct_answer.strip().lower())

    db = SessionLocal()
    student = db.query(Student).filter_by(vk_id=attempt.vk_id).first()
    if not student:
        student = Student(vk_id=attempt.vk_id, name=f"User{attempt.vk_id}")
        db.add(student)
        db.commit()
        db.refresh(student)

    db_attempt = Attempt(
        student_id=student.id,
        question_id=attempt.question_id,
        concept=concept,
        correct=correct,
        answer_text=attempt.answer,
        time_spent=attempt.time_spent
    )
    db.add(db_attempt)
    db.commit()
    db.close()
    delta = 0.1 if correct else -0.05
    return AttemptResponse(correct=correct, correct_answer=correct_answer, score_delta=delta)

@app.post("/set_name")
def set_name(data: dict):
    vk_id = data["vk_id"]
    name = data["name"]
    db = SessionLocal()
    student = db.query(Student).filter_by(vk_id=vk_id).first()
    if student:
        student.name = name
    else:
        student = Student(vk_id=vk_id, name=name)
        db.add(student)
    db.commit()
    db.close()
    return {"status": "ok"}

@app.get("/student/{vk_id}/stats")
def student_stats(vk_id: int):
    return compute_student_stats(vk_id)

@app.get("/student/{vk_id}/gaps")
def student_gaps(vk_id: int):
    return {"gaps": get_knowledge_gaps_by_section(vk_id)}

@app.get("/student/{vk_id}/history")
def student_history(vk_id: int):
    return get_attempt_history(vk_id)

# ---------- Админ-эндпоинты для студентов и расписания ----------
@app.get("/admin/students")
def list_students():
    db = SessionLocal()
    students = db.query(Student).all()
    db.close()
    return [{"id": s.id, "vk_id": s.vk_id, "name": s.name} for s in students]

@app.get("/admin/student/{vk_id}/full_stats")
def full_student_stats(vk_id: int):
    stats = compute_student_stats(vk_id)
    history = get_attempt_history(vk_id)
    return {"stats": stats, "history": history}

@app.post("/admin/schedule_test")
def schedule_test(test: dict):
    db = SessionLocal()
    scheduled = ScheduledTest(
        start_time=datetime.fromisoformat(test["start_time"]),
        end_time=datetime.fromisoformat(test["end_time"]),
        concept_filter=test.get("concept_filter"),
        description=test.get("description")
    )
    db.add(scheduled)
    db.commit()
    db.close()
    return {"status": "scheduled"}

@app.get("/admin/scheduled_tests")
def get_scheduled_tests():
    db = SessionLocal()
    tests = db.query(ScheduledTest).all()
    db.close()
    return [
        {"id": t.id, "start_time": t.start_time.isoformat(), "end_time": t.end_time.isoformat(),
         "concept_filter": t.concept_filter, "description": t.description}
        for t in tests
    ]

@app.get("/can_test/{vk_id}")
def can_test(vk_id: int):
    now = datetime.utcnow()
    db = SessionLocal()
    active = db.query(ScheduledTest).filter(
        ScheduledTest.start_time <= now,
        ScheduledTest.end_time >= now
    ).first()
    db.close()
    return {"allowed": active is not None}

# ---------- Админ-эндпоинты для работы с определениями (вопросы) ----------
@app.get("/admin/definitions")
def get_definitions():
    definitions = []
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'definition':
            concept_id = None
            for pred in graph.predecessors(node):
                if graph.nodes[pred].get('type') == 'concept':
                    concept_id = pred
                    break
            concept_name = graph.nodes[concept_id].get('name') if concept_id else None
            section_id = None
            if concept_id:
                for pred in graph.predecessors(concept_id):
                    if graph.nodes[pred].get('type') == 'section':
                        section_id = pred
                        break
            definitions.append({
                "id": node,
                "text": data.get('text'),
                "concept": concept_name,
                "section": section_id
            })
    return definitions

@app.put("/admin/definition/{did}")
def update_definition(did: str, payload: dict):
    if not graph.has_node(did) or graph.nodes[did].get('type') != 'definition':
        raise HTTPException(404, "Определение не найдено")
    graph.nodes[did]['text'] = payload['text']
    save_graph(graph)
    return {"status": "ok"}

@app.delete("/admin/definition/{did}")
def delete_definition(did: str):
    if not graph.has_node(did):
        raise HTTPException(404, "Определение не найдено")
    graph.remove_node(did)
    save_graph(graph)
    return {"status": "ok"}

@app.post("/admin/definition")
def add_definition(payload: dict):
    section_id = payload['section']
    concept_name = payload['concept']
    definition_text = payload['definition']
    # Найти или создать концепт
    concept_id = None
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'concept' and data.get('name') == concept_name and data.get('section') == section_id:
            concept_id = node
            break
    if not concept_id:
        concept_id = f"c_{section_id}_{concept_name.replace(' ', '_')}"
        graph.add_node(concept_id, type='concept', name=concept_name, section=section_id, manual=True)
        graph.add_edge(section_id, concept_id, relation='HAS_CONCEPT')
    def_id = f"def_{concept_id}"
    graph.add_node(def_id, type='definition', text=definition_text)
    graph.add_edge(concept_id, def_id, relation='DEFINES')
    save_graph(graph)
    return {"status": "ok"}

# ---------- Админ-эндпоинты для управления рёбрами (отношениями) ----------
@app.get("/admin/nodes")
def get_nodes(node_type: str = None):
    """Возвращает все узлы графа, опционально фильтруя по типу."""
    nodes = []
    for node, data in graph.nodes(data=True):
        if node_type and data.get('type') != node_type:
            continue
        nodes.append({
            "id": node,
            "type": data.get('type'),
            "name": data.get('name') if data.get('type') in ('concept', 'section') else node,
            "section": data.get('section')
        })
    return nodes

@app.get("/admin/edges")
def get_edges(relation_type: str = None):
    """Возвращает все рёбра, опционально фильтруя по типу отношения."""
    edges = []
    for u, v, data in graph.edges(data=True):
        rel = data.get('relation')
        if relation_type and rel != relation_type:
            continue
        edges.append({
            "source": u,
            "target": v,
            "relation": rel,
            "weight": data.get('weight', 1)
        })
    return edges

@app.delete("/admin/edge")
def delete_edge(source: str, target: str, relation: str):
    """Удаляет ребро по трём параметрам."""
    if not graph.has_edge(source, target):
        raise HTTPException(404, "Ребро не найдено")
    edge_data = graph.get_edge_data(source, target)
    if edge_data.get('relation') != relation:
        raise HTTPException(404, "Ребро с таким типом не найдено")
    graph.remove_edge(source, target)
    save_graph(graph)
    return {"status": "ok"}

@app.post("/admin/edge")
def add_edge(payload: dict):
    """Добавляет новое ребро."""
    source = payload['source']
    target = payload['target']
    relation = payload['relation']
    weight = payload.get('weight', 0.5)
    if not graph.has_node(source) or not graph.has_node(target):
        raise HTTPException(400, "Один из узлов не существует")
    if graph.has_edge(source, target):
        # Если ребро уже существует, можно либо заменить, либо вернуть ошибку
        raise HTTPException(400, "Ребро уже существует")
    graph.add_edge(source, target, relation=relation, weight=weight)
    save_graph(graph)
    return {"status": "ok"}

# ---------- Админ-эндпоинты для управления разделами ----------
@app.get("/admin/sections")
def admin_sections():
    sections = []
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'section':
            sections.append({"id": node, "name": data.get('name')})
    return sections

@app.get("/admin/concepts/{section_id}")
def admin_concepts(section_id: str):
    concepts = []
    for _, target, data in graph.out_edges(section_id, data=True):
        if data.get('relation') == 'HAS_CONCEPT':
            concept_data = graph.nodes[target]
            concepts.append({"id": target, "name": concept_data.get('name')})
    return concepts

# ---------- Эндпоинты для исправления вопросов (FixedQuestion) – опционально, но оставим ----------
@app.post("/admin/fix_question")
def fix_question(payload: dict):
    db = SessionLocal()
    q = db.query(FixedQuestion).filter(
        FixedQuestion.concept_id == payload['concept_id'],
        FixedQuestion.relation_type == payload['relation_type']
    )
    if payload.get('target_concept_id'):
        q = q.filter(FixedQuestion.target_concept_id == payload['target_concept_id'])
    old = q.first()
    if old:
        db.delete(old)
    fixed = FixedQuestion(
        concept_id=payload['concept_id'],
        relation_type=payload['relation_type'],
        target_concept_id=payload.get('target_concept_id'),
        fixed_text=payload['fixed_text'],
        fixed_answer=payload['fixed_answer'],
        fixed_options=json.dumps(payload.get('fixed_options', []))
    )
    db.add(fixed)
    db.commit()
    db.close()
    return {"status": "ok"}

@app.delete("/admin/fix_question")
def delete_fix_question(concept_id: str, relation_type: str, target_concept_id: str = None):
    db = SessionLocal()
    q = db.query(FixedQuestion).filter(
        FixedQuestion.concept_id == concept_id,
        FixedQuestion.relation_type == relation_type
    )
    if target_concept_id:
        q = q.filter(FixedQuestion.target_concept_id == target_concept_id)
    q.delete()
    db.commit()
    db.close()
    return {"status": "ok"}

@app.post("/complaint")
def create_complaint(payload: dict):
    """
    Ожидает: {
        "vk_id": int,
        "question_id": str,
        "question_type": str,
        "concept_id": str,
        "target_concept_id": str (опционально),
        "student_answer": str,
        "correct_answer": str,
        "question_text": str
    }
    """
    db = SessionLocal()
    student = db.query(Student).filter_by(vk_id=payload['vk_id']).first()
    if not student:
        db.close()
        raise HTTPException(404, "Student not found")
    complaint = Complaint(
        student_id=student.id,
        question_id=payload['question_id'],
        question_type=payload['question_type'],
        concept_id=payload['concept_id'],
        target_concept_id=payload.get('target_concept_id'),
        student_answer=payload['student_answer'],
        correct_answer=payload['correct_answer'],
        question_text=payload['question_text'],
        status='pending'
    )
    db.add(complaint)
    db.commit()
    db.close()
    return {"status": "ok"}

@app.get("/admin/complaints")
def get_complaints(status: str = None):
    db = SessionLocal()
    q = db.query(Complaint)
    if status:
        q = q.filter(Complaint.status == status)
    complaints = q.all()
    result = []
    for c in complaints:
        student = db.query(Student).filter_by(id=c.student_id).first()
        result.append({
    "id": c.id,
    "vk_id": student.vk_id if student else None,
    "question_id": c.question_id,
    "question_type": c.question_type,
    "relation_type": c.question_type,   # <- добавить для совместимости с админкой
    "concept_id": c.concept_id,
    "target_concept_id": c.target_concept_id,
    "student_answer": c.student_answer,
    "correct_answer": c.correct_answer,
    "question_text": c.question_text,
    "status": c.status,
    "created_at": c.created_at.isoformat()
                    })
    db.close()
    return result

@app.put("/admin/complaint/{complaint_id}")
def resolve_complaint(complaint_id: int, payload: dict):
    """
    payload: {
        "action": "reject"  или "resolve",
        "new_correct_answer": "новый правильный ответ" (если action=resolve)
    }
    """
    db = SessionLocal()
    complaint = db.query(Complaint).filter_by(id=complaint_id).first()
    if not complaint:
        db.close()
        raise HTTPException(404, "Жалоба не найдена")
    
    if payload['action'] == 'reject':
        # Отклоняем жалобу – ответ студента был неправильным
        student = db.query(Student).filter_by(id=complaint.student_id).first()
        if student:
            # Создаём попытку с правильностью False
            attempt = Attempt(
                student_id=student.id,
                question_id=complaint.question_id,
                concept=complaint.concept_id,
                correct=False,
                answer_text=complaint.student_answer,
                time_spent=0
            )
            db.add(attempt)
        complaint.status = 'rejected'
    elif payload['action'] == 'resolve':
        # Принимаем жалобу – обновляем вопрос
        # Для определения: находим узел definition и обновляем его текст
        if complaint.question_type == 'definition':
            # Ищем определение по concept_id? Лучше по question_id (это id определения)
            if graph.has_node(complaint.question_id):
                graph.nodes[complaint.question_id]['text'] = payload['new_correct_answer']
                save_graph(graph)
        # Для отношений можно было бы обновить фиксированный вопрос, но пока просто отмечаем resolved
        complaint.status = 'resolved'
        complaint.resolved_answer = payload['new_correct_answer']
    
    db.commit()
    db.close()
    return {"status": "ok"}