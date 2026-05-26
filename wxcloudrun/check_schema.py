import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'genealogy.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 查看 members 表的列
cursor.execute("PRAGMA table_info(members)")
columns = cursor.fetchall()

print("Members table columns:")
for col_id, col_name, col_type, not_null, default, pk in columns:
    print(f"  {col_id}: {col_name} ({col_type}) - PK:{pk}, NOT NULL:{not_null}")

print(f"\nTotal columns: {len(columns)}")

conn.close()
