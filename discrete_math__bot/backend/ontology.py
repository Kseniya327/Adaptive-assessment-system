from .database import graph, save_graph

def get_all_sections():
    sections = []
    for node, data in graph.nodes(data=True):
        if data.get('type') == 'section':
            sections.append({"id": node, "name": data.get('name', node)})
    return sections

def get_concepts_by_section(section_id):
    concepts = []
    for _, target, data in graph.out_edges(section_id, data=True):
        if data.get('relation') == 'HAS_CONCEPT':
            node_data = graph.nodes[target]
            concepts.append({
                "id": target,
                "name": node_data.get('name', target),
                "section": section_id
            })
    return concepts

def get_definition(concept_id):
    """Возвращает текст определения для концепта, если есть."""
    for _, target, data in graph.out_edges(concept_id, data=True):
        if data.get('relation') == 'DEFINES':
            return graph.nodes[target].get('text', "")
    return ""

def get_related_concepts(concept_id, relation_type=None):
    """Возвращает список концептов, связанных данным отношением."""
    result = []
    for _, target, data in graph.out_edges(concept_id, data=True):
        if relation_type is None or data.get('relation') == relation_type:
            if graph.nodes[target].get('type') == 'concept':
                result.append(target)
    return result

def get_generalizations(concept_id):
    """Возвращает список концептов, которые обобщают данный (родители)."""
    parents = []
    for pred, _, data in graph.in_edges(concept_id, data=True):
        if data.get('relation') == 'GENERALIZES':
            parents.append(pred)
    return parents

def get_specializations(concept_id):
    """Возвращает список концептов, которые являются частными случаями (дети)."""
    children = []
    for _, target, data in graph.out_edges(concept_id, data=True):
        if data.get('relation') == 'GENERALIZES':
            children.append(target)
    return children


def get_student_section_performance(vk_id: int, section_id: str):
    from .database import SessionLocal, Student, Attempt
    session = SessionLocal()
    student = session.query(Student).filter_by(vk_id=vk_id).first()
    if not student:
        session.close()
        return 0.0, 0
    attempts = session.query(Attempt).filter_by(student_id=student.id, section=section_id).all()
    total = len(attempts)
    if total == 0:
        session.close()
        return 0.0, 0
    correct = sum(1 for a in attempts if a.correct)
    session.close()
    return correct / total, total

def get_knowledge_gaps_by_section(vk_id):
    from .database import SessionLocal, Student, Attempt, graph
    session = SessionLocal()
    student = session.query(Student).filter_by(vk_id=vk_id).first()
    if not student:
        return [s["id"] for s in get_all_sections()]
    correct_attempts = session.query(Attempt).filter_by(student_id=student.id, correct=True).all()
    correct_sections = set()
    for att in correct_attempts:
        concept_id = att.concept
        # Ищем раздел, которому принадлежит концепт
        for node, data in graph.nodes(data=True):
            if data.get('type') == 'section':
                for _, target, edata in graph.out_edges(node, data=True):
                    if edata.get('relation') == 'HAS_CONCEPT' and target == concept_id:
                        correct_sections.add(node)
                        break
                if concept_id in correct_sections:
                    break
    all_sections = [s["id"] for s in get_all_sections()]
    gaps = [s for s in all_sections if s not in correct_sections]
    session.close()
    return gaps


def get_concept_name_by_id(concept_id):
    from .database import graph
    return graph.nodes[concept_id].get('name', concept_id)

def get_related_concepts_by_relation(concept_id, relation_type):
    """Возвращает список ID концептов, связанных с данным отношением."""
    from .database import graph
    related = []
    for _, target, data in graph.out_edges(concept_id, data=True):
        if data.get('relation') == relation_type:
            if graph.nodes[target].get('type') == 'concept':
                related.append(target)
    return related