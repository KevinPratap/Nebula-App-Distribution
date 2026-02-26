import json
import os
import time

class AnalyticsManager:
    """Tracks interview performance and session metrics."""
    def __init__(self, filename="analytics.json"):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filename = os.path.join(self.base_dir, filename)
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return self._defaults()
        return self._defaults()

    def _defaults(self):
        return {
            "total_sessions": 0,
            "total_questions": 0,
            "total_duration_seconds": 0,
            "last_session_timestamp": 0
        }

    def _save_data(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Failed to save analytics: {e}")

    def record_session(self, duration_seconds, question_count):
        """Update stats after a session ends."""
        self.data["total_sessions"] += 1
        self.data["total_questions"] += question_count
        self.data["total_duration_seconds"] += duration_seconds
        self.data["last_session_timestamp"] = time.time()
        self._save_data()

    def get_stats(self):
        """Return formatted stats for UI."""
        total_mins = self.data["total_duration_seconds"] // 60
        return {
            "sessions": self.data["total_sessions"],
            "questions": self.data["total_questions"],
            "duration": f"{total_mins}m"
        }
