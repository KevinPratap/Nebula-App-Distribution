from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

class SplashScreen(QSplashScreen):
    def __init__(self, app_name="N E B U L A"):
        super().__init__()
        
        # Frameless and Always on Top
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Set Geometry (Center of Screen)
        self.resize(400, 250)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 40, 20, 40)
        self.setLayout(layout)
        
        # Styles
        self.setStyleSheet("background-color: #0F172A;")
        
        # Main Title
        self.lbl_title = QLabel(app_name)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: #A78BFA; font-size: 32px; font-weight: bold; font-family: 'Segoe UI Variable Display';")
        layout.addWidget(self.lbl_title)
        
        # Tagline
        self.lbl_tagline = QLabel("Waking up the AI...")
        self.lbl_tagline.setAlignment(Qt.AlignCenter)
        self.lbl_tagline.setStyleSheet("color: #94A3B8; font-size: 14px; margin-top: 10px; font-family: 'Segoe UI Variable Text';")
        layout.addWidget(self.lbl_tagline)

    def show_for(self, duration_ms):
        self.show()
        # Note: In a real app, this would be handled by the main thread loading process
