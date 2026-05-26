import os
import time
import requests
import re
from dotenv import load_dotenv
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from .states import States
from .keyboards import main_keyboard, options_keyboard

load_dotenv()
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
BACKEND_URL = os.getenv("BACKEND_URL")

user_states = {}
user_data = {}

SECTION_NAMES = {
    "number_theory": "Теория чисел",
    "algebraic_structures": "Базовые алгебраические структуры",
    "polynomial_rings": "Кольцо многочленов над полем",
    "coding": "Кодирование",
    "graphs_networks": "Сети и графы"
}

def send(vk, peer_id, msg, kb=None):
    try:
        print(f"🤖 -> {peer_id}: {msg[:200]}")
        vk.messages.send(
            peer_id=peer_id,
            message=msg,
            random_id=get_random_id(),
            keyboard=kb.get_keyboard() if kb else None
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def safe_get(url, params=None):
    try:
        return requests.get(url, params=params, timeout=30)
    except Exception as e:
        print(f"GET error {url}: {e}")
        return None

def safe_post(url, json=None):
    try:
        return requests.post(url, json=json, timeout=30)
    except Exception as e:
        print(f"POST error {url}: {e}")
        return None

def normalize_text(text):
    """Убирает эмодзи и приводит к нижнему регистру."""
    # Удаляем всё, кроме букв, цифр, пробелов
    cleaned = re.sub(r'[^\w\s]', '', text).strip().lower()
    return cleaned

def main():
    vk_session = VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("✅ Адаптивный VK бот запущен")

    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
                msg_obj = event.object.message
                user_id = msg_obj["from_id"]
                peer_id = msg_obj["peer_id"]
                text = msg_obj.get("text", "").strip()
                print(f"📩 Сообщение от {user_id}: '{text}'")

                if user_id not in user_states:
                    send(vk, peer_id, "👋 Добро пожаловать! Напишите 'Начать'.", main_keyboard())
                    user_states[user_id] = States.MAIN
                    continue

                state = user_states.get(user_id, States.MAIN)

                # --- Ожидание имени ---
                if state == States.WAITING_NAME:
                    name = text
                    resp = safe_post(f"{BACKEND_URL}/set_name", json={"vk_id": user_id, "name": name})
                    if resp and resp.status_code == 200:
                        send(vk, peer_id, f"Приятно познакомиться, {name}!", main_keyboard())
                        send(vk, peer_id, "Теперь вы можете приступить к тесту.", main_keyboard())
                    else:
                        send(vk, peer_id, "Имя сохранено! Теперь вы можете приступить к тесту.", main_keyboard())
                    user_states[user_id] = States.MAIN
                    continue

                # --- Главное меню ---
                if state == States.MAIN:
                    norm_text = normalize_text(text)

                    if norm_text in ("начать", "старт"):
                        send(vk, peer_id, "Как вас зовут? Напишите своё имя.")
                        user_states[user_id] = States.WAITING_NAME
                        continue

                    # Тест
                    if norm_text == "тест":
                        resp = safe_get(f"{BACKEND_URL}/start_test/{user_id}")
                        if not resp or resp.status_code != 200:
                            send(vk, peer_id, "❌ Ошибка запуска теста.", main_keyboard())
                            continue
                        data = resp.json()
                        if "error" in data:
                            send(vk, peer_id, f"❌ {data['error']}", main_keyboard())
                            continue
                        q = data["question"]
                        current_num = data.get("current", 1)
                        total = data.get("total", 10)
                        if not q.get("options"):
                            send(vk, peer_id, "❌ Нет вариантов ответа.", main_keyboard())
                            continue
                        user_data[user_id] = {
                            "current_question": q,
                            "start_time": time.time(),
                            "question_num": current_num,
                            "total_questions": total,
                            "correct_answer": q.get("correct_answer"),
                            "concept": q.get("concept"),
                            "concept_id": q.get("concept_id"),
                            "relation_type": q.get("type")
                        }
                        user_states[user_id] = States.WAITING_ANSWER
                        send(vk, peer_id, f"*Вопрос {current_num}/{total}: {q['text']}*\n\nВыберите вариант:", options_keyboard(q["options"]))
                        continue

                    # Статистика
                    if norm_text == "статистика":
                        resp = safe_get(f"{BACKEND_URL}/student/{user_id}/stats")
                        if resp and resp.status_code == 200:
                            s = resp.json()
                            msg = (f"📊 *Статистика*\nИмя: {s['name']}\nПопыток: {s['total_attempts']}\n"
                                   f"Точность: {s['accuracy']:.2%}\nScore: {s['overall_score']:.2f}")
                            send(vk, peer_id, msg, main_keyboard())
                        else:
                            send(vk, peer_id, "❌ Ошибка статистики.", main_keyboard())
                        continue

                    # Пробелы
                    if norm_text == "пробелы":
                        resp = safe_get(f"{BACKEND_URL}/student/{user_id}/gaps")
                        if resp and resp.status_code == 200:
                            gaps = resp.json().get("gaps", [])
                            if gaps:
                                gaps_russian = [SECTION_NAMES.get(g, g) for g in gaps]
                                # gaps – это ID разделов, можно показать их названия
                                send(vk, peer_id, "⚠️ Пробелы:\n" + "\n".join(f"• {g}" for g in gaps_russian), main_keyboard())
                            else:    
                                send(vk, peer_id, "🎉 Пробелов нет! Вы молодец.", main_keyboard())
                        else:
                            send(vk, peer_id, "❌ Ошибка пробелов.", main_keyboard())
                        continue

                    # Если ничего не подошло
                    send(vk, peer_id, "Используйте кнопки меню.", main_keyboard())
                    continue

                # --- Ожидание ответа на вопрос ---
                if state == States.WAITING_ANSWER:
                    qd = user_data.get(user_id)
                    if not qd:
                        send(vk, peer_id, "Сессия истекла. Начните заново.", main_keyboard())
                        user_states[user_id] = States.MAIN
                        continue

                    # --- Обработка жалобы ---
                    if text == "❌ Вопрос некорректный":
                        q = qd["current_question"]
                        payload = {
                            "vk_id": user_id,
                            "question_id": q.get("id"),
                            "question_text": q.get("text"),
                            "student_answer": qd.get("student_answer", "ЖАЛОБА"),
                            "correct_answer": q.get("correct_answer"),
                            "concept_id": qd.get("concept_id") or qd.get("concept"),
                            "question_type": qd.get("relation_type") or q.get("type"),
                            "target_concept_id": q.get("target_concept_id")
                        }
                        print(f"DEBUG: Sending complaint: {payload}")
                        resp = safe_post(f"{BACKEND_URL}/complaint", json=payload)
                        if resp:
                            print(f"DEBUG: Complaint response status {resp.status_code}, text: {resp.text}")
                            if resp.status_code == 200:
                                send(vk, peer_id, "📝 Спасибо! Ваша жалоба отправлена преподавателю.")
                            else:
                                send(vk, peer_id, f"❌ Не удалось отправить жалобу (ошибка {resp.status_code}).")
                        else:
                            send(vk, peer_id, "❌ Не удалось отправить жалобу. Нет ответа от сервера.")
                        
                        # Переходим к следующему вопросу без засчитывания
                        next_resp = safe_get(f"{BACKEND_URL}/next_question/{user_id}")
                        if not next_resp or next_resp.status_code != 200:
                            send(vk, peer_id, "❌ Ошибка получения следующего вопроса.", main_keyboard())
                            user_states[user_id] = States.MAIN
                            user_data.pop(user_id, None)
                            continue
                        data = next_resp.json()
                        if "error" in data:
                            send(vk, peer_id, f"Тест завершён. {data['error']}", main_keyboard())
                            user_states[user_id] = States.MAIN
                            user_data.pop(user_id, None)
                            continue
                        q_new = data["question"]
                        current_num = data.get("current", 1)
                        total = data.get("total", 10)
                        if not q_new.get("options"):
                            send(vk, peer_id, "❌ Нет вариантов ответа для следующего вопроса.", main_keyboard())
                            user_states[user_id] = States.MAIN
                            user_data.pop(user_id, None)
                            continue
                        user_data[user_id] = {
                            "current_question": q_new,
                            "start_time": time.time(),
                            "question_num": current_num,
                            "total_questions": total,
                            "correct_answer": q_new.get("correct_answer"),
                            "concept": q_new.get("concept"),
                            "concept_id": q_new.get("concept_id"),
                            "relation_type": q_new.get("type")
                        }
                        send(vk, peer_id, f"*Вопрос {current_num}/{total}: {q_new['text']}*\n\nВыберите вариант:", options_keyboard(q_new["options"]))
                        continue

                    # --- Обычный ответ на вопрос ---
                    spent = time.time() - qd["start_time"]
                    payload = {
                        "vk_id": user_id,
                        "question_id": qd["current_question"]["id"],
                        "answer": text,
                        "time_spent": spent,
                        "correct_answer": qd["correct_answer"],
                        "concept": qd["concept"]
                    }
                    resp = safe_post(f"{BACKEND_URL}/attempt", json=payload)
                    if not resp or resp.status_code != 200:
                        send(vk, peer_id, "❌ Ошибка проверки ответа.", main_keyboard())
                        user_states[user_id] = States.MAIN
                        user_data.pop(user_id, None)
                        continue
                    r = resp.json()
                    if r["correct"]:
                        send(vk, peer_id, "✅ Правильно!")
                    else:
                        send(vk, peer_id, f"❌ Неправильно (правильный ответ: {r['correct_answer']})")

                    # --- Следующий вопрос ---
                    next_resp = safe_get(f"{BACKEND_URL}/next_question/{user_id}")
                    if not next_resp or next_resp.status_code != 200:
                        send(vk, peer_id, "❌ Ошибка получения следующего вопроса.", main_keyboard())
                        user_states[user_id] = States.MAIN
                        user_data.pop(user_id, None)
                        continue
                    data = next_resp.json()
                    if "error" in data:
                        send(vk, peer_id, f"Тест завершён. {data['error']}", main_keyboard())
                        user_states[user_id] = States.MAIN
                        user_data.pop(user_id, None)
                        continue
                    q_new = data["question"]
                    current_num = data.get("current", 1)
                    total = data.get("total", 10)
                    if not q_new.get("options"):
                        send(vk, peer_id, "❌ Нет вариантов ответа для следующего вопроса.", main_keyboard())
                        user_states[user_id] = States.MAIN
                        user_data.pop(user_id, None)
                        continue
                    user_data[user_id] = {
                        "current_question": q_new,
                        "start_time": time.time(),
                        "question_num": current_num,
                        "total_questions": total,
                        "correct_answer": q_new.get("correct_answer"),
                        "concept": q_new.get("concept"),
                        "concept_id": q_new.get("concept_id"),
                        "relation_type": q_new.get("type")
                    }
                    send(vk, peer_id, f"*Вопрос {current_num}/{total}: {q_new['text']}*\n\nВыберите вариант:", options_keyboard(q_new["options"]))

        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()