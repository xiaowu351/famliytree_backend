import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(__file__), 'genealogy.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s (Line %(lineno)d): %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 查看 members 表的列
cursor.execute("PRAGMA table_info(members)")
columns = cursor.fetchall()

logger.info("Members table columns:")
for col_id, col_name, col_type, not_null, default, pk in columns:
    logger.info("  %s: %s (%s) - PK:%s, NOT NULL:%s", col_id, col_name, col_type, pk, not_null)

logger.info("Total columns: %s", len(columns))

conn.close()
