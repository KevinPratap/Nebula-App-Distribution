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
        self.current_mode = "Auto" 
        self._worker = None
        self.is_generating = False
        self._stop_event = threading.Event()
        self.interview_mode = True # Enabled by default v30.2
        
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
        """Start async generation with structured message lists (v30.7)"""
        if self.is_generating:
            self.cancel_generation()
            import time
            time.sleep(0.1) # Brief pause for cleanup

        self._stop_event.clear()
        self.is_generating = True
        
        # DEBUG: Trace context flow
        sys.stderr.write(f"DEBUG: Generating AI Response. Resume Context Len: {len(self.resume_context)}\n")
        if self.resume_context:
            sys.stderr.write(f"DEBUG: First 100 chars of context: {self.resume_context[:100].strip()}\n")
        sys.stderr.flush()

        effective_mode = self.current_mode
        if self.current_mode == "Auto":
            effective_mode = self._detect_mode_for_question(question)
        
        # Mode selective instructions
        mode_instructions = {
            "Coding interview": "Focus on implementation, time/space complexity, and edge cases.",
            "System design": "Focus on high-level architecture, scalability, and technical trade-offs.",
            "Behavioral (Soft skills)": "Use the STAR method (Situation, Task, Action, Result) for structured storytelling.",
        }
        mode_instruction = mode_instructions.get(effective_mode, "Style: Professional, natural, and helpful.")

        messages = []
        
        # 1. Base System Instruction (Minimal)
        system_content = (
            f"You are a candidate in a {effective_mode} interview. {mode_instruction} "
            "Speak naturally and concisely (2-4 sentences max). Never mention being an AI."
        )
        messages.append({"role": "system", "content": system_content})

        # 2. Identity Priming (Simulated Start - highly effective for Llama models)
        if self.resume_context:
            messages.append({"role": "user", "content": f"Please memorize this resume and adopt it as YOUR OWN identity for this interview:\n\n{self.resume_context[:5000]}"})
            messages.append({"role": "assistant", "content": "Understood. I have fully memorized this profile. I am now acting as the candidate described in this resume. I will answer all questions from my personal perspective using 'I' and 'me'."})
        else:
            messages.append({"role": "user", "content": "I haven't uploaded my resume yet, but I'm ready to start. Please keep it generic but professional."})
            messages.append({"role": "assistant", "content": "Understood. I will answer as a professional candidate with a general background until you provide your resume."})

        # 3. History
        for qa in self.conversation_history[-2:]:
             messages.append({"role": "user", "content": qa['q']})
             messages.append({"role": "assistant", "content": qa['a']})
        
        # 4. Final Question (User message)
        messages.append({"role": "user", "content": question})

        # DEBUG: Trace final prompt structure
        sys.stderr.write(f"DEBUG: Internal Messages Count: {len(messages)}\n")
        if self.resume_context:
            sys.stderr.write(f"DEBUG: Identity Priming active ({len(self.resume_context)} chars)\n")
        sys.stderr.flush()

        self._worker = AIWorker(self.groq_key, self.gemini_key, self.openai_key, messages, self._stop_event)
        self._worker.on_chunk = lambda txt: self.on_chunk_callback(txt, effective_mode) if self.on_chunk_callback else None
        self._worker.on_finished = lambda res, err: self._on_worker_finished(res, err, question, effective_mode)
        
        # Signal UI to clear for new response
        if self.on_chunk_callback:
            self.on_chunk_callback("", effective_mode)
        
        threading.Thread(target=self._worker.run, daemon=True).start()
        
    def _on_worker_finished(self, result, error, question, effective_mode):
        self.is_generating = False
        try:
            if result:
                self.conversation_history.append({'q': question, 'a': result})
                if self.on_response_callback:
                    self.on_response_callback(result, effective_mode, question)
            elif error and not self._stop_event.is_set():
                if self.on_error_callback:
                    self.on_error_callback(error)
        except Exception as e:
            sys.stderr.write(f"DEBUG: Error in worker finished callback: {e}\n")
            sys.stderr.flush()

class AIWorker:
    def __init__(self, groq_key, gemini_key, openai_key, messages, stop_event):
        self.groq_key = groq_key
        self.gemini_key = gemini_key
        self.openai_key = openai_key
        self.messages = messages
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
                    messages=self.messages,
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
                import sys
                sys.stderr.write(f"DEBUG: Groq failed: {e}\n")

        if self.on_finished: self.on_finished(None, "AI Request Failed")
