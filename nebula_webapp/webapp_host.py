import sys
import os
from PyQt6.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

# Import existing services (Restoring v6.8 logic)
from core.settings_manager import SettingsManager
from core.audio_service import AudioService
from core.ai_service import AIService
from monetization_manager import MonetizationManager

class NebulaBridge(QObject):
    """The high-speed bridge between Python and JS (Nebula v7.0)"""
    transcriptReceived = pyqtSignal(str, str) # text, source
    aiResponseReceived = pyqtSignal(str)      # response
    syncStatusUpdated = pyqtSignal(str)       # status

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @pyqtSlot(bool)
    def toggleListening(self, enabled):
        """Called from JS to start/stop the session"""
        print(f"DEBUG: Listening toggled to: {enabled}")
        if enabled:
            self.main_window.audio_interviewer.start()
        else:
            self.main_window.audio_interviewer.stop()

class WebAppHost(QWebEngineView):
    def __init__(self):
        super().__init__()
        
        # 1. Setup Shell
        self.setWindowTitle("Nebula Assistant v7.0")
        self.resize(1000, 800) # Default size, UI will be centered
        
        from PyQt6.QtGui import QColor
        self.page().setBackgroundColor(QColor(0, 0, 0, 0))
        
        # 2. Services
        self.settings = SettingsManager()
        self.ai = AIService()
        self.audio_interviewer = AudioService(use_loopback=True, source_label="Interviewer")
        
        # 3. Bridge Configuration
        self.bridge = NebulaBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)
        
        # 4. Connect Signals
        self.audio_interviewer.transcript_ready.connect(self.on_transcript)
        self.ai.response_ready.connect(self.bridge.aiResponseReceived.emit)
        
        # 5. Load UI (Development Mode)
        # In production, we'd load index.html from dist
        dev_url = "http://localhost:5173" 
        self.load(QUrl(dev_url))
        
        # Sync AI keys in background
        self.sync_ai_keys()

    def sync_ai_keys(self):
        def _sync():
            config = MonetizationManager.get_ai_config()
            if config:
                groq = config.get("GROQ_API_KEY")
                gemini = config.get("GEMINI_API_KEY")
                if groq: self.ai.groq_key = groq
                if gemini: self.ai.gemini_key = gemini
                status = f"Synced: Groq={'Yes' if groq else 'No'}, Gemini={'Yes' if gemini else 'No'}"
                self.bridge.syncStatusUpdated.emit(status)
                print(f"DEBUG: {status}")
        
        import threading
        threading.Thread(target=_sync, daemon=True).start()

    def on_transcript(self, text, source):
        if source == "Interviewer":
            self.bridge.transcriptReceived.emit(text, source)
            self.ai.generate_response(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable WebEngine Remote Debugging if needed
    # os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
    
    window = WebAppHost()
    window.show()
    sys.exit(app.exec())
