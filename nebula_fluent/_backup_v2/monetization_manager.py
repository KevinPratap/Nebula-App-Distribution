import os
import json
import requests

class MonetizationManager:
    # SERVER_URL = "http://127.0.0.1:5000"
    SERVER_URL = "https://www.nebulainterviewai.com"
    
    # Use absolute paths for persistence
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSION_FILE = os.path.join(BASE_DIR, "session.json")
    SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
    
    @staticmethod
    def get_hwid():
        import uuid
        return str(uuid.getnode())

    @staticmethod
    def save_session(token):
        try:
            with open(MonetizationManager.SESSION_FILE, "w") as f:
                json.dump({"token": token}, f)
        except: pass

    @staticmethod
    def load_session():
        if os.path.exists(MonetizationManager.SESSION_FILE):
            try:
                with open(MonetizationManager.SESSION_FILE, "r") as f:
                    return json.load(f).get("token")
            except: return None
        return None

    @staticmethod
    def is_ethics_accepted():
        if os.path.exists(MonetizationManager.SETTINGS_FILE):
            try:
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    return json.load(f).get("ethics_accepted", False)
            except: return False
        return False

    @staticmethod
    def accept_ethics():
        try:
            with open(MonetizationManager.SETTINGS_FILE, "w") as f:
                json.dump({"ethics_accepted": True}, f)
        except: pass

    @staticmethod
    def register(email, password):
        try:
            hwid = MonetizationManager.get_hwid()
            res = requests.post(f"{MonetizationManager.SERVER_URL}/register", 
                              json={"email": email, "password": password, "hwid": hwid}, timeout=30)
            try:
                return res.status_code == 201, res.json().get("message")
            except:
                return False, f"Server Error {res.status_code}: {res.text[:50]}"
        except Exception as e: return False, str(e)

    @staticmethod
    def login(email, password):
        try:
            res = requests.post(f"{MonetizationManager.SERVER_URL}/login", 
                              json={"email": email, "password": password}, timeout=30)
            try:
                if res.status_code == 200:
                    token = res.json().get("access_token")
                    MonetizationManager.save_session(token)
                    return True, "Login Successful"
                return False, res.json().get("message", "Login Failed")
            except:
                return False, f"Server Error {res.status_code}: {res.text[:50]}"
        except Exception as e: return False, str(e)

    @staticmethod
    def validate_session():
        token = MonetizationManager.load_session()
        if not token: return False, None
        try:
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.get(f"{MonetizationManager.SERVER_URL}/me", headers=headers, timeout=30)
            if res.status_code == 200:
                return True, res.json()
            return False, None
        except: return False, None
    
    @staticmethod
    def initiate_google_login(session_id):
        try:
            res = requests.get(f"{MonetizationManager.SERVER_URL}/login/google", 
                              params={"session_id": session_id}, timeout=5)
            if res.status_code == 200:
                import webbrowser
                webbrowser.open(res.json().get("auth_url"))
                return True
            return False
        except: return False

    @staticmethod
    def check_google_login(session_id):
        try:
            res = requests.get(f"{MonetizationManager.SERVER_URL}/google/check-login", 
                              params={"session_id": session_id}, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("logged_in"):
                    MonetizationManager.save_session(data.get("access_token"))
                    return True
            return False
        except: return False

    @staticmethod
    def redeem_license(key):
        """Redeem a license key to upgrade plan"""
        try:
            token = MonetizationManager.load_session()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            
            res = requests.post(f"{MonetizationManager.SERVER_URL}/api/redeem", 
                              json={"key": key}, headers=headers, timeout=3)
            
            if res.status_code == 200:
                return True, "License Activated! Please restart."
            else:
                try:
                    msg = res.json().get("message", "Invalid License Key")
                except:
                    msg = "Invalid License Key"
                return False, msg
                
        except Exception as e: return False, str(e)

    @staticmethod
    def consume_credit():
        """Deduct 1 credit for an AI session"""
        try:
            token = MonetizationManager.load_session()
            if not token: return False, "Not Logged In", 0
            
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.post(f"{MonetizationManager.SERVER_URL}/api/consume", 
                              headers=headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                return True, "Credit applied", data.get("credits", 0)
            else:
                try:
                    msg = res.json().get("message", "Request Failed")
                    bal = res.json().get("credits", 0)
                except:
                    msg = "Connection Error"
                    bal = 0
                return False, msg, bal
        except Exception as e:
            return False, str(e), 0

    @staticmethod
    def is_session_active_locally():
        """Check if we are within the 15-minute paid window locally"""
        try:
            if os.path.exists(MonetizationManager.SETTINGS_FILE):
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    expiry = data.get("session_expiry", 0)
                    import time
                    now = time.time()
                    print(f"DEBUG: Checking Session - Now: {now}, Expiry: {expiry}, Active: {now < expiry}")
                    if now < expiry:
                        return True
            else:
                print(f"DEBUG: Settings file not found at {MonetizationManager.SETTINGS_FILE}")
            return False
        except Exception as e: 
            print(f"DEBUG: Error checking session: {e}")
            return False

    @staticmethod
    def set_session_active_locally(minutes=15):
        """Save the session expiry time locally"""
        try:
            data = {}
            if os.path.exists(MonetizationManager.SETTINGS_FILE):
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    try: data = json.load(f)
                    except: data = {}
            
            import time
            data["session_expiry"] = time.time() + (minutes * 60)
            
            with open(MonetizationManager.SETTINGS_FILE, "w") as f:
                json.dump(data, f)
        except: pass
