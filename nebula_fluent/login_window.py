import sys
import os
import ctypes
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFrame, QGraphicsDropShadowEffect, QCheckBox, 
                             QSpacerItem, QSizePolicy, QApplication, QMessageBox)
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QIcon

# Theme Constants (Synced with main app)
THEME = {
    "bg_mica": QColor(20, 20, 20, 245),       # More opaque to prevent background bleed
    "accent_primary": "#A78BFA",             # Nebula Violet
    "text_vibrant": "#FFFFFF", 
    "text_secondary": "#BDBDBD",
    "border_fluent": QColor(255, 255, 255, 25), # Slightly brighter border
}

class GlassFrame(QFrame):
    """Frosted glass panel matching the Nebula aesthetic"""
    def __init__(self, parent=None, radius=20, color=None):
        super().__init__(parent)
        self.radius = radius
        self.manual_color = color or THEME["bg_mica"]
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), self.radius, self.radius)
        painter.fillPath(path, self.manual_color)
        
        # Subtle Border
        pen = QPen(THEME["border_fluent"])
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)

class LoginWindow(QWidget):
    """Premium PyQt6 Login Window with Social Auth Hooks"""
    login_success = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 600)
        
        # Result data
        self.authenticated = False
        self.user_info = None

        self.setup_ui()
        self.center_on_screen()

    def setup_ui(self):
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Glass Container
        self.container = GlassFrame(self)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 20, 30, 30)
        container_layout.setSpacing(15)

        # 1. Custom Title Bar (Close only)
        title_bar = QHBoxLayout()
        title_bar.addStretch()
        self.btn_close = QPushButton("\uE8BB")
        self.btn_close.setFont(QFont("Segoe Fluent Icons", 10))
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton { 
                background: transparent; color: white; border-radius: 4px; 
            }
            QPushButton:hover { background: rgba(255, 0, 0, 0.4); }
        """)
        self.btn_close.clicked.connect(self.close)
        title_bar.addWidget(self.btn_close)
        container_layout.addLayout(title_bar)

        # 2. Header
        self.lbl_logo = QLabel("NEBULA AI")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setStyleSheet(f"color: {THEME['accent_primary']}; font-size: 24px; font-weight: 800; letter-spacing: 4px;")
        container_layout.addWidget(self.lbl_logo)

        self.lbl_subtitle = QLabel("Elevate your interview game.")
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; margin-bottom: 20px;")
        container_layout.addWidget(self.lbl_subtitle)

        # 3. Form Fields
        self.txt_email = QLineEdit()
        self.style_input(self.txt_email, "Email Address")
        container_layout.addWidget(self.txt_email)

        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.style_input(self.txt_pass, "Password")
        container_layout.addWidget(self.txt_pass)

        # 4. Remember Me
        self.chk_remember = QCheckBox("Remember me for 30 days")
        self.chk_remember.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        container_layout.addWidget(self.chk_remember)

        # 5. Sign In Button
        self.btn_signin = QPushButton("Sign In")
        self.btn_signin.setFixedHeight(45)
        self.btn_signin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_signin.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(167, 139, 250, 0.25);
                color: white;
                border-radius: 8px;
                font-weight: 700;
                font-size: 14px;
                border: 1px solid rgba(167, 139, 250, 0.4);
            }}
            QPushButton:hover {{ 
                background-color: rgba(167, 139, 250, 0.45); 
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        self.btn_signin.clicked.connect(self.handle_login)
        container_layout.addWidget(self.btn_signin)

        # 6. Divider
        divider_layout = QHBoxLayout()
        divider_layout.setContentsMargins(0, 10, 0, 10) # Added margins
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setStyleSheet("background: rgba(255,255,255,0.1);")
        lbl_or = QLabel("OR"); lbl_or.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 10px; font-weight: 700;")
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet("background: rgba(255,255,255,0.1);")
        divider_layout.addWidget(line1); divider_layout.addWidget(lbl_or); divider_layout.addWidget(line2)
        container_layout.addLayout(divider_layout)

        # 7. Social Login Section
        social_layout = QVBoxLayout()
        buttons_row = QHBoxLayout()
        self.btn_google = QPushButton(" Google")
        self.btn_github = QPushButton(" GitHub")
        
        self.lbl_auth_status = QLabel("")
        self.lbl_auth_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_auth_status.setStyleSheet("color: #A78BFA; font-size: 11px; font-weight: 600; margin-bottom: 5px;")
        self.lbl_auth_status.setVisible(False)
        social_layout.addWidget(self.lbl_auth_status)
        
        # Set Logos
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        google_path = os.path.join(assets_dir, "google_logo.png")
        github_path = os.path.join(assets_dir, "github_logo.png")
        
        if os.path.exists(google_path):
            self.btn_google.setIcon(QIcon(google_path))
            self.btn_google.setIconSize(QSize(18, 18))
        if os.path.exists(github_path):
            self.btn_github.setIcon(QIcon(github_path))
            self.btn_github.setIconSize(QSize(18, 18))
        
        for btn in [self.btn_google, self.btn_github]:
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.05);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 600;
                    padding-left: 10px;
                }
                QPushButton:hover { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); }
            """)
        
        self.btn_google.clicked.connect(self.handle_google_login)
        self.btn_github.clicked.connect(self.handle_github_login)
        
        buttons_row.addWidget(self.btn_google)
        buttons_row.addWidget(self.btn_github)
        social_layout.addLayout(buttons_row)
        container_layout.addLayout(social_layout)

        # 8. Footer
        footer_layout = QHBoxLayout()
        lbl_new = QLabel("New to Nebula?"); lbl_new.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        btn_signup = QPushButton("Create Account")
        btn_signup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_signup.setStyleSheet(f"color: {THEME['accent_primary']}; font-size: 12px; font-weight: 700; background: transparent; border: none; text-decoration: underline;")
        btn_signup.clicked.connect(lambda: os.startfile("https://www.nebulainterviewai.com/register"))
        footer_layout.addStretch()
        footer_layout.addWidget(lbl_new)
        footer_layout.addWidget(btn_signup)
        footer_layout.addStretch()
        container_layout.addLayout(footer_layout)

        main_layout.addWidget(self.container)

        # Shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0,150))
        shadow.setOffset(0,10)
        self.container.setGraphicsEffect(shadow)

    def style_input(self, widget, placeholder):
        widget.setPlaceholderText(placeholder)
        widget.setFixedHeight(45)
        widget.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding-left: 15px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {THEME['accent_primary']};
                background: rgba(255, 255, 255, 0.08);
            }}
        """)

    def handle_google_login(self):
        """Initiate Google OAuth flow with enhanced status (v6.2)"""
        from monetization_manager import MonetizationManager
        import uuid
        
        if hasattr(self, 'google_timer') and self.google_timer.isActive():
            # If already running, allow manual check status
            self.check_google_status()
            return

        self.session_id = str(uuid.uuid4())
        
        # Reset UI
        self.lbl_auth_status.setText("Connecting to Secure Auth Server...")
        self.lbl_auth_status.setVisible(True)
        self.btn_google.setText(" Cancel")
        self.btn_github.setEnabled(False)
        self.btn_signin.setEnabled(False)
        
        if MonetizationManager.initiate_google_login(self.session_id):
            self.lbl_auth_status.setText("Complete sign-in in your browser...")
            # Switch Google button to a "Check Status" manual fallback (v6.2.1)
            self.btn_google.setText(" Check Status")
            self.btn_google.setStyleSheet(self.btn_google.styleSheet().replace("rgba(255,255,255,0.05)", "rgba(167, 139, 250, 0.2)"))
            
            # Start polling for login status (Faster 1s polling for v6.2.5)
            self.google_timer = QTimer(self)
            self.google_timer.timeout.connect(self.check_google_status)
            self.google_timer.start(1000) 
        else:
            self.lbl_auth_status.setText("Failed to connect to auth server.")
            self.lbl_auth_status.setStyleSheet("color: #EF4444;")

    def handle_github_login(self):
        """Initiate GitHub OAuth flow (v6.8)"""
        from monetization_manager import MonetizationManager
        import uuid
        
        if hasattr(self, 'github_timer') and self.github_timer.isActive():
            self.check_github_status()
            return

        self.session_id = str(uuid.uuid4())
        
        # Reset UI
        self.lbl_auth_status.setText("Connecting to Secure Auth Server...")
        self.lbl_auth_status.setVisible(True)
        self.btn_github.setText(" Cancel")
        self.btn_google.setEnabled(False)
        self.btn_signin.setEnabled(False)
        
        if MonetizationManager.initiate_github_login(self.session_id):
            self.lbl_auth_status.setText("Complete sign-in in your browser...")
            # Start polling for login status
            self.github_timer = QTimer(self)
            self.github_timer.timeout.connect(self.check_github_status)
            self.github_timer.start(1000) 
        else:
            self.lbl_auth_status.setText("Failed to connect to auth server.")
            self.lbl_auth_status.setStyleSheet("color: #EF4444;")

    def check_github_status(self):
        """Check if Github auth completed"""
        from monetization_manager import MonetizationManager
        if MonetizationManager.check_github_login(self.session_id):
            if hasattr(self, 'github_timer'): self.github_timer.stop()
            self.lbl_auth_status.setText("GitHub Auth Successful!")
            self.lbl_auth_status.setStyleSheet("color: #10B981;")
            QTimer.singleShot(1000, self.accept)
            self.btn_github.setEnabled(True)
            self.btn_signin.setEnabled(True)
            QMessageBox.critical(self, "Google Login", "Failed to contact auth server.")

    def cancel_google_login(self):
        """Abort the polling process"""
        if hasattr(self, 'google_timer'):
            self.google_timer.stop()
        self.lbl_auth_status.setVisible(False)
        self.btn_google.setText(" Google")
        self.btn_github.setEnabled(True)
        self.btn_signin.setEnabled(True)

    def check_google_status(self):
        """Poll for successful Google authentication (v6.2)"""
        from monetization_manager import MonetizationManager
        if MonetizationManager.check_google_login(self.session_id):
            self.google_timer.stop()
            self.lbl_auth_status.setText("Authentication Successful! Finalizing...")
            
            # Successfully logged in via Google
            valid, info = MonetizationManager.validate_session()
            if valid:
                self.authenticated = True
                self.user_info = info
                self.login_success.emit(info)
                self.close()
            else:
                self.lbl_auth_status.setText("Session validation failed.")
                self.btn_google.setText(" Google")
                self.btn_google.setEnabled(True)
                self.btn_github.setEnabled(True)
                self.btn_signin.setEnabled(True)
                QMessageBox.critical(self, "Login Error", "Authentication succeeded but session validation failed.")

    def handle_login(self):
        from auth_manager import AuthManager
        email = self.txt_email.text().strip()
        password = self.txt_pass.text()

        if not email or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both email and password")
            return

        success, info = AuthManager.validate_login(email, password)
        if success:
            AuthManager.save_credentials(email, password, self.chk_remember.isChecked())
            self.authenticated = True
            self.user_info = info
            self.login_success.emit(info)
            self.close()
        else:
            error = info.get('error', 'Invalid Credentials')
            QMessageBox.critical(self, "Login Failed", error)

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def run(self):
        self.show()
        # Modal execution logic if used as standalone
        # However, for PyQt we often use signals or exec() for dialogs.
        # This is a basic non-blocking show.
        return self.authenticated, self.user_info

    # Drag window support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'drag_pos'):
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec())
