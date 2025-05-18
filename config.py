import logging

API_TOKEN = '7812084701:AAGjhN1eG3s-VDtyiosPZemWgre9lGwrGME'
DB_PATH = "lists.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицу с актуальной структурой
cursor.execute("""
CREATE TABLE IF NOT EXISTS lists (
    user_id INTEGER,
    list_name TEXT,
    items TEXT,
    shared_with TEXT DEFAULT '',
    reminders TEXT DEFAULT '',
    archived INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, list_name)
)""")

# Проверяем и добавляем недостающие колонки
cursor.execute("PRAGMA table_info(lists)")
existing_columns = [column[1].lower() for column in cursor.fetchall()]
required_columns = {
    'reminders': 'TEXT DEFAULT ""',
    'archived': 'INTEGER DEFAULT 0',
    'shared_with': 'TEXT DEFAULT ""'
}

for column, definition in required_columns.items():
    if column not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE lists ADD COLUMN {column} {definition}")
            logger.info(f"Added missing column: {column}")
        except sqlite3.OperationalError as e:
            logger.error(f"Error adding column {column}: {e}")

conn.commit()
