import sqlite3
import uuid
import datetime
import bcrypt
import hmac
import hashlib
import json
import os
import secrets
from flask import Flask, request, jsonify, render_template, redirect, session, url_for, send_from_directory, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from functools import wraps
from authlib.integrations.flask_client import OAuth
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import razorpay
import socket
from werkzeug.middleware.proxy_fix import ProxyFix

# --- CLOUD PERSISTENCE HACK: Force IPv4 ---
# Railway/Docker environments sometimes fail with "Network is unreachable" 
# because they try IPv6 first. This forces IPv4 for all outbound connections.
orig_getaddrinfo = socket.getaddrinfo
def ipv4_only_getaddrinfo(*args, **kwargs):
    res = orig_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET]
socket.getaddrinfo = ipv4_only_getaddrinfo

# Load environment variables
load_dotenv()

# --- PRODUCTION HARDENING (v25) ---
REQUIRED_ENV_VARS = [
    "JWT_SECRET_KEY", "SECRET_KEY", "ADMIN_PASSWORD",
    "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"
]
missing_vars = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
if missing_vars:
    print(f"CRITICAL ERROR: The following environment variables are missing: {', '.join(missing_vars)}")
    if os.getenv("FLASK_ENV") == "production":
        raise EnvironmentError(f"Missing required production environment variables: {missing_vars}")
    else:
        print("WARNING: Running in development mode without full security. Ensure these are set in production.")

app = Flask(__name__)
# Apply ProxyFix for correct protocol (https) behind Railway's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Enable CORS for frontend flexibility
# IMPORTANT: In production, specify the exact domain
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "https://www.nebulainterviewai.com", "https://nebulainterviewai.com"])

# JWT Configuration for Secure Cookies
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "nebula-super-secret-123")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "flask-secret-key-change-me")
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]  # Headers first for desktop app reliability
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
app.config["JWT_REFRESH_COOKIE_PATH"] = "/api/token/refresh"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # Matches app requirement for unified auth
# Force Secure cookies in production or if accessed via HTTPS
app.config["JWT_COOKIE_SECURE"] = True # Recommended for all modern apps
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(days=30)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = datetime.timedelta(days=30)

jwt = JWTManager(app)

DB_FILE = os.getenv("DB_FILE", "licenses.db")

# Force persistence check for Railway Volumes
if not os.getenv("DB_FILE"):
    if os.path.exists("/data"):
        DB_FILE = "/data/licenses.db"
        print(f"--> [PERSISTENCE] Railway Volume detected at /data. Using: {DB_FILE}", flush=True)
    else:
        print(f"--> [WARNING] No persistent volume detected at /data. Database will be EPHEMERAL!", flush=True)

# Ensure database directory exists if a path is provided
if os.path.dirname(DB_FILE):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
print(f"--> USING DATABASE FILE: {os.path.abspath(DB_FILE)}", flush=True)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")
STATIC_SITE_DIR = os.path.join(os.getcwd(), 'local_static')

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
if RAZORPAY_KEY_ID:
    print(f"--> [PAYMENT] Initializing Razorpay with Key: {RAZORPAY_KEY_ID[:10]}...", flush=True)
else:
    print("--> [PAYMENT] Razorpay Key ID not configured in environment.", flush=True)

# Initialize Razorpay Client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# In-memory store for app-based social login sessions
PENDING_SOCIAL_LOGINS = {}

# OAuth Configuration
oauth = OAuth(app)

# GitHub OAuth
github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Google OAuth
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- EMAIL HELPERS ---
def send_reset_email(target_email, code):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    resend_api_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

    if not resend_api_key:
        print(f"--> [MOCK EMAIL] To: {target_email} | Code: {code}")
        return True

    def _send():
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": f"Nebula AI <{sender_email}>",
                "to": [target_email],
                "subject": f"Your Verification Code: {code}",
                "text": f"Hello,\n\nWe received a request to reset your password. Use the following 6-digit code to proceed:\n\n{code}\n\nIf you didn't request this, you can safely ignore this email.\n\nBest,\nThe Nebula Team"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                print(f"--> RESEND SUCCESS: To {target_email}", flush=True)
            else:
                print(f"--> RESEND ERROR: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"--> RESEND EXCEPTION: {str(e)}", flush=True)

    import threading
    threading.Thread(target=_send).start()
    return True

def send_welcome_email(target_email):
    import requests
    resend_api_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

    if not resend_api_key:
        print(f"--> [MOCK WELCOME EMAIL] To: {target_email}")
        return True

    def _send():
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": f"Nebula AI <{sender_email}>",
                "to": [target_email],
                "subject": "Welcome to Nebula • Next Steps Inside",
                "text": f"Hi there,\n\nWelcome to Nebula! We're thrilled to have you onboard.\n\nNebula is designed to be your elite cognitive companion during technical interviews. To get started, download the desktop app and join your first meeting. Nebula will automatically listen and provide real-time guidance.\n\nDownload Link: https://nebulainterviewai.com/download\n\nIf you have any questions, simply reply to this email.\n\nBest,\nThe Nebula Team",
                "html": """
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #1f2937;">
                    <h1 style="color: #9f7aea;">Welcome to Nebula ✨</h1>
                    <p>Hi there,</p>
                    <p>We're thrilled to have you onboard! Nebula is your elite cognitive companion for professional technical interviews.</p>
                    <div style="background: #f3f4f6; padding: 20px; border-radius: 12px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Next Steps:</h3>
                        <ol>
                            <li><strong>Download:</strong> Get the desktop app for Windows, macOS, or Linux.</li>
                            <li><strong>Install:</strong> Run the installer (takes 10 seconds).</li>
                            <li><strong>Ace It:</strong> Join your meeting and read the real-time insights.</li>
                        </ol>
                        <a href="https://nebulainterviewai.com/download" style="display: inline-block; background: #9f7aea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 10px;">Download Nebula</a>
                    </div>
                    <p>If you have any questions, we're here to help.</p>
                    <p>Best,<br>The Nebula Team</p>
                </div>
                """
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                print(f"--> RESEND WELCOME SUCCESS: To {target_email}", flush=True)
            else:
                print(f"--> RESEND WELCOME ERROR: {response.status_code} - {response.text}", flush=True)
        except Exception as e:
            print(f"--> RESEND WELCOME EXCEPTION: {str(e)}", flush=True)

    import threading
    threading.Thread(target=_send).start()
    return True

# --- DATABASE HELPERS ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Licenses
        cursor.execute('''CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY, status TEXT DEFAULT 'ACTIVE', hwid TEXT, 
            created_at TEXT, expires_at TEXT, notes TEXT)''')
        # Users
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, 
            password_hash TEXT, hwid TEXT, google_id TEXT, github_id TEXT, 
            github_username TEXT, avatar_url TEXT, display_name TEXT, 
            credits INTEGER DEFAULT 0, total_questions INTEGER DEFAULT 0,
            total_minutes INTEGER DEFAULT 0, created_at TEXT)''')
        # Subscriptions
        cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY, plan TEXT DEFAULT 'FREE_TRIAL', 
            status TEXT DEFAULT 'ACTIVE', trial_start TEXT, trial_end TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # Password Resets
        cursor.execute('''CREATE TABLE IF NOT EXISTS password_resets (
            email TEXT PRIMARY KEY, code TEXT, expires_at TEXT)''')

        # Logs
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, 
            description TEXT, timestamp TEXT)''')
        
        # System Config
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY, value TEXT)''')
        
        # Pending Social Auth Bridge (v17 Persistent)
        cursor.execute('''CREATE TABLE IF NOT EXISTS pending_social_auths (
            session_id TEXT PRIMARY KEY, access_token TEXT, created_at TEXT)''')
        
        conn.commit()

def log_event(event, description):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO system_logs (event, description, timestamp) VALUES (?, ?, ?)", 
                        (event, description, datetime.datetime.now().isoformat()))
            conn.commit()
    except: pass

init_db()

# --- AUTH DECORATORS ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_password = request.headers.get('X-Admin-Password')
        if provided_password != ADMIN_PASSWORD:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    hwid = data.get('hwid')
    
    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400
        
    pwd_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    created_at = datetime.datetime.now().isoformat()
    trial_end = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, password_hash, hwid, created_at) VALUES (?, ?, ?, ?)",
                         (email, pwd_hash, hwid, created_at))
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO subscriptions (user_id, trial_end) VALUES (?, ?)", (user_id, trial_end))
            conn.commit()
        log_event("USER_REGISTER", f"New user: {email}")
        send_welcome_email(email)
        return jsonify({"message": "User registered successfully", "status": "success"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "User already exists"}), 409

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (data.get('email'),))
        user = cursor.fetchone()

    if user and user['password_hash'] and bcrypt.checkpw(data.get('password').encode('utf-8'), user['password_hash'].encode('utf-8')):
        access_token = create_access_token(identity=str(user['id']))
        log_event("USER_LOGIN", f"Login success: {data.get('email')}")
        
        # Support both app (JSON body) and web (Cookies)
        resp = jsonify({
            "login": True, 
            "message": "Login successful",
            "access_token": access_token,
            "user": {"email": user['email'], "id": user['id']}
        })
        from flask_jwt_extended import set_access_cookies
        set_access_cookies(resp, access_token)
        return resp, 200
    return jsonify({"message": "Invalid email or password"}), 401
    
# --- PROTECTED API ROUTES (v20 SESSION STABILITY) ---

@app.route('/me', methods=['GET'])
@jwt_required()
def me():
    uid = get_jwt_identity()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        u = conn.cursor().execute("SELECT u.*, s.plan, s.status FROM users u LEFT JOIN subscriptions s ON u.id=s.user_id WHERE u.id=?", (uid,)).fetchone()
    return jsonify(dict(u)) if u else (jsonify({"error": "User not found"}), 404)

@app.route('/api/consume', methods=['POST'])
@jwt_required()
def consume_credit():
    uid_raw = get_jwt_identity()
    try:
        uid = int(uid_raw)
    except:
        return jsonify({"success": False, "message": "Invalid identity"}), 401
        
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT credits FROM users WHERE id=?", (uid,))
        row = c.fetchone()
        credits = (row[0] if row else 0) or 0
        
        if credits <= 0: 
            return jsonify({"success": False, "message": "No credits"}), 403
            
        c.execute("UPDATE users SET credits=? WHERE id=?", (credits-1, uid))
        conn.commit()
    return jsonify({"success": True, "credits": credits-1})

@app.route('/auth/logout', methods=['POST'])
def logout():
    resp = jsonify({"logout": True})
    from flask_jwt_extended import unset_jwt_cookies
    unset_jwt_cookies(resp)
    return resp, 200

@app.route('/auth/delete-account', methods=['POST'])
@jwt_required()
def delete_account():
    user_id = get_jwt_identity()
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Delete related data first
            cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        
        # Logout after deletion
        resp = jsonify({"message": "Account deleted successfully"})
        from flask_jwt_extended import unset_jwt_cookies
        unset_jwt_cookies(resp)
        return resp, 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    # We can return a simple success if the frontend just needs to trigger a request to get the cookie.
    return jsonify({"success": True}), 200



# --- FORGOT PASSWORD ---

@app.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    if not email:
        return jsonify({"message": "Email is required"}), 400

    # Check if user exists
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user:
            # For security, don't reveal if email exists, but here we can be helpful
            return jsonify({"message": "If that email exists in our system, you will receive a code."}), 200

        # Generate 6-digit code
        import random
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()

        # Save/Update Reset Request
        cursor.execute("INSERT OR REPLACE INTO password_resets (email, code, expires_at) VALUES (?, ?, ?)", 
                     (email, code, expires_at))
        conn.commit()

    # Send Email
    resend_configured = bool(os.getenv("RESEND_API_KEY"))
    success = send_reset_email(email, code)
    
    if success:
        mode_msg = "Verification code sent to your email." if resend_configured else "[DEBUG] Resend API not configured. Code printed to server logs."
        return jsonify({
            "message": mode_msg,
            "smtp_configured": resend_configured
        }), 200
    else:
        return jsonify({"message": "Failed to initiate email sending."}), 500

@app.route('/auth/test-email', methods=['POST'])
def test_email():
    """Synchronous test for Resend API configuration"""
    email = request.json.get('email')
    if not email: return jsonify({"message": "Email required"}), 400

    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

    if not api_key:
        return jsonify({"status": "error", "message": "RESEND_API_KEY not configured in environment"}), 400

    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": f"Nebula Test <{sender}>",
            "to": [email],
            "subject": "Nebula Resend API Connection Test",
            "text": "If you see this, your Resend API configuration is correct!"
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code in [200, 201]:
            return jsonify({"status": "success", "message": "Test email sent successfully via Resend API!"}), 200
        else:
            return jsonify({"status": "error", "message": f"Resend API Error: {response.status_code} - {response.text}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Request Error: {str(e)}"}), 500

@app.route('/auth/reset-password', methods=['POST'])
def reset_password():
    email = request.json.get('email')
    code = request.json.get('code')
    new_password = request.json.get('new_password')

    if not all([email, code, new_password]):
        return jsonify({"message": "Missing required fields"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Verify Code
        cursor.execute("SELECT code, expires_at FROM password_resets WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({"message": "Invalid email or verification code."}), 400
        
        saved_code, expires_at = row
        if saved_code != code:
            return jsonify({"message": "Invalid verification code."}), 400
        
        if datetime.datetime.now().isoformat() > expires_at:
            return jsonify({"message": "Verification code has expired."}), 400

        # Update Password
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hashed, email))
        
        # Clear Reset Code
        cursor.execute("DELETE FROM password_resets WHERE email = ?", (email,))
        conn.commit()

    return jsonify({"message": "Password reset successfully. You can now log in."}), 200

# --- PAYMENTS ---

@app.route('/payments/create-order', methods=['POST'])
@jwt_required()
def create_order():
    try:
        data = request.json
        amount = data.get('amount') # In paise
        credits = data.get('credits')
        
        if not amount or not credits:
            return jsonify({"error": "Missing amount or credits"}), 400
            
        order_data = {
            "amount": int(amount) * 100, # Convert to paise
            "currency": "INR",
            "receipt": f"order_rcptid_{uuid.uuid4().hex[:10]}",
            "notes": {
                "credits": credits,
                "user_id": get_jwt_identity()
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        return jsonify(order)
    except Exception as e:
        print(f"Razorpay Order Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/payments/verify', methods=['POST'])
@jwt_required()
def verify_payment():
    data = request.json
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    credits_to_add = data.get('credits')
    user_id = get_jwt_identity()

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, credits_to_add]):
         return jsonify({"status": "failure", "message": "Missing required fields"}), 400

    try:
        # Verify Signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        # Payment Successful - Update DB
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Add Credits
            cursor.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (credits_to_add, user_id))
            
            # AUTO-UPGRADE TO PREMIUM
            # We assume any credit purchase qualifies for Premium status
            cursor.execute("UPDATE subscriptions SET plan='PREMIUM', status='ACTIVE' WHERE user_id=?", (user_id,))
            
            # Log Transaction
            cursor.execute("INSERT INTO system_logs (event, description, timestamp) VALUES (?, ?, ?)",
                         ("PAYMENT_SUCCESS", f"User {user_id} bought {credits_to_add} credits. Order: {razorpay_order_id}", datetime.datetime.now().isoformat()))
            
            conn.commit()

        return jsonify({"status": "success"})
    except razorpay.errors.SignatureVerificationError:
        return jsonify({"status": "failure", "message": "Signature Verification Failed"}), 400
    except Exception as e:
        print(f"Payment Verification Error: {e}")
        return jsonify({"status": "failure", "message": str(e)}), 500

    # Combined with /me above for v20 priority
    pass

@app.route('/update_profile', methods=['POST'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.json
    display_name = data.get('display_name')
    if not display_name: return jsonify({"message": "Display name required"}), 400

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id))
            conn.commit()
        return jsonify({"message": "Profile updated", "display_name": display_name}), 200
    except Exception as e: return jsonify({"message": str(e)}), 500

@app.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.json
    new_password = data.get('new_password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400
        
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
            conn.commit()
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/auth/toggle-2fa', methods=['POST'])
@jwt_required()
def toggle_2fa():
    user_id = get_jwt_identity()
    data = request.json
    enabled = data.get('enabled', False)
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET two_factor_enabled = ? WHERE id = ?", (1 if enabled else 0, user_id))
            conn.commit()
        return jsonify({"message": f"2FA {'enabled' if enabled else 'disabled'} successfully"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# --- OAUTH (WEB FLOW) ---

@app.route('/auth/github')
def auth_github():
    # Dynamic Redirect URI handling (v26)
    if "localhost" in request.host or "127.0.0.1" in request.host:
        redirect_uri = url_for('auth_github_callback', _external=True)
    else:
        # Detect host dynamically (handles both nebula and www.nebula)
        host = request.host
        redirect_uri = f"https://{host}/auth/github/callback"
    
    flow_session_id = request.args.get('flow_session_id')
    state_val = None
    if flow_session_id:
        session['nebula_flow_id'] = flow_session_id
        state_val = f"nebula_app_{flow_session_id}"
        
    return github.authorize_redirect(redirect_uri, state=state_val)

@app.route('/auth/github/callback')
def auth_github_callback():
    try:
        token = github.authorize_access_token()
        profile = github.get('user', token=token).json()
        github_id = str(profile['id'])
        github_username = profile.get('login')
        display_name = profile.get('name') or github_username
        avatar_url = profile.get('avatar_url')
        
        # Try to get email from profile, otherwise fetch from /user/emails
        email = profile.get('email')
        if not email:
            try:
                emails = github.get('user/emails', token=token).json()
                # Find primary verified email
                primary_email = next((e['email'] for e in emails if e['primary'] and e['verified']), None)
                # Fallback to any verified email
                if not primary_email:
                    primary_email = next((e['email'] for e in emails if e['verified']), None)
                if primary_email:
                    email = primary_email
            except:
                pass
        
        # Final fallback
        if not email:
            email = f"gh_{github_id}@nebula.local"
        
        user_id = None
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE github_id=?", (github_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                # Update existing user data
                cursor.execute("UPDATE users SET avatar_url=COALESCE(?, avatar_url), display_name=COALESCE(?, display_name), github_username=? WHERE id=?", 
                             (avatar_url, display_name, github_username, user_id))
            else:
                cursor.execute("INSERT INTO users (email, github_id, github_username, display_name, avatar_url, created_at) VALUES (?, ?, ?, ?, ?, ?)", 
                             (email, github_id, github_username, display_name, avatar_url, datetime.datetime.now().isoformat()))
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO subscriptions (user_id) VALUES (?)", (user_id,))
            conn.commit()
            
        access_token = create_access_token(identity=str(user_id))
        
        # Check for flow_session_id (App Flow) - v22 Fix with Prefix
        state = request.args.get('state')
        cookie_flow_id = session.get('nebula_flow_id')
        
        final_flow_id = None
        if cookie_flow_id:
            final_flow_id = cookie_flow_id
        elif state and state.startswith('nebula_app_'):
            final_flow_id = state.replace('nebula_app_', '', 1)
            
        if final_flow_id:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT OR REPLACE INTO pending_social_auths (session_id, access_token, created_at) VALUES (?, ?, ?)", 
                            (final_flow_id, access_token, datetime.datetime.now().isoformat()))
                conn.commit()
            # Clear session to prevent state bleeding
            session.pop('nebula_flow_id', None)
            return "<html><body><h1>Login Success!</h1><script>window.close();</script></body></html>"

        # Base URL from the request (ProxyFix makes this correct)
        base_url = request.host_url.rstrip('/')
        frontend_url = "http://localhost:5173" if "localhost" in base_url or "127.0.0.1" in base_url else base_url
             
        resp = redirect(f"{frontend_url}/dashboard")
        from flask_jwt_extended import set_access_cookies
        set_access_cookies(resp, access_token)
        return resp
    except Exception as e:
        base_url = request.host_url.rstrip('/')
        frontend_url = "http://localhost:5173" if "localhost" in base_url or "127.0.0.1" in base_url else base_url
        return redirect(f"{frontend_url}/login?error={str(e)}")

@app.route('/auth/google')
def auth_google():
    # Dynamic Redirect URI handling (v26)
    if "localhost" in request.host or "127.0.0.1" in request.host:
        redirect_uri = url_for('auth_google_callback', _external=True)
    else:
        # Detect host dynamically (handles both nebula and www.nebula)
        host = request.host
        redirect_uri = f"https://{host}/auth/google/callback"
        
    flow_session_id = request.args.get('flow_session_id')
    state_val = None
    if flow_session_id:
        session['nebula_flow_id'] = flow_session_id
        state_val = f"nebula_app_{flow_session_id}"
        
    return google.authorize_redirect(redirect_uri, state=state_val)

@app.route('/auth/google/callback')
def auth_google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo') or google.get('userinfo').json()
        google_id = user_info['sub']
        email = user_info['email']
        display_name = user_info.get('name')
        avatar_url = user_info.get('picture')

        user_id = None
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE google_id=?", (google_id,))
            row = cursor.fetchone()
            if row: 
                user_id = row[0]
                # Update existing user data
                cursor.execute("UPDATE users SET avatar_url=COALESCE(?, avatar_url), display_name=COALESCE(?, display_name) WHERE id=?", 
                             (avatar_url, display_name, user_id))
            else:
                cursor.execute("INSERT INTO users (email, google_id, display_name, avatar_url, created_at) VALUES (?, ?, ?, ?, ?)", 
                             (email, google_id, display_name, avatar_url, datetime.datetime.now().isoformat()))
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO subscriptions (user_id) VALUES (?)", (user_id,))
            conn.commit()

        access_token = create_access_token(identity=str(user_id))
        
        # Check for flow_session_id (App Flow) - v22 Fix with Prefix
        state = request.args.get('state')
        cookie_flow_id = session.get('nebula_flow_id')
        
        final_flow_id = None
        if cookie_flow_id:
            final_flow_id = cookie_flow_id
        elif state and state.startswith('nebula_app_'):
            final_flow_id = state.replace('nebula_app_', '', 1)
            
        if final_flow_id:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT OR REPLACE INTO pending_social_auths (session_id, access_token, created_at) VALUES (?, ?, ?)", 
                            (final_flow_id, access_token, datetime.datetime.now().isoformat()))
                conn.commit()
            # Clear session to prevent state bleeding
            session.pop('nebula_flow_id', None)
            return "<html><body><h1>Login Success!</h1><script>window.close();</script></body></html>"

        base_url = request.host_url.rstrip('/')
        frontend_url = "http://localhost:5173" if "localhost" in base_url or "127.0.0.1" in base_url else base_url
             
        resp = redirect(f"{frontend_url}/dashboard")
        from flask_jwt_extended import set_access_cookies
        set_access_cookies(resp, access_token)
        return resp
    except Exception as e:
        base_url = request.host_url.rstrip('/')
        frontend_url = "http://localhost:5173" if "localhost" in base_url or "127.0.0.1" in base_url else base_url
        return redirect(f"{frontend_url}/login?error={str(e)}")

# --- OAUTH (APP FLOW) ---

@app.route('/login/google', methods=['GET'])
def app_google_login():
    session_id = request.args.get('session_id')
    if not session_id: return jsonify({"error": "session_id required"}), 400
    auth_url = url_for('auth_google', flow_session_id=session_id, _external=True)
    if 'nebulainterviewai.com' in auth_url:
        auth_url = auth_url.replace('http://', 'https://')
    return jsonify({"auth_url": auth_url})

@app.route('/login/github', methods=['GET'])
def app_github_login():
    session_id = request.args.get('session_id')
    if not session_id: return jsonify({"error": "session_id required"}), 400
    auth_url = url_for('auth_github', flow_session_id=session_id, _external=True)
    if 'nebulainterviewai.com' in auth_url:
        auth_url = auth_url.replace('http://', 'https://')
    return jsonify({"auth_url": auth_url})

@app.route('/google/callback', methods=['GET'])
def app_google_callback():
    session_id = request.args.get('session_id')
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo') or google.get('userinfo').json()
        google_id = user_info['sub']
        email = user_info['email']

        user_id = None
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE google_id=?", (google_id,))
            row = cursor.fetchone()
            if row: user_id = row[0]
            else:
                cursor.execute("INSERT INTO users (email, google_id, created_at) VALUES (?, ?, ?)", 
                             (email, google_id, datetime.datetime.now().isoformat()))
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO subscriptions (user_id) VALUES (?)", (user_id,))
            conn.commit()

        access_token = create_access_token(identity=str(user_id))
        if session_id in PENDING_SOCIAL_LOGINS:
            PENDING_SOCIAL_LOGINS[session_id] = access_token
        
        return "<html><body style='background:#0B0E14;color:#9F7AEA;text-align:center;padding-top:50px;'><h1>🚀 Login Success!</h1><p>Returning to app...</p><script>window.onload=()=>{setTimeout(()=>window.close(),2000);};</script></body></html>"
    except Exception as e:
        return f"<html><body><h1>Login Failed</h1><p>{str(e)}</p></body></html>", 400

@app.route('/auth/status', methods=['GET'])
def check_auth_status():
    sid = request.args.get('session_id')
    if not sid: return jsonify({"logged_in": False}), 400
    
    token = None
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT access_token FROM pending_social_auths WHERE session_id=?", (sid,))
        row = cursor.fetchone()
        if row:
            token = row[0]
            conn.execute("DELETE FROM pending_social_auths WHERE session_id=?", (sid,))
            conn.commit()
            
    if token:
        return jsonify({"logged_in": True, "access_token": token})
    return jsonify({"logged_in": False})

@app.route('/google/check-login', methods=['GET'])
def check_google_login_legacy():
    # Legacy support
    return check_auth_status()

# --- RAZORPAY & LICENSING ---

@app.route('/api/redeem', methods=['POST'])
@jwt_required()
def redeem_license():
    user_id = get_jwt_identity()
    key = request.json.get('key')
    if not key: return jsonify({"success": False, "message": "Key required"}), 400
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM licenses WHERE key=?", (key,))
        row = cursor.fetchone()
        if not row: return jsonify({"success": False, "message": "Key not found"}), 404
        if row[0] != 'ACTIVE': return jsonify({"success": False, "message": "Key already used"}), 400
        cursor.execute("UPDATE subscriptions SET plan='PREMIUM', status='ACTIVE' WHERE user_id=?", (user_id,))
        cursor.execute("UPDATE licenses SET status='REDEEMED' WHERE key=?", (key,))
        conn.commit()
    return jsonify({"success": True, "message": "License redeemed!"})

@app.route('/verify_license', methods=['POST'])
def verify_license():
    data = request.json
    key, hwid = data.get('license_key'), data.get('hwid')
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, hwid FROM licenses WHERE key=?", (key,))
        row = cursor.fetchone()
        if not row: return jsonify({"valid": False, "message": "Key not found"})
        status, db_hwid = row
        if status != 'ACTIVE': return jsonify({"valid": False, "message": f"License is {status}"})
        if db_hwid is None:
            cursor.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
            conn.commit()
            return jsonify({"valid": True, "message": "Activation Successful"})
        return jsonify({"valid": db_hwid == hwid, "message": "Valid" if db_hwid == hwid else "Machine mismatch"})

# --- ADMIN ---

@app.route('/admin')
def admin_panel():
    try:
        return render_template('admin.html')
    except Exception as e:
        import traceback
        return f"<h1>Error loading admin</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route('/admin/stats')
@admin_required
def admin_stats():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE plan='PREMIUM'")
        premium_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(total_questions), SUM(total_minutes) FROM users")
        sums = cursor.fetchone()
        total_questions = sums[0] or 0
        total_minutes = sums[1] or 0
        cursor.execute("SELECT * FROM system_logs ORDER BY id DESC LIMIT 10")
        logs = [dict(zip(['id','event','desc','time'], r)) for r in cursor.fetchall()]
    return jsonify({
        "total_users": total_users, 
        "premium_users": premium_users, 
        "total_questions": total_questions,
        "total_minutes": total_minutes,
        "recent_logs": logs
    })

@app.route('/admin/users')
@admin_required
def admin_users():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT u.id, u.email, s.plan, s.status, s.trial_end, u.credits, u.total_questions, u.total_minutes, u.created_at, u.hwid FROM users u JOIN subscriptions s ON u.id=s.user_id")
        return jsonify([dict(zip(['id','email','plan','status','trial_end','credits','total_questions','total_minutes','created','hwid'], r)) for r in cursor.fetchall()])

@app.route('/admin/config', methods=['GET'])
@admin_required
def get_admin_config():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_config")
        config = {row[0]: row[1] for row in cursor.fetchall()}
    return jsonify(config)

@app.route('/admin/config/update', methods=['POST'])
@admin_required
def update_admin_config():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    if not key: return jsonify({"error": "Key required"}), 400
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    
    log_event("CONFIG_UPDATE", f"Updated system config: {key}")
    return jsonify({"success": True})

@app.route('/api/desktop/config', methods=['GET'])
def get_desktop_config():
    # This endpoint can be further secured with machine-level auth or JWT
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_config WHERE key IN ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'GROQ_API_KEY')")
        rows = cursor.fetchall()
        config = {row[0]: row[1] for row in rows}
    
    return jsonify({
        "openai_api_key": config.get('OPENAI_API_KEY', ""),
        "gemini_api_key": config.get('GEMINI_API_KEY', ""),
        "groq_api_key": config.get('GROQ_API_KEY', "")
    })

@app.route('/api/ai/config', methods=['GET'])
@jwt_required()
def get_ai_config_legacy():
    """Provides AI API keys to the verified app instance (Legacy support)"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_config WHERE key IN ('GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENAI_API_KEY')")
        rows = cursor.fetchall()
        config = {row[0]: row[1] for row in rows}
    return jsonify(config)

@app.route('/api/version', methods=['GET'])
def get_version():
    """Returns latest supported desktop version for update checks"""
    return jsonify({
        "version": "v6.1",
        "update_url": "https://www.nebulainterviewai.com/download",
        "critical": False
    })

@app.route('/api/sync', methods=['POST'])
@jwt_required()
def sync_data():
    """Synchronize session analytics from app to website"""
    uid = get_jwt_identity()
    data = request.json
    add_q = int(data.get('questions', 0))
    add_m = int(data.get('minutes', 0))
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET total_questions = total_questions + ?, total_minutes = total_minutes + ? WHERE id=?", 
                 (add_q, add_m, uid))
        conn.commit()
    return jsonify({"success": True})

@app.route('/admin/user/update', methods=['POST'])
@admin_required
def admin_update_user():
    data = request.json
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Auto-Upgrade Logic: Credits > 0 implies PREMIUM
            if int(data.get('credits', 0)) > 0:
                data['plan'] = 'PREMIUM'
                data['status'] = 'ACTIVE'

            # Update Subscription
            cursor.execute("UPDATE subscriptions SET plan=?, status=?, trial_end=? WHERE user_id=?", 
                         (data['plan'], data['status'], data.get('trial_end'), data['id']))
            # Update User Credits & Email (optional but good for corrections)
            cursor.execute("UPDATE users SET credits=?, email=? WHERE id=?", 
                         (data.get('credits', 0), data['email'], data['id']))
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/user/delete', methods=['POST'])
@admin_required
def admin_delete_user():
    user_id = request.json.get('id')
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/generate_bulk', methods=['POST'])
@admin_required
def admin_generate_bulk():
    count = int(request.json.get('count', 1))
    days = int(request.json.get('days', 30))
    new_keys = []
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for _ in range(count):
            key = str(uuid.uuid4()).upper()
            cursor.execute("INSERT INTO licenses (key, notes, created_at) VALUES (?, ?, ?)", 
                         (key, f"Generated Bulk ({days} days)", datetime.datetime.now().isoformat()))
            new_keys.append(key)
        conn.commit()
    return jsonify({"status": "success", "keys": new_keys})

@app.route('/admin/download_db')
@admin_required
def admin_download_db():
    try:
        if os.path.exists(DB_FILE):
            return send_file(DB_FILE, as_attachment=True, download_name='licenses.db')
        return jsonify({"error": "Database file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/list')
@admin_required
def admin_list_keys():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM licenses ORDER BY created_at DESC")
        return jsonify([dict(zip(['key','status','hwid','created','expiry','notes'], r)) for r in cursor.fetchall()])

# --- SYSTEM & SPA ---

@app.route('/health')
def health(): return jsonify({"status": "healthy", "version": "v25_PRODUCTION_STABILITY_PUSH", "time": datetime.datetime.now().isoformat()})

@app.route('/download')
def download_app():
    """Smart binary distribution redirect (v25) - Fallback to local installer if no URL set"""
    download_url = os.getenv("DOWNLOAD_URL")
    if download_url:
        return redirect(download_url)
    
    # Fallback to local installer
    local_installer = 'Nebula-Installer.zip'
    if os.path.exists(os.path.join(STATIC_SITE_DIR, local_installer)):
        return redirect(f'/{local_installer}')
        
    return jsonify({
        "status": "pending",
        "message": "Public Beta download link is currently being updated. Please check back in a moment or contact support."
    }), 503

@app.route('/')
def index_fallback():
    try:
        return send_from_directory(STATIC_SITE_DIR, 'index.html')
    except:
        return jsonify({"status": "Nebula API Running", "version": "v16_FIX_2"})

@app.route('/<path:path>')
def catch_all(path):
    # This prevents the website from intercepting API calls
    # Stricter prefix check (login/, auth/, api/, static/, google/)
    if any(path.startswith(prefix) for prefix in ['api/', 'auth/', 'login/', 'static/', 'google/']):
        return jsonify({"error": "Not Found", "message": "API endpoint not found", "path": path}), 404
        
    file_path = os.path.join(STATIC_SITE_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(STATIC_SITE_DIR, path)
    
    try:
        return send_from_directory(STATIC_SITE_DIR, 'index.html')
    except:
        return "Frontend not found", 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
