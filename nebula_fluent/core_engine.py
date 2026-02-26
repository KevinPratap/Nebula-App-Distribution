import os
import threading
import wave
import io
import time
import json
import requests
import re
import queue
import platform
import numpy as np

# Try to import speech_recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_AVAILABLE = False
    print("WARNING: speech_recognition not found. Transcription will not work.")

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
            if self.callback:
                self.callback(None, f"Audio Init Error: {e}", self.source_label)

    def _process_loop(self, continuous):
        """Consumer: Get audio from queue and recognize speech with silence detection"""
        
        if not SPEECH_AVAILABLE:
            print("Speech recognition not available")
            return

        if not self.recognizer:
            self.recognizer = sr.Recognizer()
        
        self.recognizer.energy_threshold = 300
        
        frames = []
        silence_counter = 0
        energy_threshold = 0.020  # V27: Increased from 0.012 to ignore noise floor hallucinations
        sample_rate = 16000
        
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
            
        try:
            audio_data = np.concatenate(frames)
            # V27: Guard against low-signal chunks (Whisper hallucinations)
            avg_rms = np.sqrt(np.mean(audio_data**2))
            if avg_rms < 0.015: # Total silence or near-silence
                # print(f"[{self.source_label}] Silence detected (RMS: {avg_rms:.4f})")
                # self.callback(None, "No speech detected (Silence)", self.source_label)
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
                pass # Silent fail on no speech
                
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
