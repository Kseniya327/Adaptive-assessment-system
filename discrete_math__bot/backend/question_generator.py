import random
from .ontology import get_all_sections, get_concepts_by_section, get_definition, get_related_concepts_by_relation

MAX_ANSWER_LEN = 40

def shorten(text: str, max_len: int = MAX_ANSWER_LEN) -> str:
    """Обрезает текст до max_len, добавляя '...' если необходимо."""
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."

def get_definition_text(concept_id: str) -> str:
    """Возвращает текст определения концепта или пустую строку."""
    return get_definition(concept_id) or ""

def generate_distractors(correct_concept_name, section_id, count=3, question_type=None):
    """
    Генерирует отвлекающие варианты.
    Если question_type == 'definition' – возвращает тексты определений других концептов (обрезанные).
    Иначе – возвращает названия других концептов (обрезанные).
    """
    concepts = get_concepts_by_section(section_id)
    if question_type == "definition":
        # Собираем определения других концептов
        other_defs = []
        for c in concepts:
            if c["name"] != correct_concept_name:
                def_text = get_definition_text(c["id"])
                if def_text and len(def_text) > 5:
                    other_defs.append(shorten(def_text))
        # Если не хватает определений, добавим универсальные
        while len(other_defs) < count:
            other_defs.append("Математическое понятие")
        random.shuffle(other_defs)
        return other_defs[:count]
    else:
        # Старая логика: названия концептов
        manual_names = [c["name"] for c in concepts if c.get('manual') and c["name"] != correct_concept_name]
        auto_names = [c["name"] for c in concepts if not c.get('manual') and c["name"] != correct_concept_name]
        candidates = manual_names + auto_names
        if len(candidates) < count:
            candidates += ["Алгебраическая структура", "Математический объект", "Теорема", "Алгоритм"]
        random.shuffle(candidates)
        return [shorten(c) for c in candidates[:count]]

# --- Вопросы по определениям ---
def generate_definition_question(concept_id, concept_name, section_id):
    definition = get_definition(concept_id)
    if not definition or len(definition) < 10:
        return None
    short_definition = shorten(definition)
    templates = [
        "Что такое {concept}?",
        "Дайте определение понятию {concept}",
        "Объясните, что означает {concept}"
    ]
    question_text = random.choice(templates).format(concept=concept_name.capitalize())
    options = [short_definition] + generate_distractors(concept_name, section_id, count=3, question_type="definition")
    random.shuffle(options)
    return {
        "text": question_text,
        "options": options,
        "correct_answer": short_definition,
        "concept": concept_name,
        "section": section_id,
        "type": "definition",
        "id": f"def_q_{concept_id}",
        "concept_id": concept_id
    }

# --- Вопросы по агрегации (часть-целое) ---
def generate_aggregation_question(concept_id, concept_name, related_ids, section_id):
    if not related_ids:
        return None
    correct_id = random.choice(related_ids)
    correct_name = get_concept_name_by_id(correct_id)
    short_correct = shorten(correct_name)
    templates = [
        "Какой компонент входит в состав {concept}?",
        "Что является частью {concept}?",
        "Из какого элемента состоит {concept}?"
    ]
    question_text = random.choice(templates).format(concept=concept_name.capitalize())
    options = [short_correct] + generate_distractors(correct_name, section_id, count=3, question_type=None)
    random.shuffle(options)
    return {
        "text": question_text,
        "options": options,
        "correct_answer": short_correct,
        "concept": concept_name,
        "section": section_id,
        "type": "aggregation",
        "id": f"agg_q_{concept_id}",
        "concept_id": concept_id,
        "target_concept_id": correct_id
    }

# --- Вопросы по композиции (образует) ---
def generate_composition_question(concept_id, concept_name, related_ids, section_id):
    if not related_ids:
        return None
    correct_id = random.choice(related_ids)
    correct_name = get_concept_name_by_id(correct_id)
    short_correct = shorten(correct_name)
    templates = [
        "Что образует {concept}?",
        "Что порождает {concept}?",
        "Что строится из {concept}?"
    ]
    question_text = random.choice(templates).format(concept=concept_name.capitalize())
    options = [short_correct] + generate_distractors(correct_name, section_id, count=3, question_type=None)
    random.shuffle(options)
    return {
        "text": question_text,
        "options": options,
        "correct_answer": short_correct,
        "concept": concept_name,
        "section": section_id,
        "type": "composition",
        "id": f"comp_q_{concept_id}",
        "concept_id": concept_id,
        "target_concept_id": correct_id
    }

# --- Вопросы по ассоциации ---
def generate_association_question(concept_id, concept_name, related_ids, section_id):
    if not related_ids:
        return None
    correct_id = random.choice(related_ids)
    correct_name = get_concept_name_by_id(correct_id)
    short_correct = shorten(correct_name)
    templates = [
        "С каким понятием связано {concept}?",
        "Какой термин ассоциируется с {concept}?",
        "Что использует {concept}?"
    ]
    question_text = random.choice(templates).format(concept=concept_name.capitalize())
    options = [short_correct] + generate_distractors(correct_name, section_id, count=3, question_type=None)
    random.shuffle(options)
    return {
        "text": question_text,
        "options": options,
        "correct_answer": short_correct,
        "concept": concept_name,
        "section": section_id,
        "type": "association",
        "id": f"assoc_q_{concept_id}",
        "concept_id": concept_id,
        "target_concept_id": correct_id
    }

# --- Вопросы по реализации (реализует) ---
def generate_realization_question(concept_id, concept_name, related_ids, section_id):
    if not related_ids:
        return None
    correct_id = random.choice(related_ids)
    correct_name = get_concept_name_by_id(correct_id)
    short_correct = shorten(correct_name)
    templates = [
        "Какую задачу решает {concept}?",
        "Что реализует {concept}?",
        "Для чего используется {concept}?"
    ]
    question_text = random.choice(templates).format(concept=concept_name.capitalize())
    options = [short_correct] + generate_distractors(correct_name, section_id, count=3, question_type=None)
    random.shuffle(options)
    return {
        "text": question_text,
        "options": options,
        "correct_answer": short_correct,
        "concept": concept_name,
        "section": section_id,
        "type": "realization",
        "id": f"real_q_{concept_id}",
        "concept_id": concept_id,
        "target_concept_id": correct_id
    }

# --- Генерация всех типов вопросов для концепта ---
def generate_all_questions_for_concept(concept_id, concept_name, section_id):
    questions = []
    q_def = generate_definition_question(concept_id, concept_name, section_id)
    if q_def:
        questions.append(q_def)
    related = get_related_concepts_by_relation(concept_id, "AGGREGATION")
    if related:
        q = generate_aggregation_question(concept_id, concept_name, related, section_id)
        if q:
            questions.append(q)
    related = get_related_concepts_by_relation(concept_id, "COMPOSITION")
    if related:
        q = generate_composition_question(concept_id, concept_name, related, section_id)
        if q:
            questions.append(q)
    related = get_related_concepts_by_relation(concept_id, "ASSOCIATION")
    if related:
        q = generate_association_question(concept_id, concept_name, related, section_id)
        if q:
            questions.append(q)
    related = get_related_concepts_by_relation(concept_id, "REALIZES")
    if related:
        q = generate_realization_question(concept_id, concept_name, related, section_id)
        if q:
            questions.append(q)
    return questions

def get_next_question_for_student(vk_id):
    sections = get_all_sections()
    all_questions = []
    for sec in sections:
        concepts = get_concepts_by_section(sec["id"])
        for c in concepts:
            qs = generate_all_questions_for_concept(c["id"], c["name"], sec["id"])
            all_questions.extend(qs)
    if not all_questions:
        # fallback вопрос с короткими вариантами
        fallback_q = {
            "text": "Что такое дискретная математика?",
            "options": ["Наука о дискретных структурах", "Математика непрерывных функций", "Теория вероятностей", "Математический анализ"],
            "correct_answer": "Наука о дискретных структурах",
            "concept": "дискретная математика",
            "section": "default",
            "id": "fallback",
            "type": "fallback",
            "concept_id": "fallback"
        }
        fallback_q["options"] = [shorten(opt) for opt in fallback_q["options"]]
        fallback_q["correct_answer"] = shorten(fallback_q["correct_answer"])
        return fallback_q
    return random.choice(all_questions)

# Вспомогательная функция получения имени концепта по ID
def get_concept_name_by_id(concept_id):
    from .database import graph
    return graph.nodes[concept_id].get('name', concept_id)
