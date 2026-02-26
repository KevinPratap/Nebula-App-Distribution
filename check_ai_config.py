import sqlite3
DB_FILE = 'licenses.db'
try:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Show all system_config keys
        cursor.execute("SELECT key, value FROM system_config ORDER BY key")
        rows = cursor.fetchall()
        print("=== system_config table ===")
        for row in rows:
            key = row[0]
            val = str(row[1])[:30] + "..." if row[1] and len(str(row[1])) > 30 else row[1]
            print(f"  {key}: {val}")
        # Also show the schema
        cursor.execute("PRAGMA table_info(system_config)")
        schema = cursor.fetchall()
        print("\n=== system_config schema ===")
        for col in schema:
            print(f"  {col}")
except Exception as e:
    print(f"Error: {e}")
