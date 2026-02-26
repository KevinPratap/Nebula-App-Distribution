import os

def load_stylesheet():
    """Load QSS file from the same directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    style_path = os.path.join(current_dir, "styles.qss")
    
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            return f.read()
    return ""
