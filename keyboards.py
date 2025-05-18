from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from typing import Optional

class ListCallback(CallbackData, prefix="list"):
    action: str
    list_name: Optional[str] = None
    item: Optional[str] = None

def lists_keyboard(lists: list, action_prefix: str):
    builder = InlineKeyboardBuilder()
    for name in lists:
        builder.button(
            text=name,
            callback_data=ListCallback(action=action_prefix, list_name=name).pack()
        )
    builder.button(text="❌ Закрыть", callback_data=ListCallback(action="close").pack())
    builder.adjust(2)
    return builder.as_markup()

def items_keyboard(list_name: str, items: List[str], for_delete=False):
    builder = InlineKeyboardBuilder()
    for item in items:
        action = "confirm_item_delete" if for_delete else "done"
        builder.button(
            text=f"❌ {item}" if for_delete else f"✅ {item}",
            callback_data=ListCallback(
                action=action,
                list_name=list_name,
                item=item
            ).pack()
        )
    builder.button(text="⬅️ Назад", callback_data=ListCallback(action="back_to_lists").pack())
    builder.button(text="❌ Закрыть", callback_data=ListCallback(action="close").pack())
    builder.adjust(2)
    return builder.as_markup()
