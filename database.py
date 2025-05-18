import sqlite3
import json
from typing import List, Dict, Any
from config import DB_PATH, logger

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
