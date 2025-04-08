import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram.utils.keyboard import ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '7812084701:AAGjhN1eG3s-VDtyiosPZemWgre9lGwrGME'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Database setup
conn = sqlite3.connect("lists.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS lists (
        user_id INTEGER,
        list_name TEXT,
        items TEXT,
        UNIQUE(user_id, list_name))
""")
conn.commit()

user_states = {}

async def setup_commands():
    await bot.set_my_commands([
        BotCommand(command='/add_to_list', description='Пополнить список'),
        BotCommand(command='/create_list', description='Создать список'),
        BotCommand(command='/delete_list', description='Удалить список'),
        BotCommand(command='/delete_object', description='Удалить объект'),
        BotCommand(command='/show_lists', description='Показать списки'),
    ])

def create_keyboard(items, adjust: int = 2):
    builder = ReplyKeyboardBuilder()
    for item in items:
        builder.add(types.KeyboardButton(text=item))
    builder.adjust(adjust)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def get_user_lists(user_id: int):
    cursor.execute("SELECT list_name FROM lists WHERE user_id=?", (user_id,))
    return [row[0] for row in cursor.fetchall()]

async def get_list_items(user_id: int, list_name: str):
    cursor.execute(
        "SELECT items FROM lists WHERE user_id=? AND list_name=?",
        (user_id, list_name)
    )
    result = cursor.fetchone()
    return result[0].split(',') if result and result[0] else []

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    help_text = (
        "Привет! Я бот для управления списками.\n"
        "Доступные команды:\n"
        "/create_list <название> - создать список\n"
        "/add_to_list <название> <элемент> - добавить элемент\n"
        "/show_lists - показать все списки\n"
        "/delete_list - удалить список\n"
        "/delete_object - удалить элемент"
    )
    await message.answer(help_text)

@dp.message(Command("create_list"))
async def handle_create_list(message: types.Message):
    try:
        _, list_name = message.text.split(maxsplit=1)
        list_name = list_name.strip()
    except ValueError:
        await message.answer("❌ Укажите название списка: /create_list <название>")
        return

    user_id = message.from_user.id

    if not list_name.isalnum():
        await message.answer("❌ Название должно содержать только буквы и цифры")
        return

    try:
        cursor.execute(
            "INSERT INTO lists (user_id, list_name, items) VALUES (?, ?, ?)",
            (user_id, list_name, "")
        )
        conn.commit()
        await message.answer(f"✅ Список '{list_name}' создан!")
    except sqlite3.IntegrityError:
        await message.answer(f"❌ Список '{list_name}' уже существует!")
    except Exception as e:
        logger.error(f"Create list error: {e}")
        await message.answer("⚠️ Ошибка при создании списка")

@dp.message(Command("add_to_list"))
async def handle_add_to_list(message: types.Message):
    try:
        _, list_name, item = message.text.split(maxsplit=2)
        list_name = list_name.strip()
        item = item.strip()
    except ValueError:
        await message.answer("❌ Формат: /add_to_list <название> <элемент>")
        return

    user_id = message.from_user.id

    try:
        items = await get_list_items(user_id, list_name)
        items.append(item)

        cursor.execute(
            "UPDATE lists SET items=? WHERE user_id=? AND list_name=?",
            (','.join(items), user_id, list_name)
        )
        conn.commit()
        await message.answer(f"✅ Добавлено в '{list_name}': {item}")
    except Exception as e:
        logger.error(f"Add to list error: {e}")
        await message.answer("⚠️ Ошибка при добавлении элемента")

@dp.message(Command("delete_list"))
async def handle_delete_list(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("📭 Нет списков для удаления")
        return

    await message.answer(
        "Выберите список для удаления:",
        reply_markup=create_keyboard(lists)
    )
    user_states[user_id] = {"action": "delete_list"}

@dp.message(Command("delete_object"))
async def handle_delete_object(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("📭 Нет списков")
        return

    await message.answer(
        "Выберите список:",
        reply_markup=create_keyboard(lists)
    )
    user_states[user_id] = {"action": "select_list_for_deletion"}

@dp.message(Command("show_lists"))
async def handle_show_lists(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("📭 У вас нет списков")
        return

    await message.answer(
        "📋 Ваши списки:\n" + "\n".join([f"• {lst}" for lst in lists]),
        reply_markup=create_keyboard(lists)
    )
    user_states[user_id] = {"action": "show_list_selection"}

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in user_states:
        return

    state = user_states.pop(user_id)

    try:
        if state["action"] == "delete_list":
            cursor.execute(
                "DELETE FROM lists WHERE user_id=? AND list_name=?",
                (user_id, text)
            )
            conn.commit()
            await message.answer(
                f"✅ Список '{text}' удалён!",
                reply_markup=types.ReplyKeyboardRemove()
            )

        elif state["action"] == "select_list_for_deletion":
            items = await get_list_items(user_id, text)

            if not items:
                await message.answer(
                    "❌ Список пуст",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return

            await message.answer(
                f"Элементы списка '{text}':",
                reply_markup=create_keyboard(items)
            )
            user_states[user_id] = {"action": "delete_item", "list_name": text}

        elif state["action"] == "delete_item":
            list_name = state["list_name"]
            items = await get_list_items(user_id, list_name)

            if text not in items:
                await message.answer(
                    "❌ Элемент не найден",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return

            items.remove(text)
            cursor.execute(
                "UPDATE lists SET items=? WHERE user_id=? AND list_name=?",
                (','.join(items), user_id, list_name)
            )
            conn.commit()
            await message.answer(
                f"✅ Элемент '{text}' удалён из '{list_name}'!",
                reply_markup=types.ReplyKeyboardRemove()
            )

        elif state["action"] == "show_list_selection":
            items = await get_list_items(user_id, text)
            response = (
                    f"📋 Содержимое списка '{text}':\n" +
                    "\n".join([f"• {item}" for item in items] if items else "Список пуст")
            )
            await message.answer(response, reply_markup=types.ReplyKeyboardRemove())

    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await message.answer(
            "⚠️ Ошибка обработки запроса",
            reply_markup=types.ReplyKeyboardRemove()
        )

# Обработчик /menu (Reply-клавиатура)
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="Кнопка 1")
    builder.button(text="Кнопка 2")
    builder.button(text="Геолокация", request_location=True)
    builder.adjust(2)
    await message.answer("Выберите действие:", reply_markup=builder.as_markup(resize_keyboard=True))

async def start_bot():
    await setup_commands()

async def main():
    #await dp.start_polling(bot)
    dp.startup.register(start_bot)

    #await dp.start_polling(bot, on_startup=set_bot_commands)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
