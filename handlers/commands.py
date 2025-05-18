from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from database import *
from keyboards import *
from config import logger

router = Router()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await setup_bot_commands()
    await message.answer(
        "👋 Привет! Я бот для управления списками.\n"
        "Используй команды из меню или напиши название списка, чтобы посмотреть его содержимое!"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "ℹ️ Доступные команды:\n"
        "/create_list - Создать новый список\n"
        "/add_to_list - Добавить элемент в список\n"
        "/show_lists - Показать все списки\n"
        "/delete_list - Удалить список\n"
        "/delete_item - Удалить элемент из списка\n"
        "/search - Поиск по всем спискам\n"
        "/export - Экспорт списка в текстовом формате\n"
        "/share - Поделиться списком с другим пользователем\n"
        "/remind - Установить напоминание для списка\n"
        "/archive - Архивировать список\n"
        "/unarchive - Восстановить список из архива\n"
        "/help - Показать это сообщение"
    )
    await message.answer(help_text)

@dp.message(Command("create_list"))
async def cmd_create_list(message: types.Message):
    user_id = message.from_user.id
    await message.answer('Введите название нового списка:')
    user_states[user_id] = {"action": "awaiting_list_name"}

@dp.message(Command("add_to_list"))
async def cmd_add_to_list(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("У вас нет списков. Сначала создайте список.")
        return
    await message.answer("Выберите список:", reply_markup=lists_keyboard(lists, "add_to_selected_list"))

@dp.message(Command("delete_list"))
async def cmd_delete_list(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Нет списков для удаления.")
        return
    await message.answer("Выберите список для удаления:", reply_markup=lists_keyboard(lists, "confirm_delete"))

@dp.message(Command("delete_item"))
async def cmd_delete_item(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Нет списков.")
        return
    await message.answer("Выберите список для удаления элемента:", reply_markup=lists_keyboard(lists, "select_list_for_deletion"))

@dp.message(Command("show_lists"))
async def cmd_show_lists(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Списки пусты!")
        return
    await message.answer("Ваши списки:", reply_markup=lists_keyboard(lists, "view"))

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    user_id = message.from_user.id
    await message.answer("Введите поисковый запрос по всем вашим спискам:")
    user_states[user_id] = {"action": "awaiting_search_query"}

@dp.message(Command("export"))
async def cmd_export(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Нет списков для экспорта.")
        return
    await message.answer("Выберите список для экспорта:", reply_markup=lists_keyboard(lists, "export_list"))

@dp.message(Command("share"))
async def cmd_share(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Нет списков для совместного доступа.")
        return
    await message.answer("Выберите список для совместного доступа:", reply_markup=lists_keyboard(lists, "share_list"))

@dp.message(Command("remind"))
async def cmd_remind(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Нет списков для напоминаний.")
        return
    await message.answer("Выберите список для напоминания:", reply_markup=lists_keyboard(lists, "set_reminder"))

@dp.message(Command("archive"))
async def cmd_archive(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id)
    if not lists:
        await message.answer("Нет списков для архивирования.")
        return
    await message.answer("Выберите список для архивирования:", reply_markup=lists_keyboard(lists, "archive_list"))

@dp.message(Command("unarchive"))
async def cmd_unarchive(message: types.Message):
    user_id = message.from_user.id
    lists = get_user_lists(user_id, include_archived=True)
    archived_lists = []
    for name in lists:
        cursor.execute("SELECT archived FROM lists WHERE user_id=? AND list_name=?", (user_id, name))
        if cursor.fetchone()[0] == 1:
            archived_lists.append(name)
    if not archived_lists:
        await message.answer("Нет архивированных списков.")
        return
    await message.answer("Выберите список для восстановления:", reply_markup=lists_keyboard(archived_lists, "unarchive_list"))

# ... (остальные обработчики команд аналогично предыдущей версии)

@dp.callback_query(ListCallback.filter(F.action == "view"))
async def view_list_items(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    list_name = callback_data.list_name
    items = get_list_items(user_id, list_name)

    if not items:
        await callback.message.edit_text(
            f"Список '{list_name}' пуст.",
            reply_markup=lists_keyboard(get_user_lists(user_id), "view")
        )
        return

    items_text = "\n".join(f"• {item}" for item in items)
    await callback.message.edit_text(
        f"📋 Список: {list_name}\n{items_text}",
        reply_markup=items_keyboard(list_name, items)
    )


@dp.callback_query(ListCallback.filter(F.action == "add_to_selected_list"))
async def add_to_selected_list_handler(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    list_name = callback_data.list_name
    user_states[user_id] = {"action": "awaiting_item_for_list", "selected_list": list_name}
    await callback.message.answer(f"Введите новый элемент для списка '{list_name}':")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "confirm_delete"))
async def confirm_delete_list(callback: types.CallbackQuery, callback_data: ListCallback):
    builder = InlineKeyboardBuilder()
    builder.button(
        text='✅ Да',
        callback_data=ListCallback(action="execute_delete", list_name=callback_data.list_name).pack()
    )
    builder.button(
        text='❌ Нет',
        callback_data=ListCallback(action="cancel_delete").pack()
    )
    await callback.message.edit_text(
        f"Удалить список '{callback_data.list_name}'?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "execute_delete"))
async def execute_delete_list(callback: types.CallbackQuery, callback_data: ListCallback):
    delete_list(callback.from_user.id, callback_data.list_name)
    await callback.message.edit_text(f"Список '{callback_data.list_name}' удалён!")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "cancel_delete"))
async def cancel_delete_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "select_list_for_deletion"))
async def select_items_for_deletion(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    items = get_list_items(user_id, callback_data.list_name)
    if not items:
        await callback.message.edit_text("Список пуст.")
        await callback.answer()
        return
    await callback.message.edit_text(
        f"Выберите элемент для удаления из '{callback_data.list_name}':",
        reply_markup=items_keyboard(callback_data.list_name, items, for_delete=True)
    )
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "confirm_item_delete"))
async def confirm_delete_item(callback: types.CallbackQuery, callback_data: ListCallback):
    builder = InlineKeyboardBuilder()
    builder.button(
        text='✅ Да',
        callback_data=ListCallback(
            action="execute_item_delete",
            list_name=callback_data.list_name,
            item=callback_data.item
        ).pack()
    )
    builder.button(
        text='❌ Нет',
        callback_data=ListCallback(action="cancel_delete").pack()
    )
    await callback.message.edit_text(
        f"Удалить '{callback_data.item}' из '{callback_data.list_name}'?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "execute_item_delete"))
async def execute_delete_item(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    items = get_list_items(user_id, callback_data.list_name)
    if callback_data.item in items:
        items.remove(callback_data.item)
        save_list_items(user_id, callback_data.list_name, items)
        await callback.message.edit_text(f"Элемент '{callback_data.item}' удалён!")
    else:
        await callback.message.edit_text("Элемент не найден.")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "done"))
async def mark_item_done(callback: types.CallbackQuery, callback_data: ListCallback):
    await callback.message.edit_text(f"✅ Готово: {callback_data.item}")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "close"))
async def close_handler(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Клавиатура закрыта")

@dp.callback_query(ListCallback.filter(F.action == "export_list"))
async def export_list_callback(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    text = export_list(user_id, callback_data.list_name)
    await callback.message.answer_document(
        types.BufferedInputFile(text.encode(), filename=f"{callback_data.list_name}.txt"),
        caption=f"Экспорт списка '{callback_data.list_name}'"
    )
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "share_list"))
async def share_list_callback(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    user_states[user_id] = {"action": "awaiting_share_id", "list_name": callback_data.list_name}
    await callback.message.answer(
        "Введите ID пользователя Telegram, которому хотите дать доступ к списку.\n"
        "ID можно узнать у пользователя через @userinfobot"
    )
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "set_reminder"))
async def set_reminder_callback(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    user_states[user_id] = {"action": "awaiting_reminder_time", "list_name": callback_data.list_name}
    await callback.message.answer(
        "Введите время напоминания в формате ЧЧ:ММ (например, 09:30):"
    )
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "archive_list"))
async def archive_list_callback(callback: types.CallbackQuery, callback_data: ListCallback):
    archive_list(callback.from_user.id, callback_data.list_name)
    await callback.message.edit_text(f"Список '{callback_data.list_name}' архивирован!")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "unarchive_list"))
async def unarchive_list_callback(callback: types.CallbackQuery, callback_data: ListCallback):
    unarchive_list(callback.from_user.id, callback_data.list_name)
    await callback.message.edit_text(f"Список '{callback_data.list_name}' восстановлен из архива!")
    await callback.answer()

@dp.callback_query(ListCallback.filter(F.action == "back_to_lists"))
async def back_to_lists_callback(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    lists = get_user_lists(user_id)
    await callback.message.edit_text("Ваши списки:", reply_markup=lists_keyboard(lists, "view"))
    await callback.answer()

# --- Обработка текстовых сообщений (состояния и быстрые действия) ---
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
