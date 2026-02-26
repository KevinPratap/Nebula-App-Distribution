from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

class TitleBar(QWidget):
    minimize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: transparent; border-bottom: 1px solid rgba(255, 255, 255, 0.05);")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        # Icon (Placeholder)
        self.lbl_icon = QLabel("✨") 
        layout.addWidget(self.lbl_icon)
        
        # Title
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("border: none;")
        layout.addWidget(self.lbl_title)
        
        layout.addStretch()
        
        # Minimize Button
        self.btn_min = QPushButton("─")
        self.btn_min.setFixedSize(45, 30) # Wider click area
        self.btn_min.clicked.connect(self.minimize_clicked.emit)
        self.btn_min.setStyleSheet("""
            QPushButton { 
                background-color: rgba(255, 255, 255, 0.1); /* Visible */
                color: #CBD5E1; 
                border: none; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 0px; 
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 0.2); 
                color: #F8FAFC; 
            }
        """)
        layout.addWidget(self.btn_min)
        
        # Close Button
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(45, 30)
        self.btn_close.clicked.connect(self.close_clicked.emit)
        self.btn_close.setStyleSheet("""
            QPushButton { 
                background-color: rgba(255, 255, 255, 0.1); /* Visible */
                color: #CBD5E1; 
                border: none; 
                font-size: 14px; 
                border-top-right-radius: 16px; /* Match window corner */
            }
            QPushButton:hover { 
                background-color: #EF4444; 
                color: white; 
            }
        """)
        layout.addWidget(self.btn_close)

    def mousePressEvent(self, event):
        # Pass press event to the actual window for dragging
        if event.button() == Qt.LeftButton:
            # self.window() returns the top-level window (MainWindow)
            self.window().start_drag(event.globalPosition().toPoint())
