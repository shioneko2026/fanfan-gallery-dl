"""
Settings - Updates management
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QCheckBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.gallery_dl_manager import GalleryDLManager
from datetime import datetime
import webbrowser


class UpdateCheckerThread(QThread):
    """Background thread for checking updates"""
    finished = pyqtSignal(dict)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        result = self.manager.check_for_updates()
        self.finished.emit(result or {})


class UpdatesPage(QWidget):
    """Updates and preferences settings page"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.manager = GalleryDLManager()
        self.update_thread = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Updates & Preferences")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(title)

        # gallery-dl updates
        gdl_group = QGroupBox("gallery-dl Updates")
        gdl_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        gdl_layout = QVBoxLayout()

        # Version info
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Current version:"))
        self.current_version_label = QLabel("—")
        self.current_version_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(self.current_version_label)
        version_layout.addStretch()
        gdl_layout.addLayout(version_layout)

        latest_layout = QHBoxLayout()
        latest_layout.addWidget(QLabel("Latest version:"))
        self.latest_version_label = QLabel("— (click Check for Updates)")
        self.latest_version_label.setStyleSheet("color: #999; font-weight: normal;")
        latest_layout.addWidget(self.latest_version_label)
        latest_layout.addStretch()
        gdl_layout.addLayout(latest_layout)

        # Update buttons
        update_btn_layout = QHBoxLayout()

        self.update_now_btn = QPushButton("Update Now")
        self.update_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        self.update_now_btn.clicked.connect(self.update_gallery_dl)

        self.changelog_btn = QPushButton("View Changelog")
        self.changelog_btn.clicked.connect(self.view_changelog)
        self.changelog_url = ""

        self.check_update_btn = QPushButton("Check for Updates")
        self.check_update_btn.clicked.connect(self.check_updates)

        update_btn_layout.addWidget(self.check_update_btn)
        update_btn_layout.addWidget(self.update_now_btn)
        update_btn_layout.addWidget(self.changelog_btn)
        update_btn_layout.addStretch()

        gdl_layout.addLayout(update_btn_layout)

        # Last checked
        self.last_checked_label = QLabel("Last checked: Never")
        self.last_checked_label.setStyleSheet("color: #999; font-size: 12px;")
        gdl_layout.addWidget(self.last_checked_label)

        # Auto-notify checkbox
        self.auto_notify_check = QCheckBox("Automatically notify me of new versions")
        self.auto_notify_check.setChecked(True)
        gdl_layout.addWidget(self.auto_notify_check)

        gdl_group.setLayout(gdl_layout)
        layout.addWidget(gdl_group)

        # Rollback section
        rollback_group = QGroupBox("Rollback")
        rollback_group.setStyleSheet(gdl_group.styleSheet())

        rollback_layout = QVBoxLayout()

        rollback_info = QHBoxLayout()
        rollback_info.addWidget(QLabel("Previous version stored:"))
        self.prev_version_label = QLabel("None")
        self.prev_version_label.setStyleSheet("font-weight: bold;")
        rollback_info.addWidget(self.prev_version_label)
        rollback_info.addStretch()
        rollback_layout.addLayout(rollback_info)

        self.restore_btn = QPushButton("Restore Previous Version")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.rollback_version)
        rollback_layout.addWidget(self.restore_btn)

        rollback_group.setLayout(rollback_layout)
        layout.addWidget(rollback_group)

        # App updates
        app_group = QGroupBox("Application Updates")
        app_group.setStyleSheet(gdl_group.styleSheet())

        app_layout = QVBoxLayout()

        app_version_layout = QHBoxLayout()
        app_version_layout.addWidget(QLabel("Current app version:"))
        app_version = QLabel("v1.0.0")
        app_version.setStyleSheet("font-weight: bold;")
        app_version_layout.addWidget(app_version)
        app_version_layout.addStretch()
        app_layout.addLayout(app_version_layout)

        check_app_btn = QPushButton("Check for App Updates")
        app_layout.addWidget(check_app_btn)

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        layout.addStretch()

        # Load current settings
        self.load_settings()

    def load_settings(self):
        """Load current settings from database"""
        auto_notify = self.db.get_setting("auto_notify_updates", "true") == "true"
        self.auto_notify_check.setChecked(auto_notify)

        # Load gallery-dl version
        self.refresh_version_info()

    def refresh_version_info(self):
        """Refresh gallery-dl version information"""
        # Ensure binary exists
        if not self.manager.ensure_binary():
            self.current_version_label.setText("Not installed")
            return

        # Get current version
        version = self.manager.get_version()
        if version:
            self.current_version_label.setText(f"v{version}")
        else:
            self.current_version_label.setText("Unknown")

        # Check if backup exists
        if self.manager.backup_path.exists():
            self.prev_version_label.setText("Available")
            self.restore_btn.setEnabled(True)
        else:
            self.prev_version_label.setText("None")
            self.restore_btn.setEnabled(False)

    def check_updates(self):
        """Check for gallery-dl updates"""
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("Checking...")

        # Run check in background thread
        self.update_thread = UpdateCheckerThread(self.manager)
        self.update_thread.finished.connect(self.on_update_check_complete)
        self.update_thread.start()

    def on_update_check_complete(self, result):
        """Handle update check completion"""
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("Check for Updates")

        if not result:
            QMessageBox.warning(self, "Check Failed", "Failed to check for updates. Please try again.")
            return

        # Update UI
        self.current_version_label.setText(f"v{result.get('current', 'Unknown')}")
        self.latest_version_label.setText(f"v{result.get('latest', 'Unknown')}")
        self.changelog_url = result.get('changelog_url', '')

        # Update timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_checked_label.setText(f"Last checked: {timestamp}")

        # Show notification if update available
        if result.get('update_available'):
            self.latest_version_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            self.update_now_btn.setEnabled(True)

            QMessageBox.information(
                self,
                "Update Available",
                f"A new version is available!\n\n"
                f"Current: v{result['current']}\n"
                f"Latest: v{result['latest']}\n\n"
                f"Click 'Update Now' to install."
            )
        else:
            self.latest_version_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.update_now_btn.setEnabled(False)

    def update_gallery_dl(self):
        """Update gallery-dl to latest version"""
        reply = QMessageBox.question(
            self,
            "Confirm Update",
            "This will update gallery-dl to the latest version.\n"
            "Your current version will be backed up for rollback.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Show progress dialog
        from PyQt6.QtWidgets import QProgressDialog
        progress = QProgressDialog("Updating gallery-dl...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        def progress_callback(message):
            progress.setLabelText(message)

        # Perform update
        success = self.manager.update_binary(progress_callback)
        progress.close()

        if success:
            QMessageBox.information(self, "Update Successful", "gallery-dl has been updated successfully!")
            self.refresh_version_info()
        else:
            QMessageBox.critical(self, "Update Failed", "Failed to update gallery-dl. Your previous version has been restored.")

    def rollback_version(self):
        """Rollback to previous gallery-dl version"""
        reply = QMessageBox.question(
            self,
            "Confirm Rollback",
            "This will restore the previous version of gallery-dl.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.manager.rollback():
            QMessageBox.information(self, "Rollback Successful", "Previous version has been restored!")
            self.refresh_version_info()
        else:
            QMessageBox.critical(self, "Rollback Failed", "Failed to rollback. No backup found.")

    def view_changelog(self):
        """Open changelog URL in browser"""
        if self.changelog_url:
            webbrowser.open(self.changelog_url)
        else:
            webbrowser.open("https://github.com/mikf/gallery-dl/releases")

    def showEvent(self, event):
        """Refresh version info when page is shown"""
        super().showEvent(event)
        self.refresh_version_info()
