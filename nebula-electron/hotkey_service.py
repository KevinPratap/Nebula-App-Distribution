from PyQt6.QtCore import QObject, pyqtSignal as Signal, QThread
import keyboard
import time

class HotkeyService(QThread):
    """
    Listens for Global Hotkeys (Spacebar PTT).
    """
    ptt_pressed = Signal()
    ptt_released = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True
        self.space_held = False

    def run(self):
        while self.is_running:
            if keyboard.is_pressed('f2'):
                if not self.space_held:
                    self.space_held = True
                    self.ptt_pressed.emit()
            else:
                if self.space_held:
                    self.space_held = False
                    self.ptt_released.emit()
            time.sleep(0.05)

    def stop(self):
        self.is_running = False
        self.wait()
