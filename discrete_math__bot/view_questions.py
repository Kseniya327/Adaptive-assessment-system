import json
import networkx as nx
from backend.question_generator import generate_all_questions_for_concept
from backend.ontology import get_all_sections, get_concepts_by_section

def preview_questions():
    # Загружаем граф с правильной кодировкой
    with open("./data/graph.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    G = nx.node_link_graph(data)
    
    import backend.ontology as onto
    onto.graph = G

    sections = get_all_sections()
    print("=== Все сгенерированные вопросы (определения + отношения) ===\n")
    total = 0
    for sec in sections:
        sec_id = sec["id"]
        sec_name = sec["name"]
        concepts = get_concepts_by_section(sec_id)
        print(f"Раздел: {sec_name} (концептов: {len(concepts)})")
        for c in concepts:
            qs = generate_all_questions_for_concept(c["id"], c["name"], sec_id)
            for q in qs:
                total += 1
                print(f"  [{q['type']}] {q['text']}")
                print(f"       Ответ: {q['correct_answer']}")
                print(f"       Варианты: {', '.join(q['options'])}")
                print()
    print(f"Всего сгенерировано вопросов: {total}")

if __name__ == "__main__":
    preview_questions()