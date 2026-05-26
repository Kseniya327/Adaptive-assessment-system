import streamlit as st
import requests
import plotly.express as px
from datetime import datetime

API_URL = "http://localhost:8000"
st.set_page_config(layout="wide")
st.title("👨‍🏫 Админ-панель: адаптивная аттестация")

menu = st.sidebar.selectbox("Меню", [
    "Студенты",
    "Статистика студента",
    "Жалобы",
    "Вопросы (определения)",
    "Добавить определение",
    "Отношения"
])

# ---------- Студенты ----------
if menu == "Студенты":
    r = requests.get(f"{API_URL}/admin/students")
    if r.status_code == 200:
        students = r.json()
        if students:
            st.table([{"ID": s["id"], "VK ID": s["vk_id"], "Имя": s["name"]} for s in students])
        else:
            st.info("Нет зарегистрированных студентов")
    else:
        st.error("Ошибка загрузки")

# ---------- Статистика студента ----------
elif menu == "Статистика студента":
    vk_id = st.number_input("VK ID студента", min_value=1, step=1)
    if st.button("Показать"):
        r = requests.get(f"{API_URL}/admin/student/{vk_id}/full_stats")
        if r.status_code == 200:
            data = r.json()
            stats = data["stats"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Имя", stats["name"])
            col2.metric("Точность", f"{stats['accuracy']:.2%}")
            col3.metric("Общий score", f"{stats['overall_score']:.2f}")
            st.write("**Пробелы:**", ", ".join(stats["concept_gaps"]) if stats["concept_gaps"] else "нет")
            if data["history"]:
                history = data["history"]
                timestamps = [h["timestamp"] for h in history]
                correct_vals = [1 if h["correct"] else 0 for h in history]
                fig = px.line(x=timestamps, y=correct_vals, title="Динамика правильности",
                              labels={"x": "Время", "y": "Правильность (0/1)"})
                st.plotly_chart(fig)
                st.write("**История попыток:**")
                for a in history:
                    st.write(f"{a['timestamp']} – {a['section']} – {a['concept']} – {'✅' if a['correct'] else '❌'} – {a['time_spent']:.1f} с")
        else:
            st.error("Студент не найден")

# ---------- Жалобы ----------
elif menu == "Жалобы":
    st.subheader("📋 Жалобы на некорректные вопросы")
    status_filter = st.selectbox("Статус", ["pending", "resolved", "rejected", "all"])
    params = {} if status_filter == "all" else {"status": status_filter}
    r = requests.get(f"{API_URL}/admin/complaints", params=params)
    if r.status_code == 200:
        complaints = r.json()
        if not complaints:
            st.info("Нет жалоб")
        else:
            # Словарь для перевода статусов
            status_ru = {
                "pending": "На рассмотрении",
                "resolved": "Принятые",
                "rejected": "Отклоненые",
                "all": "Все"
            }
            for c in complaints:
                with st.expander(f"Жалоба #{c['id']} от vk_id {c['vk_id']} ({c['created_at']}) – {c['relation_type']}"):
                    st.write(f"**Вопрос:** {c['question_text']}")
                    st.write(f"**Ответ студента:** {c['student_answer']}")
                    st.write(f"**Правильный ответ (на момент жалобы):** {c['correct_answer']}")
                    st.write(f"**Тип вопроса:** {c['relation_type']}")
                    if c['status'] == 'pending':
                        col1, col2 = st.columns(2)
                        with col1:
                            new_answer = st.text_input("Исправленный правильный ответ", value=c['correct_answer'], key=f"ans_{c['id']}")
                            if st.button(f"✅ Принять и исправить", key=f"resolve_{c['id']}"):
                                resp = requests.put(f"{API_URL}/admin/complaint/{c['id']}", json={
                                    "action": "resolve",
                                    "new_correct_answer": new_answer
                                })
                                if resp.status_code == 200:
                                    st.success("Жалоба принята, вопрос исправлен")
                                    st.rerun()
                                else:
                                    st.error("Ошибка")
                        with col2:
                            if st.button(f"❌ Отклонить", key=f"reject_{c['id']}"):
                                resp = requests.put(f"{API_URL}/admin/complaint/{c['id']}", json={"action": "reject"})
                                if resp.status_code == 200:
                                    st.success("Жалоба отклонена, ответ студента засчитан как неверный")
                                    st.rerun()
                                else:
                                    st.error("Ошибка")
                    else:
                        st.write(f"**Статус:** {c['status']}")
                        if c.get('resolved_answer'):
                            st.write(f"**Исправленный ответ:** {c['resolved_answer']}")
    else:
        st.error("Ошибка загрузки жалоб")

# ---------- Вопросы (определения) ----------
elif menu == "Вопросы (определения)":
    st.subheader("📋 Список определений (вопросов)")
    r_defs = requests.get(f"{API_URL}/admin/definitions")
    if r_defs.status_code == 200:
        definitions = r_defs.json()
        if not definitions:
            st.info("Нет определений")
        else:
            for d in definitions:
                with st.expander(f"📝 {d['concept']}: {d['text'][:80]}..."):
                    st.write(f"**ID определения:** {d['id']}")
                    st.write(f"**Концепт:** {d['concept']}")
                    st.write(f"**Раздел:** {d.get('section', '—')}")
                    st.write(f"**Текст:** {d['text']}")
                    with st.form(f"edit_def_{d['id']}"):
                        new_text = st.text_area("Новый текст определения", value=d['text'])
                        if st.form_submit_button("Сохранить"):
                            resp = requests.put(f"{API_URL}/admin/definition/{d['id']}", json={"text": new_text})
                            if resp.status_code == 200:
                                st.success("Сохранено")
                                st.rerun()
                            else:
                                st.error("Ошибка")
                    if st.button(f"🗑️ Удалить", key=f"del_def_{d['id']}"):
                        resp = requests.delete(f"{API_URL}/admin/definition/{d['id']}")
                        if resp.status_code == 200:
                            st.success("Удалено")
                            st.rerun()
                        else:
                            st.error("Ошибка")
    else:
        st.error("Ошибка загрузки")

# ---------- Добавить определение ----------
elif menu == "Добавить определение":
    st.subheader("➕ Добавить новое определение (вопрос)")
    r_sect = requests.get(f"{API_URL}/admin/sections")
    if r_sect.status_code != 200:
        st.error("Не удалось загрузить разделы")
    else:
        sections = r_sect.json()
        section_names = [s["name"] for s in sections]
        selected_section_name = st.selectbox("Раздел", section_names)
        section_id = next(s["id"] for s in sections if s["name"] == selected_section_name)

        r_con = requests.get(f"{API_URL}/admin/concepts/{section_id}")
        concepts = []
        if r_con.status_code == 200:
            concepts = r_con.json()
        concept_names = ["(новый концепт)"] + [c["name"] for c in concepts]
        selected_concept_option = st.selectbox("Концепт", concept_names)
        
        if selected_concept_option == "(новый концепт)":
            new_concept = st.text_input("Название нового концепта")
            concept_name = new_concept
        else:
            concept_name = selected_concept_option
        
        definition_text = st.text_area("Текст определения (будет ответом на вопрос)")
        if st.button("Добавить"):
            if not concept_name or not definition_text:
                st.error("Заполните концепт и определение")
            else:
                payload = {
                    "section": section_id,
                    "concept": concept_name,
                    "definition": definition_text
                }
                resp = requests.post(f"{API_URL}/admin/definition", json=payload)
                if resp.status_code == 200:
                    st.success("Определение добавлено!")
                    st.rerun()
                else:
                    st.error("Ошибка добавления")

# ---------- Отношения ----------
elif menu == "Отношения":
    st.subheader("🔗 Управление рёбрами (отношениями между концептами)")
    
    # Загрузка списка узлов для выпадающих списков
    r_nodes = requests.get(f"{API_URL}/admin/nodes")
    if r_nodes.status_code == 200:
        all_nodes = r_nodes.json()
        node_options = {f"{n['id']} ({n['type']})": n['id'] for n in all_nodes}
    else:
        st.error("Не удалось загрузить узлы")
        node_options = {}
    
    # Фильтр по типу отношения
    relation_types = ["AGGREGATION", "COMPOSITION", "ASSOCIATION", "REALIZES", "GENERALIZES", "HAS_CONCEPT", "DEFINES"]
    selected_rel_type = st.selectbox("Фильтр по типу отношения", ["Все"] + relation_types)
    
    # Загрузка рёбер
    params = {} if selected_rel_type == "Все" else {"relation_type": selected_rel_type}
    r_edges = requests.get(f"{API_URL}/admin/edges", params=params)
    if r_edges.status_code == 200:
        edges = r_edges.json()
        if not edges:
            st.info("Нет рёбер")
        else:
            for e in edges:
                with st.expander(f"🔹 {e['source']} --[{e['relation']}]--> {e['target']} (вес: {e.get('weight', 1)})"):
                    st.write(f"**Источник:** {e['source']}")
                    st.write(f"**Цель:** {e['target']}")
                    st.write(f"**Тип:** {e['relation']}")
                    st.write(f"**Вес:** {e.get('weight', 1)}")
                    if st.button(f"🗑️ Удалить", key=f"del_edge_{e['source']}_{e['target']}_{e['relation']}"):
                        resp = requests.delete(f"{API_URL}/admin/edge", params={
                            "source": e['source'],
                            "target": e['target'],
                            "relation": e['relation']
                        })
                        if resp.status_code == 200:
                            st.success("Ребро удалено")
                            st.rerun()
                        else:
                            st.error("Ошибка удаления")
    else:
        st.error("Ошибка загрузки рёбер")
    
    st.markdown("---")
    st.subheader("➕ Добавить новое ребро")
    with st.form("add_edge_form"):
        source = st.selectbox("Исходный узел", options=list(node_options.keys()), format_func=lambda x: x)
        source_id = node_options[source]
        target = st.selectbox("Целевой узел", options=list(node_options.keys()), format_func=lambda x: x)
        target_id = node_options[target]
        rel = st.selectbox("Тип отношения", relation_types)
        weight = st.slider("Вес (0.0–1.0)", 0.0, 1.0, 0.5, 0.05)
        if st.form_submit_button("Добавить ребро"):
            payload = {
                "source": source_id,
                "target": target_id,
                "relation": rel,
                "weight": weight
            }
            resp = requests.post(f"{API_URL}/admin/edge", json=payload)
            if resp.status_code == 200:
                st.success("Ребро добавлено")
                st.rerun()
            else:
                st.error(f"Ошибка: {resp.text}")