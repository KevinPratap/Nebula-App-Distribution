from PyQt6.QtCore import QObject, pyqtSignal as Signal, QThread
import os
import requests
from groq import Groq

class AIService(QObject):
    """
    Manages AI Context and Generates Responses.
    Uses a worker thread and signals for real-time streaming updates.
    """
    response_ready = Signal(str)      # Full response (finished)
    chunk_ready = Signal(str)         # Partial token (streaming)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.groq_key = os.environ.get('GROQ_API_KEY', '')
        self.gemini_key = os.environ.get('GEMINI_API_KEY', '')
        self.conversation_history = []
        self.resume_context = ""
        self.job_context = ""
        self.current_mode = "General" # Default mode
        self._worker = None

    def set_context(self, text, context_type="resume"):
        if context_type == "resume":
            self.resume_context = text
        elif context_type == "job":
            self.job_context = text

    def set_interview_mode(self, enabled):
        self.interview_mode = enabled

    def set_expert_mode(self, mode):
        """Allows switching between Technical, Architectural, and Behavioral modes"""
        valid_modes = ["Standard assistant", "Coding interview", "System design", "Behavioral (Soft skills)"]
        if mode in valid_modes:
            self.current_mode = mode

    def generate_response(self, question):
        """Start async generation with mode-specific structured instructions"""
        history_text = self._format_history()
        
        # Expert mode Logic (Nebula v6.0 Strategy)
        if self.current_mode == "Coding interview":
            mode_instruction = (
                "INTERVIEW MODE: TECHNICAL CODING. "
                "Structure your response: 1. Approach (2 sentences) 2. Time/Space Complexity (O(n)) 3. Edge Cases. "
                "Be technically precise. Use Big-O notation. Avoid generic fluff."
            )
        elif self.current_mode == "System design":
            mode_instruction = (
                "INTERVIEW MODE: SYSTEM DESIGN / ARCHITECTURE. "
                "Focus on: Scalability, High Availability, and Trade-offs (e.g., CAP Theorem). "
                "Suggest specific components (Load Balancers, Redis, S3, etc.) where relevant."
            )
        elif self.current_mode == "Behavioral (Soft skills)":
            mode_instruction = (
                "INTERVIEW MODE: BEHAVIORAL / HR. "
                "Enforce the STAR METHOD: Situation, Task, Action, Result. "
                "Ensure every answer concludes with a concrete measurable outcome/result."
            )
        else:
            mode_instruction = "Style: Professional, confident, and natural. Speak like a real person."

        # Base System Instruction
        if getattr(self, 'interview_mode', False):
             system_instruction = (
                 f"Context: You are the candidate, Kevin Pratap, in a live interview ({self.current_mode}). "
                 f"Special Instruction: {mode_instruction} "
                 "Task: Answer the interviewer's question directly using 'I' statements. "
                 "Approach: Mention specific resume projects naturally (e.g., 'When I built Nebula...'). "
                 "Constraint: No robotic preambles. No bullet points. Stay concise (2-4 sentences)."
             )
        else:
             system_instruction = f"Task: Helpful assistant. Mode: {self.current_mode}."

        # Combine Contexts
        full_context_block = ""
        if self.resume_context:
            full_context_block += f"Resume Context:\n{self.resume_context[:4000]}\n\n"
        if self.job_context:
            full_context_block += f"Job Description:\n{self.job_context[:2000]}\n"

        prompt = f"""[SYSTEM: {system_instruction}]
{full_context_block}
{history_text}
Interviewer: "{question}" """

        print(f"DEBUG: AI Prompt prepared. Mode: {self.current_mode}")
        self._worker = AIWorker(self.groq_key, self.gemini_key, prompt)
        self._worker.chunk_emitted.connect(self.chunk_ready.emit)
        self._worker.finished_signal.connect(lambda res, err: self._on_worker_finished(res, err, question, prompt))
        print("DEBUG: AI Worker starting...")
        self._worker.start()
        
    def _format_history(self):
        if not self.conversation_history: return ""
        hist = "\n--- HISTORY ---\n"
        for qa in self.conversation_history[-3:]:
             hist += f"Q: {qa['q']}\nA: {qa['a'][:100]}...\n"
        return hist
        
    def _on_worker_finished(self, result, error, question, prompt):
        if result:
            print(f"DEBUG: AI Response received ({len(result)} chars)")
            self.conversation_history.append({'q': question, 'a': result})
            self.response_ready.emit(result)
        elif error:
            print(f"DEBUG: AI Error: {error}")
            self.error_occurred.emit(error)

class AIWorker(QThread):
    chunk_emitted = Signal(str)     # Streaming token
    finished_signal = Signal(str, str) # result, error

    def __init__(self, groq_key, gemini_key, prompt):
        super().__init__()
        self.groq_key = groq_key
        self.gemini_key = gemini_key
        self.prompt = prompt

    def run(self):
        print("DEBUG: AIWorker thread running...")
        # Try Groq Streaming First
        if self.groq_key:
            try:
                print("DEBUG: Attempting Groq generation...")
                full_text = ""
                client = Groq(api_key=self.groq_key)
                
                stream = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": self.prompt}],
                    max_tokens=1000,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_text += token
                        self.chunk_emitted.emit(token)
                
                self.finished_signal.emit(full_text, None)
                return
            except Exception as e:
                print(f"Groq streaming failed: {e}")
        
        # Fallback Gemini (Non-streaming for now, or implement requests stream if needed)
        if self.gemini_key:
            try:
                # Basic Fallback (requests)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
                data = {"contents": [{"parts": [{"text": self.prompt}]}]}
                resp = requests.post(url, json=data, timeout=30)
                resp.raise_for_status()
                res = resp.json()['candidates'][0]['content']['parts'][0]['text']
                
                # Emit in one go for fallback
                self.chunk_emitted.emit(res)
                self.finished_signal.emit(res, None)
                return
            except Exception as e:
                pass
        
        self.finished_signal.emit(None, "All AI providers failed.")
