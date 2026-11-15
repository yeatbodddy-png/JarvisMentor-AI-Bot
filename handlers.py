import os
import tempfile
import base64
import docx
from config import bot, client, MODES, user_histories, user_modes
from ai_service import ask_ai, ask_ai_with_vision
from utils import get_keyboard, send_long_message, send_smart_reply

def check_mode_selected(message):
    """Проверяет, выбрал ли пользователь режим. Если нет — предупреждает и возвращает False."""
    chat_id = message.chat.id
    if chat_id not in user_modes or user_modes[chat_id] is None:
        bot.reply_to(
            message,
            "🛑 Стоп-слово! Сначала выбери мой режим общения с помощью кнопок на клавиатуре снизу 👇",
            reply_markup=get_keyboard()
        )
        return False
    return True


@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id

    # Сбрасываем прошлый режим при новом старте, чтобы заставить выбрать заново
    user_modes[chat_id] = None

    bot.send_chat_action(chat_id, "typing")

    greeting_prompt = (
        "Поприветствуй меня в начале диалога как JarvisMentor — твой личный ИИ-ментор и компаньон. "
        "Начни тепло, живо и уютно (в духе доверительного разговора), но обязательно дай понять свою суть. "
        "Мягко и органично намекни на выбор: хочешь просто пообщаться на своём вайбе, разобрать "
        "код и бэкенд на уровне 'Кодера' или углубиться в чистую архитектуру в режиме 'Эксперта'? "
        "Без сухих шаблонов, каждый раз по-новому, но с чётким техническим позиционированием."
    )

    try:
        reply = ask_ai_chat_preview(chat_id, greeting_prompt) if 'ask_ai_chat_preview' in globals() else ask_ai(chat_id,
                                                                                                                greeting_prompt)
        bot.reply_to(message, reply, reply_markup=get_keyboard())
    except Exception as e:
        print(f"⚠️ Ошибка приветствия от ИИ: {e}")
        bot.reply_to(
            message,
            "Привет! Я твой личный ИИ-ментор JarvisMentor. Выбери режим общения кнопками ниже 👇",
            reply_markup=get_keyboard()
        )

@bot.message_handler(commands=["reset"])
def handle_reset(message):
    chat_id = message.chat.id
    current_mode = user_modes.get(chat_id, "🤝 Свой бро")

    if chat_id in user_histories and current_mode in user_histories[chat_id]:
        user_histories[chat_id][current_mode] = []

    bot.reply_to(
        message,
        f"🧹 Память режима *{current_mode}* очищена! Начинаем разговор с чистого листа.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text in MODES)
def handle_mode_switch(message):
    chat_id = message.chat.id
    user_modes[chat_id] = message.text
    bot.reply_to(message, f"Режим переключён на: *{message.text}*!", parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not check_mode_selected(message):
        return
    chat_id = message.chat.id
    caption = message.caption if message.caption else "Проанализируй этот документ/файл и помоги разобраться."
    file_name = message.document.file_name.lower()

    try:
        bot.send_chat_action(chat_id, "typing")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_content = ""

        if file_name.endswith('.docx'):
            temp_path = "temp_doc.docx"
            with open(temp_path, "wb") as f:
                f.write(downloaded_file)

            doc = docx.Document(temp_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            file_content = "\n".join(paragraphs)
        else:
            file_content = downloaded_file.decode('utf-8')

        if len(file_content) > 15000:
            file_content = file_content[:15000] + "\n\n[... файл слишком длинный, показана первая часть ...]"

        prompt = (
            f"Пользователь прикрепил документ: {message.document.file_name}\n"
            f"Задача: {caption}\n\n"
            f"Содержимое документа:\n```\n{file_content}\n```"
        )

        reply = ask_ai(chat_id, prompt)
        send_long_message(message, reply)

    except UnicodeDecodeError:
        bot.reply_to(
            message,
            "⚠️ Этот файл имеет бинарную структуру, которую я пока не могу прочитать как текст. "
            "Пришли текстовый файл, код или документ Word (.docx)."
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Произошла ошибка при обработке файла: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not check_mode_selected(message):
        return
    chat_id = message.chat.id
    caption = message.caption if message.caption else "Проанализируй этот скриншот, объясни суть или найди ошибку в коде."

    try:
        bot.send_chat_action(chat_id, "typing")

        photo_file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_photo = bot.download_file(photo_file_info.file_path)

        base64_image = base64.b64encode(downloaded_photo).decode('utf-8')

        reply = ask_ai_with_vision(chat_id, caption, base64_image)
        send_long_message(message, reply)

    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось обработать изображение: {e}")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    if not check_mode_selected(message):
        return
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, "typing")
    temp_path = None

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
            temp_audio.write(downloaded_file)
            temp_path = temp_audio.name

        with open(temp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(temp_path), audio_file.read()),
                model="whisper-large-v3-turbo",
                language="ru"
            )

        recognized_text = transcription.text.strip()
        if not recognized_text:
            bot.reply_to(message, "Не удалось разобрать слова в голосовом 🤷‍♂️")
            return

        bot.reply_to(message, f"🎤 _Ты сказал:_ «{recognized_text}»", parse_mode="Markdown")
        bot.send_chat_action(chat_id, "typing")

        reply = ask_ai(chat_id, recognized_text)
        send_smart_reply(message, reply)

    except Exception as e:
        print(f"❌ Ошибка голосового: {e}")
        bot.reply_to(message, "Не получилось обработать голосовое сообщение.")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_text(message):
    if not check_mode_selected(message):
        return
    bot.send_chat_action(message.chat.id, "typing")
    reply = ask_ai(message.chat.id, message.text)
    send_smart_reply(message, reply)