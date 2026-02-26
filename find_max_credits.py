import sqlite3
import os

dbs = [
    "licenses.db",
    "meeting-prompter-v2/licenses.db",
    "meeting-prompter-v2/meeting-prompter-v2/licenses.db"
]

def find_max():
    for db in dbs:
        if not os.path.exists(db):
            print(f"[{db}] Not found")
            continue
        
        try:
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            cursor.execute("SELECT email, credits FROM users ORDER BY credits DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                print(f"[{db}] Max Credits: {row[1]} (User: {row[0]})")
            else:
                print(f"[{db}] No users found")
            conn.close()
        except Exception as e:
            print(f"[{db}] Error: {e}")

if __name__ == "__main__":
    find_max()
