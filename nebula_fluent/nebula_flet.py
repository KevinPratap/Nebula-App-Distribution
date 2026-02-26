"""
Nebula Prompter Pro - Complete Flet Version
Full feature parity with CustomTkinter app_v3.py + Glassmorphism UI
"""
import flet as ft
import sys
import os
import ctypes
from ctypes import wintypes
import platform
import json
import threading
import time
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk
import asyncio

# Windows API constants
WDA_EXCLUDEFROMCAPTURE = 0x11
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

# Import backend from app_v3.py
from app_v3 import (
    AIProvider,
    TechnicalFixer,
    VoiceListener,
    DualVoiceListener,
    MonetizationManager,    # Added for parity
    SPEECH_AVAILABLE,
    KEYBOARD_AVAILABLE
)
import requests # Needed for some API calls if not in backend
import re # Needed for some formatting
import locale # Needed for auto-language detection

try:
    import keyboard
except:
    KEYBOARD_AVAILABLE = False

class NebulaPrompterFlet:
    def __init__(self):
        # Ledgerix-Inspired Unified Metrics
        self.br_container = 28
        self.br_element = 16
        self.br_pill = 100
        self.anim_std = ft.Animation(400, ft.AnimationCurve.EASE_OUT)
        self.anim_fast = ft.Animation(300, ft.AnimationCurve.DECELERATE)
        
        # Theme Colors (Deep Slate Navy)
        self.clr_bg = "#0B0F19"
        self.clr_glass = "#1E293B60"
        self.clr_accent = "#A78BFA"
        self.clr_neon = "#22D3EE"
        self.clr_pink = "#EC4899"
        self.clr_danger = "#F87171"
        self.clr_success = "#34D399"
        self.clr_text = "#F8FAFC"
        self.clr_dim = "#94A3B8"
        
        # Initialize AI
        self.ai = AIProvider()
        
        # State variables
        self.font_size = 16
        self.zen_opacity = 0.85
        self.zen_mode = False
        self.is_voice_active = False
        self.is_live_assist_active = False
        self.stealth_mode = False
        self.space_held = False
        self.f3_held = False
        self.is_locked = False
        
        # Voice listeners
        self.voice_listener = None
        self.dual_listener = None
        
        # Document storage
        self.loaded_documents = []
        
        # Session data
        self.live_transcript = []
        self.last_ai_update_time = 0
        self.pending_speech = {"Interviewer": "", "Me": ""}
        self.speech_timers = {"Interviewer": None, "Me": None}
        self.silence_delay = 3000
        self.current_question = ""
        
        # Subscription info
        self.sub_info = {"plan": "FREE_TRIAL", "status": "ACTIVE", "email": "user@example.com"}
        
        # Language settings
        self.languages = {
            "English (US)": "en-US",
            "English (UK)": "en-GB",
            "Spanish": "es-ES",
            "French": "fr-FR",
            "German": "de-DE",
            "Auto-Detect": "auto"
        }
        self.selected_lang = "English (US)"
        
        # Ethics Check
        self.ethics_accepted = MonetizationManager.is_ethics_accepted()
        self.session_valid = False
        
        # Ghost Window System Init
        self.ghost_hwnd = self._create_stealth_ghost()
        
    def _create_stealth_ghost(self):
        """Standard ghost window for light synchronization (Non-destructive)"""
        if platform.system() != "Windows": return 0
        try:
            hwnd = ctypes.windll.user32.CreateWindowExW(0, "Static", "NebulaGhost", 0, 0, 0, 1, 1, 0, 0, 0, 0)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0) 
            return hwnd
        except: return 0
        
        
    def get_shadow(self, intensity="LOW"):
        """Unified high-performance shadow system"""
        if intensity == "NONE": return None
        blur = 10 if intensity == "LOW" else 18
        opacity = "30" if intensity == "LOW" else "50"
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=f"#000000{opacity}",
            offset=ft.Offset(0, 4 if intensity == "LOW" else 6),
        )
        
    def main(self, page: ft.Page):
        self.page = page
        page.title = "Nebula Prompter Pro"
        page.window.width = 950
        page.window.height = 750
        page.window.always_on_top = True
        page.bgcolor = self.clr_bg
        page.padding = 0
        page.theme_mode = ft.ThemeMode.DARK
        
        # Build UI
        self.build_ui()
        
        # Setup hotkeys
        self.setup_hotkeys()
        
        # Non-blocking startup sequence
        threading.Thread(target=self.startup_sequence, daemon=True).start()
            
        # Keyboard event handler
        page.on_keyboard_event = self.on_keyboard
        
    def build_ui(self):
        """Build complete glassmorphism UI"""
        
        # 1. Profile Pill
        self.profile_btn = self.create_glass_circle(
            "👤", 56, lambda e: self.show_profile_menu()
        )
        
        # 2. Status Label (Vision Pro Style)
        self.status_lbl = ft.Text(
            "NEBULA PROMPTER",
            size=15,
            weight=ft.FontWeight.BOLD,
            color=self.clr_text,
            opacity=0,
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, 0.1),
            animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        )
        
        # Quick Action Buttons
        self.btn_interview = self.create_glass_button(
            "👁️", "Interview Mode", self.toggle_interview_mode
        )
        
        self.btn_stealth = self.create_glass_button(
            "🛡️", "Stealth", self.toggle_stealth_ui
        )
        
        self.btn_voice = self.create_glass_button(
            "🎤", "Live Assist", self.toggle_live_assist
        )
        
        self.btn_upload = self.create_glass_button(
            "📄", "Upload", self.upload_resume
        )
        
        # 3. Header (Uniform Metrics)
        self.header = ft.Container(
            content=ft.Row([
                self.profile_btn,
                ft.Container(width=16),
                self.status_lbl,
                ft.Container(expand=True),
                self.btn_interview,
                ft.Container(width=12),
                self.btn_stealth,
                ft.Container(width=12),
                self.btn_voice,
                ft.Container(width=12),
                self.btn_upload,
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=80,
            bgcolor=self.clr_glass,
            border_radius=self.br_container,
            padding=ft.Padding(24, 0, 24, 0),
            shadow=self.get_shadow("LOW"),
            animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, -0.2),
            animate_offset=ft.Animation(500, ft.AnimationCurve.DECELERATE),
        )
        
        # Text Area - Optimized for full space
        self.text_area = ft.TextField(
            value="🎯 Welcome to Nebula Prompter Pro\n\nUpload your resume to unlock AI-powered interview assistance.\n\n📌 HOTKEYS:\n• F2 (Hold): Push-to-Talk (Interviewer)\n• F3 (Hold): Push-to-Talk (You)\n• F4: Toggle Live Assist\n• Ctrl+Alt+Z: Interview Mode\n• Ctrl+S: Stealth Mode\n• +/-: Font Size\n• Ctrl+Q: Quit",
            multiline=True,
            expand=True,
            text_size=self.font_size,
            color=self.clr_text,
            bgcolor="#0F172A40",
            border_color="transparent",
            focused_border_color="transparent",
            read_only=True,
            border_radius=15,
            cursor_color=self.clr_accent,
            selection_color=self.clr_accent,
        )
        
        # Display Container - Optimized to center content and use full space
        self.display_container = ft.Container(
            content=ft.Column([self.text_area], expand=True),
            bgcolor=self.clr_glass,
            border_radius=self.br_container,
            padding=20,
            shadow=self.get_shadow("LOW"),
            expand=True,
            animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, 0.05),
            animate_offset=ft.Animation(600, ft.AnimationCurve.DECELERATE),
        )
        
        # Zen Back Button
        self.btn_back_zen = self.create_glass_circle(
            "←", 48, self.toggle_interview_mode
        )
        self.btn_back_zen.visible = False
        self.btn_back_zen.opacity = 0
        self.btn_back_zen.animate_opacity = 400
        
        # Spacer for Layout
        self.layout_spacer = ft.Container(height=24, animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT))

        # Main Layout
        self.layout = ft.Column([
            self.header,
            self.layout_spacer,
            self.display_container,
        ], expand=True, spacing=0)
        
        self.main_container = ft.Container(
            content=self.layout,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=["#0B0F19", "#171D2D"],
            ),
            padding=24,
            expand=True,
            animate=self.anim_std,
        )
        
        # Zen Back (Floating)
        self.zen_stack = ft.Stack([
            self.main_container,
            ft.Container(content=self.btn_back_zen, left=20, top=20)
        ], expand=True)
        
        self.page.add(self.zen_stack)
        
        # Trigger Entrance Animations
        self.page.run_task(self.start_entrance_animations)

    async def start_entrance_animations(self):
        """Uniform Snappy Entrance - optimized for 60fps"""
        import asyncio
        await asyncio.sleep(0.4)
        # 1. Slide main containers
        self.header.offset = ft.Offset(0, 0)
        self.display_container.offset = ft.Offset(0, 0)
        
        # 2. Fade in status
        self.status_lbl.opacity = 1
        self.status_lbl.offset = ft.Offset(0, 0)
        
        # 3. Batch show buttons
        btns = [self.profile_btn, self.btn_interview, self.btn_stealth, self.btn_voice, self.btn_upload]
        for btn in btns:
            btn.scale = 1.0
            btn.opacity = 1
            
        self.page.update() # ALL AT ONCE FOR PERFORMANCE
        
    def create_glass_button(self, icon, text, on_click):
        """Standardized glass button with Ledgerix metrics"""
        btn = ft.Container(
            content=ft.Row([
                ft.Text(icon, size=18),
                ft.Text(text, size=12, color=self.clr_text, weight=ft.FontWeight.W_600),
            ], spacing=8, tight=True),
            padding=ft.Padding(16, 10, 16, 10),
            border_radius=self.br_element,
            bgcolor=self.clr_glass,
            shadow=self.get_shadow("LOW"),
            on_click=on_click,
            scale=0.9,
            opacity=0,
            animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            on_hover=lambda e: self.on_hover(e, btn),
        )
        return btn
        
    def create_glass_circle(self, icon, size, on_click):
        """Standardized circular component with Ledgerix metrics"""
        btn = ft.Container(
            content=ft.Text(icon, size=18),
            width=size,
            height=size,
            border_radius=size//2,
            bgcolor=self.clr_glass,
            alignment=ft.Alignment(0, 0),
            shadow=self.get_shadow("LOW"),
            scale=0.9,
            opacity=0,
            animate_scale=ft.Animation(300, ft.AnimationCurve.DECELERATE),
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
            on_click=on_click,
            on_hover=lambda e: self.on_hover(e, btn),
        )
        return btn
        
    def on_hover(self, e, container):
        """Unified hover handler - Stutter-free performance"""
        is_hover = e.data == "true"
        target_scale = 1.05 if is_hover else 1.0
        
        if container.scale == target_scale:
            return
            
        container.scale = target_scale
        container.shadow = self.get_shadow("HIGH" if is_hover else "LOW")
        container.update()
        
    def setup_hotkeys(self):
        """Setup global hotkeys"""
        if KEYBOARD_AVAILABLE:
            try:
                # F2: Push-to-talk (Interviewer)
                keyboard.on_press_key('f2', lambda e: self.on_f2_press())
                keyboard.on_release_key('f2', lambda e: self.on_f2_release())
                
                # F3: Push-to-talk (Me)
                keyboard.on_press_key('f3', lambda e: self.on_f3_press())
                keyboard.on_release_key('f3', lambda e: self.on_f3_release())
                
                # F4: Toggle Live Assist
                keyboard.add_hotkey('f4', lambda: self.toggle_live_assist(None))
                
                # Ctrl+Alt+Z: Interview Mode
                keyboard.add_hotkey('ctrl+alt+z', lambda: self.toggle_interview_mode(None))
                
                # Ctrl+S: Stealth
                keyboard.add_hotkey('ctrl+s', lambda: self.toggle_stealth_ui(None))
                
                # Ctrl+Q: Quit
                keyboard.add_hotkey('ctrl+q', lambda: self.on_close())
            except Exception as e:
                print(f"Hotkey setup error: {e}")
                
    def on_keyboard(self, e: ft.KeyboardEvent):
        """Handle keyboard events"""
        if e.key == "+":
            self.change_font_size(2)
        elif e.key == "-":
            self.change_font_size(-2)
            
    def on_f2_press(self):
        """F2 pressed - start interviewer PTT"""
        if not self.space_held:
            self.space_held = True
            self.start_push_to_talk("Interviewer")
            
    def on_f2_release(self):
        """F2 released - stop interviewer PTT"""
        if self.space_held:
            self.space_held = False
            self.stop_push_to_talk()
            
    def on_f3_press(self):
        """F3 pressed - start my PTT"""
        if not self.f3_held:
            self.f3_held = True
            self.start_push_to_talk("Me")
            
    def on_f3_release(self):
        """F3 released - stop my PTT"""
        if self.f3_held:
            self.f3_held = False
            self.stop_push_to_talk()
            
    def start_push_to_talk(self, source):
        """Start PTT"""
        if self.is_locked: return
        self.is_voice_active = True
        self.set_status(f"🎙️ CAPTURING {source.upper()}...", self.clr_accent)
        use_loopback = (source == "Interviewer")
        self.voice_listener = VoiceListener(self.on_push_to_talk_result, use_loopback=use_loopback, source_label=source)
        self.voice_listener.start_listening(continuous=False)
        
    def stop_push_to_talk(self):
        """Stop PTT"""
        self.is_voice_active = False
        if self.voice_listener:
            self.voice_listener.stop_listening()
        self.set_status("🧠 THINKING...", self.clr_neon)
        
    def on_push_to_talk_result(self, text, error, label):
        """Handle PTT result"""
        if error:
            self.append_text(f"\n[{label} Error: {error}]\n")
            self.set_status("Error", self.clr_danger)
        elif text:
            fixed_text = TechnicalFixer.fix(text)
            self.show_heard_question(fixed_text)
            self.ai.answer_question(fixed_text, self.on_ai_answer)
            
    def toggle_interview_mode(self, e=None):
        """Toggle Interview Mode with standardized metrics"""
        self.zen_mode = not self.zen_mode
        self.page.window.opacity = self.zen_opacity if self.zen_mode else 1.0
        
        if self.zen_mode:
            self.header.height = 0
            self.header.opacity = 0
            self.header.offset = ft.Offset(0, -0.1)
            self.layout_spacer.height = 0
            self.main_container.padding = 16
            self.display_container.border_radius = self.br_container - 4
            self.btn_back_zen.visible = True
            self.btn_back_zen.opacity = 0.8
            self.set_status("INTERVIEW MODE", self.clr_neon)
        else:
            self.header.height = 80
            self.header.opacity = 1
            self.header.offset = ft.Offset(0, 0)
            self.layout_spacer.height = 24
            self.main_container.padding = 24
            self.display_container.border_radius = self.br_container
            self.btn_back_zen.opacity = 0
            self.btn_back_zen.visible = False
            self.set_status("NEBULA READY", self.clr_success)

        self.page.update()
        
    def toggle_stealth_ui(self, e):
        """Toggle stealth from UI"""
        self.stealth_mode = not self.stealth_mode
        self.toggle_stealth()
        
    def toggle_stealth(self):
        """Safe Stealth: Crash-Proof Protection with Ghost-Opacity Fallback"""
        if self.is_locked:
            self.stealth_mode = False
            return
            
        if platform.system() == "Windows":
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            def safe_strike(status):
                try:
                    # 1. Native Flet Taskbar Control (Always Safe)
                    try: self.page.window.skip_task_bar = status
                    except: pass
                    
                    # 2. Find the Flet UI absolute root
                    h_target = user32.FindWindowW(None, "Nebula Prompter Pro")
                    if not h_target: h_target = user32.FindWindowW("FLUTTER_RUNNER_WIN32_WINDOW", None)
                    
                    if not h_target:
                        # Fast enum search
                        found_h = []
                        def enum_nebula(h, lp):
                            if user32.IsWindowVisible(h):
                                b = ctypes.create_unicode_buffer(512)
                                user32.GetWindowTextW(h, b, 512)
                                if "Nebula" in b.value: found_h.append(h)
                            return True
                        user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_nebula), 0)
                        if found_h: h_target = found_h[0]

                    if not h_target: return False, -404
                    
                    # Target the absolute top-most container
                    root_h = user32.GetAncestor(h_target, 3) 
                    if not root_h: root_h = h_target
                    
                    if status:
                        # 3. Apply Window Styles (Non-destructive)
                        ex = user32.GetWindowLongW(root_h, -20)
                        ex |= 0x00000080 # WS_EX_TOOLWINDOW
                        ex &= ~0x00040000 # WS_EX_APPWINDOW
                        user32.SetWindowLongW(root_h, -20, ex)
                        
                        # 4. Attempt Capture Exclusion (May still return Error 5)
                        # We try it, but we DON'T crash if it fails
                        res = user32.SetWindowDisplayAffinity(root_h, 0x11)
                        err = 0 if res != 0 else kernel32.GetLastError()
                        
                        user32.SetWindowPos(root_h, 0, 0,0,0,0, 0x27)
                        return True, err # Return True because we applied styles
                    else:
                        # REVERT
                        user32.SetWindowDisplayAffinity(root_h, 0)
                        ex = user32.GetWindowLongW(root_h, -20)
                        ex &= ~0x00000080
                        ex |= 0x00040000
                        user32.SetWindowLongW(root_h, -20, ex)
                        user32.SetWindowPos(root_h, 0, 0,0,0,0, 0x27)
                        return True, 0
                except Exception as e:
                    return False, -99
            
            ok, err = safe_strike(self.stealth_mode)
            
            if self.stealth_mode:
                if err == 5:
                    # Windows blocked affinity. Using Ghost Opacity Fallback
                    self.set_status("🛡️ GHOST STEALTH ACTIVE", self.clr_pink)
                    try: self.page.window.opacity = 0.5 # Semi-transparent to bypass simple capture
                    except: pass
                else:
                    self.set_status("🛡️ STEALTH PROTECTED", self.clr_pink)
                    try: self.page.window.opacity = 0.99
                    except: pass
            else:
                self.set_status("NEBULA READY", self.clr_success)
                try: self.page.window.opacity = 1.0
                except: pass
                
            def hammer():
                for _ in range(3):
                    time.sleep(1)
                    safe_strike(self.stealth_mode)
            import threading
            threading.Thread(target=hammer, daemon=True).start()
            
        self.page.update()
        
    def toggle_live_assist(self, e):
        """Toggle Live Assist"""
        self.is_live_assist_active = not self.is_live_assist_active
        
        if self.is_live_assist_active:
            if SPEECH_AVAILABLE:
                self.start_live_assist()
                self.set_status("LIVE ASSIST ACTIVE", self.clr_success)
            else:
                self.set_status("Speech not available", self.clr_danger)
                self.is_live_assist_active = False
        else:
            self.stop_live_assist()
            self.set_status("NEBULA", self.clr_text)
        self.page.update()
        
    def start_live_assist(self):
        """Start dual voice monitoring"""
        if not self.dual_listener:
            self.dual_listener = DualVoiceListener(self.on_speech_detected, language=self.languages.get(self.selected_lang, "en-US"))
        self.dual_listener.start()
        self.append_text("\n\n=== LIVE ASSIST STARTED ===\n")
        
    def stop_live_assist(self):
        """Stop dual voice monitoring"""
        if self.dual_listener:
            self.dual_listener.stop()
        self.append_text("\n\n=== LIVE ASSIST STOPPED ===\n")
        
    def on_speech_detected(self, text, error, source):
        """Handle speech detection"""
        if error:
            self.append_text(f"\n[{source} Error: {error}]\n")
            return
            
        if text:
            fixed_text = TechnicalFixer.fix(text)
            self.append_text(f"\n{source}: {fixed_text}\n")
            
            self.live_transcript.append(f"{source}: {fixed_text}")
            
            if source == "Interviewer":
                self.handle_delayed_ai_response(source, fixed_text)
                
    def handle_delayed_ai_response(self, source, text):
        """Delayed AI response"""
        self.pending_speech[source] = self.pending_speech.get(source, "") + " " + text
        
        def trigger_ai():
            full_text = self.pending_speech[source]
            self.pending_speech[source] = ""
            transcript = "\n".join(self.live_transcript[-10:])
            self.ai.answer_live_conversation(transcript, self.on_live_ai_suggest)
            
        threading.Timer(3.0, trigger_ai).start()
        
    def on_live_ai_suggest(self, answer, error):
        """Handle live AI suggestion"""
        if error:
            self.append_text(f"\n[AI Error: {error}]\n")
        elif answer:
            self.append_text(f"\n💡 SUGGESTED RESPONSE:\n{answer}\n")
            self.set_status("SUGGESTION READY", self.clr_accent)
            
    def upload_resume(self, e):
        """Upload resume with window focus fix"""
        # Toggle AlwaysOnTop to allow file explorer to front
        self.page.window.always_on_top = False
        self.page.update()
        
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.lift()
        
        files = filedialog.askopenfilenames(
            parent=root,
            title="Select Resume/Context Files",
            filetypes=[
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            for filepath in files:
                self.load_document(filepath)
                
        root.destroy()
        
        # Restore priority
        self.page.window.always_on_top = True
        self.page.update()
        
    def load_document(self, filepath):
        """Load document"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self.loaded_documents.append({
                "filename": os.path.basename(filepath),
                "content": content
            })
            
            combined_context = "\n\n".join([
                f"=== {doc['filename']} ===\n{doc['content']}"
                for doc in self.loaded_documents
            ])
            self.ai.set_document_context(combined_context)
            
            self.append_text(f"\n✅ Loaded: {os.path.basename(filepath)}\n")
            self.set_status(f"Loaded {len(self.loaded_documents)} document(s)", self.clr_success)
            
        except Exception as e:
            self.append_text(f"\n❌ Error: {e}\n")
            
    def show_profile_menu(self):
        """Show profile menu with all options"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
            
        # Create dialog content
        menu_items = ft.Column([
            # Account Info Card
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=self.clr_accent, size=40),
                        ft.Column([
                            ft.Text(self.sub_info["email"], size=14, weight=ft.FontWeight.BOLD, color=self.clr_text),
                            ft.Container(
                                content=ft.Text(self.sub_info["plan"].replace("_", " "), size=10, weight=ft.FontWeight.BOLD, color=self.clr_bg),
                                bgcolor=self.clr_accent,
                                padding=ft.Padding(8, 2, 8, 2),
                                border_radius=10,
                            ),
                        ], spacing=2, tight=True),
                    ], spacing=15),
                ], tight=True),
                padding=ft.Padding(20, 15, 20, 15),
                bgcolor="#1E293B40",
            ),
            ft.Divider(height=1, color="#334155"),
            
            # Manual Query
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.HELP_CENTER, color=self.clr_text, size=20),
                    ft.Text("Ask Manual Query", size=14, color=self.clr_text),
                ], spacing=15),
                padding=ft.Padding(20, 12, 20, 12),
                on_click=lambda e: [close_dialog(e), self.ask_manual_question()],
                ink=True,
                border_radius=10,
            ),
            
            # Settings
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SETTINGS, color=self.clr_text, size=20),
                    ft.Text("Settings & License", size=14, color=self.clr_text),
                ], spacing=15),
                padding=ft.Padding(20, 12, 20, 12),
                on_click=lambda e: [close_dialog(e), self.show_settings_window()],
                ink=True,
                border_radius=10,
            ),
            
            # Save Session
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SAVE, color=self.clr_text, size=20),
                    ft.Text("Save Session", size=14, color=self.clr_text),
                ], spacing=15),
                padding=ft.Padding(20, 12, 20, 12),
                on_click=lambda e: [close_dialog(e), self.save_session()],
                ink=True,
                border_radius=10,
            ),
            
            # Clear Conversation
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CLEAR_ALL, color=self.clr_danger, size=20),
                    ft.Text("Clear Conversation", size=14, color=self.clr_danger),
                ], spacing=15),
                padding=ft.Padding(20, 12, 20, 12),
                on_click=lambda e: [close_dialog(e), self.clear_text()],
                ink=True,
                border_radius=10,
            ),
            
            # Controls Guide
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.KEYBOARD, color=self.clr_text, size=20),
                    ft.Text("Controls Guide", size=14, color=self.clr_text),
                ], spacing=15),
                padding=ft.Padding(20, 12, 20, 12),
                on_click=lambda e: [close_dialog(e), self.show_controls_guide()],
                ink=True,
                border_radius=10,
            ),
            
            ft.Divider(height=1, color="#334155"),
            
            # Logout
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.LOGOUT, color=self.clr_danger, size=20),
                    ft.Text("Logout & Switch", size=14, color=self.clr_danger),
                ], spacing=15),
                padding=ft.Padding(20, 15, 20, 15),
                on_click=lambda e: [close_dialog(e), self.logout_and_switch()],
                ink=True,
                border_radius=10,
            ),
        ], spacing=0, tight=True)
        
        dialog = ft.AlertDialog(
            content=ft.Container(
                content=menu_items,
                width=300,
                bgcolor="#1E293B", # Solid inner color
                border_radius=20,
                border=ft.Border.all(1, "#334155"),
            ),
            bgcolor="transparent",
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
    def ask_manual_question(self):
        """Ask manual question via dialog"""
        def submit_question(e):
            question = question_field.value
            if question:
                dialog.open = False
                self.page.update()
                self.show_heard_question(question)
                self.set_status("Generating answer...", self.clr_neon)
                self.ai.answer_question(question, self.on_ai_answer)
        
        question_field = ft.TextField(
            label="Type your question",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_color=self.clr_accent,
            text_size=14,
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text("Manual Query", color=self.clr_accent),
            content=ft.Container(
                content=question_field,
                width=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(dialog, 'open', False) or self.page.update()),
                ft.FilledButton("Ask", on_click=submit_question, bgcolor=self.clr_accent, color=self.clr_bg),
            ],
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        
    def save_session(self):
        """Save session to file with window focus fix"""
        if not self.live_transcript and not self.text_area.value.strip():
            self.set_status("No session data to save", self.clr_danger)
            return
            
        # Toggle AlwaysOnTop to allow file explorer to front
        self.page.window.always_on_top = False
        self.page.update()

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.lift()
        
        filename = filedialog.asksaveasfilename(
            parent=root,
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt")],
            initialfile=f"Interview_Session_{time.strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        if filename:
            try:
                content = "# Interview Session Recording\n"
                content += f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                content += "## Full Transcript & Suggestions\n\n"
                content += self.text_area.value
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.set_status("✅ Session Saved", self.clr_success)
            except Exception as e:
                self.set_status(f"Save error", self.clr_danger)
                
        root.destroy()
        
        # Restore priority
        self.page.window.always_on_top = True
        self.page.update()
        
    def clear_text(self):
        """Clear conversation"""
        self.text_area.value = ""
        self.live_transcript = []
        self.text_area.update()
        self.set_status("Conversation cleared", self.clr_success)
        
    def show_controls_guide(self):
        """Show controls guide"""
        shortcuts = [
            ("F2 (HOLD)", "Push-to-Talk (Interviewer)"),
            ("F3 (HOLD)", "Push-to-Talk (You)"),
            ("F4", "Toggle Live Assist"),
            ("CTRL + ALT + Z", "Toggle Interview Mode"),
            ("CTRL + S", "Toggle Stealth Mode"),
            ("CTRL + Q", "Quit Application"),
            ("+ / -", "Change Font Size"),
        ]
        
        guide_content = ft.Column([
            ft.Container(
                content=ft.Text("COMMAND CENTER", size=20, weight=ft.FontWeight.BOLD, color=self.clr_accent),
                padding=ft.Padding(0, 0, 0, 20),
            ),
        ] + [
            ft.Container(
                content=ft.Row([
                    ft.Text(key, size=12, weight=ft.FontWeight.BOLD, color=self.clr_neon, width=150),
                    ft.Text(desc, size=11, color=self.clr_text),
                ], spacing=20),
                padding=ft.Padding(0, 8, 0, 8),
            )
            for key, desc in shortcuts
        ], spacing=0)
        
        dialog = ft.AlertDialog(
            content=ft.Container(
                content=guide_content,
                width=450,
                padding=20,
                bgcolor=self.clr_glass,
                border_radius=20,
            ),
            actions=[
                ft.FilledButton("GOT IT", on_click=lambda e: setattr(dialog, 'open', False) or self.page.update(), bgcolor=self.clr_accent, color=self.clr_bg),
            ],
            bgcolor="transparent",
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        
    def show_settings_window(self):
        """Show settings with tabs matching app_v3.py"""
        def on_opacity_change(e):
            self.zen_opacity = e.control.value / 100
            self.page.window.opacity = self.zen_opacity
            # Simulate Zen UI during preview if not already in it
            self.header.visible = False
            self.header.opacity = 0
            self.main_container.padding = 16
            self.display_container.border_radius = 24
            self.page.update()

        def on_opacity_end(e):
            # Revert to current mode's reality
            if not self.zen_mode:
                self.page.window.opacity = 1.0
                self.header.visible = True
                self.header.opacity = 1
                self.main_container.padding = 24
                self.display_container.border_radius = 28
            else:
                # Keep Zen state but with new opacity
                self.page.window.opacity = self.zen_opacity
            self.page.update()

        def on_language_change(e):
            self.selected_lang = e.control.value
            self.set_status(f"Language set to {self.selected_lang}", self.clr_success)

        def redeem_license(e):
            key = license_field.value
            if not key: return
            success, msg = MonetizationManager.redeem_license(key)
            if success:
                self.set_status("LICENSE REDEEMED", self.clr_success)
                license_field.value = ""
                self.check_session() # Refresh
            else:
                self.set_status(msg[:20], self.clr_danger)
            self.page.update()

        # Language Dropdown (set on_change after init for stability)
        lang_dropdown = ft.Dropdown(
            label="Speech Language",
            value=self.selected_lang,
            options=[ft.dropdown.Option(l) for l in self.languages.keys()],
            border_color=self.clr_accent,
        )
        lang_dropdown.on_change = on_language_change

        # Define fields first for clear scoping
        license_field = ft.TextField(label="Enter Key", border_color=self.clr_accent, password=True, can_reveal_password=True)

        # Tabs Content
        general_tab = ft.Column([
            ft.Text("APPEARANCE", size=12, weight=ft.FontWeight.BOLD, color=self.clr_dim),
            ft.Text("Window Opacity (Interview Mode)", size=14, color=self.clr_text),
            ft.Slider(min=30, max=100, value=self.zen_opacity * 100, divisions=70, label="{value}%", 
                     on_change=on_opacity_change, on_change_end=on_opacity_end, active_color=self.clr_accent),
            ft.Container(height=10),
            ft.Text("LOCALIZATION", size=12, weight=ft.FontWeight.BOLD, color=self.clr_dim),
            lang_dropdown
        ], spacing=10, tight=True)

        account_tab = ft.Column([
            ft.Text("SUBSCRIPTION", size=12, weight=ft.FontWeight.BOLD, color=self.clr_dim),
            ft.Row([
                ft.Text("Status:", size=14, color=self.clr_text),
                ft.Text(self.sub_info["plan"], size=14, weight=ft.FontWeight.BOLD, color=self.clr_accent),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Text("REDEEM LICENSE", size=12, weight=ft.FontWeight.BOLD, color=self.clr_dim),
            license_field,
            ft.FilledButton("Redeem Now", on_click=redeem_license, bgcolor=self.clr_accent, color=self.clr_bg, width=400),
        ], spacing=10, tight=True)

        # Settings Content (Sleek single-view for max compatibility)
        settings_content = ft.Column([
            ft.Container(content=general_tab, bgcolor="#1E293B40", padding=20, border_radius=15),
            ft.Container(height=10),
            ft.Container(content=account_tab, bgcolor="#1E293B40", padding=20, border_radius=15),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

        dialog = ft.AlertDialog(
            title=ft.Text("NEBULA SETTINGS", color=self.clr_accent, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=settings_content,
                width=500,
                height=500,
                bgcolor="#1E293B",
                border_radius=20,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: [setattr(dialog, 'open', False), self.page.update()]),
            ],
            bgcolor="transparent",
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    async def show_ethics_dialog(self):
        """Ethics acceptance at startup (Async for thread safety)"""
        def accept(e):
            MonetizationManager.accept_ethics()
            self.ethics_accepted = True
            dialog.open = False
            self.page.update()
            threading.Thread(target=self.check_session, daemon=True).start()

        content = ft.Column([
            ft.Text("NEBULA AI ETHICS POLICY", size=18, weight=ft.FontWeight.BOLD, color=self.clr_accent),
            ft.Text("This tool is intended for personal development and interview preparation. By using Nebula, you agree to:", size=13, color=self.clr_text),
            ft.Text("• Use the AI assistance responsibly.\n• Not represent AI output as your own unfiltered thought.\n• Respect all NDA and confidentiality agreements.", size=12, color=self.clr_dim),
        ], spacing=15, tight=True)

        dialog = ft.AlertDialog(
            content=ft.Container(content=content, width=450, padding=10),
            actions=[ft.FilledButton("I AGREE & ACCEPT", on_click=accept, bgcolor=self.clr_accent, color=self.clr_bg)],
            modal=True,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def startup_sequence(self):
        """Perform startup checks without blocking UI"""
        time.sleep(2.0) # Ensure window is fully visible
        if not self.ethics_accepted:
            self.page.run_task(self.show_ethics_dialog)
        else:
            self.check_session()

    async def show_login_dialog(self):
        """Standard login dialog (Async for thread safety)"""
        def do_login(e):
            email = email_field.value
            password = pass_field.value
            if not email or not password: return
            self.set_status("CONNECTING...", self.clr_neon)
            success, msg = MonetizationManager.login(email, password)
            if success:
                dialog.open = False
                self.page.update()
                threading.Thread(target=self.check_session, daemon=True).start()
            else:
                # Provide trial bypass on error
                self.set_status(f"Error: {msg[:15]}", self.clr_danger)
                bypass_btn.visible = True
            self.page.update()

        def bypass_login(e):
            dialog.open = False
            self.session_valid = True
            self.sub_info = {"plan": "LOCAL_TRIAL", "status": "ACTIVE", "email": "guest@nebula.local"}
            self.is_locked = False
            self.set_status("NEBULA TRIAL ACTIVE", self.clr_success)
            self.page.update()

        email_field = ft.TextField(label="Email", border_color=self.clr_accent)
        pass_field = ft.TextField(label="Password", border_color=self.clr_accent, password=True, can_reveal_password=True)
        bypass_btn = ft.TextButton("ENTER AS GUEST (TRIAL)", on_click=bypass_login, icon=ft.Icons.LOCK_OPEN, visible=False)

        dialog = ft.AlertDialog(
            title=ft.Text("NEBULA SECURE LOGIN", color=self.clr_accent, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                email_field, 
                pass_field,
                ft.Text("Login failed? Ensure backend is running or use Guest Mode.", size=11, color=self.clr_dim),
                bypass_btn
            ], tight=True, spacing=15),
            actions=[
                ft.FilledButton("LOGIN", on_click=do_login, bgcolor=self.clr_accent, color=self.clr_bg),
                ft.TextButton("SKIP", on_click=bypass_login),
            ],
            modal=True,
        )
        # Always show bypass if we already know we're stuck
        if "HTTPCONNECTION" in self.status_lbl.value:
            bypass_btn.visible = True

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def check_session(self):
        """Validate session or show login"""
        try:
            success, info = MonetizationManager.validate_session()
            if success and info:
                self.session_valid = True
                self.sub_info = {
                    "plan": info.get("plan", "FREE_TRIAL"),
                    "status": info.get("status", "ACTIVE"),
                    "email": info.get("email", "user@nebula.ai")
                }
                self.is_locked = (self.sub_info["plan"] == "FREE_TRIAL")
                self.set_status("NEBULA READY", self.clr_success)
            else:
                # Check if we should allow a local bypass for testing
                self.set_status("LOGIN REQUIRED", self.clr_accent)
                self.page.run_task(self.show_login_dialog)
        except Exception as e:
            # Fallback if offline
            err_msg = str(e).upper()
            self.set_status(f"OFFLINE: {err_msg[:20]}", self.clr_dim)
            self.session_valid = False
            # Don't auto-pop if we're clearly offline, let them click profile to login or show it with an error
            self.page.run_task(self.show_login_dialog)

    def logout_and_switch(self):
        """Clear session and restart login"""
        if os.path.exists(MonetizationManager.SESSION_FILE):
            os.remove(MonetizationManager.SESSION_FILE)
        self.session_valid = False
        self.show_login_dialog()

    def reset_opacity_preview(self):
        """Reset opacity to 1.0 if not in zen or stealth mode"""
        if not self.zen_mode and not self.stealth_mode:
            self.page.window.opacity = 1.0
            self.page.update()

    def show_heard_question(self, question):
        """Display heard question"""
        self.current_question = question
        separator = "\n\n" + "━" * 40 + "\n\n"
        new_content = f"🎤 Q: \"{question}\"\n\n⏳ Generating..."
        
        current = self.text_area.value.strip()
        if current and not current.startswith("🎯"):
            self.text_area.value += separator + new_content
        else:
            self.text_area.value = new_content
        self.text_area.update()
        
    def on_ai_answer(self, answer, error):
        """Handle AI answer"""
        if error:
            self.set_status(f"Error: {error[:20]}", self.clr_danger)
            self.append_text(f"\n\n❌ Error: {error}")
        else:
            current = self.text_area.value
            if "⏳ Generating..." in current:
                current = current.replace("⏳ Generating...", "")
                self.text_area.value = current + f"\n💬 SAY THIS:\n\n{answer}"
            else:
                self.text_area.value += f"\n💬 SAY THIS:\n\n{answer}"
            self.text_area.update()
            self.set_status("✅ Answer ready!", self.clr_success)
            
            if hasattr(self, 'current_question'):
                self.ai.add_to_history(self.current_question, answer)
                
    def set_status(self, text, color=None):
        """Update status thread-safely"""
        try:
            self.status_lbl.value = text.upper()
            if color:
                self.status_lbl.color = color
            self.status_lbl.update()
        except:
            # Fallback for cross-thread updates if needed
            self.page.run_task(self._set_status_async, text, color)

    async def _set_status_async(self, text, color):
        self.status_lbl.value = text.upper()
        if color:
            self.status_lbl.color = color
        self.status_lbl.update()
        
    def append_text(self, text):
        """Append text thread-safely"""
        try:
            self.text_area.value += text
            self.text_area.update()
        except:
            self.page.run_task(self._append_text_async, text)

    async def _append_text_async(self, text):
        self.text_area.value += text
        self.text_area.update()
        
    def change_font_size(self, delta):
        """Change font size"""
        self.font_size = max(10, min(72, self.font_size + delta))
        self.text_area.text_size = self.font_size
        self.text_area.update()
        self.set_status(f"FONT SIZE: {self.font_size}PX", self.clr_dim)
        
    def on_close(self):
        """Close app"""
        self.is_voice_active = False
        if self.voice_listener:
            self.voice_listener.stop_listening()
        if self.dual_listener:
            self.dual_listener.stop()
        self.page.window.destroy()
        sys.exit(0)

def main(page: ft.Page):
    app = NebulaPrompterFlet()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)
