from aiogram import Router, types
from database import *
from keyboards import *
from config import logger

router = Router()

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
