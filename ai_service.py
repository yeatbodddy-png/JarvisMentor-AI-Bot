from config import client, MODES, user_histories, user_modes

def get_working_models():
    """Автоматически собирает актуальные текстовые модели Groq и отсеивает лишние."""
    excluded = [
        "whisper", "guard", "tts", "audio", "vision",
        "embed", "rerank", "allam", "playai", "orpheus"
    ]
    try:
        all_models = client.models.list().data
        valid = [
            m.id for m in all_models
            if not any(bad in m.id.lower() for bad in excluded)
        ]

        def priority(name):
            low = name.lower()
            if "llama" in low and any(tag in low for tag in ["70b", "90b", "405b", "maverick", "scout"]):
                return 0
            if "qwen" in low or "deepseek" in low:
                return 1
            if "llama" in low:
                return 2
            return 3

        valid.sort(key=priority)
        return valid
    except Exception as e:
        print(f"⚠️ Не удалось получить список моделей: {e}")
        return []

MODELS = get_working_models()

def ask_ai(chat_id, user_text):
    """Отправляет текстовый запрос в Groq с учетом истории конкретного режима."""
    if not MODELS:
        return "Не удалось загрузить список моделей Groq. Проверь интернет или API_KEY!"

    current_mode = user_modes.get(chat_id, "🤝 Свой бро")
    system_prompt = MODES[current_mode]

    if chat_id not in user_histories:
        user_histories[chat_id] = {}
    if current_mode not in user_histories[chat_id]:
        user_histories[chat_id][current_mode] = []

    history = user_histories[chat_id][current_mode]

    messages_payload = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_text}]
    )

    last_error = None
    for model_name in MODELS:
        try:
            # 1. Сам запрос к API с текущей моделькой из цикла
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages_payload,
                temperature=0.7,
                max_tokens=1500
            )
            reply_text = completion.choices[0].message.content

            # 2. Обновление истории чата
            updated_history = history + [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": reply_text}
            ]
            user_histories[chat_id][current_mode] = updated_history[-20:]

            # 3. Если всё успешно — возвращаем ответ
            return reply_text

        except Exception as e:
            print(f"⚠️ Модель {model_name} сбоит, пробуем следующую... Ошибка: {e}")
            last_error = e
            continue  # Ошибку поймали, цикл идет к следующей модели

    # 👈 Этот блок сработает ТОЛЬКО если цикл закончился, а все модели упали:
    print(f"❌ Критическая ошибка: все модели Groq недоступны. Последняя ошибка: {last_error}")
    return "Что-то нейросеть сейчас подвисла. Попробуй написать ещё раз через пару секунд!"

def ask_ai_with_vision(chat_id, user_prompt, base64_image):
    """Функция для отправки текста и картинки в мультимодальную модель Groq"""
    try:
        current_mode = user_modes.get(chat_id, "🤝 Свой бро")
        system_prompt = MODES[current_mode]

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",  # Актуальная vision-модель
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка при обращении к мультимодальной модели: {e}"