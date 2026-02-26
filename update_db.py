import sqlite3
import os

DB_PATH = r"c:\Users\prata\.gemini\antigravity\scratch\meeting-prompter-v2\licenses.db"

if not os.path.exists(DB_PATH):
    print(f"DB not found at {DB_PATH}")
else:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET credits = 10 WHERE email='pratapkevin8@gmail.com'")
        conn.commit()
        print(f"Updated credits to 10. Rows affected: {cursor.rowcount}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
