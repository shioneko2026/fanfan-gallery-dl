"""
Dual-panel Log Viewer for FanFan Gallery-DL
Tab 1: App Log — parsed, color-coded summary of what's happening
Tab 2: Raw Output — verbatim gallery-dl stdout for debugging
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                            QPushButton, QLabel, QTabWidget, QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QFont


class LogTextPanel(QTextEdit):
    """Styled read-only log text panel with automatic size limiting"""

    MAX_LINES = 5000
    TRIM_LINES = 1000  # Remove this many when max is exceeded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._line_count = 0
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: none;
                padding: 8px;
            }
        """)
        font = QFont("Consolas")
        font.setPointSize(10)
        self.setFont(font)

    def append_colored(self, line: str, is_error: bool = False):
        """Append a line with color coding"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if is_error:
            self.setTextColor(Qt.GlobalColor.red)
        elif "[debug]" in line.lower():
            self.setTextColor(Qt.GlobalColor.gray)
        elif "[warning]" in line.lower():
            self.setTextColor(Qt.GlobalColor.yellow)
        elif "[error]" in line.lower():
            self.setTextColor(Qt.GlobalColor.red)
        elif line.startswith("#"):
            self.setTextColor(Qt.GlobalColor.cyan)
        elif "✓" in line or "COMPLETE" in line:
            self.setTextColor(Qt.GlobalColor.green)
        else:
            self.setTextColor(Qt.GlobalColor.white)

        cursor.insertText(line + "\n")
        self.setTextCursor(cursor)
        self._line_count += 1

        # Trim oldest lines when buffer exceeds max to prevent memory bloat
        if self._line_count > self.MAX_LINES:
            trim_cursor = QTextCursor(self.document())
            trim_cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(self.TRIM_LINES):
                trim_cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor)
            trim_cursor.removeSelectedText()
            self._line_count -= self.TRIM_LINES

        # Auto-scroll
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        self.setTextColor(Qt.GlobalColor.white)


class LogViewerWidget(QWidget):
    """Dual-tab log viewer: App Log + Raw gallery-dl Output"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget for switching between App Log and Raw Output
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #aaa;
                padding: 8px 16px;
                border: 1px solid #3c3c3c;
                border-bottom: none;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #fff;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                color: #ddd;
            }
        """)

        # Tab 1: App Log (parsed, color-coded)
        app_log_widget = QWidget()
        app_log_layout = QVBoxLayout(app_log_widget)
        app_log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_text = LogTextPanel()
        app_log_layout.addWidget(self.log_text)

        # App log buttons
        app_btn_layout = QHBoxLayout()
        app_btn_layout.setContentsMargins(4, 4, 4, 4)

        clear_app_btn = QPushButton("Clear")
        clear_app_btn.setStyleSheet("padding: 4px 12px; background: #3d3d3d; color: white; border: none; border-radius: 3px;")
        clear_app_btn.clicked.connect(self.log_text.clear)

        copy_app_btn = QPushButton("Copy")
        copy_app_btn.setStyleSheet(clear_app_btn.styleSheet())
        copy_app_btn.clicked.connect(lambda: self._copy_text(self.log_text))

        app_btn_layout.addWidget(clear_app_btn)
        app_btn_layout.addWidget(copy_app_btn)
        app_btn_layout.addStretch()
        app_log_layout.addLayout(app_btn_layout)

        self.tabs.addTab(app_log_widget, "App Log")

        # Tab 2: Raw Output (verbatim gallery-dl stdout)
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(0, 0, 0, 0)

        self.raw_text = LogTextPanel()
        raw_layout.addWidget(self.raw_text)

        # Raw output buttons
        raw_btn_layout = QHBoxLayout()
        raw_btn_layout.setContentsMargins(4, 4, 4, 4)

        clear_raw_btn = QPushButton("Clear")
        clear_raw_btn.setStyleSheet("padding: 4px 12px; background: #3d3d3d; color: white; border: none; border-radius: 3px;")
        clear_raw_btn.clicked.connect(self.raw_text.clear)

        copy_raw_btn = QPushButton("Copy")
        copy_raw_btn.setStyleSheet(clear_raw_btn.styleSheet())
        copy_raw_btn.clicked.connect(lambda: self._copy_text(self.raw_text))

        raw_btn_layout.addWidget(clear_raw_btn)
        raw_btn_layout.addWidget(copy_raw_btn)
        raw_btn_layout.addStretch()
        raw_layout.addLayout(raw_btn_layout)

        self.tabs.addTab(raw_widget, "Raw Output")

        layout.addWidget(self.tabs)

    def append_line(self, line: str, is_error: bool = False):
        """Append a line to the App Log tab"""
        self.log_text.append_colored(line, is_error)

    def append_raw(self, line: str):
        """Append a line to the Raw Output tab"""
        self.raw_text.append_colored(line)

    def clear_log(self):
        """Clear the App Log tab"""
        self.log_text.clear()

    def clear_raw(self):
        """Clear the Raw Output tab"""
        self.raw_text.clear()

    def set_log_text(self, text: str):
        """Set the entire App Log text"""
        self.log_text.setText(text)

    def _copy_text(self, text_widget):
        """Copy text from a panel to clipboard"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text_widget.toPlainText())
