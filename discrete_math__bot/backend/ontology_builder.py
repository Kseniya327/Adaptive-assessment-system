import os
import re
import json
import networkx as nx
from .text_processor import split_into_sentences, extract_ngrams, clean_text
from .concept_extractor import filter_concepts, cluster_concepts
from .relation_markers import detect_relation_from_text
from .database import save_graph

def find_closest_concept(G, phrase):
    from .text_processor import lemmatize_sentence
    phrase_norm = lemmatize_sentence(phrase).strip()
    for node, data in G.nodes(data=True):
        if data.get('type') == 'concept':
            name = data.get('name', '')
            name_norm = lemmatize_sentence(name).strip()
            if name == phrase or phrase in name or name_norm == phrase_norm:
                return node
    return None

def add_definition_edges(G, section_id, text, concept_ids):
    """Расширенные шаблоны поиска определений."""
    sentences = re.split(r'[.!?]+', text)
    for concept_id in concept_ids:
        concept_name = G.nodes[concept_id].get('name', '')
        has_def = any(edge[2].get('relation') == 'DEFINES' for edge in G.out_edges(concept_id, data=True))
        if has_def:
            continue
        definition = None
        rel_type = None
        for sent in sentences:
            sent = sent.strip()
            # Шаблоны (включая варианты с тире, двоеточием)
            patterns = [
                rf'{re.escape(concept_name)}\s*[-—–:]\s*это\s*(.+)',
                rf'{re.escape(concept_name)}\s+это\s+(.+)',
                rf'{re.escape(concept_name)}\s+называется\s+(.+)',
                rf'Под\s+{re.escape(concept_name)}\s+понимается\s*(.+)',
                rf'{re.escape(concept_name)}\s+[-—–]\s+(.+)'
            ]
            for pat in patterns:
                m = re.search(pat, sent, re.IGNORECASE)
                if m:
                    definition = m.group(1).strip()
                    break
            if definition:
                rel_type = detect_relation_from_text(sent)
                break
        if not definition:
            for sent in sentences:
                if concept_name in sent.lower():
                    definition = sent
                    break
        if definition and len(definition) > 10:
            def_node = f"def_{concept_id}"
            G.add_node(def_node, type="definition", text=definition)
            G.add_edge(concept_id, def_node, relation="DEFINES")
            if rel_type:
                G.add_edge(concept_id, def_node, relation=rel_type, weight=0.7)
                print(f"  Отношение {rel_type} для {concept_name}")

def add_relation_edges_between_concepts(G, text):
    """Ищет в тексте маркеры отношений между концептами и добавляет рёбра."""
    sentences = re.split(r'[.!?]+', text)
    for sent in sentences:
        rel_type = detect_relation_from_text(sent)
        if not rel_type:
            continue
        # Ищем все концепты в предложении
        concept_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'concept']
        found_concepts = []
        for cid in concept_nodes:
            name = G.nodes[cid].get('name', '')
            if name and name.lower() in sent.lower():
                found_concepts.append(cid)
        if len(found_concepts) >= 2:
            for i in range(len(found_concepts)):
                for j in range(i+1, len(found_concepts)):
                    if not G.has_edge(found_concepts[i], found_concepts[j]):
                        G.add_edge(found_concepts[i], found_concepts[j], relation=rel_type, weight=0.6)

def add_generalization_edges(G):
    concepts = [(n, data) for n, data in G.nodes(data=True) if data.get('type') == 'concept']
    for i, (n1, d1) in enumerate(concepts):
        name1 = d1.get('name', '')
        for j, (n2, d2) in enumerate(concepts):
            if i == j:
                continue
            name2 = d2.get('name', '')
            if name1 in name2 and len(name1) < len(name2):
                if not G.has_edge(n1, n2):
                    G.add_edge(n1, n2, relation="GENERALIZES", weight=0.8)

def load_manual_concepts(json_path="./data/manual_concepts.json"):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def build_ontology_from_sections(sections: dict, textbook_folder: str):
    G = nx.DiGraph()
    manual_concepts = load_manual_concepts()
    all_concept_ids = []

    for sec_id, sec_data in sections.items():
        G.add_node(sec_id, type="section", name=sec_data["name"])
        file_path = os.path.join(textbook_folder, sec_data['filename'])
        if not os.path.exists(file_path):
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        clean = clean_text(raw_text)
        sentences = split_into_sentences(clean)

        # --- Автоматические концепты (n-граммы) ---
        ngrams = extract_ngrams(sentences, min_freq=4, max_features=50)
        raw_concepts = filter_concepts(ngrams, min_len=5, forbid_digits=True)
        concept_groups = cluster_concepts(raw_concepts, threshold=0.65)
        auto_count = 0
        for canonical, variants in concept_groups.items():
            # Проверяем, нет ли такого же ручного
            is_manual = any(canonical == (m.get('name') if isinstance(m, dict) else m)
                            for m in manual_concepts.get(sec_id, []))
            if is_manual:
                continue
            concept_id = f"c_{sec_id}_{canonical.replace(' ', '_')}"
            G.add_node(concept_id, type="concept", name=canonical, section=sec_id, manual=False, auto=True)
            G.add_edge(sec_id, concept_id, relation="HAS_CONCEPT", weight=len(variants))
            all_concept_ids.append(concept_id)
            auto_count += 1
        print(f"Раздел {sec_data['name']}: авто-концептов {auto_count}")

        # --- Ручные концепты из JSON ---
        for item in manual_concepts.get(sec_id, []):
            if isinstance(item, dict):
                term = item['name']
                definition = item.get('definition')
            else:
                term = item
                definition = None
            concept_id = f"c_{sec_id}_{term.replace(' ', '_')}"
            if not G.has_node(concept_id):
                G.add_node(concept_id, type="concept", name=term, section=sec_id, manual=True, auto=False)
                G.add_edge(sec_id, concept_id, relation="HAS_CONCEPT", weight=1.0)
                all_concept_ids.append(concept_id)
                if definition:
                    def_node = f"def_{concept_id}"
                    G.add_node(def_node, type="definition", text=definition)
                    G.add_edge(concept_id, def_node, relation="DEFINES")

        # Поиск определений для всех концептов раздела
        add_definition_edges(G, sec_id, raw_text, all_concept_ids)
        # Поиск отношений между концептами на основе маркеров
        add_relation_edges_between_concepts(G, raw_text)

    # Глобальные обобщения (только для ручных, чтобы не плодить шум)
    add_generalization_edges(G)

    save_graph(G)
    return G