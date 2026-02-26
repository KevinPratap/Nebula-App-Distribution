import os
import sys
import io
import json
import threading
import time
import numpy as np
import traceback

# Stability Fixes for Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1" 

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

    def _buffer_watchdog(self):
        while True:
            time.sleep(0.1) # v20.5 high-frequency check
            if not self.transcript_buffer: continue
            
            time_since_last = time.time() - self.last_transcript_time
            combined_text = " ".join(self.transcript_buffer).strip()
            
            is_question = any(q in combined_text.lower() for q in ["?", "what", "how", "why", "when", "can you", "could you", "tell me"])
            
            
            should_trigger = False
            if "?" in combined_text: # INSTANT TRIGGER (v20.5)
                should_trigger = True
            elif is_question and time_since_last > 1.0: # More breathing room (v21.2)
                should_trigger = True
            elif time_since_last > 3.0: # More breathing room for statements
                should_trigger = True
                
            if should_trigger:
                if self.ai.is_generating:
                    self.current_query += " " + combined_text
                else:
                    self.current_query = combined_text
                
                sys.stderr.write(f"DEBUG: Triggering AI with: \"{self.current_query}\"\n")
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
            self.ai.resume_context = payload
            self.send_to_electron("status", {"msg": "Context Synced"})

        elif action == "get-settings":
            self.send_to_electron("settings-data", self.settings.settings)

        elif action == "update-setting":
            self.settings.set(payload.get("key"), payload.get("val"))
            if payload.get("key") == "expert_mode":
                self.ai.set_expert_mode(payload.get("val"))

        elif action == "fake-transcript":
            self.on_transcript(payload, "Manual")

if __name__ == "__main__":
    engine = SidecarEngine()
    engine.listen_for_commands()
