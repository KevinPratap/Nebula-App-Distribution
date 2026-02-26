import sys
import os
os.environ["QT_API"] = "pyqt6"

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Delayed import
    from qfluentwidgets import FluentWindow
    
    w = FluentWindow()
    w.show()
    sys.exit(app.exec())
