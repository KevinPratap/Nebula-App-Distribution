import os
import sys

# 0. SETUP ENVIRONMENT
os.environ["QT_API"] = "pyqt6"

# Hack: PRevent PyQt5 from being imported
sys.modules["PyQt5"] = None

from PyQt6.QtWidgets import QApplication, QWidget
print("--- PyQt6 Loaded ---")

app = QApplication(sys.argv)
print(f"--- App Created: {app} ---")

try:
    import qfluentwidgets
    print("--- qfluentwidgets imported ---")
    
    from qfluentwidgets import PrimaryPushButton
    btn = PrimaryPushButton("Test")
    print(f"--- Button Created: {btn} ---")
    
except Exception as e:
    print(f"--- Error: {e} ---")
    import traceback
    traceback.print_exc()
