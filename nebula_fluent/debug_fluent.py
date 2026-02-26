import os
import sys
# Force PyQt6
os.environ["QT_API"] = "pyqt6"

try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print(f"App created: {app}")
except Exception as e:
    print(f"App creation failed: {e}")

try:
    import qfluentwidgets
    print(f"qfluentwidgets file: {qfluentwidgets.__file__}")
    
    # Try to find what backend it picked
    from qfluentwidgets.common.config import qconfig
    print(f"qconfig thinks QT_API is: {os.environ.get('QT_API')}")
    
    # Check if PyQt5 is loaded
    if 'PyQt5' in sys.modules:
        print("WARNING: PyQt5 is loaded!")
    if 'PyQt6' in sys.modules:
        print("CONFIRM: PyQt6 is loaded!")
        
    # Try to create a widget
    from qfluentwidgets import PrimaryPushButton
    btn = PrimaryPushButton("Test")
    print(f"Button created: {btn}")
    
except Exception as e:
    print(f"Fluent fail: {e}")
    import traceback
    traceback.print_exc()
