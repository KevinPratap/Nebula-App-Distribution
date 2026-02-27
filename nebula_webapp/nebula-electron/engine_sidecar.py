import os
import sys
import io
import json
import threading
import time
import numpy as np
import traceback
import re

# Stability Fixes for Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1" 

try:
    import pypdf
    from docx import Document
except ImportError:
    pypdf = None
    Document = None

if sys.stdout: sys.stdout.reconfigure(line_buffering=True)
if sys.stdin: sys.stdin.reconfigure(line_buffering=True)

from core.audio_service import AudioService
from core.ai_service import AIService
from core.settings_manager import SettingsManager
from monetization_manager import MonetizationManager

class SidecarEngine:
    def __init__(self):
        sys.stderr.write("DEBUG: SidecarEngine v16.1 (Auth+Intel) START\n")
        sys.stderr.flush()
        
        self.settings = SettingsManager()
        self.ai = AIService()
        self.audio = AudioService(use_loopback=True, source_label="Internal Audio")
        
        # v16.0 Intelligence State
        self.transcript_buffer = [] 
        self.last_transcript_time = 0
        self.current_query = "" 
        self.last_trigger_time = 0      # v26.0 Joining logic
        self.last_trigger_text = ""      # v26.0 Joining logic
        
        self.audio.on_transcript_callback = self.on_transcript
        self.ai.on_response_callback = self.on_ai_response
        self.ai.on_chunk_callback = self.on_ai_chunk
        self.ai.on_error_callback = self.on_ai_error
        
        MonetizationManager.sync_server_time()
        self.sync_ai_keys()
        
        # Preload and Start Threads
        self.audio.preload()
        threading.Thread(target=self.stream_volume, daemon=True).start()
        threading.Thread(target=self._buffer_watchdog, daemon=True).start()

        sys.stderr.write("DEBUG: SidecarEngine ready.\n")
        sys.stderr.flush()

    def send_to_electron(self, msg_type, payload):
        try:
            print(json.dumps({"type": msg_type, "payload": payload}))
            sys.stdout.flush()
        except: pass

    def sync_ai_keys(self):
        try:
            config = MonetizationManager.get_ai_config()
            if config:
                self.ai.groq_key   = config.get('GROQ_API_KEY') or config.get('GROQ_KEY') or ""
                self.ai.gemini_key = config.get('GEMINI_API_KEY') or config.get('GEMINI_KEY') or ""
                self.ai.openai_key = config.get('OPENAI_API_KEY') or config.get('OPENAI_KEY') or ""
                self.audio.groq_key = self.ai.groq_key
                self.send_to_electron("status", {"msg": "AI Keys Ready"})
        except: pass

    def on_transcript(self, text, source):
        if text.startswith("@SYSTEM:"):
            self.send_to_electron("status", {"msg": text.replace("@SYSTEM: ", "")})
            return

        junk = ["[", "(", "music", "noise", "silence", "thank you", "watching", "youtube"]
        if any(m in text.lower() for m in junk) and len(text) < 40: return

        sys.stderr.write(f"DEBUG: Heard fragment: \"{text}\"\n")
        sys.stderr.flush()
        
        self.transcript_buffer.append(text)
        self.last_transcript_time = time.time()
        
        if self.ai.is_generating:
            sys.stderr.write("DEBUG: Interruption detected! Merging context...\n")
            sys.stderr.flush()
        
        self.send_to_electron("transcript", {"text": text, "source": source, "buffered": True})

    def _clean_stutters(self, text):
        if not text: return ""
        # Deduplicate adjacent identical words/phrases (v26.0)
        text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(\w+\s+\w+)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
        return text

    def _is_fragment(self, text):
        t = text.strip().lower()
        if not t: return True
        # Ends in a preposition or connecting word
        if t.split()[-1] in ["the", "a", "an", "is", "are", "of", "to", "in", "with", "and", "or", "for", "from", "at", "by"]:
            return True
        # Very short and no question word
        words = t.split()
        if len(words) < 3 and not any(kw in t for kw in ["what", "how", "why", "who", "when", "?", "explain"]):
            return True
        return False

    def _buffer_watchdog(self):
        while True:
            time.sleep(0.1) 
            if not self.transcript_buffer: continue
            
            now = time.time()
            time_since_last = now - self.last_transcript_time
            combined_text = " ".join(self.transcript_buffer).strip()
            
            is_question = any(q in combined_text.lower() for q in ["?", "what", "how", "why", "when", "can you", "could you", "tell me", "explain", "describe"])
            
            should_trigger = False
            # Determine threshold
            threshold = 1.0 if is_question else 3.0
            if self._is_fragment(combined_text):
                threshold *= 2.0 # Wait longer for fragments (v26.0)

            if "?" in combined_text: # INSTANT TRIGGER
                should_trigger = True
            elif time_since_last > threshold:
                should_trigger = True
                
            if should_trigger:
                combined_text = self._clean_stutters(combined_text)
                
                # Contextual Coalescing (v26.0)
                if now - self.last_trigger_time < 4.0:
                    sys.stderr.write(f"DEBUG: Coalescing with last trigger: {self.last_trigger_text}\n")
                    self.current_query = (self.last_trigger_text + " " + combined_text).strip()
                else:
                    self.current_query = combined_text
                
                # Clean query one more time after merge
                self.current_query = self._clean_stutters(self.current_query)
                self.last_trigger_time = now
                self.last_trigger_text = self.current_query

                sys.stderr.write(f"DEBUG: Triggering AI: \"{self.current_query}\"\n")
                sys.stderr.flush()
                trigger_q = self.current_query
                self.transcript_buffer = []
                self.send_to_electron("status", {"msg": "Nebula: Thinking..."})
                self.ai.generate_response(trigger_q)

    def on_ai_response(self, response, mode=""):
        self.send_to_electron("ai-response", {
            "text": response, 
            "provider": "Groq", 
            "strategy": mode,
            "trigger_question": self.current_query # Restore History (v21.0)
        })
        self.send_to_electron("status", {"msg": "Nebula Ready"})
        self.current_query = ""

    def on_ai_chunk(self, token, mode):
        self.send_to_electron("ai-chunk", {"text": token, "strategy": mode})

    def on_ai_error(self, error):
        self.send_to_electron("error", {"msg": f"AI Error: {error}"})
        self.send_to_electron("status", {"msg": "Nebula Ready"})

    def stream_volume(self):
        while True:
            vol = getattr(self.audio, 'current_volume', 0) if self.audio.is_listening else 0
            self.send_to_electron("volume", {"level": vol})
            time.sleep(0.1)

    def listen_for_commands(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line: break
                self.handle_command(json.loads(line))
            except: pass

    def handle_command(self, cmd):
        action, payload = cmd.get("action"), cmd.get("payload")
        
        if action == "toggle-listening":
            if bool(payload): self.audio.start()
            else: self.audio.stop()
        
        elif action == "fetch-account":
            active, data = MonetizationManager.validate_session()
            self.send_to_electron("account-info", data)
            if active:
                self.sync_ai_keys() # Ensure keys are ready when session restored
        
        elif action == "login":
            success, msg = MonetizationManager.login(payload.get("email"), payload.get("password"))
            self.send_to_electron("auth-complete", {"success": success, "message": msg})
            if success: self.sync_ai_keys()

        elif action == "login-token":
            # Direct token login (v16.1)
            MonetizationManager.save_session(payload.get("token"))
            active, data = MonetizationManager.validate_session()
            self.send_to_electron("auth-complete", {"success": active, "message": "Logged in via Token"})
            if active: 
                self.send_to_electron("account-info", data)
                self.sync_ai_keys()

        elif action == "login-google":
            MonetizationManager.initiate_google_login(payload)
        
        elif action == "login-github":
            MonetizationManager.initiate_github_login(payload)

        elif action == "check-auth":
            if MonetizationManager.check_google_login(payload):
                active, data = MonetizationManager.validate_session()
                self.send_to_electron("auth-complete", {"success": True, "message": "OAuth Success"})
                self.send_to_electron("account-info", data)
                self.sync_ai_keys()

        elif action == "logout":
            if os.path.exists(MonetizationManager.SESSION_FILE):
                os.remove(MonetizationManager.SESSION_FILE)
            self.send_to_electron("status", {"msg": "Logged Out"})

        elif action == "get-session-status":
            active = MonetizationManager.is_session_active_locally()
            remaining = MonetizationManager.get_session_remaining_seconds()
            self.send_to_electron("session-status", {"active": active, "remaining_seconds": remaining})

        elif action == "start-session":
            # Deduct credit and start the 15-min window
            success, msg, credits = MonetizationManager.consume_credit()
            if success:
                MonetizationManager.set_session_active_locally(minutes=15)
                remaining = MonetizationManager.get_session_remaining_seconds()
                self.send_to_electron("session-started", {"success": True, "remaining_seconds": remaining})
                self.send_to_electron("account-info", {"credits": credits})
            else:
                self.send_to_electron("session-started", {"success": False, "message": msg})

        elif action == "update-context":
            if payload or not self.ai.resume_context:
                self.ai.resume_context = payload
                self.send_to_electron("status", {"msg": "Context Synced"})
                sys.stderr.write(f"DEBUG: Context updated ({len(payload)} chars)\n")
            else:
                sys.stderr.write("DEBUG: Ignored empty context update (keep existing)\n")
            sys.stderr.flush()

        elif action == "parse-file":
            path = payload
            text = self._extract_text_from_file(path)
            if text:
                self.ai.resume_context = text
                self.send_to_electron("context-fetched-received", {"text": text})
                self.send_to_electron("status", {"msg": "File Parsed & Synced"})
            else:
                self.send_to_electron("error-received", {"msg": "Failed to parse file format"})

        elif action == "fetch-context":
            # URL Scraping logic (v30.0)
            url = payload
            threading.Thread(target=self._scrape_url, args=(url,), daemon=True).start()

        elif action == "get-settings":
            self.send_to_electron("settings-data", self.settings.settings)

        elif action == "update-setting":
            self.settings.set(payload.get("key"), payload.get("val"))
            if payload.get("key") == "expert_mode":
                self.ai.set_expert_mode(payload.get("val"))

        elif action == "fake-transcript":
            self.on_transcript(payload, "Manual")

    def _extract_text_from_file(self, path):
        sys.stderr.write(f"DEBUG: Extracting text from: {path}\n")
        sys.stderr.flush()
        try:
            ext = os.path.splitext(path)[1].lower()
            sys.stderr.write(f"DEBUG: Extension detected: {ext}\n")
            sys.stderr.flush()
            if ext == '.txt':
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif ext == '.pdf':
                if pypdf:
                    reader = pypdf.PdfReader(path)
                    text = ""
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                    sys.stderr.write(f"DEBUG: PDF Extraction complete. Chars: {len(text)}\n")
                    sys.stderr.flush()
                    return text
                sys.stderr.write("DEBUG: pypdf library NOT AVAILABLE\n")
                sys.stderr.flush()
                return "PDF library not available"
            elif ext in ['.doc', '.docx']:
                if Document:
                    doc = Document(path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    sys.stderr.write(f"DEBUG: Word Extraction complete. Chars: {len(text)}\n")
                    sys.stderr.flush()
                    return text
                sys.stderr.write("DEBUG: python-docx library NOT AVAILABLE\n")
                sys.stderr.flush()
                return "Word library not available"
            return None
        except Exception as e:
            sys.stderr.write(f"ERROR parsing file {path}: {str(e)}\n")
            sys.stderr.flush()
            return None

    def _scrape_url(self, url):
        try:
            self.send_to_electron("status", {"msg": "Scraping URL..."})
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code == 200:
                # Remove script/style tags with regex
                from re import sub
                text = sub(r'<(script|style).*?>.*?</\1>', '', resp.text, flags=sub('D', '', 'is'))
                # Pull visible text
                text = sub(r'<.*?>', ' ', text)
                text = sub(r'\s+', ' ', text).strip()
                # Safeguard length
                text = text[:5000]
                self.send_to_electron("context-fetched", {"text": text, "url": url})
                self.send_to_electron("status", {"msg": "URL Context Parsed"})
                # Auto-sync it to AI service
                self.ai.resume_context = text
            else:
                self.send_to_electron("error", {"msg": f"URL Load Failed: {resp.status_code}"})
                self.send_to_electron("status", {"msg": "Nebula Ready"})
        except Exception as e:
            self.send_to_electron("error", {"msg": f"Scrape Error: {str(e)}"})
            self.send_to_electron("status", {"msg": "Nebula Ready"})

if __name__ == "__main__":
    engine = SidecarEngine()
    engine.listen_for_commands()
