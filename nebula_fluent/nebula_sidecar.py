import time
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app_v3 import (
        AIProvider,
        TechnicalFixer,
        DualVoiceListener,
        SPEECH_AVAILABLE
    )
except ImportError as e:
    print(f"Error importing from app_v3: {e}")
    # Partial fallback for testing if app_v3 is missing
    AIProvider = None
    TechnicalFixer = None
    DualVoiceListener = None
    SPEECH_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Global State
state = {
    "is_listening": False,
    "transcript": [],
    "ai_suggestion": "Ready to assist. Start capture to begin.",
    "ai_timestamp": time.time(),
    "zen_mode": False
}

# Initialize AI
ai = AIProvider() if AIProvider else None
listener = None

def on_speech_detected(text, error, source):
    if error:
        print(f"[{source} Error: {error}]")
        return
    if text:
        fixed_text = TechnicalFixer.fix(text) if TechnicalFixer else text
        line = f"{source}: {fixed_text}"
        state["transcript"].append(line)
        if len(state["transcript"]) > 50:
            state["transcript"] = state["transcript"][-50:]
        
        # If interviewer speaks, trigger AI suggestion
        if source == "Interviewer" and ai:
            trigger_ai_suggestion(fixed_text)

def trigger_ai_suggestion(question):
    def callback(answer, error):
        if answer:
            state["ai_suggestion"] = answer
            state["ai_timestamp"] = time.time()
        elif error:
            state["ai_suggestion"] = f"AI Error: {error}"
            state["ai_timestamp"] = time.time()
            
    if ai:
        ai.answer_question(question, callback)

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "listening": state["is_listening"],
        "zen_mode": state["zen_mode"],
        "transcript_count": len(state["transcript"])
    })

@app.route('/transcript', methods=['GET'])
def get_transcript():
    limit = int(request.args.get('limit', 15))
    return jsonify({
        "lines": state["transcript"][-limit:]
    })

@app.route('/ai_response', methods=['GET'])
def get_ai_response():
    return jsonify({
        "text": state["ai_suggestion"],
        "timestamp": state["ai_timestamp"]
    })

@app.route('/toggle_listen', methods=['POST'])
def toggle_listen():
    global listener
    if not SPEECH_AVAILABLE:
        return jsonify({"error": "Speech recognition not available on this system"}), 500
        
    state["is_listening"] = not state["is_listening"]
    
    if state["is_listening"]:
        if not listener:
            listener = DualVoiceListener(on_speech_detected, ai_instance=ai)
        listener.start()
    else:
        if listener:
            listener.stop()
            
    return jsonify({"success": True, "listening": state["is_listening"]})

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    question = data.get('question')
    if question:
        trigger_ai_suggestion(question)
        return jsonify({"success": True})
    return jsonify({"error": "No question provided"}), 400

if __name__ == '__main__':
    print("Nebula Sidecar API starting on http://127.0.0.1:5001")
    app.run(port=5001)
