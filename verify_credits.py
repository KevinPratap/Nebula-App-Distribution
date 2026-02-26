import requests
import json
import sqlite3
import os

SERVER_URL = "http://127.0.0.1:5000"
DB_PATH = "meeting-prompter-v2/licenses.db"

def test_credits():
    print("--- Nebula Credit System Test ---")
    
    # 1. Setup Test User in DB
    email = "test@nebula.io"
    password = "password123"
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Delete if exists to ensure password matches our test
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        
    # Register fresh
    reg_res = requests.post(f"{SERVER_URL}/register", json={"email": email, "password": password, "hwid": "test-hwid"})
    print(f"Step 1b: Register status: {reg_res.status_code}, {reg_res.text}")

    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Ensure user has 10 credits
        cursor.execute("UPDATE users SET credits = 10 WHERE email = ?", (email,))
        conn.commit()


    
    print(f"Step 1: Set user {email} to 10 credits in DB.")

    # 2. Login to get token
    res = requests.post(f"{SERVER_URL}/login", json={"email": email, "password": password})
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        return
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Step 2: Login successful. Token obtained.")

    # 3. Check Balance via /me
    res = requests.get(f"{SERVER_URL}/me", headers=headers)
    balance = res.json().get("credits")
    print(f"Step 3: Initial Balance from /me: {balance}")

    # 4. Consume Credit
    print("Step 4: Consuming 1 credit...")
    res = requests.post(f"{SERVER_URL}/api/consume", headers=headers)
    if res.status_code == 200:
        new_balance = res.json().get("credits")
        print(f"SUCCESS: New Balance: {new_balance}")
    else:
        print(f"FAILED: {res.text}")

    # 5. Check DB directly
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT credits FROM users WHERE email = ?", (email,))
        db_balance = cursor.fetchone()[0]
        print(f"Step 5: Direct DB Check: {db_balance}")

if __name__ == "__main__":
    test_credits()
