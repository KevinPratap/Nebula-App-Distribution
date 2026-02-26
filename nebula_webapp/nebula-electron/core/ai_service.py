import os
import sys
import requests
import threading
from groq import Groq

class AIService:
    """
    Manages AI Context and Generates Responses.
    Uses standard threading and callbacks for updates.
    v16.0: Added is_generating and interruption support.
    """
    def __init__(self):
        self.groq_key = os.environ.get('GROQ_API_KEY', '')
        self.gemini_key = os.environ.get('GEMINI_API_KEY', '')
        self.openai_key = os.environ.get('OPENAI_API_KEY', '')
        self.conversation_history = []
        self.resume_context = ""
        self.job_context = ""
        self.current_mode = "General" 
        self._worker = None
        self.is_generating = False
        self._stop_event = threading.Event()
        
        # Callbacks (Replaces Signals)
        self.on_response_callback = None # func(text, mode)
        self.on_chunk_callback = None    # func(token, mode)
        self.on_error_callback = None    # func(error_msg)

    def set_context(self, text, context_type="resume"):
        if context_type == "resume":
            self.resume_context = text
        elif context_type == "job":
            self.job_context = text

    def set_interview_mode(self, enabled):
        self.interview_mode = enabled

    def set_expert_mode(self, mode):
        """Allows switching between Technical, Architectural, Behavioral, and Auto modes"""
        valid_modes = ["Standard assistant", "Coding interview", "System design", "Behavioral (Soft skills)", "Auto"]
        if mode in valid_modes:
            self.current_mode = mode

    def cancel_generation(self):
        """Force stops the current AI worker"""
        if self.is_generating:
            sys.stderr.write("DEBUG: Interrupting active AI generation...\n")
            sys.stderr.flush()
            self._stop_event.set()
            self.is_generating = False

    def _detect_mode_for_question(self, question: str) -> str:
        """Classify the interviewer's question to automatically select the best strategy."""
        q = question.lower()
        
        coding_keywords = ["code", "algorithm", "function", "write", "implement", "complexity", "array", "string", "tree", "graph"]
        systems_keywords = ["design", "system", "scale", "architecture", "database", "microservice", "api", "load balancer"]
        behavioral_keywords = ["tell me about", "describe a time", "example of", "situation where", "how do you handle", "challenge"]
        
        coding_score = sum(1 for kw in coding_keywords if kw in q)
        systems_score = sum(1 for kw in systems_keywords if kw in q)
        behavioral_score = sum(1 for kw in behavioral_keywords if kw in q)
        
        max_score = max(coding_score, systems_score, behavioral_score)
        if max_score == 0: return "Standard assistant"
        if max_score == coding_score: return "Coding interview"
        if max_score == systems_score: return "System design"
        return "Behavioral (Soft skills)"

    def generate_response(self, question):
        """Start async generation with mode-specific structured instructions"""
        if self.is_generating:
            self.cancel_generation()
            time.sleep(0.1) # Brief pause for cleanup

        self._stop_event.clear()
        self.is_generating = True
        
        history_text = self._format_history()
        
        effective_mode = self.current_mode
        if self.current_mode == "Auto":
            effective_mode = self._detect_mode_for_question(question)
        
        # Mode selective instructions
        mode_instructions = {
            "Coding interview": "INTERVIEW MODE: TECHNICAL CODING. Structure: 1. Approach 2. Complexity 3. Edge Cases.",
            "System design": "INTERVIEW MODE: SYSTEM DESIGN. Focus on Scalability and Trade-offs.",
            "Behavioral (Soft skills)": "INTERVIEW MODE: BEHAVIORAL. Use STAR Method.",
        }
        mode_instruction = mode_instructions.get(effective_mode, "Style: Professional and natural.")

        if getattr(self, 'interview_mode', False):
             system_instruction = (
                 f"Context: Candidate Kevin Pratap ({effective_mode}). "
                 f"Instruction: {mode_instruction} Answer directly with 'I'. Stay concise (2-4 sentences)."
             )
        else:
             system_instruction = f"Task: Helpful assistant. Mode: {effective_mode}."

        full_context_block = f"Resume:\n{self.resume_context[:2000]}\n" if self.resume_context else ""
        
        prompt = f"[SYSTEM: {system_instruction}]\n{full_context_block}\n{history_text}\nInterviewer: \"{question}\""

        self._worker = AIWorker(self.groq_key, self.gemini_key, self.openai_key, prompt, self._stop_event)
        self._worker.on_chunk = lambda txt: self.on_chunk_callback(txt, effective_mode) if self.on_chunk_callback else None
        self._worker.on_finished = lambda res, err: self._on_worker_finished(res, err, question, effective_mode)
        
        threading.Thread(target=self._worker.run, daemon=True).start()
        
    def _format_history(self):
        if not self.conversation_history: return ""
        hist = "\n--- HISTORY ---\n"
        for qa in self.conversation_history[-3:]:
             hist += f"Q: {qa['q']}\nA: {qa['a'][:80]}...\n"
        return hist
        
    def _on_worker_finished(self, result, error, question, effective_mode):
        self.is_generating = False
        if result:
            self.conversation_history.append({'q': question, 'a': result})
            if self.on_response_callback:
                self.on_response_callback(result, effective_mode)
        elif error and not self._stop_event.is_set():
            if self.on_error_callback:
                self.on_error_callback(error)

class AIWorker:
    def __init__(self, groq_key, gemini_key, openai_key, prompt, stop_event):
        self.groq_key = groq_key
        self.gemini_key = gemini_key
        self.openai_key = openai_key
        self.prompt = prompt
        self.stop_event = stop_event
        self.on_chunk = None
        self.on_finished = None

    def run(self):
        def has_key(k): return bool(k and str(k).strip())

        if has_key(self.groq_key):
            try:
                client = Groq(api_key=self.groq_key)
                stream = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": self.prompt}],
                    max_tokens=800,
                    stream=True
                )
                full_text = ""
                for chunk in stream:
                    if self.stop_event.is_set(): return
                    if chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_text += token
                        if self.on_chunk: self.on_chunk(token)
                if self.on_finished: self.on_finished(full_text, None)
                return
            except Exception as e:
                sys.stderr.write(f"DEBUG: Groq failed: {e}\n")

        # Fallback Gemini/OpenAI removed for brevity in this scratch version for sidecar usage
        if self.on_finished: self.on_finished(None, "AI Request Failed")
