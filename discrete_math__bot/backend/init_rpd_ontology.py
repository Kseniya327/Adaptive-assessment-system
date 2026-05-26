import os
from .ontology_builder import build_ontology_from_sections

SECTIONS = {
    "number_theory": {"name": "Теория чисел", "filename": "number_theory.txt"},
    "algebraic_structures": {"name": "Базовые алгебраические структуры", "filename": "algebraic_structures.txt"},
    "polynomial_rings": {"name": "Кольцо многочленов над полем", "filename": "polynomial_rings.txt"},
    "coding": {"name": "Кодирование", "filename": "coding.txt"},
    "graphs_networks": {"name": "Сети и графы", "filename": "graphs_networks.txt"}
}

if __name__ == "__main__":
    os.makedirs("./textbook", exist_ok=True)
    print("Убедитесь, что в папке textbook есть файлы:", list(SECTIONS.keys()))
    input("Нажмите Enter, чтобы начать построение онтологии...")
    build_ontology_from_sections(SECTIONS, "./textbook")
    print("Готово!")