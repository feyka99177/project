import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Конфигурация бота
API_TOKEN = '7812084701:AAGjhN1eG3s-VDtyiosPZemWgre9lGwrGME'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
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

# Хранение состояний пользователей
user_states = {}


class ListCallback(CallbackData, prefix="list"):
    action: str
    list_name: str | None = None
    item: str | None = None


async def setup_bot_commands():
    commands = [
        BotCommand(command='/start', description='Главное меню'),
        BotCommand(command='/create_list', description='Создать список'),
        BotCommand(command='/add_to_list', description='Добавить элемент'),
        BotCommand(command='/show_lists', description='Показать списки'),
        BotCommand(command='/delete_list', description='Удалить список'),
        BotCommand(command='/delete_item', description='Удалить элемент'),
    ]
    await bot.set_my_commands(commands)


def create_reply_keyboard(items: list[str], adjust: int = 2):
    builder = ReplyKeyboardBuilder()
    for item in items:
        builder.add(types.KeyboardButton(text=item))
    builder.adjust(adjust)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def create_inline_keyboard(items: list[tuple[str, str]], adjust: int = 2):
    builder = InlineKeyboardBuilder()
    for text, callback_data in items:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(adjust)
    return builder.as_markup()


async def get_user_lists(user_id: int) -> list[str]:
    cursor.execute("SELECT list_name FROM lists WHERE user_id=?", (user_id,))
    return [row[0] for row in cursor.fetchall()]


async def get_list_items(user_id: int, list_name: str) -> list[str]:
    cursor.execute(
        "SELECT items FROM lists WHERE user_id=? AND list_name=?",
        (user_id, list_name)
    )
    result = cursor.fetchone()
    return result[0].split(',') if result and result[0] else []


async def save_list_items(user_id: int, list_name: str, items: list[str]):
    cursor.execute(
        "INSERT OR REPLACE INTO lists (user_id, list_name, items) VALUES (?, ?, ?)",
        (user_id, list_name, ','.join(items))
    )
    conn.commit()


async def delete_list(user_id: int, list_name: str):
    cursor.execute(
        "DELETE FROM lists WHERE user_id=? AND list_name=?",
        (user_id, list_name))
    conn.commit()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    help_text = (
        "Привет! Я бот для управления списками.\n"
        "Доступные команды:\n"
        "/create_list - создать список\n"
        "/add_to_list - добавить элемент\n"
        "/show_lists - показать списки\n"
        "/delete_list - удалить список\n"
        "/delete_item - удалить элемент"
    )
    await message.answer(help_text)


@dp.message(Command("create_list"))
async def cmd_create_list(message: types.Message):
    user_id = message.from_user.id
    await message.answer('Введите название списка')
    user_states[user_id] = {"action": "awaiting_list_name"}


@dp.message(Command("add_to_list"))
async def cmd_add_to_list(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("У вас нет списков. Сначала создайте список.")
        return

    await message.answer(
        "Выберите список:",
        reply_markup=create_reply_keyboard(lists)
    )
    user_states[user_id] = {"action": "selecting_list_for_add"}


@dp.message(Command("delete_list"))
async def cmd_delete_list(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("📭 Нет списков для удаления")
        return

    keyboard_buttons = [
        (list_name, ListCallback(action="confirm_delete", list_name=list_name).pack())
        for list_name in lists
    ]
    keyboard_buttons.append(("❌ Закрыть", ListCallback(action="close").pack()))

    await message.answer(
        "Выберите список для удаления:",
        reply_markup=create_inline_keyboard(keyboard_buttons, 2)
    )


@dp.message(Command("delete_item"))
async def cmd_delete_item(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("📭 Нет списков")
        return

    keyboard_buttons = [
        (list_name, ListCallback(action="select_list_for_deletion", list_name=list_name).pack())
        for list_name in lists
    ]
    keyboard_buttons.append(("❌ Закрыть", ListCallback(action="close").pack()))

    await message.answer(
        "Выберите список:",
        reply_markup=create_inline_keyboard(keyboard_buttons, 2)
    )


@dp.message(Command("show_lists"))
async def cmd_show_lists(message: types.Message):
    user_id = message.from_user.id
    lists = await get_user_lists(user_id)

    if not lists:
        await message.answer("🗑 Списки пусты!")
        return

    keyboard_buttons = [
        (list_name, ListCallback(action="view", list_name=list_name).pack())
        for list_name in lists
    ]
    keyboard_buttons.append(("❌ Закрыть", ListCallback(action="close").pack()))

    await message.answer(
        "📋 Ваши списки:",
        reply_markup=create_inline_keyboard(keyboard_buttons, 2)
    )


@dp.callback_query(ListCallback.filter(F.action == "view"))
async def view_list_items(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    list_name = callback_data.list_name
    items = await get_list_items(user_id, list_name)

    try:
        await callback.message.edit_text(f"📋 Список: {list_name}")
        for i, item in enumerate(items):
            builder = InlineKeyboardBuilder()
            builder.button(
                text='❌ Удалить',
                callback_data=ListCallback(
                    action="delete",
                    list_name=list_name,
                    item=item
                ).pack()
            )
            builder.button(
                text='✅ Готово',
                callback_data=ListCallback(
                    action="done",
                    list_name=list_name,
                    item=item
                ).pack()
            )
            builder.adjust(2)
            await callback.message.answer(
                f"Элемент {i + 1}: {item}",
                reply_markup=builder.as_markup()
            )
    except Exception as e:
        logger.error(f"Ошибка отображения списка: {e}")
    finally:
        await callback.answer()


@dp.callback_query(ListCallback.filter(F.action == "delete"))
async def delete_item_handler(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    list_name = callback_data.list_name
    item = callback_data.item

    items = await get_list_items(user_id, list_name)
    if item in items:
        items.remove(item)
        await save_list_items(user_id, list_name, items)
        try:
            await callback.message.edit_text(f"❌ Удалено: {item}")
        except Exception as e:
            logger.error(f"Ошибка редактирования: {e}")
        await callback.answer(f"Элемент удалён из '{list_name}'")
    else:
        await callback.answer("Элемент не найден")


@dp.callback_query(ListCallback.filter(F.action == "done"))
async def mark_item_done(callback: types.CallbackQuery, callback_data: ListCallback):
    try:
        await callback.message.edit_text(f"✅ Готово: {callback_data.item}")
    except Exception as e:
        logger.error(f"Ошибка отметки: {e}")
    await callback.answer()


@dp.callback_query(ListCallback.filter(F.action == "close"))
async def close_handler(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Ошибка закрытия: {e}")
    await callback.answer("Клавиатура закрыта")


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

    try:
        await callback.message.edit_text(
            f"Удалить список '{callback_data.list_name}'?",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка подтверждения: {e}")
    await callback.answer()


@dp.callback_query(ListCallback.filter(F.action == "execute_delete"))
async def execute_delete_list(callback: types.CallbackQuery, callback_data: ListCallback):
    await delete_list(callback.from_user.id, callback_data.list_name)
    try:
        await callback.message.edit_text(f"✅ Список '{callback_data.list_name}' удалён!")
    except Exception as e:
        logger.error(f"Ошибка удаления: {e}")
    await callback.answer()


@dp.callback_query(ListCallback.filter(F.action == "cancel_delete"))
async def cancel_delete_handler(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text("❌ Удаление отменено")
    except Exception as e:
        logger.error(f"Ошибка отмены: {e}")
    await callback.answer()


@dp.callback_query(ListCallback.filter(F.action == "select_list_for_deletion"))
async def select_items_for_deletion(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    items = await get_list_items(user_id, callback_data.list_name)

    keyboard_buttons = [
        (item, ListCallback(action="confirm_item_delete", list_name=callback_data.list_name, item=item).pack())
        for item in items
    ]
    keyboard_buttons.append(("❌ Закрыть", ListCallback(action="close").pack()))

    try:
        await callback.message.edit_text(
            f"Выберите элемент для удаления:",
            reply_markup=create_inline_keyboard(keyboard_buttons, 2)
        )
    except Exception as e:
        logger.error(f"Ошибка выбора элемента: {e}")
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

    try:
        await callback.message.edit_text(
            f"Удалить '{callback_data.item}'?",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка подтверждения: {e}")
    await callback.answer()


@dp.callback_query(ListCallback.filter(F.action == "execute_item_delete"))
async def execute_delete_item(callback: types.CallbackQuery, callback_data: ListCallback):
    user_id = callback.from_user.id
    items = await get_list_items(user_id, callback_data.list_name)

    if callback_data.item in items:
        items.remove(callback_data.item)
        await save_list_items(user_id, callback_data.list_name, items)
        try:
            await callback.message.edit_text(f"✅ Элемент удалён!")
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
    else:
        await callback.answer("Элемент не найден")
    await callback.answer()


@dp.callback_query()
async def unknown_callback(callback: types.CallbackQuery):
    try:
        data = ListCallback.unpack(callback.data)
        logger.warning(f"Необработанное действие: {data.action}")
        await callback.answer(f"⚠️ Действие '{data.action}' не реализовано")
    except ValueError:
        logger.warning(f"Неизвестный колбэк: {callback.data}")
        await callback.answer("⚠️ Неизвестная команда")


@dp.message(F.text)
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in user_states:
        if text in await get_user_lists(user_id):
            items = await get_list_items(user_id, text)
            response = f"📋 Список {text}:\n" + "\n".join(
                f"• {item}" for item in items) if items else f"📭 Список '{text}' пуст"
            await message.answer(response)
        return

    state = user_states[user_id]

    if state.get("action") == "awaiting_list_name":
        if not text:
            return await message.answer("Название не может быть пустым!")
        if text in await get_user_lists(user_id):
            return await message.answer("⚠️ Список уже существует!")

        await save_list_items(user_id, text, [])
        await message.answer(f"✅ Список '{text}' создан!")
        del user_states[user_id]

    elif state.get("action") == "selecting_list_for_add":
        if text not in await get_user_lists(user_id):
            return await message.answer("⚠️ Выберите список из кнопок!")

        user_states[user_id] = {
            "action": "awaiting_item_for_list",
            "selected_list": text
        }
        await message.answer(f"Введите элемент для списка '{text}':", reply_markup=types.ReplyKeyboardRemove())

    elif state.get("action") == "awaiting_item_for_list":
        list_name = state["selected_list"]
        items = await get_list_items(user_id, list_name)
        items.append(text)
        await save_list_items(user_id, list_name, items)
        await message.answer(f"✅ Добавлено в '{list_name}': {text}")
        del user_states[user_id]


async def on_startup():
    await setup_bot_commands()
    logger.info("Бот запущен")


async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
