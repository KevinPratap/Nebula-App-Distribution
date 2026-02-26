import sqlite3
import os

DB_PATH = "meeting-prompter-v2/licenses.db"

def grant():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET credits = 50 WHERE email = 'pratapkevin8@gmail.com'")
        conn.commit()
        print(f"Successfully granted 50 credits to pratapkevin8@gmail.com. Rowcount: {cursor.rowcount}")

if __name__ == "__main__":
    grant()
