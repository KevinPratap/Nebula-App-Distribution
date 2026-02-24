import json
import os

class SettingsManager:
    def __init__(self, filename="user_settings.json"):
        self.filename = os.path.join(os.getcwd(), filename)
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return self.defaults()
        return self.defaults()

    def defaults(self):
        return {
            "always_on_top": False,
            "stealth_mode": False,
            "interview_mode": False,
            "opacity": 100,
            "theme": "Nebula Dark",
            "groq_key": os.environ.get("GROQ_API_KEY", ""),
            "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
            "text_size": 14
        }

    def save_settings(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.defaults().get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
