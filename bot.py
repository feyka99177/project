import asyncio
import logging
import sqlite3
from random import randint
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import BotCommand
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

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


class MyCallback(CallbackData, prefix="my"):
    action: str
    item_id: str


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


@dp.callback_query(F.data == "random_value")
async def send_random_value(callback: types.CallbackQuery):
    await callback.message.answer(str(randint(1, 10)))


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
    user_id = message.from_user.id
    await message.answer('Введите название списка')
    user_states[user_id] = {"action": "create_list"}


@dp.message(Command("add_to_list"))
async def handle_delete_object(message: types.Message, callback=None):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    await message.answer(
        "Выберите список:",
        reply_markup=create_keyboard(lists)
    )
    user_states[user_id] = {"action": "add_to_list"}
    await callback.message.delete()


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
async def show_lists(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)
    if not lists:
        await message.answer("🗑 Списки пусты!")
        return

    builder = InlineKeyboardBuilder()

    for index, item in enumerate(lists):
        builder.button(text=item, callback_data=f"list_{index}")

    builder.adjust(2)

    builder.row(types.InlineKeyboardButton(
        text="❌ Закрыть",
        callback_data="close"
    ))

    await message.answer(
        "📋 Ваши списки:",
        reply_markup=builder.as_markup()
    )
    user_states[user_id] = {"action": "show_lists"}


@dp.callback_query()
async def handle_button_click(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    lists = await get_user_lists(user_id)
    if data == "close":
        await callback.message.delete()
        await callback.answer("Клавиатура закрыта")
    elif data.startswith("list_"):
        index = int(data.split("_")[1])
        selected_list = lists[index]
        items = await get_list_items(user_id, lists[index])
        if not items:
            await callback.answer("🗑 Список пуст!")
            return

        await callback.message.edit_text(f"список: {selected_list}")
        for i in range(len(items)):
            builder = InlineKeyboardBuilder()
            builder.button(
                text='❌- удалить',
                callback_data=MyCallback(action="no", item_id=f"{selected_list}_{items[i]}").pack()
            )
            builder.button(
                text='✅- готово',
                callback_data=MyCallback(action="yes", item_id=f"{selected_list}_{items[i]}").pack()
            )
            builder.adjust(2)
            await callback.message.answer(text=f"элемент {i + 1} : {items[i]}", reply_markup=builder.as_markup())
        await callback.message.delete()
        await callback.answer("Клавиатура закрыта")


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

        elif state["action"] == "create_list":
            try:
                cursor.execute(
                    "SELECT 1 FROM lists WHERE user_id=? AND list_name=?",
                    (user_id, text.strip())
                )

                if cursor.fetchone():
                    await message.answer("⚠️ У вас уже есть список с таким именем!")
                    return

                cursor.execute(
                    "INSERT INTO lists (user_id, list_name, items) VALUES (?, ?, ?)",
                    (user_id, text.strip(), "")
                )
                conn.commit()
                await message.answer(f"✅ Список '{text}' создан!")

            except Exception as e:
                logger.error(f"Create list error: {e}")
                await message.answer("⚠️ Ошибка при создании списка")

        elif state["action"] == "add_to_list":
            user_states[user_id] = {"action": "add", "list_name": text}
            await message.answer('введите элемент')

        elif state["action"] == "add":
            list_name = state["list_name"]
            try:
                items = await get_list_items(user_id, list_name)
                items.append(text)

                cursor.execute(
                    "UPDATE lists SET items=? WHERE user_id=? AND list_name=?",
                    (','.join(items), user_id, list_name)
                )
                conn.commit()
                await message.answer(f"✅ Добавлено в '{list_name}': {text}")
            except Exception as e:
                logger.error(f"Add to list error: {e}")
                await message.answer("⚠️ Ошибка при добавлении элемента")

    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await message.answer(
            "⚠️ Ошибка обработки запроса",
            reply_markup=types.ReplyKeyboardRemove()
        )


async def start_bot():
    await setup_commands()


async def main():
    dp.startup.register(start_bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
