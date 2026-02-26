import sqlite3
import os

DB_PATH = "meeting-prompter-v2/meeting-prompter-v2/licenses.db"

def check():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, credits FROM users")
        rows = cursor.fetchall()
        print(f"--- Users Table ({DB_PATH}) ---")
        for row in rows:
            print(f"ID: {row[0]}, Email: {row[1]}, Credits: {row[2]}")

if __name__ == "__main__":
    check()
