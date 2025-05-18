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


