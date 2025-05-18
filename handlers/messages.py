from aiogram import Router, F
from aiogram.types import Message
from database import *
from keyboards import *
from config import logger

router = Router()

@dp.message(F.text)
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if user_id not in user_states:
        # Быстрый просмотр по названию списка
        if text in get_user_lists(user_id):
            items = get_list_items(user_id, text)
            response = f"📋 Список {text}:\n" + "\n".join(f"• {item}" for item in items) if items else f"Список '{text}' пуст."
            await message.answer(response)
        return
    state = user_states[user_id]
    # Создание списка
    if state.get("action") == "awaiting_list_name":
        if not text:
            return await message.answer("Название не может быть пустым!")
        if text in get_user_lists(user_id):
            return await message.answer("Список уже существует!")
        create_list(user_id, text)
        await message.answer(f"Список '{text}' создан!")
        del user_states[user_id]
    # Добавление элемента
    elif state.get("action") == "awaiting_item_for_list":
        list_name = state["selected_list"]
        items = get_list_items(user_id, list_name)
        if text in items:
            await message.answer("Такой элемент уже есть в списке.")
        else:
            items.append(text)
            save_list_items(user_id, list_name, items)
            await message.answer(f"Добавлено в '{list_name}': {text}")
        del user_states[user_id]
    # Поиск
    elif state.get("action") == "awaiting_search_query":
        found = search_items(user_id, text)
        if found:
            await message.answer("Найдено:\n" + "\n".join(found))
        else:
            await message.answer("Ничего не найдено.")
        del user_states[user_id]
    # Совместный доступ
    elif state.get("action") == "awaiting_share_id":
        list_name = state["list_name"]
        try:
            target_id = int(text)
            share_list(user_id, list_name, target_id)
            await message.answer(f"Список '{list_name}' теперь доступен пользователю {target_id}!")
        except Exception:
            await message.answer("Некорректный ID пользователя.")
        del user_states[user_id]
    # Напоминание
    elif state.get("action") == "awaiting_reminder_time":
        list_name = state["list_name"]
        try:
            hour, minute = map(int, text.split(":"))
            now = datetime.now()
            remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if remind_time < now:
                remind_time += timedelta(days=1)
            set_reminder(user_id, list_name, remind_time.strftime("%Y-%m-%d %H:%M"))
            await message.answer(f"Напоминание для списка '{list_name}' установлено на {remind_time.strftime('%d.%m %H:%M')}")
        except Exception:
            await message.answer("Некорректный формат времени. Пример: 09:30")
        del user_states[user_id]
