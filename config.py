import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DB_NAME = "todo_lists.db"
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    ITEMS_LIMIT = 50
    LOGS_FILE = "bot.log"
    DEFAULT_LIST_NAME = "Мой список"
