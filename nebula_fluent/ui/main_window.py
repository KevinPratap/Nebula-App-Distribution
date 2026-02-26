from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QTextEdit, QSizeGrip, QFrame, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, Slot, QPoint, QRectF, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QBitmap, QLinearGradient, QColor
from core.audio_service import AudioService
from core.ai_service import AIService
from core.hotkey_service import HotkeyService
from core.settings_manager import SettingsManager # Persistence logic
from ui.title_bar import TitleBar
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Nebula Desktop")
        self.resize(1000, 700)
        
        # Frameless Window
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Dragging State
        self.drag_pos = QPoint()
        
        # Init Settings
        self.settings_manager = SettingsManager()
        
        # Services
        self.audio_interviewer = None
        self.audio_me = None
        self.ai_service = AIService()
        
        # Hotkeys
        self.hotkeys = HotkeyService()
        self.hotkeys.ptt_pressed.connect(self.on_ptt_press)
        self.hotkeys.ptt_released.connect(self.on_ptt_release)
        self.hotkeys.start()
        
        # State
        self.is_capturing = False
        
        # Central Widget Container
        # We replace the basic stylesheet container with a custom paint container
        # to support the nice background gradient behind transparency.
        self.container = QWidget()
        self.container.setObjectName("Container")
        # Note: We let QSS handle borders/radius, but we paint the bg manually for complex gradients
        self.setCentralWidget(self.container)
        
        # Main Layout
        self.layout_root = QVBoxLayout(self.container)
        self.layout_root.setContentsMargins(0, 0, 0, 0)
        self.layout_root.setSpacing(0)
        
        # 0. Title Bar
        self.title_bar = TitleBar(self)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.close_clicked.connect(self.close)
        self.layout_root.addWidget(self.title_bar)
        
        # Content Widget
        self.widget_content = QWidget()
        self.layout_content = QHBoxLayout(self.widget_content)
        self.layout_content.setContentsMargins(0, 0, 0, 0)
        self.layout_content.setSpacing(0)
        self.layout_root.addWidget(self.widget_content)
        self.setup_ui()


    def paintEvent(self, event):
        # Premium "Glass" Rendering
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Determine Opacity
        # If Interview Mode: Use Slider Value. Else: Opaque (255)
        # Note: We now control ALPHA, not Window Opacity
        if getattr(self, 'interview_active', False):
             opacity_val = self.settings_manager.get("opacity") # 20-100
             alpha = int((opacity_val / 100.0) * 255)
        else:
             alpha = 255 # Opaque
             
        # 2. Draw Main Background (Content Area)
        # We want the content area to get transparent, but maybe keep the sidebar solid?
        # Actually, simpler premium look: Whole background has the gradient with alpha.
        # BUT Sidebar has its own container that we can style as solid.
        
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 24, 24)
        
        # Gradient with Alpha
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(15, 23, 42, alpha))   # Slate 900
        gradient.setColorAt(1.0, QColor(30, 27, 75, alpha))   # Indigo 950
        
        painter.fillPath(path, gradient)
        
        # 3. Border (Subtle Glow)
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)

        
    def setup_ui(self):
        # 1. Sidebar
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(300)
        # SOLID Background for Sidebar (Glass Sidebar)
        self.sidebar.setStyleSheet("""
            QWidget#Sidebar {
                background-color: rgba(15, 23, 42, 255); /* Always Opaque */
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-top-left-radius: 24px;
                border-bottom-left-radius: 24px;
            }
        """)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(20, 30, 20, 30)
        self.sidebar_layout.setSpacing(15)
        
        # Profile Avatar
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(80, 80) # Bigger Avatar
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        self.load_avatar()
        self.sidebar_layout.addWidget(self.lbl_avatar, 0, Qt.AlignTop | Qt.AlignHCenter)
        
        # Logo (Replaces Text)
        self.lbl_logo = QLabel()
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setFixedHeight(150) # Big and Tall
        # Load Logo
        try:
            # Path: ui/../assets/logo.png
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(current_dir, "..", "assets", "logo.png")
            
            if os.path.exists(logo_path):
                pix = QPixmap(logo_path)
                # Scale nicely - Fit within 260px (300 - 40 padding)
                # Max scale: 250x140
                pix = pix.scaled(250, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_logo.setPixmap(pix)
            else:
                self.lbl_logo.setText("NEBULA")
                self.lbl_logo.setStyleSheet("font-size: 24px; font-weight: 800; color: #F8FAFC; letter-spacing: 4px; margin-top: 10px;")
        except:
             self.lbl_logo.setText("NEBULA")
             
        self.sidebar_layout.addWidget(self.lbl_logo, 0, Qt.AlignTop | Qt.AlignHCenter)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155;")
        self.sidebar_layout.addWidget(line)
        
        # Controls
        from PySide6.QtWidgets import QCheckBox, QSlider
        
        # Always on Top is now Conditional (Managed by Interview Mode)
        # self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint) # REMOVED
        
        self.chk_stealth = QCheckBox("Stealth Mode")
        self.chk_stealth.setCursor(Qt.PointingHandCursor)
        self.chk_stealth.stateChanged.connect(self.toggle_stealth_mode)
        self.sidebar_layout.addWidget(self.chk_stealth)
        
        self.chk_interview = QCheckBox("Interview Mode")
        self.chk_interview.setCursor(Qt.PointingHandCursor)
        self.chk_interview.setToolTip("Optimizes AI prompt for Interview responses")
        self.chk_interview.setChecked(True)
        # We perform connection LATER to avoid triggering animation before UI is ready
        # self.chk_interview.stateChanged.connect(self.toggle_interview_mode) 
        self.sidebar_layout.addWidget(self.chk_interview)
        
        # Resume Upload
        self.btn_upload = QPushButton("📄 Upload Resume")
        self.btn_upload.setCursor(Qt.PointingHandCursor)
        self.btn_upload.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px dashed rgba(255, 255, 255, 0.3);
                color: #A78BFA;
                border-radius: 12px;
                padding: 10px;
                font-size: 13px;
                text-align: left;
                padding-left: 20px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: rgba(167, 139, 250, 0.1);
                border-color: #A78BFA;
            }
        """)
        self.btn_upload.clicked.connect(self.upload_resume)
        self.sidebar_layout.addWidget(self.btn_upload)
        
        self.lbl_opacity = QLabel("Window Opacity")
        self.lbl_opacity.setStyleSheet("color: #94A3B8; font-size: 12px; margin-top: 10px; font-weight: 600; text-transform: uppercase;")
        self.sidebar_layout.addWidget(self.lbl_opacity)
        
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(20, 100)
        self.slider_opacity.setValue(100)
        self.slider_opacity.setCursor(Qt.PointingHandCursor)
        self.slider_opacity.valueChanged.connect(self.change_opacity)
        self.sidebar_layout.addWidget(self.slider_opacity)
        
        self.sidebar_layout.addStretch()
        
        # Bottom Actions 
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setObjectName("GhostButton")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.open_settings)
        self.sidebar_layout.addWidget(self.btn_settings)
        
        self.btn_logout = QPushButton("Logout")
        self.btn_logout.setObjectName("DestructiveButton")
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.clicked.connect(self.close) 
        self.sidebar_layout.addWidget(self.btn_logout)
        
        # 2. Main Content
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(50, 50, 50, 50) # Increased Spacing
        self.content_layout.setSpacing(25)
        
        # Transcript View
        self.lbl_heading = QLabel("Live Transcript")
        self.lbl_heading.setStyleSheet("font-size: 14px; font-weight: bold; color: #94A3B8; text-transform: uppercase;")
        self.content_layout.addWidget(self.lbl_heading)

        self.txt_transcript = QTextEdit()
        self.txt_transcript.setReadOnly(True)
        # Style set by QSS globally
        self.content_layout.addWidget(self.txt_transcript, 1) 
        
        # AI Response Area
        self.lbl_ai = QLabel("AI Suggestion")
        self.lbl_ai.setStyleSheet("font-size: 14px; font-weight: bold; color: #A78BFA; text-transform: uppercase;")
        self.content_layout.addWidget(self.lbl_ai)
        
        self.txt_ai = QTextEdit()
        self.txt_ai.setReadOnly(True)
        self.txt_ai.setMaximumHeight(200) # Bigger (User Request)
        # Style set by QSS globally
        self.content_layout.addWidget(self.txt_ai)
        
        # Controls
        self.btn_capture = QPushButton("Start Capture")
        self.btn_capture.setFixedSize(220, 55)
        self.btn_capture.setCursor(Qt.PointingHandCursor)
        self.btn_capture.clicked.connect(self.toggle_capture)
        # Style set by QSS locally for toggle state logic or globally? 
        # For toggle, we need dynamic style updates, so keep inline logic for color swaps but use QSS for base
        self.content_layout.addWidget(self.btn_capture, 0, Qt.AlignCenter)
        
        # floating "Back to Dashboard" button for Interview Mode (Initially Hidden)
        self.btn_exit_interview = QPushButton("Back to Dashboard")
        self.btn_exit_interview.setCursor(Qt.PointingHandCursor)
        self.btn_exit_interview.hide()
        self.btn_exit_interview.clicked.connect(lambda: self.toggle_interview_mode(0)) # 0 = Unchecked
        self.btn_exit_interview.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.4);
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 8px 16px;
                font-size: 13px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        self.content_layout.addWidget(self.btn_exit_interview, 0, Qt.AlignCenter)
        
        # Add a SizeGrip for resizing
        self.layout_root.addWidget(QSizeGrip(self), 0, Qt.AlignBottom | Qt.AlignRight)
        
        # Assemble
        self.layout_content.addWidget(self.sidebar)
        self.layout_content.addWidget(self.content_area)
        
        # Connect Signals LAST to avoid incomplete-init crashes
        self.chk_interview.stateChanged.connect(self.toggle_interview_mode)
        
        # Initial Animation State (if checked by default)
        if self.chk_interview.isChecked():
             # We manually trigger the animation setup *after* UI is ready
             # But QPropertyAnimation needs the window to be shown/sized? 
             # Let's just set the flag without animation for startup?
             # Or simpler: animate it now that everything exists.
             self.animate_interview_mode(True)

    def start_drag(self, global_pos):
        self.drag_pos = global_pos - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    @Slot()
    def toggle_capture(self):
        if self.is_capturing:
            # Stop
            self.stop_capture()
        else:
            # Start
            self.start_capture()
    
    def start_capture(self):
        self.is_capturing = True
        self.btn_capture.setText("Stop Capture")
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #F87171; 
                color: #0F172A; 
                font-size: 16px; 
                border-radius: 25px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FECACA;
            }
        """)
        
        # 1. Interviewer Listener (System Loopback)
        self.audio_interviewer = AudioService(use_loopback=True, source_label="Interviewer")
        self.audio_interviewer.transcript_ready.connect(self.on_transcript)
        self.audio_interviewer.error_occurred.connect(self.on_error)
        self.audio_interviewer.start()
        
        # 2. Candidate Listener (Microphone)
        self.audio_me = AudioService(use_loopback=False, source_label="Me")
        self.audio_me.transcript_ready.connect(self.on_transcript)
        self.audio_me.error_occurred.connect(self.on_error)
        self.audio_me.start()
        
        self.log("System", "Dual Capture Started (Mic + System Audio)...")

    def stop_capture(self):
        self.is_capturing = False
        self.btn_capture.setText("Start Capture")
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #A78BFA; 
                color: #0F172A; 
                font-size: 16px; 
                border-radius: 25px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C4B5FD;
            }
        """)
        
        if hasattr(self, 'audio_interviewer') and self.audio_interviewer:
            self.audio_interviewer.stop()
            self.audio_interviewer = None
            
        if hasattr(self, 'audio_me') and self.audio_me:
            self.audio_me.stop()
            self.audio_me = None
            
        self.log("System", "Capture Stopped.")

    @Slot(str, str)
    def on_transcript(self, text, source):
        self.log(source, text)
        
        # Generate AI Response for everything for now
        # In real app, only generate on "Interviewer" text
        self.log("AI", "Thinking...")
        self.ai_service.generate_response(f"The user said: '{text}'. Suggest a brief professional reply.")
        self.ai_service.response_ready.connect(self.on_ai_response)

    @Slot(str)
    def on_ai_response(self, text):
        self.try_disconnect_ai() # Prevent duplicate connections
        self.txt_ai.setText(text)
        self.log("AI", "Response Updated")
        
    def try_disconnect_ai(self):
        try: self.ai_service.response_ready.disconnect(self.on_ai_response)
        except: pass

    @Slot(str)
    def on_error(self, message):
        self.log("Error", message)

    def log(self, source, message):
        color = "#A78BFA" if source == "Me" else "#F87171" if source == "Error" else "#94A3B8"
        self.txt_transcript.append(f'<span style="color:{color}; font-weight:bold;">[{source}]</span> {message}')

    @Slot(int)
    def change_opacity(self, value):
        self.lbl_opacity.setText(f"Opacity: {value}%")
        self.settings_manager.set("opacity", value)
        self.update() # Trigger paintEvent to redraw alpha

    @Slot(int)
    def toggle_always_on_top(self, state):
        is_on = (state == 2)
        if is_on:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()
        self.settings_manager.set("always_on_top", is_on)

    @Slot(int)
    def toggle_stealth_mode(self, state):
        is_stealth = (state == 2)
        self.settings_manager.set("stealth_mode", is_stealth)
        
        if is_stealth:
            # Stealth: Low Opacity + Hide from Taskbar
            self.setWindowOpacity(0.01) # Almost invisible
            # Qt.Tool hides from Taskbar
            self.setWindowFlags(self.windowFlags() | Qt.Tool)
            self.show()
        else:
            # Restore: Normal Opacity + Show in Taskbar
            # Remove Qt.Tool flag
            self.setWindowFlags(self.windowFlags() & ~Qt.Tool)
            
            # Smart Restore
            if getattr(self, 'interview_active', False):
                # We are in Interview Mode, revert to slider opacity
                val = self.slider_opacity.value()
                self.setWindowOpacity(val / 100.0)
            else:
                # We are in Dashboard Mode, FORCE OPAQUE
                self.setWindowOpacity(1.0)
                
            self.show()

    @Slot()
    def open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        if dlg.exec():
            pass

    @Slot(int)
    def toggle_interview_mode(self, state):
        is_on = (state == 2)
        self.interview_active = is_on
        
        # 1. Update AI Service
        if hasattr(self.ai_service, 'set_interview_mode'):
            self.ai_service.set_interview_mode(is_on)
        
        # 2. Window Behavior (Per User Request)
        if is_on:
            # INTERVIEW: Always on Top
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            # Opacity handled by paintEvent
            self.show()
        else:
            # DASHBOARD: Normal
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            # Opacity handled by paintEvent (Forces 255)
            self.show()

        # 3. Trigger Visual Transition
        self.animate_interview_mode(is_on)
        self.settings_manager.set("interview_mode", is_on)
        self.update() # Redraw

    def animate_interview_mode(self, enable):
        """Standard Industry-Level Animation Suite"""
        duration = 500
        curve = QEasingCurve.InOutQuart
        
        self.interview_active = enable # Flag for paintEvent
        
        # Group animations for parallel execution
        self.anim_group = QParallelAnimationGroup()
        
        # A. Sidebar Width Animation
        # We need a wrapper or minimum width manipulation because QWidget doesn't animate generic geometry smoothly in layouts without hacks.
        # Better approach: Set min/max width on the sidebar widget itself.
        an_sidebar = QPropertyAnimation(self.sidebar, b"minimumWidth")
        an_sidebar.setDuration(duration)
        an_sidebar.setStartValue(self.sidebar.width())
        an_sidebar.setEndValue(0 if enable else 300)
        an_sidebar.setEasingCurve(curve)
        
        an_sidebar_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        an_sidebar_max.setDuration(duration)
        an_sidebar_max.setStartValue(self.sidebar.width())
        an_sidebar_max.setEndValue(0 if enable else 300)
        an_sidebar_max.setEasingCurve(curve)
        
        self.anim_group.addAnimation(an_sidebar)
        self.anim_group.addAnimation(an_sidebar_max)
        
        # B. Transcript Height/Visibility
        # We'll use Maximum Height to collapse it
        an_trans = QPropertyAnimation(self.txt_transcript, b"maximumHeight")
        an_trans.setDuration(duration)
        an_trans.setStartValue(self.txt_transcript.height())
        an_trans.setEndValue(0 if enable else 500) # Restore to flexible size logic? 500 is a safe max-min
        # Note: Layouts will expand it if max height is QWIDGETSIZE_MAX. 
        # Using 0 vs 16777215 (max) is better.
        an_trans.setEndValue(0 if enable else 16777215)
        an_trans.setEasingCurve(curve)
        self.anim_group.addAnimation(an_trans)
        
        # Start
        self.anim_group.start()
        
        # C. Update Paint State (Trigger Repaint for Transparency)
        self.update() 
        
        if enable:
            self.txt_ai.setMaximumHeight(16777215) # Allow full expansion
            self.lbl_heading.hide()
            self.lbl_ai.hide()
            self.btn_capture.hide() # Minimalist Overlay
            self.btn_exit_interview.show() # Show Escape Hatch
        else:
            self.txt_ai.setMaximumHeight(150)
            self.lbl_heading.show()
            self.lbl_ai.show()
            self.btn_capture.show()
            self.btn_exit_interview.hide()
            
            # Sync Checkbox State if triggered via Back Button
            self.chk_interview.blockSignals(True)
            self.chk_interview.setChecked(False)
            self.chk_interview.blockSignals(False)

    @Slot()
    def upload_resume(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Resume", "", "PDF Files (*.pdf);;Text Files (*.txt)")
        if file_path:
            try:
                # Simple text loader for now (PDF requires pypdf, assumption: user wants simple context)
                # If PDF, we'd need a reader. For now let's support txt or just read raw bytes if simple.
                # Actually, let's just stick to reading text content if .txt, else placeholder.
                # Just reading text for now to be safe without deps.
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                self.ai_service.set_context(content)
                self.log("System", f"Resume Loaded: {os.path.basename(file_path)}")
                self.btn_upload.setText(f"📄 {os.path.basename(file_path)}")
                self.btn_upload.setStyleSheet("border-color: #4ADE80; color: #4ADE80;")
            except Exception as e:
                self.log("Error", f"Upload Failed: {e}")

    @Slot(int)
    def toggle_stealth_mode(self, state):
        import ctypes
        from ctypes import wintypes
        
        # Windows Constant for Display Affinity
        WDA_NONE = 0x00000000
        WDA_EXCLUDEFROMCAPTURE = 0x00000011
        
        hwnd = self.winId()
        
        try:
            user32 = ctypes.windll.user32
            if state == 2: # Checked
                user32.SetWindowDisplayAffinity(int(hwnd), WDA_EXCLUDEFROMCAPTURE)
                self.log("System", "Stealth Mode ON (Hidden from Recorders)")
            else:
                user32.SetWindowDisplayAffinity(int(hwnd), WDA_NONE)
                self.log("System", "Stealth Mode OFF")
        except Exception as e:
            self.log("Error", f"Stealth Failed: {e}")

    def load_avatar(self):
        """Loads and masks the avatar image"""
        try:
            # Path to assets (Adjust based on structure)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.join(current_dir, "..", "assets") # Assuming ui/..
            if not os.path.exists(assets_dir):
                # Fallback to dev path if running from root
                assets_dir = os.path.join(os.getcwd(), "assets")
                
            img_path = os.path.join(assets_dir, "default_avatar.png")
            
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Circular Mask
                target = QPixmap(pixmap.size())
                target.fill(Qt.transparent)
                
                painter = QPainter(target)
                painter.setRenderHint(QPainter.Antialiasing, True)
                path = QPainterPath()
                path.addEllipse(0, 0, pixmap.width(), pixmap.height())
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                
                self.lbl_avatar.setPixmap(target)
        except Exception as e:
            print(f"Avatar Load Error: {e}")

    @Slot()
    def on_ptt_press(self):
        if not self.is_capturing:
            self.start_capture()

    @Slot()
    def on_ptt_release(self):
        if self.is_capturing:
            # Hold-to-Talk Logic: User requested "F2 Hold" functionality.
            # So releasing F2 should STOP capture.
            self.stop_capture() 
            
    def closeEvent(self, event):
        if hasattr(self, 'hotkeys'): self.hotkeys.stop()
        if hasattr(self, 'audio_interviewer') and self.audio_interviewer: self.audio_interviewer.stop()
        if hasattr(self, 'audio_me') and self.audio_me: self.audio_me.stop()
        super().closeEvent(event)

