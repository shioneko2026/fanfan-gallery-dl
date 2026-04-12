"""
Main application window with sidebar navigation
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QStackedWidget, QScrollArea, QLabel,
                            QFrame, QTextEdit, QSplitter, QDockWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QTextCursor

from db.database import Database
from ui.dashboard import DashboardPage
from ui.downloads import DownloaderPage
from ui.download_queue_page import DownloadQueuePage
from ui.artists import ArtistsPage
from ui.crosscheck import CrossCheckPage
from ui.settings.naming import NamingPage
from ui.settings.credentials import CredentialsPage
from ui.settings.updates import UpdatesPage
from ui.settings.data import DataPage
from ui.settings.general import GeneralPage
from ui.settings.downloader import DownloaderPage as DownloaderSettingsPage
from core.logger import logger


class SidebarButton(QPushButton):
    """Custom sidebar navigation button"""

    def __init__(self, text, icon=None, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px 20px;
                border: none;
                background-color: transparent;
                color: #333;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #e3f2fd;
                color: #1976d2;
                border-left: 3px solid #1976d2;
                padding-left: 17px;
            }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("FanFan Gallery-DL")
        self.setMinimumSize(1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Right-side container (banner + content + log)
        right_container = QWidget()
        right_vbox = QVBoxLayout(right_container)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        # Update banner (hidden by default)
        self.update_banner = self._create_update_banner()
        right_vbox.addWidget(self.update_banner)

        # Content area with log panel
        content_and_log = QHBoxLayout()
        content_and_log.setContentsMargins(0, 0, 0, 0)
        content_and_log.setSpacing(0)

        # Content stack
        self.content_stack = QStackedWidget()
        content_and_log.addWidget(self.content_stack, 1)

        # Log panel (right side, collapsible)
        from ui.log_viewer import LogViewerWidget
        self.log_panel = LogViewerWidget(self)
        self.log_panel.setMinimumWidth(400)
        self.log_panel.setMaximumWidth(600)
        content_and_log.addWidget(self.log_panel, 0)

        content_widget = QWidget()
        content_widget.setLayout(content_and_log)
        right_vbox.addWidget(content_widget, 1)

        main_layout.addWidget(right_container, 1)

        # Add pages
        self.add_pages()

        # Show dashboard by default
        self.show_page(0)
        
        # Add welcome message to log
        self.log("=== FanFan Gallery-DL Log ===")
        self.log("All gallery-dl output will appear here")
        self.log("")

    def create_sidebar(self):
        """Create the collapsible sidebar"""
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border-right: 1px solid #e0e0e0;
            }
        """)
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(2)

        # App title with log toggle
        title_layout = QHBoxLayout()
        
        title = QLabel("FanFan Gallery-DL")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #1976d2;
                padding: 10px 0px 20px 20px;
            }
        """)
        
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.setContentsMargins(0, 0, 10, 0)
        
        layout.addLayout(title_layout)

        # Navigation buttons
        self.nav_buttons = []

        # Main pages
        self.btn_dashboard = SidebarButton("🏠 Dashboard")
        self.btn_downloader = SidebarButton("⬇ Downloader")
        self.btn_queue = SidebarButton("📋 Download Queue")
        self.btn_crosscheck = SidebarButton("🔍 Cross-Check")
        self.btn_creators = SidebarButton("👥 Creators")

        for btn in [self.btn_dashboard, self.btn_downloader, self.btn_queue, self.btn_crosscheck, self.btn_creators]:
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
            btn.clicked.connect(self.on_nav_clicked)

        # Settings section separator
        separator = QLabel("SETTINGS")
        separator.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 11px;
                font-weight: bold;
                padding: 20px 20px 5px 20px;
            }
        """)
        layout.addWidget(separator)

        # Settings pages
        self.btn_general = SidebarButton("General")
        self.btn_downloader_settings = SidebarButton("Downloader")
        self.btn_naming = SidebarButton("Naming")
        self.btn_credentials = SidebarButton("Credentials")
        self.btn_updates = SidebarButton("Updates")
        self.btn_data = SidebarButton("Data")

        for btn in [self.btn_general, self.btn_downloader_settings, self.btn_naming, self.btn_credentials, self.btn_updates, self.btn_data]:
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
            btn.clicked.connect(self.on_nav_clicked)

        layout.addStretch()

        return sidebar

    def setup_log_dock(self):
        """Setup log panel as a dockable widget"""
        # Create dock widget
        dock = QDockWidget("System Logs", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)

        # Create log panel content
        log_widget = self.create_log_panel()
        dock.setWidget(log_widget)

        # Add to main window
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        # Connect logger
        logger.log_message.connect(self.on_log_message)

        # Send initial log
        logger.info("FanFan Gallery-DL started")

    def create_log_panel(self):
        """Create the system log panel"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-left: 1px solid #e0e0e0;
            }
        """)
        panel.setMinimumWidth(250)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("System Logs")
        header.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        layout.addWidget(header)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.log_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        clear_btn.clicked.connect(self.log_text.clear)

        copy_btn = QPushButton("Copy All")
        copy_btn.setStyleSheet(clear_btn.styleSheet())
        copy_btn.clicked.connect(self.copy_logs)

        button_layout.addWidget(clear_btn)
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        return panel

    @pyqtSlot(str, str)
    def on_log_message(self, level: str, message: str):
        """Handle log message from logger"""
        # Color code by level
        colors = {
            "INFO": "#61afef",      # Blue
            "SUCCESS": "#98c379",   # Green
            "WARNING": "#e5c07b",   # Yellow
            "ERROR": "#e06c75",     # Red
            "DEBUG": "#c678dd"      # Purple
        }

        color = colors.get(level, "#d4d4d4")

        # Format message with HTML color
        formatted = f'<span style="color: {color};">{message}</span>'

        # Append to log
        self.log_text.append(formatted)

        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def copy_logs(self):
        """Copy all logs to clipboard"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_text.toPlainText())
        logger.success("Logs copied to clipboard")

    def add_pages(self):
        """Add all pages to the content stack"""
        # Create shared download queue manager
        from core.gallery_dl_manager import GalleryDLManager
        from core.download_queue import DownloadQueueManager

        gallery_dl_manager = GalleryDLManager()
        max_concurrent = int(self.db.get_setting("concurrent_downloads", "2"))
        self.queue_manager = DownloadQueueManager(gallery_dl_manager, self.db, max_concurrent=max_concurrent)

        # Connect queue signals to log panels
        self.queue_manager.item_output.connect(self.on_queue_raw_output)
        self.queue_manager.item_log.connect(self.on_queue_log)
        self.queue_manager.confirm_needed.connect(self.on_queue_confirm)

        # Main pages
        self.dashboard_page = DashboardPage(self.db)
        self.downloader_page = DownloaderPage(self.db, self.queue_manager)
        self.queue_page = DownloadQueuePage(self.queue_manager)
        self.crosscheck_page = CrossCheckPage(self.db, self.queue_manager)
        self.artists_page = ArtistsPage(self.db)

        # Settings pages
        self.general_page = GeneralPage(self.db)
        self.downloader_settings_page = DownloaderSettingsPage(self.db)
        self.naming_page = NamingPage(self.db)
        self.credentials_page = CredentialsPage(self.db)
        self.updates_page = UpdatesPage(self.db)
        self.data_page = DataPage(self.db)

        # Add to stack (order must match button order)
        pages = [
            self.dashboard_page,            # 0
            self.downloader_page,           # 1
            self.queue_page,                # 2
            self.crosscheck_page,           # 3
            self.artists_page,              # 4
            self.general_page,              # 5
            self.downloader_settings_page,  # 6
            self.naming_page,               # 7
            self.credentials_page,          # 8
            self.updates_page,              # 9
            self.data_page                  # 10
        ]

        for page in pages:
            self.content_stack.addWidget(page)

    def on_nav_clicked(self):
        """Handle navigation button clicks"""
        clicked_button = self.sender()
        index = self.nav_buttons.index(clicked_button)
        self.show_page(index)

    def show_page(self, index):
        """Show a specific page and update button states"""
        self.content_stack.setCurrentIndex(index)

        # Update button checked states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    @pyqtSlot(str, str)
    def on_queue_raw_output(self, item_id: str, line: str):
        """Handle raw gallery-dl output — show in Raw Output tab"""
        self.log_panel.append_raw(line)

    @pyqtSlot(str, str)
    def on_queue_log(self, item_id: str, line: str):
        """Handle parsed download messages — show in App Log tab"""
        self.log(line)

    @pyqtSlot(str, str)
    def on_queue_confirm(self, item_id: str, question: str):
        """Handle confirmation request from download thread — show dialog"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Download Confirmation",
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        self.queue_manager.confirm_response(item_id, reply == QMessageBox.StandardButton.Yes)

    def log(self, message: str, is_error: bool = False):
        """Add message to log panel"""
        self.log_panel.append_line(message, is_error)
    
    def clear_log(self):
        """Clear log panel"""
        self.log_panel.clear_log()

    # ── Update banner ──────────────────────────────────────────────────

    def _create_update_banner(self) -> QFrame:
        """Create the slim update notification banner (hidden by default)."""
        banner = QFrame()
        banner.setVisible(False)
        banner.setStyleSheet("""
            QFrame {
                background-color: #1565c0;
                border-bottom: 1px solid #0d47a1;
            }
        """)
        banner.setFixedHeight(38)

        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(12)

        self._banner_label = QLabel("")
        self._banner_label.setStyleSheet("color: white; font-size: 13px;")
        layout.addWidget(self._banner_label)
        layout.addStretch()

        self._banner_action_btn = QPushButton("Update Now")
        self._banner_action_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #1565c0;
                border: none;
                padding: 4px 14px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e3f2fd; }
        """)
        self._banner_action_btn.clicked.connect(self._on_banner_action)
        layout.addWidget(self._banner_action_btn)

        dismiss_btn = QPushButton("✕")
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.7);
                border: none;
                font-size: 14px;
                padding: 2px 6px;
            }
            QPushButton:hover { color: white; }
        """)
        dismiss_btn.clicked.connect(self.hide_update_banner)
        layout.addWidget(dismiss_btn)

        return banner

    def show_update_banner(self, version: str, download_ready: bool = False):
        """Show update notification banner."""
        if download_ready:
            self._banner_label.setText(f"FanFan Gallery-DL v{version} downloaded — restart to apply.")
            self._banner_action_btn.setText("Restart Now")
            self._banner_action_btn.setProperty("mode", "restart")
        else:
            self._banner_label.setText(f"FanFan Gallery-DL v{version} is available.")
            self._banner_action_btn.setText("Update Now")
            self._banner_action_btn.setProperty("mode", "update")
        self.update_banner.setVisible(True)

    def hide_update_banner(self):
        self.update_banner.setVisible(False)

    def _on_banner_action(self):
        mode = self._banner_action_btn.property("mode")
        if mode == "restart":
            from core.app_updater import AppUpdater
            AppUpdater().apply_update()
        else:
            # Navigate to Updates settings page
            self.show_page(9)

    # ── Startup update check ───────────────────────────────────────────

    def run_startup_update_check(self):
        """Run app update check in background after window is shown."""
        if self.db.get_setting("auto_check_app_updates", "true") != "true":
            return
        from core.app_updater import AppUpdater
        from PyQt6.QtCore import QThread
        from PyQt6.QtCore import pyqtSignal as Signal

        class _CheckThread(QThread):
            done = Signal(dict)
            def __init__(self, updater):
                super().__init__()
                self.updater = updater
            def run(self):
                result = self.updater.check_for_updates()
                self.done.emit(result or {})

        self._startup_updater = AppUpdater()
        self._startup_check_thread = _CheckThread(self._startup_updater)
        self._startup_check_thread.done.connect(self._on_startup_check_done)
        self._startup_check_thread.start()

    def _on_startup_check_done(self, result: dict):
        if not result.get("update_available"):
            return
        version = result.get("latest", "")
        auto_update = self.db.get_setting("auto_update_app", "false") == "true"
        if auto_update and self._startup_updater.is_frozen():
            # Download silently then update banner
            from PyQt6.QtCore import QThread
            from PyQt6.QtCore import pyqtSignal as Signal

            class _DownloadThread(QThread):
                done = Signal(bool)
                def __init__(self, updater):
                    super().__init__()
                    self.updater = updater
                def run(self):
                    self.done.emit(self.updater.download_update())

            self._startup_dl_thread = _DownloadThread(self._startup_updater)
            self._startup_dl_thread.done.connect(
                lambda ok: self.show_update_banner(version, download_ready=ok)
            )
            self._startup_dl_thread.start()
        else:
            self.show_update_banner(version, download_ready=False)

    # ── Lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean up before closing"""
        self.db.close()
        event.accept()
