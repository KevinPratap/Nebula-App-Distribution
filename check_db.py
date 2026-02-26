import sqlite3
import os

DB_PATH = r"c:\Users\prata\.gemini\antigravity\scratch\meeting-prompter-v2\licenses.db"

if not os.path.exists(DB_PATH):
    print(f"DB not found at {DB_PATH}")
else:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT email, credits FROM users WHERE email='pratapkevin8@gmail.com'")
        row = cursor.fetchone()
        print(f"DB Row: {row}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
