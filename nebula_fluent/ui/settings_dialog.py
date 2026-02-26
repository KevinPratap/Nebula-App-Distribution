from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, 
                               QDialogButtonBox, QWidget, QHBoxLayout, QPushButton, 
                               QTabWidget, QFormLayout, QLineEdit, QCheckBox, QSlider)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QLinearGradient, QColor

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(700, 550)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Styles for this Dialog specific elements
        self.setStyleSheet("""
            QDialog {
                background: transparent; /* Handled by paintEvent */
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                background: rgba(15, 23, 42, 0.6); /* Semi-transparent Slate */
                border-radius: 12px;
            }
            QTabBar::tab {
                background: transparent;
                color: #94A3B8;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: #F8FAFC;
                border-bottom: 2px solid #A78BFA;
            }
            QTabBar::tab:hover {
                color: #CBD5E1;
            }
            QLabel { color: #F8FAFC; font-size: 14px; font-weight: 500; }
            QLineEdit, QComboBox { 
                background: rgba(0, 0, 0, 0.3); 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                padding: 10px; 
                color: white; 
                border-radius: 8px;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #A78BFA;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        lbl_title = QLabel("Settings")
        lbl_title.setStyleSheet("font-size: 28px; font-weight: 800; color: #F8FAFC; margin-bottom: 20px; letter-spacing: 1px;")
        layout.addWidget(lbl_title)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 1. General Tab
        self.tab_general = QWidget()
        self.init_general_tab()
        self.tabs.addTab(self.tab_general, "General")
        
        # 2. Audio Tab
        self.tab_audio = QWidget()
        self.init_audio_tab()
        self.tabs.addTab(self.tab_audio, "Audio")
        
        # 3. AI Tab
        self.tab_ai = QWidget()
        self.init_ai_tab()
        self.tabs.addTab(self.tab_ai, "AI Model")
        
        # 4. Account Tab
        self.tab_account = QWidget()
        self.init_account_tab()
        self.tabs.addTab(self.tab_account, "Account")
        
        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 12px 30px;
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton[text="OK"] {
                background-color: #7C3AED;
                color: white;
                border: 1px solid #7C3AED;
            }
            QPushButton[text="OK"]:hover {
                background-color: #8B5CF6;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(btns)

    def paintEvent(self, event):
        # Draw the Midnight Gradient Background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Base Gradient
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#1E293B"))   # Slate 800
        gradient.setColorAt(1.0, QColor("#0F172A"))   # Slate 900
        
        # Rounded Rect
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 24, 24)
        painter.fillPath(path, gradient)
        
        # Border
        painter.setPen(QColor(255, 255, 255, 20))
        painter.drawPath(path)

    def init_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Theme
        layout.addWidget(QLabel("Appearance"))
        combo_theme = QComboBox()
        combo_theme.addItems(["Nebula Dark (Pro)", "Midnight Blue", "OLED Black"])
        layout.addWidget(combo_theme)
        
        # Window Behavior
        layout.addWidget(QLabel("Window Behavior"))
        chk_top = QCheckBox("Always Keep on Top")
        chk_top.setChecked(True)
        layout.addWidget(chk_top)
        
        chk_min = QCheckBox("Minimize to Tray on Close")
        layout.addWidget(chk_min)
        
        layout.addStretch()

    def init_audio_tab(self):
        layout = QFormLayout(self.tab_audio)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        combo_mic = QComboBox()
        combo_mic.addItems(["Default Microphone (Realtek)", "Headset (Virtual)", "Webcam Mic"])
        layout.addRow("Microphone:", combo_mic)
        
        combo_spk = QComboBox()
        combo_spk.addItems(["Default Speaker (Realtek)", "Headphones (Bluetooth)"])
        layout.addRow("Speaker (Loopback):", combo_spk)
        
        combo_lang = QComboBox()
        combo_lang.addItems(["English (United States)", "English (United Kingdom)", "Spanish", "French", "German", "Hindi", "Japanese"])
        layout.addRow("Language:", combo_lang)
        
        slider_vol = QSlider(Qt.Horizontal)
        slider_vol.setValue(100)
        layout.addRow("Input Gain:", slider_vol)

    def init_ai_tab(self):
        layout = QFormLayout(self.tab_ai)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        combo_model = QComboBox()
        combo_model.addItems(["Llama 3 70B (Groq) - Ultra Fast", "GPT-4o (OpenAI)", "Claude 3.5 Sonnet", "Gemini 1.5 Pro"])
        layout.addRow("Model:", combo_model)
        
        txt_sys = QLineEdit("You are a helpful assistant.")
        layout.addRow("System Prompt:", txt_sys)
        
        slider_temp = QSlider(Qt.Horizontal)
        slider_temp.setValue(70)
        layout.addRow("Creativity (Temp):", slider_temp)
        
        chk_stream = QCheckBox("Stream Responses")
        chk_stream.setChecked(True)
        layout.addRow("", chk_stream)

    def init_account_tab(self):
        layout = QVBoxLayout(self.tab_account)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        card = QWidget()
        card.setStyleSheet("background-color: #1E293B; border-radius: 8px; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        lbl_plan = QLabel("Nebula Pro Plan")
        lbl_plan.setStyleSheet("font-size: 18px; font-weight: bold; color: #A78BFA;")
        card_layout.addWidget(lbl_plan)
        
        lbl_status = QLabel("Status: Active (Renews Jan 2026)")
        lbl_status.setStyleSheet("color: #94A3B8;")
        card_layout.addWidget(lbl_status)
        
        btn_manage = QPushButton("Manage Subscription")
        btn_manage.setCursor(Qt.PointingHandCursor)
        btn_manage.setStyleSheet("background-color: #334155; margin-top: 10px;")
        card_layout.addWidget(btn_manage)
        
        layout.addWidget(card)
        layout.addStretch()
