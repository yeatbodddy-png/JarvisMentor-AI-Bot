from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from config import bot
# utils.py

def make_py_file(code_text: str, filename: str = "script.py"):
  """Конвертирует строку с кодом в объект для отправки через telebot"""
  file_bytes = code_text.encode("utf-8")
  # telebot принимает файлы из памяти в виде кортежа (имя_файла, байты)
  return (filename, file_bytes)

def get_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(
        KeyboardButton("🤝 Свой бро"),
        KeyboardButton("💻 Кодер"),
        KeyboardButton("🧠 Эксперт")
    )
    return markup

def send_long_message(message, text):
    """Разбивает длинный текст на части по 4000 символов и отправляет по очереди"""
    max_length = 4000
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        if i == 0:
            bot.reply_to(message, chunk)
        else:
            bot.send_message(message.chat.id, chunk)

def send_smart_reply(message, text):
    """Отправляет ответ с разметкой; если Telegram ругается на символы — шлёт обычным текстом."""
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        try:
            bot.reply_to(message, chunk, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, chunk)