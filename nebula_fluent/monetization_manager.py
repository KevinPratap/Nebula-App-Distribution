import os
import json
import requests

class MonetizationManager:
    SERVER_URL = "https://www.nebulainterviewai.com"
    # SERVER_URL = "http://127.0.0.1:5000"
    
    # Use absolute paths for persistence
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSION_FILE = os.path.join(BASE_DIR, "session.json")
    SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
    
    _clock_offset = 0 # Network drift (v6.7)

    @staticmethod
    def sync_server_time():
        """Fetch global server time to calculate network drift offset (v6.7)"""
        try:
            import time
            from email.utils import parsedate_to_datetime
            # HEAD request to get world time from server headers
            res = requests.head(MonetizationManager.SERVER_URL, timeout=5)
            server_date_str = res.headers.get('Date')
            if server_date_str:
                server_time = parsedate_to_datetime(server_date_str).timestamp()
                local_time = time.time()
                MonetizationManager._clock_offset = server_time - local_time
                print(f"DEBUG: Time Sync - Offset: {MonetizationManager._clock_offset:.2f}s")
        except Exception as e:
            print(f"DEBUG: Time Sync Error: {e}")

    @staticmethod
    def get_synced_time():
        """Returns the world-synchronized time regardless of local clock state"""
        import time
        return time.time() + MonetizationManager._clock_offset

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
            res = requests.get(f"{MonetizationManager.SERVER_URL}/auth/status", 
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
    def initiate_github_login(session_id):
        """Initiate GitHub OAuth flow (v6.8)"""
        try:
            res = requests.get(f"{MonetizationManager.SERVER_URL}/login/github", 
                              params={"session_id": session_id}, timeout=5)
            if res.status_code == 200:
                import webbrowser
                webbrowser.open(res.json().get("auth_url"))
                return True
            return False
        except: return False

    @staticmethod
    def check_github_login(session_id):
        """Check status of GitHub OAuth flow (v6.8)"""
        # Reuse the generic auth/status checker which handles both Google & GitHub
        return MonetizationManager.check_google_login(session_id)

    @staticmethod
    def setup_2fa():
        """Request 2FA setup (returns QR code and secret)"""
        try:
            token = MonetizationManager.load_session()
            if not token: return False, "Not Logged In"
            
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.post(f"{MonetizationManager.SERVER_URL}/auth/2fa/setup", headers=headers, timeout=10)
            
            if res.status_code == 200:
                return True, res.json()
            return False, "Failed to initiate setup"
        except Exception as e: return False, str(e)

    @staticmethod
    def enable_2fa(secret, code):
        """Verify and enable 2FA"""
        try:
            token = MonetizationManager.load_session()
            if not token: return False, "Not Logged In"
            
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.post(f"{MonetizationManager.SERVER_URL}/auth/2fa/enable", 
                              json={"secret": secret, "code": code},
                              headers=headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("success"):
                    return True, "2FA Enabled Successfully"
                return False, data.get("message", "Verification Failed")
            return False, "Verification Failed"
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
    def get_ai_config():
        """Fetch AI API keys from the server"""
        try:
            token = MonetizationManager.load_session()
            if not token: return None
            
            headers = {"Authorization": f"Bearer {token}"}
            res = requests.get(f"{MonetizationManager.SERVER_URL}/api/ai/config", 
                              headers=headers, timeout=10)
            
            if res.status_code == 200:
                return res.json()
            return None
        except Exception as e:
            print(f"DEBUG: Error fetching AI config: {e}")
            return None

    @staticmethod
    def is_session_active_locally():
        """Check if we are within the 15-minute paid window locally"""
        try:
            if os.path.exists(MonetizationManager.SETTINGS_FILE):
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    expiry = data.get("session_expiry", 0)
                    now = MonetizationManager.get_synced_time()
                    print(f"DEBUG: Checking Session - Now: {now}, Expiry: {expiry}, Active: {now < expiry}")
                    if now < expiry:
                        return True
            else:
                pass
            return False
        except Exception as e: 
            return False

    @staticmethod
    def get_session_remaining_seconds():
        """Get remaining seconds synced with World Time (v6.7)"""
        try:
            if os.path.exists(MonetizationManager.SETTINGS_FILE):
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    expiry = data.get("session_expiry", 0)
                    remaining = int(expiry - MonetizationManager.get_synced_time())
                    # SANITY CHECK: Never allow timer to exceed 15 mins
                    return min(900, max(0, remaining))
            return 0
        except Exception: 
            return 0

    @staticmethod
    def set_session_active_locally(minutes=15):
        """Save the session expiry time locally using world time sync"""
        try:
            data = {}
            if os.path.exists(MonetizationManager.SETTINGS_FILE):
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    try: data = json.load(f)
                    except: data = {}
            
            data["session_expiry"] = MonetizationManager.get_synced_time() + (minutes * 60)
            
            with open(MonetizationManager.SETTINGS_FILE, "w") as f:
                json.dump(data, f)
        except: pass
