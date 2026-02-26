
import requests
import json

BASE_URL = "https://nebula-ai.railway.app"

def check_credits(email, password):
    print(f"Checking credits for {email} on {BASE_URL}...")
    try:
        # Login
        resp = requests.post(f"{BASE_URL}/login", json={"email": email, "password": password})
        if resp.status_code != 200:
            print(f"Login Failed: {resp.text}")
            return

        token = resp.json().get("access_token")
        print("Login Successful. Token obtained.")

        # Check /me
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = requests.get(f"{BASE_URL}/me", headers=headers)
        
        if me_resp.status_code == 200:
            cid = me_resp.json().get("credits")
            print(f"User Credits on Server: {cid}")
        else:
            print(f"Available Failed: {me_resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # We don't have user password here, but I can ask the user OR 
    # just print the diagnostic steps.
    # Actually, I'll just check if the URL is reachable.
    try:
        r = requests.get(BASE_URL)
        print(f"Server reachable: {r.status_code}")
    except Exception as e:
        print(f"Server unreachable: {e}")
