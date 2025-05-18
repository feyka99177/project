import sqlite3
import logging
from typing import List, Dict, Any, Optional
from config import Config


logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
        self._init_db()
        self._migrate()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    user_id INTEGER NOT NULL,
                    list_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    items TEXT,
                    is_archived BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (user_id, list_name)
            )""")

    def _migrate(self):
        try:
            with self.conn:
                self.conn.execute("ALTER TABLE lists ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
        except sqlite3.OperationalError:
            pass

    def create_list(self, user_id: int, list_name: str) -> bool:
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO lists (user_id, list_name, items) VALUES (?, ?, '')",
                    (user_id, list_name)
                )
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"List {list_name} already exists for user {user_id}")
            return False

    def add_item(self, user_id: int, list_name: str, item: str) -> bool:
        items = self.get_items(user_id, list_name)
        if len(items) >= Config.ITEMS_LIMIT:
            return False
        items.append(item)
        return self._update_items(user_id, list_name, items)

    def delete_item(self, user_id: int, list_name: str, item_index: int) -> bool:
        items = self.get_items(user_id, list_name)
        if 0 <= item_index < len(items):
            del items[item_index]
            return self._update_items(user_id, list_name, items)
        return False

    def get_lists(self, user_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
        query = "SELECT list_name, created_at, is_archived FROM lists WHERE user_id = ?"
        params = (user_id,)
        if not include_archived:
            query += " AND is_archived = FALSE"
        
        cursor = self.conn.execute(query, params)
        return [
            {
                "name": row[0],
                "created_at": row[1],
                "is_archived": bool(row[2])
            }
            for row in cursor.fetchall()
        ]

    def get_items(self, user_id: int, list_name: str) -> List[str]:
        cursor = self.conn.execute(
            "SELECT items FROM lists WHERE user_id = ? AND list_name = ?",
            (user_id, list_name)
        )
        result = cursor.fetchone()
        return result[0].split(',') if result and result[0] else []

    def _update_items(self, user_id: int, list_name: str, items: List[str]) -> bool:
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE lists SET items = ? WHERE user_id = ? AND list_name = ?",
                    (','.join(items), user_id, list_name)
                )
            return True
        except Exception as e:
            logger.error(f"Error updating items: {e}")
            return False

    def archive_list(self, user_id: int, list_name: str) -> bool:
        return self._update_list_status(user_id, list_name, True)

    def unarchive_list(self, user_id: int, list_name: str) -> bool:
        return self._update_list_status(user_id, list_name, False)

    def _update_list_status(self, user_id: int, list_name: str, is_archived: bool) -> bool:
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE lists SET is_archived = ? WHERE user_id = ? AND list_name = ?",
                    (is_archived, user_id, list_name)
                )
            return True
        except Exception as e:
            logger.error(f"Error updating list status: {e}")
            return False

    def close(self):
        self.conn.close()
