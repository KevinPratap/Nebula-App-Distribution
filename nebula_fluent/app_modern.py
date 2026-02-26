import sys
import os
import ctypes
import time
from ctypes import c_int, c_void_p, Structure, byref

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QFrame, QGraphicsDropShadowEffect, QInputDialog, QFileDialog, QMessageBox, 
                             QMenu, QComboBox, QSlider, QCheckBox, QStackedLayout, QStackedWidget, QGridLayout, QPlainTextEdit, QSizePolicy, QLineEdit)
from PyQt6.QtCore import Qt, QPoint, QTimer, QThread, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QSize, QRect
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient, QRadialGradient, QPen, QBrush, QIcon, QAction
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

# Core Services - Lazy loaded to prevent COM conflicts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# from core.audio_service import AudioService # Moved to __init__
# from core.ai_service import AIService
# from core.hotkey_service import HotkeyService
# from core.settings_manager import SettingsManager
from monetization_manager import MonetizationManager
from auth_manager import AuthManager

# --- FLUENT WINDOWS 11 DESIGN SYSTEM ---
THEME = {
    "bg_mica": QColor(15, 15, 15, 120),       # Pure Translucent Acrylic
    "accent_primary": "#A78BFA",             # Nebula Violet
    "text_vibrant": "#FFFFFF", 
    "text_secondary": "#BDBDBD",
    "text_dim": "#888888",
    "border_fluent": QColor(255, 255, 255, 12),
    "font_main": "Segoe UI Variable Display, Segoe UI, sans-serif",
}

# --- WINDOWS BLUR ENGINE (Acrylic Mode) ---
class WINDOWCOMPOSITIONATTRIBDATA(Structure):
    _fields_ = [("Attribute", c_int), ("Data", c_void_p), ("SizeOfData", c_int)]

class AccentPolicy(Structure):
    _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), 
                ("GradientColor", c_int), ("AnimationId", c_int)]

def apply_soft_blur(hwnd):
    try:
        user32 = ctypes.windll.user32
        # 3 = ACCENT_ENABLE_BLURBEHIND (Stable backdrop blur)
        policy = AccentPolicy(3, 2, 0x00000000, 0) 
        data = WINDOWCOMPOSITIONATTRIBDATA(19, ctypes.cast(ctypes.pointer(policy), c_void_p), ctypes.sizeof(policy))
        user32.SetWindowCompositionAttribute(hwnd, byref(data))
        
        # --- STEALTH MODE (Hide from Screen Recording/Sharing) ---
        # WDA_EXCLUDEFROMCAPTURE = 0x00000011 (Windows 10+)
        user32.SetWindowDisplayAffinity(hwnd, 0x00000011)
    except: pass

def apply_hardcore_stealth(hwnd):
    """
    Advanced Stealth: Hide from Taskbar and Alt-Tab switcher.
    Uses Win32 Extended Window Styles.
    """
    try:
        user32 = ctypes.windll.user32
        # GWL_EXSTYLE = -20
        # WS_EX_TOOLWINDOW = 0x00000080
        # WS_EX_APPWINDOW = 0x00040000
        style = user32.GetWindowLongW(hwnd, -20)
        style = style | 0x00000080  # Add ToolWindow (hides from taskbar)
        style = style & ~0x00040000 # Remove AppWindow (prevent taskbar override)
        user32.SetWindowLongW(hwnd, -20, style)
    except: pass

class SoftGlass(QFrame):
    """Frosted acrylic panel with organic highlights"""
    def __init__(self, parent=None, radius=25, color=None, show_handle=True):
        super().__init__(parent)
        self.radius = radius
        self.manual_color = color
        self.show_handle = show_handle
        # REMOVED WA_TranslucentBackground to prevent click-through issues on child widgets

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect()
            
            # 1. Base material
            path = QPainterPath()
            path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), self.radius, self.radius)
            painter.fillPath(path, self.manual_color if self.manual_color else THEME["bg_mica"])
            
            # 2. Border REMOVED to satisfy "Clean Aesthetic"
            # (User requested no white borders)
            
            # 3. Horizontal Drag Handle (Small system detail)
            if self.show_handle:
                handle_pen = QPen(QColor(255, 255, 255, 40))
                handle_pen.setWidth(2)
                painter.setPen(handle_pen)
                center_x = rect.width() / 2
                painter.drawLine(int(center_x - 12), 4, int(center_x + 12), 4)
        except Exception:
            pass # Fail silently on render errors to prevent app exit

class FloatingPill(QWidget):
    """The soft-translucent 'Pill' with restored features"""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(420, 100)
        
        
        # Shared Services - Lazy Import
        from core.settings_manager import SettingsManager
        from core.audio_service import AudioService
        from core.hotkey_service import HotkeyService
        from core.ai_service import AIService
        from core.analytics_manager import AnalyticsManager
        from core.sync_manager import SyncManager
        
        self.settings = SettingsManager()
        self.analytics = AnalyticsManager()
        self.sync = SyncManager()
        self.audio_interviewer = AudioService(use_loopback=True, source_label="Interviewer")
        self.audio_me = AudioService(use_loopback=False, source_label="Me")
        self.hotkeys = HotkeyService()
        self.ai = AIService()
        self.ai.set_interview_mode(True) # Force Interview Persona
        
        # Load State
        saved_key = self.settings.get("groq_key")
        if saved_key: self.ai.groq_key = saved_key
        
        # Sync AI Keys from Website (v6.8)
        self.sync_ai_keys()
        
        # World Time Sync (v6.7)
        from monetization_manager import MonetizationManager
        MonetizationManager.sync_server_time()
        
        # Session Data
        self.user_info = None
        self.credits = 0
        self.is_session_paid = False

        self.is_live = False
        self.current_drawer_mode = None
        self.session_questions = 0
        self.session_start_time = 0 
        self.drawer_angle = 0 
        self.drag_pos = QPoint(0, 0) # Track mouse for movement (v6.2.4)
        self.current_drawer_mode = "response" 

        self.setup_ui()
        self.connect_signals()
        
        # v6.0 Core Stealth
        apply_hardcore_stealth(int(self.winId()))
        apply_hardcore_stealth(int(self.overlay.winId()))
        
        # Start hotkey listener
        self.hotkeys.start()

    def setup_ui(self):
        # 0. Global Fluent Font Asset
        self.f_icon = QFont("Segoe Fluent Icons", 14)
        if not self.f_icon.exactMatch(): self.f_icon = QFont("Segoe MDL2 Assets", 12)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(830) # 800px visual + 30px margins (15 each side)
        
        # --- STEALTH MODE: Translucency from Screen Capture ---
        try:
            # WDA_EXCLUDEFROMCAPTURE = 17 (Totally invisible, no black box)
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 17)
        except Exception as e:
            print(f"Stealth Mode Init Error: {e}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 12) # Account for handle
        
        # The Bar
        self.pill = SoftGlass(self, radius=8) # Sharper, modern Win11 radius
        self.pill.setFixedSize(800, 42) # STRICT ORIGINAL DIMENSIONS
        bar_layout = QHBoxLayout(self.pill)
        bar_layout.setContentsMargins(16, 0, 8, 0)
        bar_layout.setSpacing(12)
        
        # 1. Brand (Fluent Style)
        self.label = QLabel("Nebula AI [v6.1]")
        self.label.setStyleSheet(f"""
            color: {THEME['text_vibrant']}; 
            font-family: {THEME['font_main']}; 
            font-size: 13px; 
            font-weight: 500; 
        """)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {THEME['accent_primary']}; font-size: 14px; border: none; background: transparent;")
        
        # 2.1 Session Timer (v6.5)
        self.lbl_session_timer = QLabel("")
        self.lbl_session_timer.setStyleSheet(f"color: {THEME['accent_primary']}; font-family: {THEME['font_main']}; font-size: 11px; font-weight: 700; margin-left: 2px;")
        self.lbl_session_timer.setVisible(False)
        
        # 3. Operations Group
        self.btn_account = QPushButton("\uE77B") # User Profile icon
        self.setup_fluent_btn(self.btn_account)
        self.btn_account.setToolTip("Account & Credits")
        self.btn_account.clicked.connect(self.show_account)

        self.btn_context = QPushButton("\uE929") # Clipboard List (Context/Prep)
        self.setup_fluent_btn(self.btn_context)
        self.btn_context.setToolTip("Interview Context")
        self.btn_context.clicked.connect(self.prompt_context)

        self.btn_settings = QPushButton("\uE713")
        self.setup_fluent_btn(self.btn_settings)
        self.btn_settings.clicked.connect(self.show_settings)
        
        # 4. Primary Action (Fluent Accent)
        self.btn_mic = QPushButton("\uE720")
        self.btn_mic.setFixedSize(40, 28)
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic.setFont(self.f_icon)

        self.btn_mic.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(167, 139, 250, 0.25);
                color: white;
                border: 1px solid rgba(167, 139, 250, 0.4);
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: rgba(167, 139, 250, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        self.btn_mic.clicked.connect(self.toggle_session)
        
        # 5. Controls
        self.btn_expand = QPushButton("\uE70D") # Fluent style arrow
        self.setup_fluent_btn(self.btn_expand)
        self.btn_expand.clicked.connect(self.toggle_drawer)
        
        self.btn_close = QPushButton("\uE8BB") # Segoe MDL2 Assets close
        self.setup_fluent_btn(self.btn_close)
        self.btn_close.clicked.connect(self.close)
        
        bar_layout.addWidget(self.btn_account)
        bar_layout.addWidget(self.dot)
        bar_layout.addWidget(self.label)
        bar_layout.addWidget(self.lbl_session_timer)
        bar_layout.addStretch()
        bar_layout.addWidget(self.btn_context)
        bar_layout.addWidget(self.btn_settings)
        bar_layout.addWidget(self.btn_mic)
        bar_layout.addWidget(self.btn_expand)
        bar_layout.addWidget(self.btn_close)
        
        layout.addWidget(self.pill)
        self.setup_ui_post()

    def setup_fluent_btn(self, btn):
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(self.f_icon)
            
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
        color: {THEME['text_vibrant']};
            }}
        """)

    def setup_auth_btn(self, btn, primary=True):
        """Helper for elegantly styled glassmorphic text buttons"""
        btn.setFixedHeight(36)
        btn.setMinimumWidth(100)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Elegant Glassmorphic Palette
        bg = "rgba(167, 139, 250, 0.25)" if primary else "rgba(255, 255, 255, 0.05)"
        fg = "white"
        border = "rgba(167, 139, 250, 0.4)" if primary else "rgba(255, 255, 255, 0.1)"
        hov = "rgba(167, 139, 250, 0.45)" if primary else "rgba(255, 255, 255, 0.15)"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid {border};
            }}
            QPushButton:hover {{ 
                background-color: {hov}; 
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)

    def set_mini_btn_style(self, btn):
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_dim']};
                border-radius: 15px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: {THEME['text_main']};
            }}
        """)



    def reposition_overlay(self):
        """Unified repositioning to prevent ghosting/drift"""
        # Safety Check: Ensure window exists before calling isVisible()
        if not hasattr(self, 'overlay') or not self.overlay or not self.overlay.isWidgetType(): return
        if not self.overlay.isVisible(): return
        target_x = self.pos().x() + 15
        target_y = self.pos().y() + 75 # Standardized deep gap for premium aesthetic
        if self.overlay.pos() != QPoint(target_x, target_y):
            self.overlay.move(target_x, target_y)

    def open_drawer(self, mode="response"):
        """Opens drawer in specific mode (Stable v3.4)"""
        # Safety Check: Ensure window exists before calling methods
        if not hasattr(self, 'overlay') or not self.overlay or not self.overlay.isWidgetType(): return
        
        # Brute-force Hide Inactive Pages
        all_containers = [self.response_container, self.settings_container, self.account_container, self.context_container]
        
        # Explicit Switch Logic (Direct Mode)
        target_widget = None
        if mode == "response": target_widget = self.response_container
        elif mode == "settings": 
            self.refresh_settings_ui()
            target_widget = self.settings_container
        elif mode == "account": 
            self.refresh_settings_ui()
            target_widget = self.account_container
        elif mode == "context": target_widget = self.context_container
        
        if target_widget:
            self.stack_widget.setCurrentWidget(target_widget)
            for container in all_containers:
                if container == target_widget:
                    container.show()
                    container.raise_()
                else:
                    container.hide()
                
        self.current_drawer_mode = mode
        
        # Dynamic resize first
        self.adjust_drawer_size() 
        current_height = self.overlay.height()

        target_x = self.pos().x() + 15
        target_y_visible = self.pos().y() + 75 # Balanced 75 offset
        
        if not self.overlay.isVisible():
            # Animate Open
            self.overlay.setWindowOpacity(0.0)
            target_y_hidden = self.pos().y() + 60 # Hidden starting point closer to bar
            self.overlay.setGeometry(target_x, target_y_hidden, 800, current_height)
            self.overlay.show()
            
            self.anim_fade_in = QPropertyAnimation(self.overlay, b"windowOpacity")
            self.anim_fade_in.setDuration(300)
            self.anim_fade_in.setStartValue(0.0)
            self.anim_fade_in.setEndValue(1.0)
            
            self.anim_drop = QPropertyAnimation(self.overlay, b"geometry")
            self.anim_drop.setDuration(350)
            self.anim_drop.setEasingCurve(QEasingCurve.Type.OutQuad)
            self.anim_drop.setStartValue(QRect(target_x, target_y_hidden, 800, current_height))
            self.anim_drop.setEndValue(QRect(target_x, target_y_visible, 800, current_height))
            
            self.anim_fade_in.start()
            self.anim_drop.start()
            self.btn_expand.setText("\uE70E")
        else:
            self.reposition_overlay()

    def toggle_drawer(self):
        """Toggle logic for manual button click (Always opens Response)"""
        if self.overlay.isVisible():
            self.close_drawer()
        else:
            self.open_drawer("response")

    def close_drawer(self):
        if not self.overlay.isVisible(): return
        
        self.anim_fade_out = QPropertyAnimation(self.overlay, b"windowOpacity")
        self.anim_fade_out.setDuration(200)
        self.anim_fade_out.setStartValue(1.0)
        self.anim_fade_out.setEndValue(0.0)
        
        self.anim_slide_up = QPropertyAnimation(self.overlay, b"geometry")
        self.anim_slide_up.setDuration(250)
        self.anim_slide_up.setStartValue(self.overlay.geometry())
        self.anim_slide_up.setEndValue(self.overlay.geometry().translated(0, -20))
        
        self.anim_fade_out.finished.connect(self.overlay.hide)
        self.anim_fade_out.start()
        self.anim_slide_up.start()
        self.btn_expand.setText("\uE70D")

    def show_settings(self):
        """Dedicated Settings Entry (v3.4)"""
        if not hasattr(self, 'overlay') or not self.overlay or not self.overlay.isWidgetType(): return
        
        if self.overlay.isVisible() and self.current_drawer_mode == "settings":
            self.close_drawer()
        else:
            self.open_drawer("settings")

    def show_account(self):
        """Dedicated Account Entry (v3.4)"""
        if not hasattr(self, 'overlay') or not self.overlay or not self.overlay.isWidgetType(): return
        
        if self.overlay.isVisible() and self.current_drawer_mode == "account":
            self.close_drawer()
        else:
            self.open_drawer("account")

    def refresh_settings_ui(self):
        """Update Settings and Account UI with latest database data (v6.2)"""
        try:
            valid, info = MonetizationManager.validate_session()
            is_auth = valid and info is not None
            
            # UI Toggling
            if hasattr(self, 'guest_view'):
                self.guest_view.setVisible(not is_auth)
            if hasattr(self, 'auth_stats_view'):
                self.auth_stats_view.setVisible(is_auth)
            if hasattr(self, 'btn_login'):
                self.btn_login.setVisible(not is_auth)
            if hasattr(self, 'btn_logout'):
                self.btn_logout.setVisible(is_auth)
                
            if is_auth:
                # Populate with live DB data
                email = info.get("email", "User")
                name = info.get("name", email.split('@')[0].upper())
                credits = info.get("credits", 0)
                plan = info.get("plan", "Standard").upper()
                
                if hasattr(self, 'lbl_user_name'):
                    self.lbl_user_name.setText(name)
                if hasattr(self, 'lbl_user_email'):
                    self.lbl_user_email.setText(email)
                if hasattr(self, 'lbl_credits'):
                    self.lbl_credits.setText(f"{credits} Credits Remaining")
                if hasattr(self, 'lbl_plan'):
                    self.lbl_plan.setText(f"PLAN: {plan}")
                
                # Update analytics from DB
                if hasattr(self, 'lbl_stats_questions'):
                    self.lbl_stats_questions.setText(str(info.get("total_questions", 0)))
                if hasattr(self, 'lbl_stats_duration'):
                    self.lbl_stats_duration.setText(f"{info.get('total_minutes', 0)}m")
                if hasattr(self, 'lbl_sync_status'):
                    self.lbl_sync_status.setText("Synced with Cloud Database")
            else:
                # Guest Mode Defaults
                if hasattr(self, 'lbl_user_name'):
                    self.lbl_user_name.setText("GUEST USER")
                if hasattr(self, 'lbl_user_email'):
                    self.lbl_user_email.setText("Sign in to sync your profile")
                if hasattr(self, 'lbl_credits'):
                    self.lbl_credits.setText("0 Credits Remaining")
                if hasattr(self, 'lbl_plan'):
                    self.lbl_plan.setText("PLAN: GUEST")

            # Update Device Selectors (Common Logic)
            current_mic = self.settings.get("mic_id")
            current_spk = self.settings.get("speaker_id")
            
            self.cmb_mic.blockSignals(True)
            self.cmb_mic.clear()
            for dev in self.audio_me.get_input_devices():
                self.cmb_mic.addItem(dev['name'], dev['id'])
            for i in range(self.cmb_mic.count()):
                if self.cmb_mic.itemData(i) == current_mic:
                    self.cmb_mic.setCurrentIndex(i)
                    break
            self.cmb_mic.blockSignals(False)
            
            self.cmb_spk.blockSignals(True)
            self.cmb_spk.clear()
            for dev in self.audio_me.get_output_devices():
                self.cmb_spk.addItem(dev['name'], dev['id'])
            for i in range(self.cmb_spk.count()):
                if self.cmb_spk.itemData(i) == current_spk:
                    self.cmb_spk.setCurrentIndex(i)
                    break
            self.cmb_spk.blockSignals(False)
            
            # Update Text Size
            if hasattr(self, 'slider_text_size'):
                sz = self.settings.get("text_size")
                if sz:
                    self.slider_text_size.setValue(int(sz))
                    self.apply_text_size(sz)

        except Exception as e:
            print(f"Settings Refresh Error: {e}")

    def on_device_changed(self, index, type):
        try:
            if type == "mic":
                dev_id = self.cmb_mic.currentData()
                self.settings.set("mic_id", dev_id)
            else:
                dev_id = self.cmb_spk.currentData()
                self.settings.set("speaker_id", dev_id)
            
            # Restart Audio if live
            if self.is_live:
                self.stop_session()
                QTimer.singleShot(300, self.start_session)
        except Exception as e:
            print(f"Device Change Error: {e}")

    def prompt_context(self):
        """Open Context Drawer"""
        if self.overlay.isVisible() and self.current_drawer_mode == "context":
             self.close_drawer()
        else:
             self.open_drawer("context")

    def upload_resume(self):
        """Professional Resume Upload (PDF/DOCX/TXT)"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Upload Resume", "", 
                                                  "Documents (*.pdf *.docx *.txt);;All Files (*)")
        if file_path:
            content = ""
            try:
                ext = file_path.lower().split('.')[-1]
                if ext == 'pdf' and PyPDF2:
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        content = "\n".join(page.extract_text() or "" for page in reader.pages)
                elif ext == 'docx' and docx:
                    doc = docx.Document(file_path)
                    content = "\n".join(para.text for para in doc.paragraphs)
                else:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                
                if content:
                    self.ai.set_context(content, "resume")
                    self.lbl_resume_status.setText(f"Resume: {file_path.split('/')[-1]} ✅")
                    self.lbl_resume_status.setStyleSheet("color: #10B981; font-size: 12px;")
                else:
                    QMessageBox.warning(self, "Warning", "File appeared empty.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to parse document: {str(e)}")

    def sync_context(self):
        """Save Job Description & Sync"""
        job_text = self.txt_job_context.toPlainText()
        self.ai.set_context(job_text, "job")
        
        # Visual Feedback
        self.btn_sync.setText("Synced! 🚀")
        QTimer.singleShot(2000, lambda: self.btn_sync.setText("Save & Sync Context"))
        
        # Auto-switch to response view after short delay
        QTimer.singleShot(1000, lambda: self.open_drawer("response"))

    def setup_ui_post(self):
        # Overall Shadow
        outer_shadow = QGraphicsDropShadowEffect()
        outer_shadow.setBlurRadius(30)
        outer_shadow.setColor(QColor(0, 0, 0, 100))
        outer_shadow.setOffset(0, 10)
        self.pill.setGraphicsEffect(outer_shadow)
        
        # Expandable Suggestion Overlay
        # RE-ENABLE init done guard for strict single-run
        if not hasattr(self, 'overlay_init_done'):
             self.setup_overlay()
             self.overlay_init_done = True

    def setup_overlay(self):
        # DEFINITIVE ZOMBIE PURGE: Kill ANY window across the process named 'NebulaDrawerOverlay'
        # This prevents the "AACCOUNT" and "Buttons not opening" issues (Zombie windows blocking clicks)
        for widget in QApplication.topLevelWidgets():
            if widget.objectName() == "NebulaDrawerOverlay":
                try:
                    widget.hide()
                    widget.deleteLater()
                except: pass
            
        self.overlay = QWidget()
        self.overlay.setObjectName("NebulaDrawerOverlay") # STATIC NAME for purge
        self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.overlay.resize(800, 280) 
        
        # Apply Stealth to Overlay too
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.overlay.winId()), 17)
        except: pass
        ov_layout = QVBoxLayout(self.overlay)
        ov_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Glass Container
        drawer_bg = QColor(15, 15, 15, 110)
        self.ov_glass = SoftGlass(self.overlay, radius=12, color=drawer_bg, show_handle=False)
        self.ov_glass.setMinimumHeight(220)
        self.ov_glass.setStyleSheet(f"border-radius: 12px;")
        
        # Main Layout for ov_glass
        glass_layout = QVBoxLayout(self.ov_glass)
        glass_layout.setContentsMargins(30, 20, 30, 20)
        glass_layout.setSpacing(15)

        # Stacked Widget for Content Switching
        self.stack_widget = QStackedWidget()
        glass_layout.addWidget(self.stack_widget)
        
        # --- VIEW 1: RESPONSE TEXT ---
        self.response_container = QWidget()
        self.response_container.setStyleSheet("background: transparent; border: none;")
        rc_layout = QVBoxLayout(self.response_container)
        rc_layout.setContentsMargins(25, 20, 25, 20)
        
        self.suggest_text = QLabel("Nebula is ready. Focus on your interview.")
        self.suggest_text.setWordWrap(True)
        self.suggest_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.suggest_text.setStyleSheet(f"color: {THEME['text_vibrant']}; font-size: 14px; line-height: 1.4;")
        rc_layout.addWidget(self.suggest_text)
        self.stack_widget.addWidget(self.response_container)
        
        # --- VIEW 2: SETTINGS (General) ---
        self.setup_settings_panel()
        self.stack_widget.addWidget(self.settings_container)
        
        # --- VIEW 3: ACCOUNT ---
        self.setup_account_panel()
        self.stack_widget.addWidget(self.account_container)
        
        # --- VIEW 4: CONTEXT ---
        self.setup_context_panel()
        self.stack_widget.addWidget(self.context_container)
        
        ov_layout.addWidget(self.ov_glass)
        
        # Shadow removed from ov_glass to prevent mouse event blocking (Hotfix v4.3)
        
        self.overlay.hide()
        apply_soft_blur(self.overlay.winId())

    def setup_context_panel(self):
        if hasattr(self, 'context_container'): return
        self.context_container = QWidget()
        cl = QVBoxLayout(self.context_container)
        cl.setSpacing(10)
        cl.setContentsMargins(25, 15, 25, 15)
        
        # Header
        lbl_head = QLabel("INTERVIEW STRATEGY", self.context_container)
        lbl_head.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: none; background: transparent;")
        cl.addWidget(lbl_head)

        # Mode Selector (v6.0)
        self.cmb_mode = QComboBox(self.context_container)
        self.cmb_mode.addItems(["Standard assistant", "Coding interview", "System design", "Behavioral (Soft skills)"])
        self.cmb_mode.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(167, 139, 250, 0.1);
                border: 1px solid rgba(167, 139, 250, 0.3);
                border-radius: 6px;
                color: {THEME['text_vibrant']};
                padding: 8px 12px;
                font-weight: 500;
                font-size: 13px;
                min-height: 38px;
            }}
            QComboBox:hover {{ border: 1px solid {THEME['accent_primary']}; }}
            QComboBox QAbstractItemView {{
                background-color: #1A1A1A;
                color: white;
                selection-background-color: {THEME['accent_primary']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                outline: none;
                padding: 4px;
            }}
        """)
        self.cmb_mode.currentTextChanged.connect(self.ai.set_expert_mode)
        cl.addWidget(self.cmb_mode)
        
        cl.addSpacing(10)

        lbl_context = QLabel("JOB CONTEXT", self.context_container)
        lbl_context.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: none; background: transparent;")
        cl.addWidget(lbl_context)
        
        # Job Description Input
        self.txt_job_context = QPlainTextEdit(self.context_container)
        self.txt_job_context.setMinimumHeight(100)
        self.txt_job_context.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.txt_job_context.setPlaceholderText("Paste Job Description, Role Details, or specific topics here...")
        self.txt_job_context.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: {THEME['text_vibrant']};
                font-family: {THEME['font_main']};
                font-size: 13px;
                padding: 12px;
                line-height: 1.4;
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {THEME['accent_primary']};
                background-color: rgba(255, 255, 255, 0.08);
            }}
        """)
        cl.addWidget(self.txt_job_context)
        
        # Resume Status
        self.lbl_resume_status = QLabel("Resume: Not Uploaded", self.context_container)
        self.lbl_resume_status.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 12px; border: none; background: transparent;")
        cl.addWidget(self.lbl_resume_status)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        btn_upload = QPushButton("📄 Upload Resume", self.context_container)
        btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.15); }}
        """)
        btn_upload.clicked.connect(self.upload_resume)
        
        self.btn_sync = QPushButton("💾 Save & Sync", self.context_container)
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent_primary']};
                color: black;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{ background-color: #C4B5FD; }}
        """)
        self.btn_sync.clicked.connect(self.sync_context)
        
        btn_layout.addWidget(btn_upload)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_sync)
        
        cl.addLayout(btn_layout)

    def setup_settings_panel(self):
        if hasattr(self, 'settings_container'): return
        self.settings_container = QWidget()
        self.settings_container.setStyleSheet("background: transparent; border: none;")
        sl = QVBoxLayout(self.settings_container)
        sl.setSpacing(22) # Tightened for v4.3 hotfix
        sl.setContentsMargins(40, 20, 40, 20) # Optimized margins
        
        # Minimalist Style
        combo_style = f"""
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: {THEME['text_vibrant']};
                padding: 0px 15px; 
                min-height: 50px; /* Locked height for perfect text centering */
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
                outline: none;
            }}
            QComboBox:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {THEME['accent_primary']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ 
                image: none;
                border-top: 5px solid {THEME['text_secondary']};
                border-left: 5px solid transparent; 
                border-right: 5px solid transparent;
                margin-right: 15px; /* More room */
            }}
            QComboBox QAbstractItemView {{
                background-color: #1E1E1E;
                color: white;
                selection-background-color: {THEME['accent_primary']};
                border: 1px solid #333;
                outline: none;
            }}
        """
        
        # Mic Section
        vmic = QVBoxLayout()
        vmic.setSpacing(8) # Tight gap between label and control
        lbl_mic = QLabel("MICROPHONE", self.settings_container)
        lbl_mic.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;")
        self.cmb_mic = QComboBox(self.settings_container)
        self.cmb_mic.setStyleSheet(combo_style)
        self.cmb_mic.currentIndexChanged.connect(lambda i: self.on_device_changed(i, "mic"))
        vmic.addWidget(lbl_mic)
        vmic.addWidget(self.cmb_mic)
        sl.addLayout(vmic)
        
        # Speaker Section
        vspk = QVBoxLayout()
        vspk.setSpacing(8)
        lbl_spk = QLabel("SPEAKER", self.settings_container)
        lbl_spk.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;")
        self.cmb_spk = QComboBox(self.settings_container)
        self.cmb_spk.setStyleSheet(combo_style)
        self.cmb_spk.currentIndexChanged.connect(lambda i: self.on_device_changed(i, "spk"))
        vspk.addWidget(lbl_spk)
        vspk.addWidget(self.cmb_spk)
        sl.addLayout(vspk)
        
        # --- NEW: Opacity Control ---
        vopac = QVBoxLayout()
        vopac.setSpacing(12)
        lbl_opacity = QLabel("OPACITY", self.settings_container)
        lbl_opacity.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: none; background: transparent;")
        
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal, self.settings_container)
        self.slider_opacity.setRange(50, 255) # 50 = barely visible, 255 = opaque
        self.slider_opacity.setValue(120) # Default
        self.slider_opacity.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid rgba(255, 255, 255, 10);
                height: 4px; 
                background: rgba(0, 0, 0, 0.3);
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['accent_primary']};
                border: 1px solid {THEME['accent_primary']};
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }}
        """)
        self.slider_opacity.valueChanged.connect(self.on_opacity_changed)
        vopac.addWidget(lbl_opacity)
        vopac.addWidget(self.slider_opacity)
        sl.addLayout(vopac)

        # --- NEW: Stealth Mode ---
        vpriv = QVBoxLayout()
        vpriv.setSpacing(12)
        lbl_stealth = QLabel("PRIVACY", self.settings_container)
        lbl_stealth.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: none; background: transparent;")
        
        self.chk_stealth = QCheckBox("Ghost Mode (Hide from Screen Share)", self.settings_container)
        self.chk_stealth.setChecked(True) # Default ON for safety
        self.chk_stealth.setStyleSheet(f"""
            QCheckBox {{
                color: {THEME['text_vibrant']};
                font-family: {THEME['font_main']};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: rgba(255, 255, 255, 0.05);
            }}
            QCheckBox::indicator:checked {{
                background: {THEME['accent_primary']};
                border: 1px solid {THEME['accent_primary']};
                image: url(none); /* Custom checkmark could go here if needed */
            }}
        """)
        self.chk_stealth.toggled.connect(self.on_stealth_toggled)
        vpriv.addWidget(lbl_stealth)
        vpriv.addWidget(self.chk_stealth)
        sl.addLayout(vpriv)
        
        # --- NEW: Text Size Control (v4.2) ---
        vtext = QVBoxLayout()
        vtext.setSpacing(12)
        lbl_tsize = QLabel("TEXT SIZE", self.settings_container)
        lbl_tsize.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: none; background: transparent;")
        
        self.slider_text_size = QSlider(Qt.Orientation.Horizontal, self.settings_container)
        self.slider_text_size.setRange(10, 32)
        self.slider_text_size.setValue(14)
        self.slider_text_size.setStyleSheet(self.slider_opacity.styleSheet()) # Reuse slider styling
        self.slider_text_size.valueChanged.connect(self.on_text_size_changed)
        
        vtext.addWidget(lbl_tsize)
        vtext.addWidget(self.slider_text_size)
        
        # --- NEW: Live Preview Box (v4.3) ---
        self.lbl_preview = QLabel("Sample: This is how Nebula responses will look.")
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setMinimumHeight(60)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet(f"""
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            color: {THEME['text_vibrant']};
            padding: 15px;
            font-size: 14px;
        """)
        vtext.addWidget(self.lbl_preview)
        
        sl.addLayout(vtext)
        
        # Spacer to push everything up
        sl.addStretch()

    def on_text_size_changed(self, value):
        """Handle real-time font scaling"""
        self.settings.set("text_size", value)
        self.apply_text_size(value)

    def apply_text_size(self, size):
        """Update suggestion label and preview font size"""
        style = f"color: {THEME['text_vibrant']}; font-size: {size}px; line-height: 1.4;"
        
        if hasattr(self, 'suggest_text'):
            self.suggest_text.setStyleSheet(style)
        
        if hasattr(self, 'lbl_preview'):
            # Preview box has a background, so we just update the font part of the style
            self.lbl_preview.setStyleSheet(f"""
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: {THEME['text_vibrant']};
                padding: 15px;
                font-size: {size}px;
            """)
            
        # Force height recalculation
        self.adjust_drawer_size()

    def setup_guest_benefits(self):
        """Showcase features for unauthenticated users"""
        gv = QWidget()
        gl = QVBoxLayout(gv)
        gl.setSpacing(20)
        gl.setContentsMargins(0, 10, 0, 10)
        
        msg = QLabel("Sign in to unlock professional interview guidance.")
        msg.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 13px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gl.addWidget(msg)
        
        # Benefits Grid
        grid = QHBoxLayout()
        grid.setSpacing(15)
        
        benefits = [
            ("\uE95A", "AI Copilot", "Real-time responses"),
            ("\uE8A5", "Analytics", "Track performance"),
            ("\uE72D", "Cloud Sync", "Secure & Private")
        ]
        
        for icon, title, desc in benefits:
            item = QVBoxLayout()
            item.setSpacing(5)
            
            ic = QLabel(icon)
            ic.setFont(QFont("Segoe Fluent Icons", 18))
            ic.setStyleSheet(f"color: {THEME['accent_primary']};")
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            tl = QLabel(title)
            tl.setStyleSheet("color: white; font-size: 12px; font-weight: 700;")
            tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            ds = QLabel(desc)
            ds.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 10px;")
            ds.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item.addWidget(ic)
            item.addWidget(tl)
            item.addWidget(ds)
            grid.addLayout(item)
            
        gl.addLayout(grid)
        return gv

    def create_stat_item(self, parent_layout, icon, label):
        """Helper to create small stat blocks for the account panel"""
        container = QVBoxLayout()
        container.setSpacing(2)
        
        ic = QLabel(icon)
        ic.setFont(QFont("Segoe Fluent Icons", 14))
        ic.setStyleSheet(f"color: {THEME['accent_primary']};")
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        val = QLabel("0")
        val.setStyleSheet("color: white; font-size: 16px; font-weight: 700;")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 9px; font-weight: 700;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        container.addWidget(ic)
        container.addWidget(val)
        container.addWidget(lbl)
        parent_layout.addLayout(container)
        return val

    def setup_account_panel(self):
        """View 3: User Profile & Credits (v6.2 Refined)"""
        if hasattr(self, 'account_container'): return
        self.account_container = QWidget()
        self.account_container.setStyleSheet("background: transparent; border: none;")
        
        # Main vertical layout for the container
        outer_layout = QVBoxLayout(self.account_container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea(self.account_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent; border: none;")
        al = QVBoxLayout(scroll_content)
        al.setSpacing(25) # Tightened from 35
        al.setContentsMargins(40, 30, 40, 30)
        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll)
        
        # 1. Profile Header
        header = QVBoxLayout()
        header.setSpacing(10)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Placeholder PFP
        self.lbl_pfp = QLabel("\uE77B") # No explicit parent here!
        self.lbl_pfp.setFont(QFont("Segoe Fluent Icons", 32))
        self.lbl_pfp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pfp.setStyleSheet(f"""
            color: {THEME['accent_primary']}; 
            background: rgba(255,255,255,0.05); 
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 40px; 
        """)
        self.lbl_pfp.setFixedSize(80, 80)
        
        self.lbl_user_name = QLabel("GUEST USER")
        self.lbl_user_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_user_name.setStyleSheet(f"color: white; font-size: 18px; font-weight: 700; margin-top: 5px;")
        
        self.lbl_user_email = QLabel("Sign in to sync your profile")
        self.lbl_user_email.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_user_email.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        
        header.addWidget(self.lbl_pfp, alignment=Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.lbl_user_name, alignment=Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.lbl_user_email, alignment=Qt.AlignmentFlag.AlignCenter)
        al.addLayout(header)
        
        # 2. Progress/Credits Section
        credit_box = QVBoxLayout()
        credit_box.setSpacing(8)
        self.lbl_creds_title = QLabel("CREDITS")
        self.lbl_creds_title.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px;")
        
        self.lbl_credits = QLabel("0 Credits Remaining")
        self.lbl_credits.setStyleSheet(f"color: {THEME['text_vibrant']}; font-size: 14px; font-weight: 600;")
        
        self.lbl_plan = QLabel("Plan: Free Guest")
        self.lbl_plan.setStyleSheet(f"color: {THEME['accent_primary']}; font-size: 11px; font-weight: 700; background: rgba(167, 139, 250, 0.1); border-radius: 4px; padding: 2px 8px;")
        self.lbl_plan.setFixedWidth(120)
        self.lbl_plan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_buy = QPushButton("Buy More Credits")
        self.btn_buy.setMinimumWidth(160)
        self.btn_buy.setFixedHeight(36)
        self.btn_buy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buy.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(167, 139, 250, 0.25);
                color: white;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid rgba(167, 139, 250, 0.4);
            }}
            QPushButton:hover {{ 
                background-color: rgba(167, 139, 250, 0.45); 
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        self.btn_buy.clicked.connect(lambda: os.startfile("https://www.nebulainterviewai.com/pricing"))
        
        credit_box.addWidget(self.lbl_credits, alignment=Qt.AlignmentFlag.AlignCenter)
        credit_box.addWidget(self.lbl_plan, alignment=Qt.AlignmentFlag.AlignCenter)
        credit_box.addSpacing(5)
        credit_box.addWidget(self.btn_buy, alignment=Qt.AlignmentFlag.AlignCenter)
        al.addLayout(credit_box)
        
        # Guest Benefits View (Visible when not logged in)
        self.guest_view = self.setup_guest_benefits()
        al.addWidget(self.guest_view)

        # Authenticated Analytics View (v4.1)
        self.auth_stats_view = QWidget()
        sl = QVBoxLayout(self.auth_stats_view)
        sl.setSpacing(15)
        
        stat_grid = QHBoxLayout()
        self.lbl_stats_questions = self.create_stat_item(stat_grid, "\uE8A5", "QUESTIONS")
        self.lbl_stats_duration = self.create_stat_item(stat_grid, "\uE916", "DURATION")
        sl.addLayout(stat_grid)
        
        self.lbl_sync_status = QLabel("Syncing...")
        self.lbl_sync_status.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 10px;")
        self.lbl_sync_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(self.lbl_sync_status)
        
        al.addWidget(self.auth_stats_view)
        
        # 3. Authentication Actions
        auth_box = QHBoxLayout()
        auth_box.setSpacing(15)
        
        self.btn_login = QPushButton("Sign In")
        self.setup_auth_btn(self.btn_login, primary=True)
        self.btn_login.clicked.connect(self.on_login_clicked)
        
        self.btn_logout = QPushButton("Logout")
        self.setup_auth_btn(self.btn_logout, primary=False)
        self.btn_logout.clicked.connect(self.on_logout_clicked)
        
        auth_box.addWidget(self.btn_login)
        auth_box.addWidget(self.btn_logout)
        auth_box.addStretch()
        al.addLayout(auth_box)
        
        al.addStretch()

    def on_opacity_changed(self, value):
        try:
            # Update both Pill and Overlay transparency
            # Pill uses a transparent window with a painted pill, so we update the pill's manual color
            # Overlay uses ov_glass.
            color = QColor(15, 15, 15, value)
            if hasattr(self, 'pill'):
                self.pill.manual_color = color
                self.pill.update()
                
            if hasattr(self, 'ov_glass'):
                self.ov_glass.manual_color = color
                self.ov_glass.update()
        except Exception as e:
            print(f"Opacity Error: {e}")

    def on_stealth_toggled(self, enabled):
        """Dynamically toggle invisibility for screen capture"""
        # WDA_EXCLUDEFROMCAPTURE = 17, WDA_NONE = 0
        affinity = 17 if enabled else 0
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), affinity)
            if hasattr(self, 'overlay') and self.overlay:
                ctypes.windll.user32.SetWindowDisplayAffinity(int(self.overlay.winId()), affinity)
        except Exception as e:
            print(f"Stealth Toggle Error: {e}")

    def on_groq_changed(self, text):
        """Save Groq Key to settings and AI service"""
        self.settings.set("groq_key", text)
        if hasattr(self, 'ai'):
            self.ai.groq_key = text

    def on_login_clicked(self):
        """Launch Premium PyQt6 Login flow (v3.7)"""
        try:
            from login_window import LoginWindow
            # Instantiate the new PyQt6 Login Window
            self.login_win = LoginWindow()
            # Connect the success signal to refresh the Pill UI
            self.login_win.login_success.connect(self.refresh_settings_ui)
            self.login_win.show()
        except Exception as e:
            print(f"Login Launch Error: {e}")

    def on_logout_clicked(self):
        """Clear session and refresh UI"""
        from auth_manager import AuthManager
        AuthManager.clear_saved_credentials()
        # Also clear session.json via monetization manager
        try:
            if os.path.exists("session.json"):
                os.remove("session.json")
        except: pass
        self.refresh_settings_ui()

    def connect_signals(self):
        self.ai.chunk_ready.connect(self.on_ai_chunk)
        self.ai.response_ready.connect(self.on_ai_response)
        self.audio_interviewer.transcript_ready.connect(lambda t: self.on_transcript(t, "Interviewer"))
        self.audio_me.transcript_ready.connect(lambda t: self.on_transcript(t, "Me"))
        
        # Global UI Update Timer (Session Countdown v6.5)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_session_timer)
        self.ui_timer.start(1000)
        
        # Hotkey PTT Integration
        self.hotkeys.ptt_pressed.connect(self.start_session)
        self.hotkeys.ptt_released.connect(self.stop_session)

    def update_session_timer(self):
        """Update the 15-minute countdown (Persistent Window v6.6)"""
        try:
            seconds = MonetizationManager.get_session_remaining_seconds()
            if seconds > 0:
                mins = seconds // 60
                secs = seconds % 60
                self.lbl_session_timer.setText(f"• {mins:02d}:{secs:02d}")
                if not self.lbl_session_timer.isVisible():
                    self.lbl_session_timer.setVisible(True)
            else:
                # SESSION EXPIRED
                if self.lbl_session_timer.isVisible():
                    self.lbl_session_timer.setVisible(False)
                
                # Force stop the session if it's currently live
                if self.is_live:
                    self.stop_session()
                    QMessageBox.information(self, "Session Expired", "Your 15-minute credit window has ended. Please start a new session to continue.")
        except: pass
        
    def adjust_drawer_size(self):
        """Dynamic resizing: Slim start, elastic growth (v6.1)"""
        # Starting height reduced to 100px for a "slim" Parakeet-style start
        min_h = 100 
        new_h = min_h
        
        if self.current_drawer_mode == "response":
            # Calculate text height
            text_w = 750
            font = self.suggest_text.font()
            
            from PyQt6.QtGui import QFontMetrics
            fm = QFontMetrics(font)
            # Use boundingRect with wrap to find out the exact height of the text
            rect = fm.boundingRect(0, 0, text_w, 0, Qt.TextFlag.TextWordWrap, self.suggest_text.text())
            text_h = rect.height()
            
            # Add padding: 30 top/bottom for a modern spacious look
            total_needed = text_h + 80 
            new_h = max(min_h, total_needed)
            
        elif self.current_drawer_mode == "settings":
            new_h = 540 # Expanded for v4.3 stability
        elif self.current_drawer_mode == "account":
            new_h = 600 # Increased for v6.2 stability and zero clipping
        elif self.current_drawer_mode == "context":
            new_h = 420 # Increased for Interview Strategy + Job Context (v6.0)
            
        if self.overlay:
            # If changing height while visible, animate or set
            self.overlay.resize(800, int(new_h))
            self.ov_glass.resize(800, int(new_h))


    def toggle_session(self):
        if not self.is_live:
            self.start_session()
        else:
            self.stop_session()


    def start_session(self):
        # Identity Gate: Force Login if no session
        if not AuthManager.load_saved_credentials() and not MonetizationManager.load_session():
            self.on_login_clicked()
            return
            
        # Credit / Session Gating (Rule: 1 credit = 15 minutes)
        if not MonetizationManager.is_session_active_locally():
            success, msg, new_bal = MonetizationManager.consume_credit()
            if success:
                self.credits = new_bal
                if hasattr(self, 'lbl_credits'):
                    self.lbl_credits.setText(f"{new_bal} Credits Remaining")
                MonetizationManager.set_session_active_locally(15)
                self.update_session_timer() # Instant feedback (v6.5.1)
            else:
                QMessageBox.warning(self, "No Credits", f"Session could not start: {msg}")
                self.show_account()
                return

        self.is_live = True
        self.session_questions = 0
        self.session_start_time = time.time()
        self.open_drawer("response")
        self.audio_interviewer.start()
        self.audio_me.start()
        
        # UI Feedback: Red Pulse
        self.btn_mic.setText("\uE720")
        self.btn_mic.setFont(self.f_icon)
        self.btn_mic.setStyleSheet(self.btn_mic.styleSheet().replace(THEME['accent_primary'], "#EF4444"))
        self.dot.setStyleSheet("color: #EF4444; font-size: 14px; border: none; background: transparent;")
        
        if not self.overlay.isVisible():
            self.toggle_drawer()

    def on_ai_chunk(self, chunk):
        """Ultra-low latency streaming update (v5.0)"""
        if not hasattr(self, 'current_stream_text') or not self.current_stream_text:
            self.current_stream_text = ""
            self.suggest_text.setText("")
            
            # Parakeet Logic: Auto-open drawer if we start speaking
            if not self.overlay.isVisible():
                self.open_drawer("response")
            elif self.current_drawer_mode not in ["settings", "account", "context"]:
                self.set_drawer_mode("response")
            
        self.current_stream_text += chunk
        self.suggest_text.setText(self.current_stream_text)
        self.adjust_drawer_size()

    def on_ai_response(self, text):
        """Final cleanup after streaming is done (v6.0)"""
        self.suggest_text.setText(text)
        self.current_stream_text = "" 
        
        # Trigger dynamic adjustment for new text ONLY in response mode
        if self.current_drawer_mode == "response" and self.overlay and self.overlay.isVisible():
             self.adjust_drawer_size()
             self.reposition_overlay()
             
        if not self.overlay.isVisible():
            self.open_drawer("response")
        else:
            # ONLY switch to response view if we aren't currently in specialized panels
            if self.current_drawer_mode not in ["settings", "account", "context"]:
                 self.stack_widget.setCurrentWidget(self.response_container)
                 self.current_drawer_mode = "response"

        if self.is_live:
            self.analytics.record_event("question")

    def stop_session(self):
        if not self.is_live: return
        self.is_live = False
        self.audio_interviewer.stop()
        self.audio_me.stop()
        
        duration = int(time.time() - self.session_start_time)
        self.analytics.record_session(duration, self.session_questions)
        self.sync.sync_file(self.analytics.filename)
        
        self.btn_mic.setText("\uE720")
        self.btn_mic.setFont(self.f_icon)
        self.btn_mic.setStyleSheet(self.btn_mic.styleSheet().replace("#EF4444", THEME['accent_primary']))
        self.dot.setStyleSheet(f"color: {THEME['accent_primary']}; font-size: 14px; border: none; background: transparent;")

    def on_transcript(self, text, source):
        # Only respond to Interviewer (Desktop Audio)
        # Ignore user mic for both UI display and AI generation to keep focus clear
        if source == "Interviewer":
            self.session_questions += 1
            # Parakeet Logic: Make sure we can see the transcription immediately
            if not self.overlay.isVisible():
                self.open_drawer("response")
            
            self.suggest_text.setText(f"<span style='color: {THEME['text_dim']};'>{source}:</span> {text}")
            self.ai.generate_response(text)
        else:
            print(f"Ignored Self-Speech: {text}")


    # Movements
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            self.reposition_overlay()

    def showEvent(self, event):
        apply_soft_blur(self.winId())
        super().showEvent(event)

    def closeEvent(self, event):
        """Cleanly exit all linked windows and threads"""
        try:
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.close()
            
            # Stop Services
            if hasattr(self, 'hotkeys'): self.hotkeys.stop()
            if hasattr(self, 'audio_interviewer'): self.audio_interviewer.stop()
            if hasattr(self, 'audio_me'): self.audio_me.stop()
            if hasattr(self, 'ai'): 
                # Terminate AI worker if running
                if self.ai._worker: self.ai._worker.terminate()
                
        except: pass
        
        super().closeEvent(event)
        QApplication.quit()
        import sys
        sys.exit(0)

    def _background_sync_keys(self):
        """Background AI key synchronization (v6.8.1)"""
        try:
            config = MonetizationManager.get_ai_config()
            if config:
                groq = config.get("GROQ_API_KEY")
                gemini = config.get("GEMINI_API_KEY")
                if groq: self.ai.groq_key = groq
                if gemini: self.ai.gemini_key = gemini
                print(f"DEBUG: AI Keys synced in background (Groq: {'Yes' if groq else 'No'}, Gemini: {'Yes' if gemini else 'No'})")
        except Exception as e:
            print(f"DEBUG: AI Key Sync Error: {e}")

    def sync_ai_keys(self):
        """Synchronize AI keys from the server (v6.8.1)"""
        import threading
        threading.Thread(target=self._background_sync_keys, daemon=True).start()

if __name__ == "__main__":
    # Enable High DPI (Must be before app creation)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    # Global Exception Handler
    def except_hook(cls, exception, traceback):
        sys.__excepthook__(cls, exception, traceback)
        with open("crash.log", "w") as f:
            import traceback as tb
            f.write("".join(tb.format_exception(cls, exception, traceback)))
            
    sys.excepthook = except_hook
    
    # GLOBAL BOOT CLEANUP: Kill ANY window named 'NebulaDrawerOverlay' BEFORE creating new ones
    # This ensures fresh starts without zombies blocking inputs
    for widget in QApplication.topLevelWidgets():
        if widget.objectName() == "NebulaDrawerOverlay":
            widget.hide()
            widget.deleteLater()
            
    window = FloatingPill()
    window.setObjectName("NebulaMainPill")
    window.show()
    
    # Position Top Center (Elite Alignment)
    screen = app.primaryScreen().geometry()
    window.move(int(screen.width()/2 - window.width()/2), 50)
    
    sys.exit(app.exec())
