from vk_api.keyboard import VkKeyboard, VkKeyboardColor

def main_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button("Тест", color=VkKeyboardColor.PRIMARY)
    kb.add_button("Статистика", color=VkKeyboardColor.SECONDARY)
    kb.add_button("Пробелы", color=VkKeyboardColor.NEGATIVE)
    return kb

def options_keyboard(options):
    """Клавиатура для вариантов ответа + кнопка жалобы."""
    kb = VkKeyboard(one_time=True)
    for opt in options:
        kb.add_button(opt, color=VkKeyboardColor.PRIMARY)
        kb.add_line()
    kb.add_button("❌ Вопрос некорректный", color=VkKeyboardColor.NEGATIVE)
    return kb