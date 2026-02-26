import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QApplication
from naming_conventions import APP_NAME
from ui.styles import load_stylesheet

# Ensure high DPI scaling on Windows
if hasattr(sys, 'getwindowsversion'):
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # Load Theme
    app.setStyleSheet(load_stylesheet())
    
    # 1. Show Splash Screen
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents() # Ensure splash draws immediately
    
    # Simulate loading or wait for real loading (imports)
    import time
    time.sleep(2) # Show for at least 2 seconds
    
    # Defer import to avoid COM conflicts
    from ui.main_window import MainWindow
    
    # Launch Main Window
    window = MainWindow()
    window.show()
    
    # Close Splash
    splash.finish(window)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
