import asyncio
from aiogram import Bot, Dispatcher
from config import API_TOKEN, logger
from database import conn
from handlers import commands, callbacks, messages
from utils import reminder_worker

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(messages.router)

    await commands.setup_bot_commands(bot)
    asyncio.create_task(reminder_worker(bot))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        conn.close()

if __name__ == "__main__":
    asyncio.run(main())
