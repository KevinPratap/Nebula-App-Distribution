import traceback
import sys

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    with open("app_crash_log.txt", "a") as f:
        f.write("\n--- CRASH LOG ---\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    print("CRASH DETECTED! Check app_crash_log.txt")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

import os
import sys
import uuid
import locale
import threading
import wave
import io
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageOps
import json
import requests
import re
import queue
import platform

# Windows-specific imports and constants
from monetization_manager import MonetizationManager

try:
    import speech_recognition as sr
except ImportError:
    sr = None
    print("WARNING: speech_recognition not found. Transcription will not work.")

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    # V16: Force DPI Awareness to prevent 'scaled-up' launch issues
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass
    
    # Windows 11 DWM Constants for Mica/Transitions/Colors
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWA_MICA_EFFECT = 1029
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWMWA_CAPTION_COLOR = 34
    DWMWA_TEXT_COLOR = 35
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWCP_ROUND = 2

def apply_modern_effects(hwnd, caption_color=0x1E293B):
    """Enable Mica, Immersive Dark Mode, and Rounded Corners for Windows 11"""
    if not IS_WINDOWS:
        return
        
    try:
        # Ensure we have the true top-level HWND (GA_ROOT = 2)
        root_hwnd = ctypes.windll.user32.GetAncestor(hwnd, 2)
        if not root_hwnd: root_hwnd = hwnd
        
        dwmapi = ctypes.WinDLL("dwmapi")
        user32 = ctypes.WinDLL("user32")
        
        # 1. Force Immersive Dark Mode (Fixes white title bar)
        dark_mode = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(root_hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
        
        # 2. Set Caption Color (Match App Header)
        # Convert hex #1E293B to BGR 0x3B291E
        if isinstance(caption_color, str) and caption_color.startswith('#'):
            r = int(caption_color[1:3], 16)
            g = int(caption_color[3:5], 16)
            b = int(caption_color[5:7], 16)
            caption_color = (b << 16) | (g << 8) | r
            
        color = ctypes.c_int(caption_color)
        dwmapi.DwmSetWindowAttribute(root_hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(color), ctypes.sizeof(color))
        
        # 3. Force Rounded Corners
        corner_pref = ctypes.c_int(2) # DWMWCP_ROUND
        dwmapi.DwmSetWindowAttribute(root_hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
        
        # 4. Enable Mica Backdrop
        backdrop_type = ctypes.c_int(4) # Tabbed (Modern Mica)
        dwmapi.DwmSetWindowAttribute(root_hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type))
        
        # 5. FORCE REFRESH
        user32.SetWindowPos(root_hwnd, 0, 0, 0, 0, 0, 0x0027) # NOSIZE | NOMOVE | NOZORDER | FRAMECHANGED
    except Exception as e:
        pass
# ========== CONFIGURATION & DATA ==========

def relaunch_login_ui():
    """Relaunch the Electron-based React Login UI"""
    import subprocess
    import os
    import sys
    
    # Path to nebula-react-ui project (sibling directory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    react_ui_cwd = os.path.abspath(os.path.join(current_dir, "..", "nebula-react-ui"))
    
    print(f"Relaunching React Login UI in: {react_ui_cwd}")
    
    try:
        if IS_WINDOWS:
            # Launch npm run electron:dev for development
            subprocess.Popen(["npm.cmd", "run", "electron:dev"], cwd=react_ui_cwd, shell=True)
        else:
            subprocess.Popen(["npm", "run", "electron:dev"], cwd=react_ui_cwd, shell=True)
    except Exception as e:
        print(f"Failed to relaunch React UI: {e}")
        
    sys.exit(0)

# Try to import speech_recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_AVAILABLE = False

# Try to import keyboard for global hotkeys
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class AIProvider:
    """Handles AI API calls to Gemini and Groq"""
    
    def __init__(self):
        self.gemini_key = os.environ.get('GEMINI_API_KEY', '')
        self.groq_key = os.environ.get('GROQ_API_KEY', '')
        self.document_context = ""  # Store uploaded documents as context
        self.conversation_history = []  # Remember previous Q&A
        
    def set_document_context(self, text):
        """Set document context for AI responses"""
        self.document_context = text
        
    def add_to_history(self, question, answer):
        """Add Q&A to conversation history"""
        self.conversation_history.append({
            'question': question,
            'answer': answer
        })
        # Keep only last 10 exchanges to avoid token limits
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
            
    def get_history_text(self):
        """Format conversation history for prompt"""
        if not self.conversation_history:
            return ""
        history = "\n--- PREVIOUS Q&A IN THIS INTERVIEW ---\n"
        for i, qa in enumerate(self.conversation_history[-5:], 1):  # Last 5
            history += f"Q{i}: {qa['question']}\nA{i}: {qa['answer'][:200]}...\n\n"
        return history
        
    def get_available_provider(self):
        """Returns the first available AI provider (prefer Groq)"""
        if self.groq_key:
            return 'groq'
        elif self.gemini_key:
            return 'gemini'
        return None

    def _call_gemini_sync(self, prompt):
        """Synchronous Gemini call"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']

    def _call_groq_sync(self, prompt):
        """Synchronous Groq call"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000
        }
        response = requests.post(
            url,
            json=data,
            headers={'Authorization': f'Bearer {self.groq_key}'},
            timeout=15
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']

    def transcribe_audio_groq(self, wav_bytes):
        """Transcribe audio using Groq Whisper (Ultra-Fast)"""
        if not self.groq_key: return None
        
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav"),
                "model": (None, "whisper-large-v3"),
                "language": (None, "en"),
                "response_format": (None, "json")
            }
            headers = {'Authorization': f'Bearer {self.groq_key}'}
            
            response = requests.post(url, files=files, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json().get("text", "")
        except Exception as e:
            print(f"Groq Whisper Error: {e}")
            return None

    def _generate_worker(self, prompt, callback):
        """Worker thread that tries Groq then falls back to Gemini"""
        last_error = "No AI provider available."
        
        print(f"[AI] Generating response. Providers: Groq={'Yes' if self.groq_key else 'No'}, Gemini={'Yes' if self.gemini_key else 'No'}")
        
        # Try Groq first
        if self.groq_key:
            try:
                print("[AI] Calling Groq API...")
                result = self._call_groq_sync(prompt)
                print("[AI] Groq Success!")
                callback(result, None)
                return
            except Exception as e:
                print(f"[AI] Groq failed: {e}")
                last_error = f"Groq failed: {str(e)}"
        
        # Fallback to Gemini
        if self.gemini_key:
            try:
                print("[AI] Calling Gemini API (Fallback)...")
                result = self._call_gemini_sync(prompt)
                print("[AI] Gemini Success!")
                callback(result, None)
                return
            except Exception as e:
                print(f"[AI] Gemini failed: {e}")
                last_error = f"Gemini also failed: {str(e)}"

        print(f"[AI] All providers failed: {last_error}")
        callback(None, last_error)

    def generate(self, prompt, callback):
        """Generate text using available AI providers with automatic fallback"""
        thread = threading.Thread(target=self._generate_worker, args=(prompt, callback))
        thread.daemon = True
        thread.start()
        
    def answer_question(self, question, callback):
        """Answer interview questions based on uploaded resume/documents"""
        history = self.get_history_text()
        
        if not self.document_context:
            prompt = f"""[SYSTEM: OUTPUT ONLY SPOKEN TEXT. NO PREFACE. NO 'HERE IS THE RESPONSE'.]
Interviewer: "{question}"
{history}

Task: Provide the EXACT words I should say.
- Persona: Elite Senior Candidate.
- Tone: Strategic, Confident, Technical.
- Length: 3-5 impact-oriented sentences.
- Accuracy: Fact-check technical complexities.
- CRITICAL: Output ONLY the spoken response."""
        else:
            prompt = f"""Resume/Experience Context:
{self.document_context[:8000]}
{history}
Interviewer Question: "{question}"

Task: Write ONLY the response I should say out loud.
- Role: Senior Executive/Lead Candidate
- Strategy: Connect the technology to the Business Problem it solved.
- Depth: Mention specific challenges (e.g. data drift, scalability, API latency) and how you overcame them.
- Accuracy: For technical queries, provide specific, accurate details. Mention Big Data tools (Spark, SQL) for scale.
- Company Fit: If the interviewer mentions their company (e.g. Microsoft), tailor your answer to their product ecosystem.
- Output ONLY the answer text. No "To answer your question...", no "I'm not sure what you mean"."""
        
        self.generate(prompt, callback)
        
    def answer_live_conversation(self, transcript, callback):
        """Provide professional, high-quality responses based on the LATEST part of the transcript"""
        # Clean transcript of common phonetic nonsense before AI sees it
        hallucinations = ["fish", "fitch", "fishes", "lee", "you you", "thank you for watching"]
        clean_transcript = transcript
        for word in hallucinations:
            pattern = re.compile(rf'\b{word}\b', re.IGNORECASE)
            clean_transcript = pattern.sub("[...]", clean_transcript)

        prompt = f"""[SYSTEM: ROLE = ELITE INTERVIEW ASSISTANT. OUTPUT = SPOKEN WORDS ONLY.]
User Resume Context: {self.document_context[:5000]}

FULL TRANSCRIPT:
{clean_transcript}

TASK: Identify the VERY LAST thing the interviewer said in the transcript above.
- If the last query is about a specific company (e.g. Microsoft), answer THAT specifically.
- If the last query is technical, answer with Senior-level depth and trade-offs.
- IGNORE previous technical discussions (like Big Data) if the interviewer has moved on to a new topic (like Microservices or Microsoft).
- Accuracy: Selection Sort = O(n^2), space = O(1). 
- Tone: Direct and decisive. No "I think" or "Maybe".
- CRITICAL: NO INTRODUCTIONS. NO "Given your question...". NO "Here is a response". JUST THE WORDS."""
        
        self.generate(prompt, callback)


class TechnicalFixer:
    """Corrects common speech recognition errors for technical jargon"""
    
    # Phrases to replace directly (multi-word)
    PHRASE_MAP = {
        "f idf": "TF-IDF",
        "tf idf": "TF-IDF",
        "ci cd": "CI/CD",
        "see eye see dee": "CI/CD",
        "see eye cd": "CI/CD",
        "auto ml": "AutoML",
        "sci kit learn": "Scikit-learn",
        "scikit learn": "Scikit-learn",
        "pi torch": "PyTorch",
        "low code": "Low-code",
        "no code": "No-code",
        "my dear": "TF-IDF"
    }
    
    # Common whole-word misrecognitions
    WORD_MAP = {
        "gf": "TF-IDF",
        "tfidf": "TF-IDF",
        "sql": "SQL",
        "sequel": "SQL",
        "nlp": "NLP",
        "aws": "AWS",
        "ml": "ML",
        "ai": "AI",
        "xgboost": "XGBoost",
        "pytorch": "PyTorch",
        "scikit": "Scikit-learn",
        "api": "API",
        "json": "JSON",
        "rest": "REST",
        "crud": "CRUD",
        "git": "Git"
    }

    @classmethod
    def fix(cls, text):
        """Clean and correct technical terms in text"""
        if not text:
            return text
        
        fixed_text = text
        
        # 1. Handle multi-word phrases (case insensitive, whole phrase)
        # Sort phrases by length descending to catch longer ones first
        sorted_phrases = sorted(cls.PHRASE_MAP.keys(), key=len, reverse=True)
        for phrase in sorted_phrases:
            replacement = cls.PHRASE_MAP[phrase]
            # Use word boundaries to avoid partial matches
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            fixed_text = pattern.sub(replacement, fixed_text)
            
        # 2. Handle whole-word replacements
        words = fixed_text.split()
        final_words = []
        
        for word in words:
            clean_word = word.lower().strip(",.!?")
            if clean_word in cls.WORD_MAP:
                punctuation = word[len(clean_word):] if len(word) > len(clean_word) else ""
                final_words.append(cls.WORD_MAP[clean_word] + punctuation)
            else:
                final_words.append(word)
                
        return " ".join(final_words)


class VoiceListener:
    """Handles speech recognition with WASAPI loopback or Microphone"""
    
    @staticmethod
    def get_audio_devices():
        """Get list of available audio devices (input and output)"""
        devices = {'mics': [], 'speakers': []}
        try:
            import soundcard as sc
            # Microphones
            mics = sc.all_microphones()
            for i, mic in enumerate(mics):
                devices['mics'].append({
                    'id': str(mic.id),
                    'name': mic.name,
                    'obj': mic
                })
            # Speakers for loopback
            speakers = sc.all_speakers()
            for i, speaker in enumerate(speakers):
                devices['speakers'].append({
                    'id': str(speaker.id),
                    'name': speaker.name,
                    'obj': speaker
                })
        except Exception as e:
            print(f"Device discovery error: {e}")
        return devices

    def __init__(self, callback, use_loopback=True, source_label="Interviewer", language="en-US", ai_instance=None, device=None, sensitivity=0.020, silence_patience=2.0):
        self.callback = callback
        self.recognizer = sr.Recognizer() if SPEECH_AVAILABLE else None
        self.use_loopback = use_loopback
        self.source_label = source_label
        self.language = language
        self.ai_instance = ai_instance
        self.device = device # Specific soundcard device object or name
        self.sensitivity = sensitivity
        self.silence_patience = silence_patience
        self.is_listening = False
        self.record_thread = None
        self.process_thread = None
        self.recognition_queue = None
        
    def start_listening(self, continuous=False):
        """Start listening. If continuous, it will keep transcribing in chunks."""
        if self.is_listening:
            return
            
        self.is_listening = True
        
        # Queue for passing audio data from recorder thread to processor thread
        import queue
        self.recognition_queue = queue.Queue()
        
        # Start processing thread first
        self.process_thread = threading.Thread(target=self._process_loop, args=(continuous,), daemon=True)
        self.process_thread.start()
        
        # Start recording thread
        self.record_thread = threading.Thread(target=self._record_loop, args=(continuous,), daemon=True)
        self.record_thread.start()
        
    def stop_listening(self):
        """Stop listening"""
        self.is_listening = False
        
    def _record_loop(self, continuous):
        """Producer: Record audio from source and put into queue"""
        import soundcard as sc
        sample_rate = 16000
        
        try:
            if self.use_loopback:
                if self.device:
                    # Specific speaker for loopback
                    source = sc.get_microphone(id=str(self.device.id), include_loopback=True)
                else:
                    # Capture from default speaker (loopback)
                    speaker = sc.default_speaker()
                    source = sc.get_microphone(id=str(speaker.id), include_loopback=True)
            else:
                if self.device:
                    # Specific microphone
                    source = self.device
                else:
                    # Capture from default microphone
                    source = sc.default_microphone()
                
            with source.recorder(samplerate=sample_rate, channels=1) as recorder:
                while self.is_listening:
                    try:
                        # Record small chunks (0.25s)
                        data = recorder.record(numframes=int(sample_rate * 0.25))
                        self.recognition_queue.put(data)
                    except Exception as e:
                        print(f"Record error: {e}")
                        break
        except Exception as e:
            print(f"Source init error: {e}")
            self.callback(None, f"Audio Init Error: {e}", self.source_label)

    def _process_loop(self, continuous):
        """Consumer: Get audio from queue and recognize speech with silence detection"""
        import numpy as np
        
        if not SPEECH_AVAILABLE:
            print("Speech recognition not available")
            return

        if not self.recognizer:
            self.recognizer = sr.Recognizer()
        
        self.recognizer.energy_threshold = 300
        
        frames = []
        silence_counter = 0
        energy_threshold = 0.020  # V27: Increased from 0.012 to ignore noise floor hallucinations
        
        while self.is_listening or not self.recognition_queue.empty():
            try:
                # Get data with timeout
                data = self.recognition_queue.get(timeout=0.1)
                frames.append(data)
                
                # V25: Adaptive Silence Detection
                rms = np.sqrt(np.mean(data**2))
                # print(f"[{self.source_label}] RMS: {rms:.4f} (Thresh: {self.sensitivity})") # Debug noisy
                if rms < self.sensitivity:
                    silence_counter += 1
                else:
                    silence_counter = 0
                
                if continuous:
                    # Trigger if pause detected (min 1.0s audio) OR we hit the 10s fallback
                    # patience_frames = self.silence_patience / 0.25 (chunk size)
                    patience_frames = int(self.silence_patience * 4)
                    should_process = (len(frames) >= 4 and silence_counter >= patience_frames) or (len(frames) >= 40)
                    
                    if should_process:
                        self._process_frames(frames, sample_rate)
                        frames = []
                        silence_counter = 0
                # If not continuous, just keep accumulating until loop breaks
                    
            except queue.Empty:
                # If listening stopped and queue empty, break
                if not self.is_listening:
                    break
        
        # Process remaining frames
        if frames:
            self._process_frames(frames, sample_rate)

    def _process_frames(self, frames, sample_rate):
        if not frames:
            if self.callback: self.callback(None, "Empty audio buffer", self.source_label)
            return
            
        import numpy as np
        
        try:
            audio_data = np.concatenate(frames)
            # V27: Guard against low-signal chunks (Whisper hallucinations)
            avg_rms = np.sqrt(np.mean(audio_data**2))
            if avg_rms < 0.015: # Total silence or near-silence
                print(f"[{self.source_label}] Silence detected (RMS: {avg_rms:.4f})")
                self.callback(None, "No speech detected (Silence)", self.source_label)
                return
                
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            wav_buffer.seek(0)
            
            text = None
            if SPEECH_AVAILABLE:
                # V26: Try Groq Whisper First (If available)
                if hasattr(self, 'ai_instance') and self.ai_instance and self.ai_instance.groq_key:
                    try:
                        text = self.ai_instance.transcribe_audio_groq(wav_buffer.getvalue())
                        if text: print(f"[{self.source_label}] Groq Result: {text}")
                    except Exception as e:
                        print(f"[{self.source_label}] Groq Transcription Error: {e}")
                
                # Fallback to Google if Groq failed or unavailable
                if not text:
                    try:
                        with sr.AudioFile(wav_buffer) as sr_source:
                            audio = self.recognizer.record(sr_source)
                        text = self.recognizer.recognize_google(audio, language=self.language)
                        if text: print(f"[{self.source_label}] Google Result: {text}")
                    except sr.UnknownValueError:
                        print(f"[{self.source_label}] Google could not understand audio")
                    except Exception as e:
                        print(f"[{self.source_label}] Google Fallback Error: {e}")
            
            if text:
                self.callback(text, None, self.source_label)
            else:
                self.callback(None, "No speech recognized", self.source_label)
                
        except Exception as e:
            print(f"[{self.source_label}] Processing Error: {e}")
            self.callback(None, f"Transcription error: {str(e)}", self.source_label)

class DualVoiceListener:
    """Combines two VoiceListeners for simultaneous Mic + Speaker monitoring"""
    def __init__(self, callback, language="en-US", ai_instance=None, mic_device=None, speaker_device=None, sensitivity=0.020, silence_patience=2.0):
        self.interviewer_listener = VoiceListener(callback, use_loopback=True, source_label="Interviewer", language=language, ai_instance=ai_instance, device=speaker_device, sensitivity=sensitivity, silence_patience=silence_patience)
        self.me_listener = VoiceListener(callback, use_loopback=False, source_label="Me", language=language, ai_instance=ai_instance, device=mic_device, sensitivity=sensitivity, silence_patience=silence_patience)
        
    def start(self):
        self.interviewer_listener.start_listening(continuous=True)
        self.me_listener.start_listening(continuous=True)
        
    def stop(self):
        self.interviewer_listener.stop_listening()
        self.me_listener.stop_listening()

class Splash:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0F172A")
        
        # Center the splash screen
        width, height = 400, 250
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Modern UI Label
        label = tk.Label(self.root, text="N E B U L A", font=("Segoe UI Variable Display", 32, "bold"), fg="#A78BFA", bg="#0F172A")
        label.pack(expand=True, pady=(40, 0))
        
        tagline = tk.Label(self.root, text="Waking up the AI...", font=("Segoe UI Variable Text", 12), fg="#94A3B8", bg="#0F172A")
        tagline.pack(expand=True, pady=(0, 40))
        
        self.root.update()

    def destroy(self):
        self.root.destroy()

class MeetingPrompter:
    # --- GLOBAL FONT SETTINGS (PREMIUM / ELEGANT) ---
    FONT_DISPLAY = "Segoe UI Variable Display" if IS_WINDOWS else "SF Pro Display"
    FONT_TEXT = "Segoe UI Variable Text" if IS_WINDOWS else "SF Pro Text"

    def __init__(self, sub_info=None, splash=None):
        self.splash = splash
        # Set Appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Nebula Desktop")
        self.root.withdraw() # Start hidden
        
        # V15: Nuclear Rounding Mask
        if IS_WINDOWS:
            self.root.configure(bg="#000001")
            self.root.wm_attributes("-transparentcolor", "#000001")
        
        self.root.geometry("980x680+100+100")
        self.root.minsize(950, 600)
        self.root.attributes('-topmost', True) 
        
        self.sub_info = sub_info or {"plan": "FREE_TRIAL", "status": "ACTIVE", "trial_end": "N/A"}
        
        # Theme Tokens: "Glass Harmony"
        self.clr_bg = "#0F172A"       
        self.clr_panel = "#1E293B"    
        self.clr_accent = "#A78BFA"   
        self.clr_neon = "#22D3EE"     
        self.clr_pink = "#EC4899"     
        self.clr_danger = "#F87171"   
        self.clr_success = "#34D399"  
        self.clr_text = "#F8FAFC"     
        self.clr_dim = "#94A3B8"      
        self.clr_glow = "#A78BFA"     
        self.corner_radius = 32       
        
        self.root.configure(fg_color=self.clr_bg)
        
        # Master State Variable Init (CRITICAL: Must be before setup_ui)
        self.ghost_var = tk.BooleanVar(value=False)
        self.font_size = 18
        self.transparency = 1.0       
        self.zen_opacity = 0.85        
        self.stealth_var = tk.BooleanVar(value=False) # Fix: Missing stealth_var
        self.is_voice_active = False
        self.space_held = False
        self.voice_listener = None
        self.dual_listener = None
        self.live_assist_mode = tk.BooleanVar(value=False)
        self.is_live_assist_active = False
        self.live_transcript = []
        self.last_ai_update_time = 0
        self.interview_mode = False 
        self._drag_data = {"x": 0, "y": 0}
        self.pending_speech = {"Interviewer": "", "Me": ""}
        self.speech_timers = {"Interviewer": None, "Me": None}
        self.silence_delay = 2000 # V29: Increased to 2.0s to allow full sentence capture
        self.is_locked = False
        self.credits = 0
        self.is_session_paid = False
        self.active_popups = {} # V9: Track open popups for toggle behavior
        self.languages = {
            "Auto-Detect": "auto",
            "English (US)": "en-US",
            "English (UK)": "en-GB",
            "Hindi": "hi-IN",
            "Spanish": "es-ES",
            "French": "fr-FR",
            "German": "de-DE",
            "Japanese": "ja-JP"
        }
        self.selected_lang = tk.StringVar(value="Auto-Detect")
        
        # Audio Settings
        self.mic_id = tk.StringVar(value="Default")
        self.speaker_id = tk.StringVar(value="Default")
        self.sensitivity = tk.DoubleVar(value=0.020) # RMS Threshold
        self.silence_patience = tk.DoubleVar(value=2.0) # Seconds
        
        # Load persisted settings
        self.load_settings()

        # Background Loading Assets
        self.ai = None # Loaded in background
        threading.Thread(target=self._init_bg_assets, daemon=True).start()

        # V16: Initial sync to settle scale/DPI
        self.root.update()
        
        # UI Construction
        self.setup_ui()
        
        # Rounding/Effects
        if IS_WINDOWS:
            self.root.after(100, lambda: apply_modern_effects(self.root.winfo_id(), caption_color="#000000"))

        self.poll_subscription_status() # V30: Immediate sync on startup
        self.check_subscription_gating()
        self.bind_hotkeys()
        self.root.after(30000, self.poll_subscription_status)

        
        # V19: Auto-launch guide on startup
        self.root.after(1000, self.show_controls_guide)

    def load_settings(self):
        """Load settings from settings.json"""
        if os.path.exists(MonetizationManager.SETTINGS_FILE):
            try:
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.mic_id.set(data.get("mic_id", "Default"))
                    self.speaker_id.set(data.get("speaker_id", "Default"))
                    self.sensitivity.set(data.get("sensitivity", 0.020))
                    self.silence_patience.set(data.get("silence_patience", 2.0))
                    self.selected_lang.set(data.get("language", "Auto-Detect"))
                    self.font_size = data.get("font_size", 18)
                    self.zen_opacity = data.get("opacity", 0.85)
                    self.stealth_var.set(data.get("stealth", False))
                    theme = data.get("theme", "Dark")
                    ctk.set_appearance_mode(theme)
            except: pass

    def save_settings(self):
        """Save current settings to settings.json"""
        try:
            data = {}
            if os.path.exists(MonetizationManager.SETTINGS_FILE):
                with open(MonetizationManager.SETTINGS_FILE, "r") as f:
                    try: data = json.load(f)
                    except: data = {}
            
            data.update({
                "mic_id": self.mic_id.get(),
                "speaker_id": self.speaker_id.get(),
                "sensitivity": self.sensitivity.get(),
                "silence_patience": self.silence_patience.get(),
                "language": self.selected_lang.get(),
                "font_size": self.font_size,
                "opacity": self.zen_opacity,
                "stealth": self.stealth_var.get(),
                "theme": ctk.get_appearance_mode()
            })
            
            with open(MonetizationManager.SETTINGS_FILE, "w") as f:
                json.dump(data, f)
        except: pass

    def run(self):
        self.root.mainloop()
    
    def logout(self):
        """Logout and relaunch the React Login UI"""
        from auth_manager import AuthManager
        import sys
        
        try:
            # Clear local session
            AuthManager.clear_saved_credentials()
            
            # Stop the app and relaunch the login UI
            relaunch_login_ui()
            
        except Exception as e:
            print(f"Logout Error: {e}")
            self.root.destroy()
            sys.exit(0)
            
    def on_relogin(self, user_info):
        """Called when user successfully logs in again"""
        # Store info
        if user_info:
            self.sub_info = user_info
        
        # Clear Login Frame
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        
        # Clear any other leftovers
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Re-initialize UI
        self.setup_ui()
        
        # V9: Bind Hotkeys LAST (after UI elements exist)
        self.bind_hotkeys()
        
        # Re-check subscription
        if hasattr(self, 'check_subscription_gating'):
            self.check_subscription_gating()

    def get_selected_device(self, name, is_speaker=False):
        """Find soundcard device object by name"""
        if name == "Default":
            return None
        try:
            devices = VoiceListener.get_audio_devices()
            key = 'speakers' if is_speaker else 'mics'
            for d in devices[key]:
                if d['name'] == name:
                    return d['obj']
        except: pass
        return None
        
    def setup_ui(self):
        # Base Layout: Side Menu + Main Hub
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # --- Main Hub --- V15: Transparent frame to show Nebula Background
        
        # 0. Solid Background with Ambient Glows
        self.main_hub = ctk.CTkFrame(self.root, corner_radius=0, fg_color="#0F172A")
        self.main_hub.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_hub.grid_rowconfigure(1, weight=1)
        self.main_hub.grid_columnconfigure(0, weight=1)

        # Top Header (Dash) - V17: Glassmorphic Slate
        self.header = ctk.CTkFrame(self.main_hub, height=80, corner_radius=40, 
                                  fg_color="#1E293B", border_width=1, border_color="#334155")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 20), padx=5)
        
        # Profile Button (Top Left)
        # Profile Button (Top Left) - Simplified & Clean
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(base_path, "assets", "default_avatar.png")
            
            # Create a simple, clean container for the profile
            self.pfp_container = ctk.CTkFrame(self.header, width=48, height=48, 
                                            corner_radius=24, fg_color="transparent")
            self.pfp_container.grid(row=0, column=0, padx=(20, 10), pady=10)
            
            if os.path.exists(img_path):
                # Load and circular crop
                original = Image.open(img_path).convert("RGBA")
                # Resize high quality
                original = original.resize((48, 48), Image.Resampling.LANCZOS)
                
                # Create mask
                mask = Image.new("L", (48, 48), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 48, 48), fill=255)
                
                # Apply mask
                circular = Image.new("RGBA", (48, 48), (0,0,0,0))
                circular.paste(original, (0,0), mask=mask)
                
                self.profile_img = ctk.CTkImage(circular, size=(40, 40))
                
                # Profile Button
                self.btn_profile = ctk.CTkButton(self.pfp_container, text="", image=self.profile_img, 
                                                width=40, height=40, corner_radius=20, 
                                                fg_color="#334155", hover_color="#475569", 
                                                border_width=2, border_color="#A78BFA",
                                                command=self.show_profile_menu)
                self.btn_profile.pack(expand=True, fill="both")
            else:
                raise FileNotFoundError("No avatar")
                
        except Exception:
            # Clean Text Fallback
            self.btn_profile = ctk.CTkButton(self.header, text="👤", width=40, height=40, corner_radius=20, 
                                            fg_color="#334155", hover_color="#475569", 
                                            border_width=2, border_color="#A78BFA",
                                            font=ctk.CTkFont(size=20), command=self.show_profile_menu)
            self.btn_profile.grid(row=0, column=0, padx=(20, 10), pady=10)

        # Configure Header Grid
        self.header.grid_columnconfigure(0, weight=0, minsize=110) # V31: Increased for overlap safety
        self.header.grid_columnconfigure(1, weight=1)             # Center (Logo) - Flexible
        self.header.grid_columnconfigure(2, weight=0, minsize=620) # Right (Actions tray) - Solid Space


        # --- Navigation & Profile (Left Tier) ---
        # (Handled already in the Triple-Lock init)

        # --- Premium Branding (Center Tier) ---
        self.brand_container = ctk.CTkFrame(self.header, fg_color="transparent")
        self.brand_container.grid(row=0, column=1, sticky="")
        
        # Try to load Logo Image
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo_header.png")
            if os.path.exists(logo_path):
                 pil_logo = Image.open(logo_path)
                 # Calculate aspect ratio
                 aspect = pil_logo.width / pil_logo.height
                 target_h = 42
                 target_w = int(target_h * aspect)
                 
                
                 self.logo_img = ctk.CTkImage(pil_logo, size=(target_w, target_h))
                 
                 # USER REQUEST: "just the logo nothing written"
                 # Always show just the image, never append text.
                 self.brand_lbl = ctk.CTkLabel(self.brand_container, text="", image=self.logo_img)
                 self.brand_lbl.pack()
            else:
                 raise FileNotFoundError
        except:
            # Fallback
            self.brand_lbl = ctk.CTkLabel(self.brand_container, text="N E B U L A", 
                                         font=ctk.CTkFont(family=self.FONT_DISPLAY, size=24, weight="bold"), 
                                         text_color="#A78BFA")
            self.brand_lbl.pack()

        # --- Quick Actions (Right Tier - Col 2) ---
        actions_grid = ctk.CTkFrame(self.header, fg_color="transparent")
        actions_grid.grid(row=0, column=2, padx=(10, 35), sticky="e") # V23: Safe Right Margin
        
        
        # 0. Credits Label (V31: Subdued Violet Glow Style - Polished)
        self.credits_pill = ctk.CTkFrame(actions_grid, fg_color="#4C1D95", 
                                        border_width=0, 
                                        corner_radius=18, height=36)
        self.credits_pill.pack(side="right", padx=(10, 0), anchor="center")
        self.credits_pill.pack_propagate(False)
        
        self.credits_lbl = ctk.CTkLabel(self.credits_pill, text="💎 --", 
                                       font=ctk.CTkFont(family=self.FONT_TEXT, size=12, weight="bold"),
                                       text_color="#E9D5FF") # Soft Lavender text
        self.credits_lbl.pack(expand=True)


        # 1. Interview Mode (Far Right)


        self.btn_interview_hdr = ctk.CTkButton(actions_grid, text="INTERVIEW MODE", width=115, height=36, corner_radius=18,
                                              fg_color="transparent", hover_color="#334155", text_color="#A78BFA",
                                              border_width=2, border_color="#A78BFA",
                                              font=ctk.CTkFont(family=self.FONT_TEXT, size=11, weight="bold"), 
                                              command=self.toggle_interview_mode)
        self.btn_interview_hdr.pack(side="right", padx=(10, 0), anchor="center")

        # 1c. Live Assist Toggle
        self.sw_live = ctk.CTkSwitch(actions_grid, text="LIVE ASSIST", variable=self.live_assist_mode,
                                        command=self.on_live_assist_toggle, font=ctk.CTkFont(family=self.FONT_TEXT, size=11, weight="bold"), 
                                        width=100, height=32, progress_color="#10B981")
        self.sw_live.pack(side="right", padx=(10, 5), anchor="center")
# ... (omitted similar lines) ...


        self.sw_ghost = ctk.CTkSwitch(actions_grid, text="GHOST", variable=self.ghost_var,
                                        command=self.toggle_ghost, font=ctk.CTkFont(family=self.FONT_TEXT, size=11, weight="bold"), 
                                        width=75, height=32, progress_color="#A78BFA")
        self.sw_ghost.pack(side="right", padx=(10, 5), anchor="center")

        # 2b. Stealth Toggle
        self.sw_stealth = ctk.CTkSwitch(actions_grid, text="STEALTH", variable=self.stealth_var,
                                        command=self.toggle_stealth, font=ctk.CTkFont(family=self.FONT_TEXT, size=11, weight="bold"), 
                                        width=85, height=32, progress_color=self.clr_neon)
        self.sw_stealth.pack(side="right", padx=(10, 5), anchor="center")
        
        # 3. Resume Upload Pill (V23: Compact width + safer spacing)
        self.upload_pill = ctk.CTkFrame(actions_grid, fg_color="#334155", corner_radius=100, width=220, height=36)
        self.upload_pill.pack(side="right", padx=(15, 5), anchor="center")
        self.upload_pill.pack_propagate(False) 
        
        # Doc Count Circle (Right Side)
        self.doc_count_lbl = ctk.CTkButton(self.upload_pill, text="0", width=28, height=28, corner_radius=14,
                                          fg_color="#0F172A", text_color=self.clr_success, state="disabled",
                                          font=ctk.CTkFont(size=10, weight="bold"), hover=False)
        self.doc_count_lbl.pack(side="right", padx=8)
        
        # Resume Button (Left Side - Expanded)
        self.btn_upload = ctk.CTkButton(self.upload_pill, text="📄 RESUME", image=self.doc_img if hasattr(self, 'doc_img') else None, 
                                       height=30, corner_radius=100, width=180,
                                       fg_color="transparent", hover_color="#475569", 
                                       font=ctk.CTkFont(family=self.FONT_TEXT, size=12, weight="bold"),
                                       command=self.upload_resume)
        self.btn_upload.pack(side="left", padx=5, expand=True, fill="x")
        
        # Content Display - V17: Pro App Radius (48px)
        self.center_hub = ctk.CTkFrame(self.main_hub, fg_color="transparent")
        self.center_hub.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.center_hub.grid_columnconfigure(0, weight=1) 
        self.center_hub.grid_rowconfigure(0, weight=1)    # V18: Allow container expansion

        self.display_container = ctk.CTkFrame(self.center_hub, corner_radius=48, fg_color="#0F172A", border_width=1, border_color="#1E293B")
        self.display_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        self.text_area = ctk.CTkTextbox(
            self.display_container,
            wrap="word",
            font=ctk.CTkFont(family=self.FONT_TEXT, size=self.font_size),
            fg_color="#0F172A",  # Darker background for contrast
            text_color="#F8FAFC",  # White text
            corner_radius=32,     # V12: Matched curvature (was 10)
            border_width=0,
            activate_scrollbars=True
        )
        self.text_area.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Welcome Splash - UPDATED TO MATCH WEBSITE
        # Welcome Splash - UPDATED TO MATCH WEBSITE
        self.text_area.insert("0.0", "Meetings, Mastered.\n\nYour personal interview assistant is ready.\nUpload a document or speak to begin.\n\n" + "━" * 40 + "\n\n🎤 Q: \"Tell me about a time you optimized a slow database query.\"\n\n💬 SAY THIS:\n\nIn my previous role, I identified a bottleneck in our reporting dashboard. I used EXPLAIN ANALYZE to find a missing index on the timestamp column. By adding a composite index and rewriting the join logic, I reduced the query execution time from 12s to roughly 200ms.")
        
        self.text_area.configure(state='disabled')
        
        # No bottom bar - ultra-clean mode
        
        # Floating Back Arrow (Zen Mode Exit) - Subtle blended button
        self.btn_back_zen_frame = ctk.CTkButton(self.main_hub, text="←", 
                                               width=50, height=50, 
                                               corner_radius=25,  # Perfect circle
                                               fg_color="#0F172A",  # Match background
                                               hover_color="#1E293B",
                                               border_width=0,
                                               font=ctk.CTkFont(size=28, weight="bold"),
                                               text_color="#64748B",  # Subtle gray
                                               command=self.toggle_interview_mode)
        
        pass        
        
        pass        

    def calculate_days_left(self, end_date_str):
        try:
            end_date = datetime.datetime.fromisoformat(end_date_str)
            delta = end_date - datetime.datetime.now()
            return max(0, delta.days)
        except: return 0

    def open_razorpay(self):
        """V6: Open Razorpay Payment Link.
        In prod, this opens a pre-generated Razorpay Payment Link with notes.
        """
        import webbrowser
        # Getting user_id from previous session validation or me endpoint
        user_id = getattr(self.root, 'user_id', 'anonymous')
        payment_url = f"https://rzp.io/l/nebula-pro?notes[user_id]={user_id}"
        webbrowser.open(payment_url)

    def check_subscription_gating(self):
        """Lock the app if subscription is not active or trial expired"""
        status = self.sub_info.get("status", "INACTIVE")
        plan = self.sub_info.get("plan", "FREE_TRIAL")
        trial_end = self.sub_info.get("trial_end", "N/A")
        
        should_lock = False
        
        # 1. Check Status & Credits
        if status != "ACTIVE" and self.credits <= 0:
            should_lock = True
            
        # 2. Check Trial Expiration
        elif plan == "FREE_TRIAL" and trial_end != "N/A" and self.credits <= 0:
            days = self.calculate_days_left(trial_end)
            if days <= 0:
                should_lock = True

        
        if should_lock:
            if not self.is_locked:
                self.is_locked = True
                self.text_area.configure(state="normal")
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", "\n\n\n\n      ❌ SUBSCRIPTION REQUIRED\n\n      Your access has ended. Please purchase a\n      subscription to unlock the study assistant.")
                self.text_area.configure(state="disabled")
                self.set_status("PAY TO USE", self.clr_danger)
        else:
            if self.is_locked:
                self.is_locked = False
                self.text_area.configure(state="normal")
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", "Welcome back! Access restored. Upload your context to begin.")
                self.text_area.configure(state="disabled")
                self.set_status("SYSTEM READY", self.clr_success)

    def poll_subscription_status(self):
        """Periodically verify subscription and credits with server"""
        try:
            valid, info = MonetizationManager.validate_session()
            if valid:
                self.sub_info = info
                self.credits = info.get("credits", 0)
                self.check_subscription_gating()
                
                # Update Credits UI
                if hasattr(self, 'credits_lbl'):
                    self.credits_lbl.configure(text=f"💎 {self.credits}")
                
                # Update status display
                if self.sub_info.get("plan") == "FREE_TRIAL" and self.sub_info.get("trial_end") != "N/A":
                    days_left = self.calculate_days_left(self.sub_info.get("trial_end"))
                    self.set_status(f"Trial: {days_left} Days Remaining", "#F59E0B" if self.is_locked else self.clr_success)
                elif "PREMIUM" in self.sub_info.get("plan", ""):
                    if not self.is_locked:
                        self.set_status("PREMIUM ACTIVE", self.clr_success)
                    else:
                        self.set_status("SUSPENDED", self.clr_danger)
        except: pass
        
        # Poll again in 30 seconds
        if self.root.winfo_exists():
            self.root.after(30000, self.poll_subscription_status)
        
    def bind_hotkeys(self):
        """Bind keyboard shortcuts - uses global hotkeys for push-to-talk"""
        # Global hotkeys using keyboard library (works even when app not focused)
        if KEYBOARD_AVAILABLE:
            keyboard.on_press_key('f2', self.on_global_ptt_press)
            keyboard.on_release_key('f2', self.on_global_ptt_release)
            
            # Interview Mode Global Toggle
            keyboard.add_hotkey('ctrl+alt+z', self.toggle_interview_mode)
            keyboard.add_hotkey('ctrl+alt+s', self.toggle_stealth_shortcut)
        
        # Local hotkeys (only when app focused)
        self.root.bind('<Control-q>', lambda e: self.on_close())
        self.root.bind('<Control-s>', lambda e: self.toggle_ghost_shortcut())
        
        # Mouse Dragging for Zen Mode
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.do_drag)
        self.text_area.bind('<Button-1>', self.start_drag, add="+")
        self.text_area.bind('<B1-Motion>', self.do_drag, add="+")
        self.root.bind('<plus>', lambda e: self.change_font_size(2))
        self.root.bind('<equal>', lambda e: self.change_font_size(2))
        self.root.bind('<minus>', lambda e: self.change_font_size(-2))
        
        # Also bind window close button
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def on_close(self):
        """Cleanly close the application"""
        self.is_voice_active = False
        if self.voice_listener:
            self.voice_listener.stop_listening()
        if self.dual_listener:
            self.dual_listener.stop()
        self.root.destroy()
        sys.exit(0)

    def show_profile_menu(self):
        """Show quick profile actions with a roomier look and consolidated tools"""
        # V9: Toggle Off if already open
        if "profile" in self.active_popups and self.active_popups["profile"].winfo_exists():
            self.active_popups["profile"].destroy()
            del self.active_popups["profile"]
            return

        menu = ctk.CTkToplevel(self.root)
        self.active_popups["profile"] = menu
        
        # Cleanup on destroy
        menu.bind("<Destroy>", lambda e: self.active_popups.pop("profile", None) if e.widget == menu else None)
        
        menu.title("")
        # Increased size for consolidated utility
        menu.geometry("320x380")
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        
        # V9: Apply Modern Rounding to Dropdown
        try:
            menu.update()
            hwnd = ctypes.windll.user32.GetParent(menu.winfo_id())
            apply_modern_effects(hwnd)
        except: pass

        try:
            x = self.btn_profile.winfo_rootx()
            y = self.btn_profile.winfo_rooty() + 55
            menu.geometry(f"+{x}+{y}")
        except:
            menu.geometry("+100+100")

        # Main glass frame
        frame = ctk.CTkFrame(menu, fg_color="#1E293B", corner_radius=18, border_width=1, border_color="#334155")
        frame.pack(fill="both", expand=True)

        # --- Account Card Section ---
        email = self.sub_info.get("email", "User")
        plan = self.sub_info.get("plan", "FREE_TRIAL")
        
        account_card = ctk.CTkFrame(frame, fg_color="#0F172A", corner_radius=15, border_width=1, border_color="#1E293B")
        account_card.pack(fill="x", padx=12, pady=(12, 8))
        
        display_email = email if len(email) < 25 else email[:22] + "..."
        ctk.CTkLabel(account_card, text=display_email, font=ctk.CTkFont(family=self.FONT_DISPLAY, size=12, weight="bold"), 
                     text_color="#F8FAFC").pack(pady=(15, 2), padx=15)
        
        badge_container = ctk.CTkFrame(account_card, fg_color="transparent")
        badge_container.pack(pady=(0, 15))
        
        if "PREMIUM" in plan:
            # Elegant Smooth Pill Badge (Full Radius)
            badge = ctk.CTkButton(badge_container, text="  ✦ PREMIUM PRO  ",
                                 width=130, height=30, corner_radius=15,
                                 fg_color="#059669", # Emerald Green
                                 hover_color="#059669", 
                                 text_color="#ECFDF5",
                                 font=ctk.CTkFont(family=self.FONT_TEXT, size=10, weight="bold"),
                                 state="disabled")
            badge.pack(pady=10)
        else:
            self.btn_upgrade_menu = ctk.CTkButton(badge_container, text="💎 GET PREMIUM", 
                                                 fg_color="#F59E0B", hover_color="#D97706",
                                                 text_color="#0F172A", corner_radius=12, height=32,
                                                 font=ctk.CTkFont(size=10, weight="bold"),
                                                 command=lambda: [menu.destroy(), self.open_razorpay()])
            self.btn_upgrade_menu.pack(pady=2, padx=15)

        # --- Utility Section ---
        btn_params = {"fg_color": "transparent", "hover_color": "#334155", "anchor": "w", "height": 38, 
                      "font": ctk.CTkFont(family="Segoe UI Variable Text", size=12)}
        
        # Manual Query is often used, so keep it accessible
        ctk.CTkButton(frame, text="  ❓  Ask Manual Query",
                     command=lambda: [menu.destroy(), self.ask_manual_question()], **btn_params).pack(fill="x", padx=10, pady=1)

        # Settings
        ctk.CTkButton(frame, text="  ⚙️  Settings & License",
                     command=lambda: [menu.destroy(), self.show_settings_window()], **btn_params).pack(fill="x", padx=10, pady=1)
        
        ctk.CTkButton(frame, text="  ✦  Save Session",
                     command=lambda: [menu.destroy(), self.save_session()], **btn_params).pack(fill="x", padx=10, pady=1)
                     
        ctk.CTkButton(frame, text="  ⌗  Controls Guide",
                     command=lambda: [menu.destroy(), self.show_controls_guide()], **btn_params).pack(fill="x", padx=10, pady=1)
        
        # Subtle Separator
        ctk.CTkFrame(frame, height=1, fg_color="#334155").pack(fill="x", padx=20, pady=5)

        # Destructive Actions Group
        ctk.CTkButton(frame, text="  🧹  Clear Conversation", text_color="#FCA5A5",
                     command=lambda: [menu.destroy(), self.clear_text()], **btn_params).pack(fill="x", padx=10, pady=(5, 1))

        # Logout
        ctk.CTkButton(frame, text="  ⏼  Log Out", text_color="#FCA5A5",
                     command=lambda: [menu.destroy(), self.logout()], **btn_params).pack(fill="x", padx=10, pady=(1, 10))
           
        # Close on click outside
        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_force()

    def show_settings_window(self):
        """Show settings with toggle behavior"""
        if "settings" in self.active_popups and self.active_popups["settings"].root.winfo_exists():
            self.active_popups["settings"].root.destroy()
            # The Registry handles deletion via its own cleanup if we add it there, 
            # but SettingsWindow is a class wrapper. Let's just track it.
            return

        settings = SettingsWindow(self)
        self.active_popups["settings"] = settings
        
        # Apply modern effects to settings window
        try:
            settings.root.update()
            hwnd = ctypes.windll.user32.GetParent(settings.root.winfo_id())
            apply_modern_effects(hwnd)
        except: pass

    # logout_and_switch removed - using unified logout() method
        
    def on_global_ptt_press(self, event):
        """Global push-to-talk press handler (F2)"""
        if self.is_locked: return
        if not self.space_held:
            # Check if this is a real press (not repeat)
            # Keyboard library sometimes fires repeat events
            self.space_held = True
            self.root.after(0, self.start_push_to_talk)
            
    def on_global_ptt_release(self, event):
        """Global push-to-talk release handler (F2)"""
        if self.space_held:
            self.space_held = False
            self.root.after(0, self.stop_push_to_talk)

    def check_and_deduct_credit(self):
        """Verify credits and deduct 1 if this is a new session"""
        # 1. Check in-memory session (fastest)
        if hasattr(self, 'is_session_paid') and self.is_session_paid:
            return True

        # 2. Check persistent local session (handles restarts)
        if MonetizationManager.is_session_active_locally():
             self.is_session_paid = True
             return True
            
        if self.credits <= 0:
            messagebox.showwarning("Out of Credits", "You have 0 credits. Please purchase more session credits on the Nebula website.")
            return False
            
        success, msg, new_bal = MonetizationManager.consume_credit()
        if success:
            self.credits = new_bal
            self.is_session_paid = True
            
            # Save expiry locally (15 mins)
            MonetizationManager.set_session_active_locally(15)
            
            if hasattr(self, 'credits_lbl'):
                self.credits_lbl.configure(text=f"💎 {self.credits}")
            return True
        else:
            messagebox.showerror("Credit Error", f"Failed to start session: {msg}")
            return False
            
    def start_push_to_talk(self):
        """Start push-to-talk listening"""
        if self.is_locked: return
        
        # Check and Deduct Credits for first session use
        if not self.check_and_deduct_credit():
            return
            
        self.is_voice_active = True
        self.set_status("🎙️ CAPTURING...", self.clr_accent)
        
        mic_dev = self.get_selected_device(self.mic_id.get(), is_speaker=False)
        lang_code = self.get_selected_language()
        self.voice_listener = VoiceListener(self.on_push_to_talk_result, use_loopback=False, source_label="Me", 
                                            language=lang_code, ai_instance=self.ai, device=mic_dev,
                                            sensitivity=self.sensitivity.get(), silence_patience=self.silence_patience.get())
        self.voice_listener.start_listening(continuous=False)

        
    def stop_push_to_talk(self):
        """Stop push-to-talk and process result"""
        self.is_voice_active = False
        if self.voice_listener:
            self.voice_listener.stop_listening()
        self.set_status("🧠 THINKING...", self.clr_neon)
        
    def on_push_to_talk_result(self, text, error, label="Interviewer"):
        """Handle push-to-talk result"""
        if error:
            self.root.after(0, lambda: self.set_status(f"AUDIO ERROR", self.clr_danger))
            return
        if text:
            # Apply technical jargon correction
            text = TechnicalFixer.fix(text)
            
            self.root.after(0, lambda: self.show_heard_question(text))
            self.root.after(0, lambda: self.set_status("ANALYZING...", self.clr_neon))
            
            if self.ai:
                self.ai.answer_question(text, self.on_ai_answer)
            else:
                self.root.after(0, lambda: self.set_status("AI NOT READY", self.clr_danger))
        else:
            self.root.after(0, lambda: self.set_status("NO SPEECH DETECTED", self.clr_dim))
            self.root.after(0, lambda: self.append_text("\n\n(No words captured. Check mic settings if this persists.)\n"))
        
    # ========== VOICE ASSISTANT METHODS ==========
    
    def upload_resume(self):
        """Load resume/report files (PDF, Word, TXT) for AI context"""
        filetypes = [
            ('All Supported', '*.pdf *.docx *.txt'),
            ('PDF files', '*.pdf'),
            ('Word files', '*.docx'),
            ('Text files', '*.txt'),
            ('All files', '*.*')
        ]
        filepaths = filedialog.askopenfilenames(
            title="Select Resume / Documents",
            filetypes=filetypes
        )
        if filepaths:
            all_content = []
            for filepath in filepaths:
                try:
                    filename = os.path.basename(filepath)
                    ext = filename.lower().split('.')[-1] if '.' in filename else ''
                    content = ""
                    
                    if ext == 'pdf':
                        try:
                            from PyPDF2 import PdfReader
                            reader = PdfReader(filepath)
                            content = "\n".join(page.extract_text() or "" for page in reader.pages)
                        except Exception as e:
                            content = f"[Could not parse PDF: {e}]"
                            
                    elif ext == 'docx':
                        try:
                            from docx import Document
                            doc = Document(filepath)
                            content = "\n".join(para.text for para in doc.paragraphs)
                        except Exception as e:
                            content = f"[Could not parse Word (.docx): {e}]"
                            
                    elif ext == 'doc':
                        content = "[Legacy .doc files are not supported. Please save as .docx and try again.]"
                            
                    else:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    
                    if content.startswith("[Could not parse"):
                        messagebox.showwarning("Parsing Error", f"Failed to read {filename}:\n{content}")
                        continue

                    if content.strip():
                        all_content.append(f"=== {filename} ===\n{content}\n")
                        if filename not in self.loaded_documents:
                            self.loaded_documents.append(filename)
                        
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read {filepath}:\n{e}")
                    
            if all_content:
                full_text = "\n".join(all_content)
                self.ai.set_document_context(full_text)
                self.update_jargon_from_resume(full_text)
                self.doc_count_lbl.configure(text=str(len(self.loaded_documents)), text_color=self.clr_success)
                self.set_status(f"✅ LOADED {len(self.loaded_documents)} DOCS", self.clr_success)
            else:
                self.set_status("⚠️ NO CONTENT EXTRACTED", self.clr_danger)

    def update_jargon_from_resume(self, text):
        """Extract tech keywords from resume to improve transcription"""
        # Find acronyms (AWS, SQL, BERT) and CamelCase (PyTorch, TensorFlow)
        keywords = re.findall(r'\b[A-Z]{2,}\b|\b[A-Z][a-z]+[A-Z][a-z]+\b', text)
        
        # Also catch words that seem like tech stack in data science/dev context
        tech_hints = ["python", "pandas", "numpy", "react", "docker", "kubernetes", "flask", "django"]
        
        count = 0
        for kw in set(keywords):
            if len(kw) >= 2:
                # Add to TechnicalFixer
                TechnicalFixer.WORD_MAP[kw.lower()] = kw
                count += 1
        
        for hint in tech_hints:
            if hint in text.lower():
                TechnicalFixer.WORD_MAP[hint] = hint.capitalize() if hint != "python" else "Python"

    def on_live_assist_toggle(self):
        """Handle Live Assist checkbox toggle"""
        if self.is_locked:
            self.live_assist_mode.set(False)
            messagebox.showwarning("Locked", "Subscription required for Live Assist.")
            return
        if self.live_assist_mode.get():
            # Check and Deduct Credits for first session use
            if not self.check_and_deduct_credit():
                self.live_assist_mode.set(False)
                return
                
            # Turn on Live Assist
            if self.is_voice_active:
                self.stop_listening() # Stop normal listen if active
            
            self.is_voice_active = True
            self.is_live_assist_active = True
            self.live_transcript = []
            self.set_status("🔄 LIVE ASSIST ACTIVE (Mic + Desktop)", self.clr_neon)

            
            lang_code = self.get_selected_language()
            mic_dev = self.get_selected_device(self.mic_id.get(), is_speaker=False)
            spk_dev = self.get_selected_device(self.speaker_id.get(), is_speaker=True)
            
            self.dual_listener = DualVoiceListener(callback=self.on_voice_input, language=lang_code, ai_instance=self.ai,
                                                  mic_device=mic_dev, speaker_device=spk_dev,
                                                  sensitivity=self.sensitivity.get(), silence_patience=self.silence_patience.get())
            self.dual_listener.start()
        else:
            # Turn off Live Assist
            self.is_live_assist_active = False
            self.stop_listening()
            
    def stop_listening(self):
        """Stop all listening modes"""
        self.is_voice_active = False
        self.is_live_assist_active = False
        self.live_assist_mode.set(False)
        self.set_status("READY", self.clr_success)
        
        if self.voice_listener:
            self.voice_listener.stop_listening()
            self.voice_listener = None
        if self.dual_listener:
            self.dual_listener.stop()
            self.dual_listener = None
            
    def on_voice_input(self, text, error, label="Interviewer"):
        """Handle voice input with jargon correction and accumulation"""
        if error:
            if not self.is_live_assist_active:
                self.root.after(0, lambda: self.set_status(f"MIC ERROR", self.clr_danger))
            return
            
        if text:
            # V27: Hallucination Filter (Ignore common noise-induced transcriptions)
            clean_text = text.lower().strip(" .!?")
            hallucinations = ["you", "you you", "thank you", "thank you for watching", "bye", "so what", "okay"]
            if clean_text in hallucinations and len(clean_text) < 10:
                return # Ignore noise hallucination
                
            # Apply technical jargon correction
            text = TechnicalFixer.fix(text)
            
            if self.is_live_assist_active:
                # 1. Accumulate speech for this speaker
                print(f"[Voice] Accumulating for {label}: '{text}'")
                self.pending_speech[label] += " " + text
                
                # 2. Reset the silence timer for this speaker
                if self.speech_timers[label]:
                    self.root.after_cancel(self.speech_timers[label])
                
                # 3. Schedule finalization after silence
                self.speech_timers[label] = self.root.after(
                    self.silence_delay, 
                    lambda l=label: self.finalize_speech(l)
                )
            else:
                # Normal PTT or Listen (responds immediately)
                prefix = " Me" if label == "Me" else " Int"
                print(f"[Voice] Immediate processing for {label}: '{text}'")
                self.root.after(0, lambda: self.append_text(f"\n{prefix}: \"{text}\""))
                if self.ai:
                    self.root.after(0, lambda: self.ai.answer_question(text, self.on_ai_answer))
                else:
                    self.root.after(0, lambda: self.set_status("AI NOT READY", self.clr_danger))
                
    def finalize_speech(self, label):
        """Finalize and process accumulated speech after a pause"""
        text = self.pending_speech[label].strip()
        if not text:
            return
            
        # Apply technical jargon correction to the full accumulated sentence
        text = TechnicalFixer.fix(text)
        
        # Clear the buffer for next time
        self.pending_speech[label] = ""
        self.speech_timers[label] = None
        
        # Show in UI with prefix
        prefix = "👤 Me" if label == "Me" else "🎤 Int"
        self.root.after(0, lambda: self.append_text(f"\n{prefix}: \"{text}\""))
        
        # Add to full transcript memory
        self.live_transcript.append(f"{label}: {text}")
        if len(self.live_transcript) > 15:
            self.live_transcript.pop(0)
            
        # If interviewer finished a thought, get AI help
        if label == "Interviewer":
            if self.ai:
                self.root.after(0, self.get_live_ai_assist)
            else:
                self.root.after(0, lambda: self.set_status("AI NOT READY", self.clr_danger))



    def get_live_ai_assist(self):
        """Get AI to suggest a response based on the LIVE conversation"""
        # Throttling AI calls to avoid rate limits
        import time
        now = time.time()
        if now - self.last_ai_update_time < 5: # Max one AI call every 5s
            return
            
        self.last_ai_update_time = now
        full_transcript = "\n".join(self.live_transcript)
        
        self.set_status("🤖 Live Thinking...", self.clr_neon)
        if self.ai:
            self.ai.answer_live_conversation(full_transcript, self.on_live_ai_suggest)
        else:
            self.set_status("AI NOT READY", self.clr_danger)

    def on_live_ai_suggest(self, answer, error):
        """Handle AI update in Live mode"""
        if not error and answer:
            print(f"[AI] Live AI Suggestion: {answer[:50]}...")
            # Clean up any potential AI artifact prefixes
            clean_answer = answer.strip()
            for prefix in ["Response:", "Suggestion:", "Tip:", "- ", '"']:
                if clean_answer.startswith(prefix):
                    clean_answer = clean_answer[len(prefix):].strip()
            
            if clean_answer:
                self.root.after(0, lambda: self.append_text(f"\n💬 {clean_answer}\n"))
                self.root.after(0, lambda: self.set_status("Live Assist Ready", self.clr_success))
        elif error:
            print(f"[AI] Live AI Error: {error}")
            self.root.after(0, lambda: self.set_status("AI Link Error", self.clr_danger))
        else:
            print("[AI] Live AI returned empty answer and no error.")
            
    def set_text(self, content):
        """Update read-only text area"""
        self.text_area.configure(state='normal')
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", content)
        self.text_area.configure(state='disabled')
        
    def append_text(self, content):
        """Append to read-only text area and scroll to bottom"""
        self.text_area.configure(state='normal')
        self.text_area.insert("end", content)
        self.text_area.see("end")  # Scroll to bottom
        self.text_area.configure(state='disabled')
            
    def show_heard_question(self, question):
        """Display the heard question (append to existing)"""
        self.current_question = question  # Store for history
        separator = "\n\n" + "━" * 40 + "\n\n"
        new_content = f"🎤 Q: \"{question}\"\n\n⏳ Generating..."
        
        # Check if this is first question or subsequent
        self.text_area.configure(state='normal')
        current = self.text_area.get("1.0", "end").strip()
        if current and not current.startswith("🎯"):  # Has previous Q&A
            self.text_area.insert("end", separator + new_content)
        else:
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", new_content)
        self.text_area.see("end")
        self.text_area.configure(state='disabled')
        
    def on_ai_answer(self, answer, error):
        """Handle AI answer - append and save to memory"""
        if error:
            self.root.after(0, lambda: self.set_status(f"Error: {error[:20]}", self.clr_danger))
            self.root.after(0, lambda: self.append_text(f"\n\n❌ Error: {error}"))
        else:
            def update_ui():
                self.text_area.configure(state='normal')
                current = self.text_area.get("1.0", "end")
                # Replace loading text with answer
                if "⏳ Generating..." in current:
                    current = current.replace("⏳ Generating...", "")
                    self.text_area.delete("1.0", "end")
                    self.text_area.insert("1.0", current + f"\n💬 SAY THIS:\n\n{answer}")
                else:
                    self.text_area.insert("end", f"\n💬 SAY THIS:\n\n{answer}")
                self.text_area.see("end")  # Scroll to bottom
                self.text_area.configure(state='disabled')
                self.set_status("✅ Answer ready!", self.clr_success)
                
                # Save to AI memory
                if hasattr(self, 'current_question'):
                    self.ai.add_to_history(self.current_question, answer)
            self.root.after(0, update_ui)
            
    def ask_manual_question(self):
        """Ask a question manually using modern input dialog"""
        if self.is_locked: return
        dialog = ctk.CTkInputDialog(text="Type the question you want answered:", title="Manual Query")
        question = dialog.get_input()
        if question:
            self.show_heard_question(question)
            self.set_status("Generating answer...", self.clr_neon)
            if self.ai:
                self.ai.answer_question(question, self.on_ai_answer)
            else:
                self.set_status("AI NOT READY", self.clr_danger)
        
    # ========== UI CONTROL METHODS ==========



    def show_controls_guide(self):
        """Show a modern modal with application shortcuts"""
        guide = ctk.CTkToplevel(self.root)
        guide.title("Controls Guide")
        guide.geometry("400x450")
        
        # Ensure it's on top and focused
        guide.attributes("-topmost", True)
        guide.lift()
        guide.focus_force()
        
        try:
            guide.update()
            hwnd = ctypes.windll.user32.GetParent(guide.winfo_id())
            apply_modern_effects(hwnd)
        except: pass

        frame = ctk.CTkFrame(guide, fg_color="#1E293B", corner_radius=18, border_width=1, border_color="#334155")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="NEBULA CONTROLS", font=ctk.CTkFont(size=18, weight="bold"), text_color="#A78BFA").pack(pady=20)
        
        controls = [
            ("F2 (Hold)", "Push-to-Talk (My Mic)"),
            ("Ctrl + Alt + Z", "Toggle Interview/Ghost Mode"),
            ("Ctrl + S", "Toggle Ghost (Anti-Capture)"),
            ("Ctrl + Q", "Exit Application"),
            ("+ / -", "Change Font Size"),
            ("Live Assist", "Listen to Mic + Desktop Audio")
        ]

        for key, action in controls:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=30, pady=5)
            ctk.CTkLabel(row, text=key, font=ctk.CTkFont(weight="bold"), text_color="#F8FAFC").pack(side="left")
            ctk.CTkLabel(row, text=f"— {action}", text_color="#94A3B8").pack(side="right")

        ctk.CTkButton(frame, text="CLOSE", fg_color="#334155", hover_color="#475569", command=guide.destroy).pack(pady=30)

    # ========== AI METHODS ==========
    
    def set_status(self, text, color=None):
        """No-op: Status bar removed per user request"""
        pass
        
    def get_selected_language(self):
        """Get the active language code, auto-detecting from system if needed"""
        choice = self.selected_lang.get()
        code = self.languages.get(choice, "en-US")
        
        if code == "auto":
            try:
                # Get system locale (e.g. 'en_GB')
                sys_lang = locale.getlocale()[0] or locale.getdefaultlocale()[0]
                if sys_lang:
                    # Convert 'en_GB' to 'en-GB' which google expects
                    return sys_lang.replace('_', '-')
            except:
                pass
            return "en-US" # Fallback
        return code
        
    def ai_callback(self, result, error):
        """Handle AI response callback"""
        if error:
            self.set_status(f"AI Error: {error[:20]}", self.clr_danger)
        else:
            self.set_text(result)
            self.set_status("AI Response Ready", self.clr_success)
            
    def clear_text(self):
        """Clear the current conversation and UI"""
        self.set_text("")
        self.live_transcript = []
        self.set_status("Ready", self.clr_success)

    def save_session(self):
        """Save the current session transcript to a file"""
        if not self.live_transcript and not self.text_area.get('1.0', tk.END).strip():
            messagebox.showinfo("Save Session", "No session data to save.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt")],
            initialfile=f"Interview_Session_{time.strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        if filename:
            try:
                content = "# Interview Session Recording\n"
                content += f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                content += "## Full Transcript & Suggestions\n\n"
                content += self.text_area.get('1.0', tk.END)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.set_status(f"✅ Session Saved", self.clr_success)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    def update_transparency(self, value):
        """Update opacity specifically for Interview Mode with live preview"""
        self.zen_opacity = float(value) / 100
        # V14: Live preview on main window during adjustment
        self.root.attributes("-alpha", self.zen_opacity)
        
        # Auto-revert preview if in normal mode
        if not self.interview_mode:
            if hasattr(self, "_op_timer"): self.root.after_cancel(self._op_timer)
            self._op_timer = self.root.after(1500, lambda: self.root.attributes("-alpha", 1.0) if not self.interview_mode else None)
        
    def change_font_size(self, delta):
        """Update font size with premium font stack preservation"""
        self.font_size = max(10, min(72, self.font_size + delta))
        self.text_area.configure(font=(self.FONT_TEXT, self.font_size))
        self.set_status(f"FONT SIZE: {self.font_size}PX", self.clr_dim)

    def toggle_ghost_shortcut(self):
        """Shortcut to toggle ghost mode"""
        self.ghost_var.set(not self.ghost_var.get())
        self.toggle_ghost()

    def toggle_ghost(self):
        """Toggle window visibility to screen sharing AND taskbar"""
        if self.is_locked:
            self.ghost_var.set(False)
            messagebox.showwarning("Locked", "Subscription required for Ghost Mode.")
            return

        if not IS_WINDOWS:
            self.set_status("PLATFORM NOT SUPPORTED", self.clr_danger)
            messagebox.showinfo("Ghost Mode", "Ghost Mode (Anti-Capture) is currently only available on Windows.")
            return

        try:
            import ctypes
            from ctypes import windll
            
            # Constants
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
                
            # Get current style
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                
            if self.ghost_var.get():
                # Activate Ghost: Hide from Capture + Hide from Taskbar
                windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
                
                # Add ToolWindow style, remove AppWindow style
                style |= WS_EX_TOOLWINDOW
                style &= ~WS_EX_APPWINDOW
                
                windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                # Trigger frame update
                windll.user32.SetWindowPos(hwnd, 0, 0,0,0,0, 0x27) # SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_FRAMECHANGED
                
                self.set_status("👻 GHOST ACTIVE", self.clr_neon)
            else:
                # Deactivate Ghost
                windll.user32.SetWindowDisplayAffinity(hwnd, 0x0)
                
                # Remove ToolWindow style, add AppWindow style
                style &= ~WS_EX_TOOLWINDOW
                style |= WS_EX_APPWINDOW
                
                windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                windll.user32.SetWindowPos(hwnd, 0, 0,0,0,0, 0x27)
                
                self.set_status("👁️ GHOST OFF", self.clr_dim)
                
        except Exception as e:
            self.set_status(f"GHOST ERROR", self.clr_danger)
            print(f"Ghost Error: {e}")

    def toggle_stealth_shortcut(self):
        """Shortcut to toggle stealth mode"""
        self.stealth_var.set(not self.stealth_var.get())
        self.toggle_stealth()

    def toggle_stealth(self):
        """Ultra-Invisibility: Low Opacity + Click-Through (Windows)"""
        if self.is_locked:
            self.stealth_var.set(False)
            messagebox.showwarning("Locked", "Subscription required for Stealth Mode.")
            return

        if not IS_WINDOWS:
            self.set_status("PLATFORM NOT SUPPORTED", self.clr_danger)
            return

        try:
            import ctypes
            from ctypes import windll
            
            # Constants for Click-Through
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            if not hwnd: hwnd = self.root.winfo_id()
                
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            if self.stealth_var.get():
                # Activate Stealth: 15% Opacity + Click-Through
                self.root.attributes("-alpha", 0.15)
                
                # Add Layered and Transparent (Click-through) styles
                style |= (WS_EX_LAYERED | WS_EX_TRANSPARENT)
                windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                
                self.set_status("🕵️ STEALTH ACTIVE", self.clr_neon)
            else:
                # Deactivate Stealth: Restore Opacity (Full or Zen)
                target_alpha = self.zen_opacity if self.interview_mode else 1.0
                self.root.attributes("-alpha", target_alpha)
                
                # Remove Transparent (Keep Layered for standard opacity support)
                style &= ~WS_EX_TRANSPARENT
                windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                
                self.set_status("👁️ STEALTH OFF", self.clr_dim)
            
            # Trigger frame update
            windll.user32.SetWindowPos(hwnd, 0, 0,0,0,0, 0x27)
            self.save_settings()

        except Exception as e:
            self.set_status(f"STEALTH ERROR", self.clr_danger)
            print(f"Stealth Error: {e}")

    def show_profile_menu(self):
        """Show the Profile/Settings window (Singleton)"""
        # Check if already open
        if "settings" in self.active_popups:
            try:
                if self.active_popups["settings"].root.winfo_exists():
                    self.active_popups["settings"].root.lift()
                    self.active_popups["settings"].root.focus_force()
                    return
            except:
                del self.active_popups["settings"]

        # Open new window
        self.active_popups["settings"] = SettingsWindow(self)

    def show_controls_guide(self):
        """Show a premium popup with all hotkeys"""
        # V9: Toggle Off if already open
        if "guide" in self.active_popups and self.active_popups["guide"].winfo_exists():
            self.active_popups["guide"].destroy()
            del self.active_popups["guide"]
            return

        guide = ctk.CTkToplevel(self.root)
        self.active_popups["guide"] = guide
        
        # Cleanup on destroy
        guide.bind("<Destroy>", lambda e: self.active_popups.pop("guide", None) if e.widget == guide else None)
        
        guide.title("Command Center")
        guide.geometry("420x550")
        guide.transient(self.root)  # V8: Link to main window
        guide.attributes("-topmost", True)
        guide.lift()                # Bring to front
        guide.configure(fg_color=self.clr_bg)
        
        # Apply modern effects to popup (Windows only)
        if IS_WINDOWS:
            try:
                guide.update()
                hwnd = ctypes.windll.user32.GetParent(guide.winfo_id())
                apply_modern_effects(hwnd)
            except: pass
        
        # Center popup
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 275
        guide.geometry(f"+{x}+{y}")
        
        # Rounded frame for content
        master_frame = ctk.CTkFrame(guide, fg_color="#1E293B", 
                                   corner_radius=self.corner_radius, border_width=1, border_color="#334155")
        master_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(master_frame, text="COMMAND CENTER", font=ctk.CTkFont(family=self.FONT_DISPLAY, size=24, weight="bold"), text_color=self.clr_accent).pack(pady=(30, 20))
        
        frame = ctk.CTkFrame(master_frame, fg_color="transparent")
        frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        shortcuts = [
            ("F2 (HOLD)", "Push-to-Talk (My Voice)"),
            ("CTRL + ALT + Z", "Toggle Zen Focus Mode"),
            ("CTRL + ALT + S", "Toggle Stealth (Click-Through)"),
            ("CTRL + S", "Toggle Ghost Mode"),
            ("CTRL + Q", "Quit Application"),
            ("+ / -", "Change Font Size"),
        ]
        
        for key, desc in shortcuts:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=8)
            ctk.CTkLabel(row, text=key, font=ctk.CTkFont(family=self.FONT_TEXT, size=12, weight="bold"), text_color=self.clr_neon).pack(side="left")
            ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(family=self.FONT_TEXT, size=11), text_color=self.clr_text).pack(side="right")

        ctk.CTkButton(master_frame, text="GOT IT", height=45, corner_radius=15, fg_color=self.clr_accent, hover_color="#8B5CF6",
                      font=ctk.CTkFont(family=self.FONT_TEXT, size=13, weight="bold"), command=guide.destroy).pack(pady=25, padx=40, fill="x")

    def toggle_interview_mode(self):
        """Minimalist 'Interview' mode: borderless, header-less, ultra-clean"""
        self.interview_mode = not self.interview_mode
        self.root.withdraw()
        
        if self.interview_mode:
            # Entering Ultra-Focus Mode - Keep window frame for rounded corners
            # DON'T use overrideredirect - it prevents DWM rounding
            self.header.grid_forget()
            
            # V15: Solid Hub BG for Artifact-Free rendering
            self.main_hub.configure(fg_color=self.clr_bg)
            
            # Full-bleed layout
            self.main_hub.grid_configure(padx=10, pady=10)
            self.center_hub.grid_configure(row=0, pady=0)  # Correct target: center_hub
            self.main_hub.grid_rowconfigure(0, weight=1)
            self.main_hub.grid_rowconfigure(1, weight=0)
            
            # Show floating back arrow - properly positioned
            self.btn_back_zen_frame.lift()  # Ensure it's on top
            self.btn_back_zen_frame.place(relx=0.02, rely=0.02, anchor="nw")
            
            # V15: Standard padding for Zen Mode (reduced from 85 to 60)
            self.text_area.pack_configure(pady=(60, 20))
            
            # V13: Apply Interview-Specific Opacity
            self.root.attributes("-alpha", self.zen_opacity)
            
            self.set_status("INTERVIEW MODE ACTIVE", self.clr_neon)
        else:
            # Restoring Standard Mode (Always 100% Opaque)
            self.root.attributes("-alpha", 1.0)
            # DON'T toggle overrideredirect - we never set it
            self.header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
            
            # V15: Transparent Hub for Normal Mode Flow
            self.main_hub.configure(fg_color=self.clr_bg) # Keep solid for rounding mask
            
            # Standard padding
            self.main_hub.grid_configure(padx=20, pady=20)
            self.center_hub.grid_configure(row=1, pady=0) # Correct target
            self.main_hub.grid_rowconfigure(1, weight=1)
            self.main_hub.grid_rowconfigure(0, weight=0)
            
            # V10: Re-apply DWM effects after window mode toggle (Delayed for OS Stability)
            def _reapply_dwmapi():
                try:
                    self.root.update()
                    hwnd = self.root.winfo_id()
                    apply_modern_effects(hwnd)
                except: pass
            self.root.after(150, _reapply_dwmapi)

            # Hide floating back arrow
            self.btn_back_zen_frame.place_forget()
            
            # V9: Restore standard padding
            self.text_area.pack_configure(pady=10)
            
            self.set_status("READY", self.clr_success)
            
        self.root.deiconify()
        self.root.attributes('-topmost', True)
        self.root.focus_force()

        # Re-apply ghost if it was active (window recreation clears styles)
        if self.ghost_var.get():
            self.toggle_ghost()
        if self.stealth_var.get():
            self.toggle_stealth()

    def start_drag(self, event):
        """Initial mouse click for borderless dragging"""
        if self.interview_mode:
            self._drag_data["x"] = event.x_root
            self._drag_data["y"] = event.y_root

    def do_drag(self, event):
        """Handle window movement during drag"""
        if self.interview_mode:
            # Calculate delta
            dx = event.x_root - self._drag_data["x"]
            dy = event.y_root - self._drag_data["y"]
            
            # Get current position
            x = self.root.winfo_x() + dx
            y = self.root.winfo_y() + dy
            
            # Move window
            self.root.geometry(f"+{x}+{y}")
            
            # Update last position
            self._drag_data["x"] = event.x_root
            self._drag_data["y"] = event.y_root
    def _init_bg_assets(self):
        """Heavy asset/API initialization in background"""
        try:
            self.ai = AIProvider()
            self.loaded_documents = []
        except Exception as e:
            print(f"Background Asset Init Error: {e}")

    def run(self):
        """Start the application and clean up splash"""
        self.root.update()
        if self.splash:
            try:
                self.splash.destroy()
            except:
                pass
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.mainloop()

    def _set_modern_effects(self):
        if IS_WINDOWS:
            apply_modern_effects(self.root.winfo_id(), caption_color="#0F172A")


# ========== LICENSING SYSTEM ==========

# ========== MONETIZATION SYSTEM (V4) ==========

from monetization_manager import MonetizationManager

class SettingsWindow:
    def __init__(self, parent_app):
        self.app = parent_app
        self.root = ctk.CTkToplevel(parent_app.root)
        self.root.title("Nebula Settings")
        self.root.geometry("640x580")
        self.root.attributes("-topmost", True)
        self.root.configure(fg_color="#0B0F19")
        
        # V16: Premium Title Bar
        if IS_WINDOWS:
            self.root.after(100, lambda: apply_modern_effects(self.root.winfo_id(), caption_color="#000000"))
        
        # Center the window
        x = parent_app.root.winfo_x() + (parent_app.root.winfo_width() // 2) - 320
        y = parent_app.root.winfo_y() + (parent_app.root.winfo_height() // 2) - 290
        self.root.geometry(f"+{x}+{y}")
        
        # Make the window modal-like
        self.root.transient(parent_app.root)
        self.root.lift()
        self.root.focus_force()
        self.root.grab_set()
        
        # Header
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(25, 0))
        ctk.CTkLabel(header, text="SETTINGS", font=ctk.CTkFont(family=self.app.FONT_DISPLAY, size=24, weight="bold"), text_color=self.app.clr_accent).pack(side="left")
        
        self.tabview = ctk.CTkTabview(self.root, fg_color="#1E293B", corner_radius=20, width=580, height=480,
                                     segmented_button_fg_color="#0F172A",
                                     segmented_button_selected_color=self.app.clr_accent,
                                     segmented_button_selected_hover_color="#7C3AED",
                                     segmented_button_unselected_hover_color="#334155")
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.tabview.add("General")
        self.tabview.add("Audio") # NEW
        self.tabview.add("Account")
        self.tabview.add("Security")
        
        self.setup_general_tab()
        self.setup_audio_tab() # NEW
        self.setup_account_tab()
        self.setup_security_tab()
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if "settings" in self.app.active_popups:
            del self.app.active_popups["settings"]
        self.root.grab_release()
        self.root.destroy()
        
    def setup_general_tab(self):
        tab = self.tabview.tab("General")
        
        # V22: Scrollable Wrapper for overflow
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        
        # --- Appearance Card ---
        card_app = ctk.CTkFrame(scroll_frame, fg_color="#0F172A", corner_radius=15)
        card_app.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(card_app, text="✨ APPEARANCE", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 10), padx=20, anchor="w")
        
        # Opacity Control
        ctk.CTkLabel(card_app, text="Window Opacity", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(5, 0), anchor="w", padx=20)
        self.opacity_slider = ctk.CTkSlider(card_app, from_=30, to=100, number_of_steps=70, 
                                           progress_color=self.app.clr_accent, button_color=self.app.clr_accent,
                                           command=self.app.update_transparency)
        self.opacity_slider.set(self.app.zen_opacity * 100)
        self.opacity_slider.pack(pady=(5, 10), padx=20, fill="x")
        
        # Font Size Control
        ctk.CTkLabel(card_app, text="Interface Font Size", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(10, 0), anchor="w", padx=20)
        font_frame = ctk.CTkFrame(card_app, fg_color="transparent")
        font_frame.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkButton(font_frame, text="A- Smaller", width=120, fg_color="#334155", font=ctk.CTkFont(size=11),
                     command=lambda: self.app.change_font_size(-2)).pack(side="left", padx=5)
        ctk.CTkButton(font_frame, text="A+ Larger", width=120, fg_color="#334155", font=ctk.CTkFont(size=11),
                     command=lambda: self.app.change_font_size(2)).pack(side="left", padx=5)

        # Theme Switcher
        ctk.CTkLabel(card_app, text="Color Theme", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(10, 0), anchor="w", padx=20)
        self.theme_dropdown = ctk.CTkOptionMenu(card_app, values=["Dark", "Light", "System"], 
                                               fg_color="#334155", button_color="#A78BFA", button_hover_color="#7C3AED",
                                               command=self.change_theme)
        self.theme_dropdown.set(ctk.get_appearance_mode())
        self.theme_dropdown.pack(pady=(5, 20), padx=20, fill="x")

    def change_theme(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.app.save_settings()
        
        # --- Privacy Card ---
        card_priv = ctk.CTkFrame(scroll_frame, fg_color="#0F172A", corner_radius=15)
        card_priv.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(card_priv, text="🛡️ PRIVACY & PROTECTION", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 10), padx=20, anchor="w")
        
        # Ghost Mode
        self.ghost_switch = ctk.CTkSwitch(card_priv, text="Ghost Protection (Hide from Capture)", 
                                           progress_color=self.app.clr_accent,
                                           command=self.app.toggle_ghost_shortcut)
        if self.app.ghost_var.get():
            self.ghost_switch.select()
        self.ghost_switch.pack(anchor="w", padx=20, pady=5)
        
        # Stealth Mode
        self.stealth_switch = ctk.CTkSwitch(card_priv, text="Stealth Mode (Invisibility & Click-Through)", 
                                           progress_color=self.app.clr_neon,
                                           command=self.app.toggle_stealth_shortcut)
        if self.app.stealth_var.get():
            self.stealth_switch.select()
        self.stealth_switch.pack(anchor="w", padx=20, pady=(5, 20))
        
        # --- Session Tools Card ---
        card_tools = ctk.CTkFrame(scroll_frame, fg_color="#0F172A", corner_radius=15)
        card_tools.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(card_tools, text="🔧 SESSION TOOLS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 10), padx=20, anchor="w")
        
        # Grid layout for tools
        tools_grid = ctk.CTkFrame(card_tools, fg_color="transparent")
        tools_grid.pack(fill="x", padx=15, pady=(0, 20))
        
        # Save
        ctk.CTkButton(tools_grid, text="💾 Save Session", fg_color="#334155", hover_color="#475569",
                     command=self.app.save_session).pack(side="left", expand=True, fill="x", padx=5)
                     
        # Clear
        ctk.CTkButton(tools_grid, text="🗑️ Clear All", fg_color="#334155", hover_color="#EF4444",
                     command=self.app.clear_text).pack(side="left", expand=True, fill="x", padx=5)
                     
        # Help
        ctk.CTkButton(tools_grid, text="❓ Controls", fg_color="#334155", hover_color="#475569",
                     command=self.app.show_controls_guide).pack(side="left", expand=True, fill="x", padx=5)

    def setup_audio_tab(self):
        tab = self.tabview.tab("Audio")
        
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        
        # --- Device Selection Card ---
        card_dev = ctk.CTkFrame(scroll_frame, fg_color="#0F172A", corner_radius=15)
        card_dev.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(card_dev, text="🎙️ AUDIO DEVICES", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 5), padx=20, anchor="w")
        
        # Discover devices
        devices = VoiceListener.get_audio_devices()
        mic_names = ["Default"] + [d['name'] for d in devices['mics']]
        spk_names = ["Default"] + [d['name'] for d in devices['speakers']]
        
        # Mic Selection
        ctk.CTkLabel(card_dev, text="Primary Microphone", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(10, 0), anchor="w", padx=20)
        self.mic_dropdown = ctk.CTkOptionMenu(card_dev, values=mic_names, variable=self.app.mic_id, 
                                             fg_color="#334155", button_color="#A78BFA", button_hover_color="#7C3AED",
                                             command=lambda _: self.app.save_settings())
        self.mic_dropdown.pack(pady=(5, 10), padx=20, fill="x")
        
        # Speaker Selection (Loopback)
        ctk.CTkLabel(card_dev, text="System Audio Source (Loopback)", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(10, 0), anchor="w", padx=20)
        self.spk_dropdown = ctk.CTkOptionMenu(card_dev, values=spk_names, variable=self.app.speaker_id, 
                                             fg_color="#334155", button_color="#A78BFA", button_hover_color="#7C3AED",
                                             command=lambda _: self.app.save_settings())
        self.spk_dropdown.pack(pady=(5, 20), padx=20, fill="x")
        
        # --- Language Card ---
        card_lang = ctk.CTkFrame(scroll_frame, fg_color="#0F172A", corner_radius=15)
        card_lang.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(card_lang, text="🌐 TRANSCRIPTION LANGUAGE", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 5), padx=20, anchor="w")
        
        lang_names = list(self.app.languages.keys())
        self.lang_dropdown = ctk.CTkOptionMenu(card_lang, values=lang_names, variable=self.app.selected_lang, 
                                              fg_color="#334155", button_color="#A78BFA", button_hover_color="#7C3AED",
                                              command=lambda _: self.app.save_settings())
        self.lang_dropdown.pack(pady=(5, 20), padx=20, fill="x")
        
        # --- Advanced AI Control Card ---
        card_ai = ctk.CTkFrame(scroll_frame, fg_color="#0F172A", corner_radius=15)
        card_ai.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(card_ai, text="🧠 VOICE SENSITIVITY", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 5), padx=20, anchor="w")
        
        # Sensitivity Slider
        ctk.CTkLabel(card_ai, text="Silence Threshold (Lower = More Sensitive)", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(10, 0), anchor="w", padx=20)
        self.sens_slider = ctk.CTkSlider(card_ai, from_=0.005, to=0.050, number_of_steps=45, 
                                         progress_color=self.app.clr_accent, button_color=self.app.clr_accent,
                                         variable=self.app.sensitivity,
                                         command=lambda _: self.app.save_settings())
        self.sens_slider.pack(pady=(5, 10), padx=20, fill="x")
        
        # Silence Patience
        ctk.CTkLabel(card_ai, text="Wait for Silence (Seconds)", font=ctk.CTkFont(size=13), text_color="#F8FAFC").pack(pady=(10, 0), anchor="w", padx=20)
        self.patience_slider = ctk.CTkSlider(card_ai, from_=0.5, to=5.0, number_of_steps=45, 
                                             progress_color=self.app.clr_accent, button_color=self.app.clr_accent,
                                             variable=self.app.silence_patience,
                                             command=lambda _: [self.app.save_settings(), setattr(self.app, 'silence_delay', int(self.app.silence_patience.get() * 1000))])
        self.patience_slider.pack(pady=(5, 20), padx=20, fill="x")
        
    def setup_account_tab(self):
        tab = self.tabview.tab("Account")
        
        # User Info Card
        email = self.app.sub_info.get("email", "Unknown User")
        plan = self.app.sub_info.get("plan", "FREE_TRIAL")
        
        card = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=15, border_width=1, border_color="#334155")
        card.pack(fill="x", padx=20, pady=20)
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=15)
        
        # User details
        ctk.CTkLabel(header, text="Loggeed in as", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748B").pack(anchor="w")
        ctk.CTkLabel(header, text=email, font=ctk.CTkFont(size=16, weight="bold"), text_color="#F8FAFC").pack(anchor="w")
        
        # Plan details
        plan_frame = ctk.CTkFrame(card, fg_color="#1E293B", corner_radius=10)
        plan_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        plan_color = "#10B981" if "PREMIUM" in plan else "#F59E0B"
        ctk.CTkLabel(plan_frame, text=f"CURRENT PLAN: {plan}", font=ctk.CTkFont(size=11, weight="bold"), text_color=plan_color).pack(pady=10)
        
        # Legacy Import Card
        card_key = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=15)
        card_key.pack(fill="x", padx=20, pady=0)
        
        ctk.CTkLabel(card_key, text="🔑 UPGRADE WITH LEGACY KEY", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748B").pack(pady=(15, 5), padx=20, anchor="w")
        
        self.key_entry = ctk.CTkEntry(card_key, placeholder_text="LEGACY-XXXXXX", height=40, font=ctk.CTkFont(family="Consolas", size=13))
        self.key_entry.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(card_key, text="Redeem License", fg_color=self.app.clr_accent, hover_color="#7C3AED", height=35,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     command=self.redeem_key).pack(pady=(0, 20), padx=20, fill="x")
        
        # Logout
        ctk.CTkButton(tab, text="🚪 Log Out & Switch Account", 
                     fg_color="#1E293B", hover_color="#334155",
                     text_color="#F87171", border_width=0,
                     font=ctk.CTkFont(family=self.app.FONT_TEXT, size=12),
                     height=40, corner_radius=12,
                     command=lambda: [self.on_close(), self.app.logout()]).pack(fill="x", pady=10, padx=20)

    def setup_security_tab(self):
        tab = self.tabview.tab("Security")
        
        # Header
        card = ctk.CTkFrame(tab, fg_color="#0F172A", corner_radius=15, border_width=1, border_color="#1E293B")
        card.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(card, text="🛡️ TWO-FACTOR AUTHENTICATION", 
                    font=ctk.CTkFont(size=12, weight="bold"), text_color="#A78BFA").pack(pady=(15, 5), padx=20, anchor="w")
        
        ctk.CTkLabel(card, text="Protect your account by requiring a code from your authenticator app.",
                    font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(pady=(0, 15), padx=20, anchor="w")
        
        # Setup Container
        self.sec_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.sec_container.pack(fill="both", expand=True, padx=20)
        
        # Initial State: Setup Button
        self.btn_setup_2fa = ctk.CTkButton(self.sec_container, text="Setup 2FA", 
                                          fg_color=self.app.clr_accent, hover_color="#7C3AED",
                                          font=ctk.CTkFont(weight="bold"),
                                          command=self.start_2fa_setup)
        self.btn_setup_2fa.pack(pady=20)
        
        # QR Display Area (Hidden initially)
        self.qr_frame = ctk.CTkFrame(self.sec_container, fg_color="#0F172A", corner_radius=15)
        
    def start_2fa_setup(self):
        from monetization_manager import MonetizationManager
        import base64
        import io
        
        self.btn_setup_2fa.configure(state="disabled", text="Loading...")
        
        success, data = MonetizationManager.setup_2fa()
        if success and data.get("qr"):
            # Hide setup button
            self.btn_setup_2fa.pack_forget()
            self.qr_frame.pack(fill="both", expand=True, pady=10)
            
            # Clear previous
            for widget in self.qr_frame.winfo_children():
                widget.destroy()
                
            # 1. Display QR Code
            try:
                qr_b64 = data.get("qr").split(",")[1] # Remove data:image/png;base64 header
                qr_bytes = base64.b64decode(qr_b64)
                qr_img = Image.open(io.BytesIO(qr_bytes))
                ctk_qr = ctk.CTkImage(qr_img, size=(180, 180))
                
                ctk.CTkLabel(self.qr_frame, text="1. Scan this QR Code", 
                            font=ctk.CTkFont(weight="bold"), text_color="#F8FAFC").pack(pady=(20, 10))
                
                ctk.CTkLabel(self.qr_frame, text="", image=ctk_qr).pack(pady=10)
                
                secret = data.get("secret", "UNKNOWN")
                ctk.CTkLabel(self.qr_frame, text=f"Secret: {secret}", 
                            font=ctk.CTkFont(family="Consolas", size=10), text_color="#64748B").pack(pady=5)
                
            except Exception as e:
                ctk.CTkLabel(self.qr_frame, text=f"Error displaying QR: {e}", text_color="#F87171").pack(pady=20)
                
            # 2. Key Entry
            ctk.CTkLabel(self.qr_frame, text="2. Enter 6-digit Code", 
                        font=ctk.CTkFont(weight="bold"), text_color="#F8FAFC").pack(pady=(20, 5))
            
            self.entry_otp = ctk.CTkEntry(self.qr_frame, placeholder_text="000000", justify="center",
                                         font=ctk.CTkFont(family="Consolas", size=18, weight="bold"), width=150)
            self.entry_otp.pack(pady=5)
            
            ctk.CTkButton(self.qr_frame, text="Verify & Enable", 
                         fg_color=self.app.clr_success, hover_color="#059669",
                         command=lambda: self.verify_2fa(secret)).pack(pady=20)
            
            # Cancel
            ctk.CTkButton(self.qr_frame, text="Cancel", fg_color="transparent", text_color="#94A3B8",
                         hover_color="#1E293B", command=self.reset_security_tab).pack(pady=(0, 20))
            
        else:
            messagebox.showerror("Error", f"Failed to setup 2FA: {data}")
            self.btn_setup_2fa.configure(state="normal", text="Setup 2FA")

    def reset_security_tab(self):
        self.qr_frame.pack_forget()
        self.btn_setup_2fa.configure(state="normal", text="Setup 2FA")
        self.btn_setup_2fa.pack(pady=20)

    def verify_2fa(self, secret):
        from monetization_manager import MonetizationManager
        code = self.entry_otp.get().strip()
        if len(code) != 6:
            messagebox.showwarning("Invalid Code", "Please enter a 6-digit code.")
            return
            
        success, msg = MonetizationManager.enable_2fa(secret, code)
        if success:
            messagebox.showinfo("Success", "Two-Factor Authentication Enabled!")
            self.reset_security_tab()
            self.btn_setup_2fa.configure(text="✅ 2FA Enabled", state="disabled", fg_color="#059669")
        else:
            messagebox.showerror("Error", msg)
            
    def redeem_key(self):
        key = self.key_entry.get().strip()
        if not key: return
        
        success, msg = MonetizationManager.redeem_license(key)
        if success:
            messagebox.showinfo("Success", msg)
            self.app.poll_subscription_status()
            self.setup_account_tab() # Refresh tab
        else:
            messagebox.showerror("Error", msg)


if __name__ == "__main__":
    # Check for Electron-provided authentication data
    auth_data_json = os.environ.get('NEBULA_AUTH_DATA')
    
    if auth_data_json:
        try:
            auth_data = json.loads(auth_data_json)
            token = auth_data.get('token')
            user_info = auth_data.get('user_info')
            
            if token:
                from monetization_manager import MonetizationManager
                MonetizationManager.save_session(token)
                
            if user_info:
                # Launch Main App directly with provided info
                app = MeetingPrompter(sub_info=user_info)
                app.run()
                sys.exit(0)
        except Exception as e:
            print(f"Error processing NEBULA_AUTH_DATA: {e}")
            relaunch_login_ui()
    else:
        # STANDALONE DEBUG MODE: Try to use existing session.json
        print("No NEBULA_AUTH_DATA found. Checking for local session...")
        from monetization_manager import MonetizationManager
        valid, info = MonetizationManager.validate_session()
        
        if valid:
            print(f"Logged in as: {info.get('email', 'Local User')}")
            app = MeetingPrompter(sub_info=info)
            app.run()
        else:
            print("No valid local session found.")
            # Only relaunch if we are NOT in a debug environment or if explicitly desired
            # For now, let's launch as a trial user for debugging purposes
            print("Launching in GUEST/TRIAL mode for debugging...")
            app = MeetingPrompter(sub_info={"plan": "FREE_TRIAL", "status": "ACTIVE", "email": "debug@local"})
            app.run()
