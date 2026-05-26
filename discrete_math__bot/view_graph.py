import json
import networkx as nx
from pyvis.network import Network

# Цвета для разных типов отношений
RELATION_COLORS = {
    "HAS_CONCEPT": "#87CEEB",      # голубой
    "DEFINES": "#2E8B57",          # тёмно-зелёный
    "GENERALIZES": "#FFA500",      # оранжевый
    "AGGREGATION": "#9370DB",      # фиолетовый
    "COMPOSITION": "#FF6347",      # томатный
    "ASSOCIATION": "#FFD700",      # золотой
    "REALIZES": "#DC143C",         # кармин
    "PREREQ": "#808080"            # серый
}
DEFAULT_COLOR = "#C0C0C0"          # светло-серый по умолчанию

def visualize_graph(graph_json_path="./data/graph.json", output_html="ontology_graph.html"):
    with open(graph_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    G = nx.node_link_graph(data)

    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")

    # Добавляем узлы
    for node, attrs in G.nodes(data=True):
        # Определяем цвет узла по типу
        if attrs.get('type') == 'section':
            color = "#1E90FF"   # синий для разделов
            title = f"Раздел: {attrs.get('name', node)}"
        elif attrs.get('type') == 'concept':
            if attrs.get('manual', False):
                color = "#32CD32"   # зелёный для ручных концептов
            else:
                color = "#FFD700"   # золотой для авто-концептов
            title = f"Концепт: {attrs.get('name', node)}"
        elif attrs.get('type') == 'definition':
            color = "#FF69B4"   # розовый для определений
            title = f"Определение: {attrs.get('text', '')[:100]}"
        else:
            color = "#D3D3D3"
            title = node
        net.add_node(node, label=attrs.get('name', node), title=title, color=color)

    # Добавляем рёбра с цветом в зависимости от типа отношения
    for u, v, attrs in G.edges(data=True):
        rel = attrs.get('relation', 'unknown')
        color = RELATION_COLORS.get(rel, DEFAULT_COLOR)
        title = f"{rel} (вес: {attrs.get('weight', 1)})"
        net.add_edge(u, v, title=title, color=color, width=2)

    # Настройки отображения: отключаем физику, чтобы узлы не разлетались
    net.set_options("""
    var options = {
      "physics": {"enabled": false},
      "interaction": {"dragNodes": true, "hover": true},
      "edges": {"smooth": {"type": "continuous"}}
    }
    """)
    net.save_graph(output_html)
    print(f"Граф сохранён в {output_html}. Откройте файл в браузере.")
    print("Цвета рёбер:")
    for rel, col in RELATION_COLORS.items():
        print(f"  {rel}: {col}")

if __name__ == "__main__":
    visualize_graph()