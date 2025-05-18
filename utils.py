import asyncio
from datetime import datetime
from database import get_reminders, set_reminder
from config import logger

async def reminder_worker():
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for user_id, list_name, remind_time in get_reminders():
            if remind_time == now:
                try:
                    await bot.send_message(
                        user_id,
                        f"⏰ Напоминание о списке '{list_name}'!"
                    )
                    set_reminder(user_id, list_name, "")
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания: {e}")
        await asyncio.sleep(60)
