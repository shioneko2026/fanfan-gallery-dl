"""
Settings - Updates management
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QCheckBox, QMessageBox,
                            QComboBox, QProgressDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.gallery_dl_manager import GalleryDLManager
from core.app_updater import AppUpdater
from version import APP_VERSION
from datetime import datetime
import webbrowser


class UpdateCheckerThread(QThread):
    """Background thread for checking gallery-dl updates"""
    finished = pyqtSignal(dict)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        result = self.manager.check_for_updates()
        self.finished.emit(result or {})


class AppUpdateCheckerThread(QThread):
    """Background thread for checking app updates"""
    finished = pyqtSignal(dict)

    def __init__(self, updater):
        super().__init__()
        self.updater = updater

    def run(self):
        result = self.updater.check_for_updates()
        self.finished.emit(result or {})


class AppUpdaterThread(QThread):
    """Background thread for downloading app update"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, updater):
        super().__init__()
        self.updater = updater

    def run(self):
        success = self.updater.download_update(
            progress_callback=lambda msg: self.progress.emit(msg)
        )
        self.finished.emit(success)


class UpdatesPage(QWidget):
    """Updates and preferences settings page"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        source = self.db.get_setting("gallery_dl_source", "codeberg")
        self.manager = GalleryDLManager(source=source)
        self.app_updater = AppUpdater()
        self.update_thread = None
        self.app_update_thread = None
        self.app_download_thread = None
        self._app_update_info = None
        self.changelog_url = ""
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

        group_style = """
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
        """

        # ── gallery-dl source selector ─────────────────────────────────
        source_group = QGroupBox("Download Source")
        source_group.setStyleSheet(group_style)
        source_layout = QVBoxLayout()

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Download gallery-dl from:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("Codeberg (full version — recommended)", "codeberg")
        self.source_combo.addItem("GitHub (lite version)", "github")
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_row.addWidget(self.source_combo)
        source_row.addStretch()
        source_layout.addLayout(source_row)

        source_note = QLabel(
            "The gallery-dl author moved the full version to Codeberg. "
            "The GitHub version is becoming a lite build. Codeberg is recommended."
        )
        source_note.setStyleSheet("color: #666; font-size: 12px;")
        source_note.setWordWrap(True)
        source_layout.addWidget(source_note)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # ── gallery-dl updates ─────────────────────────────────────────
        gdl_group = QGroupBox("gallery-dl Updates")
        gdl_group.setStyleSheet(group_style)
        gdl_layout = QVBoxLayout()

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

        update_btn_layout = QHBoxLayout()
        self.check_update_btn = QPushButton("Check for Updates")
        self.check_update_btn.clicked.connect(self.check_updates)

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
            QPushButton:hover { background-color: #1565c0; }
        """)
        self.update_now_btn.clicked.connect(self.update_gallery_dl)

        self.changelog_btn = QPushButton("View Changelog")
        self.changelog_btn.clicked.connect(self.view_changelog)

        update_btn_layout.addWidget(self.check_update_btn)
        update_btn_layout.addWidget(self.update_now_btn)
        update_btn_layout.addWidget(self.changelog_btn)
        update_btn_layout.addStretch()
        gdl_layout.addLayout(update_btn_layout)

        self.last_checked_label = QLabel("Last checked: Never")
        self.last_checked_label.setStyleSheet("color: #999; font-size: 12px;")
        gdl_layout.addWidget(self.last_checked_label)

        self.auto_notify_check = QCheckBox("Automatically notify me of new gallery-dl versions")
        self.auto_notify_check.setChecked(True)
        gdl_layout.addWidget(self.auto_notify_check)

        gdl_group.setLayout(gdl_layout)
        layout.addWidget(gdl_group)

        # ── Rollback ───────────────────────────────────────────────────
        rollback_group = QGroupBox("Rollback")
        rollback_group.setStyleSheet(group_style)
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

        # ── App updates ────────────────────────────────────────────────
        app_group = QGroupBox("Application Updates")
        app_group.setStyleSheet(group_style)
        app_layout = QVBoxLayout()

        app_version_row = QHBoxLayout()
        app_version_row.addWidget(QLabel("Current app version:"))
        self.app_version_label = QLabel(f"v{APP_VERSION}")
        self.app_version_label.setStyleSheet("font-weight: bold;")
        app_version_row.addWidget(self.app_version_label)
        app_version_row.addStretch()
        app_layout.addLayout(app_version_row)

        app_latest_row = QHBoxLayout()
        app_latest_row.addWidget(QLabel("Latest version:"))
        self.app_latest_label = QLabel("— (click Check for App Updates)")
        self.app_latest_label.setStyleSheet("color: #999;")
        app_latest_row.addWidget(self.app_latest_label)
        app_latest_row.addStretch()
        app_layout.addLayout(app_latest_row)

        app_btn_row = QHBoxLayout()
        self.check_app_btn = QPushButton("Check for App Updates")
        self.check_app_btn.clicked.connect(self.check_app_updates)

        self.update_app_btn = QPushButton("Update App Now")
        self.update_app_btn.setEnabled(False)
        self.update_app_btn.setStyleSheet("""
            QPushButton {
                background-color: #388e3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2e7d32; }
            QPushButton:disabled { background-color: #bdbdbd; color: #757575; }
        """)
        self.update_app_btn.clicked.connect(self.update_app_now)

        app_btn_row.addWidget(self.check_app_btn)
        app_btn_row.addWidget(self.update_app_btn)
        app_btn_row.addStretch()
        app_layout.addLayout(app_btn_row)

        if not self.app_updater.is_frozen():
            dev_note = QLabel("Running from source — update via git pull or download a release.")
            dev_note.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
            app_layout.addWidget(dev_note)
            self.update_app_btn.setEnabled(False)
            self.update_app_btn.setToolTip("Not available when running from source")

        self.auto_check_app_check = QCheckBox("Automatically check for app updates on startup")
        self.auto_check_app_check.stateChanged.connect(
            lambda: self.db.set_setting("auto_check_app_updates",
                                        "true" if self.auto_check_app_check.isChecked() else "false")
        )
        app_layout.addWidget(self.auto_check_app_check)

        self.auto_update_app_check = QCheckBox("Auto-install updates (downloads silently, prompts before restart)")
        self.auto_update_app_check.stateChanged.connect(
            lambda: self.db.set_setting("auto_update_app",
                                        "true" if self.auto_update_app_check.isChecked() else "false")
        )
        app_layout.addWidget(self.auto_update_app_check)

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        layout.addStretch()
        self.load_settings()

    # ── Settings ───────────────────────────────────────────────────────

    def load_settings(self):
        """Load current settings from database"""
        auto_notify = self.db.get_setting("auto_notify_updates", "true") == "true"
        self.auto_notify_check.setChecked(auto_notify)

        source = self.db.get_setting("gallery_dl_source", "codeberg")
        idx = self.source_combo.findData(source)
        if idx >= 0:
            self.source_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(idx)
            self.source_combo.blockSignals(False)

        auto_check_app = self.db.get_setting("auto_check_app_updates", "true") == "true"
        self.auto_check_app_check.setChecked(auto_check_app)

        auto_update = self.db.get_setting("auto_update_app", "false") == "true"
        self.auto_update_app_check.setChecked(auto_update)

        self.refresh_version_info()

    def _on_source_changed(self):
        source = self.source_combo.currentData()
        self.db.set_setting("gallery_dl_source", source)
        self.manager = GalleryDLManager(source=source)

    # ── gallery-dl update methods ──────────────────────────────────────

    def refresh_version_info(self):
        if not self.manager.ensure_binary():
            self.current_version_label.setText("Not installed")
            return
        version = self.manager.get_version()
        self.current_version_label.setText(f"v{version}" if version else "Unknown")
        if self.manager.backup_path.exists():
            self.prev_version_label.setText("Available")
            self.restore_btn.setEnabled(True)
        else:
            self.prev_version_label.setText("None")
            self.restore_btn.setEnabled(False)

    def check_updates(self):
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("Checking...")
        self.update_thread = UpdateCheckerThread(self.manager)
        self.update_thread.finished.connect(self.on_update_check_complete)
        self.update_thread.start()

    def on_update_check_complete(self, result):
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("Check for Updates")
        if not result:
            QMessageBox.warning(self, "Check Failed", "Failed to check for updates. Please try again.")
            return
        self.current_version_label.setText(f"v{result.get('current', 'Unknown')}")
        self.latest_version_label.setText(f"v{result.get('latest', 'Unknown')}")
        self.changelog_url = result.get("changelog_url", "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_checked_label.setText(f"Last checked: {timestamp}")
        if result.get("update_available"):
            self.latest_version_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            self.update_now_btn.setEnabled(True)
            QMessageBox.information(
                self, "Update Available",
                f"A new gallery-dl version is available!\n\n"
                f"Current: v{result['current']}\n"
                f"Latest: v{result['latest']}\n\n"
                f"Click 'Update Now' to install."
            )
        else:
            self.latest_version_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.update_now_btn.setEnabled(False)

    def update_gallery_dl(self):
        reply = QMessageBox.question(
            self, "Confirm Update",
            "This will update gallery-dl to the latest version.\n"
            "Your current version will be backed up for rollback.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        progress = QProgressDialog("Updating gallery-dl...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.show()
        success = self.manager.update_binary(lambda msg: progress.setLabelText(msg))
        progress.close()
        if success:
            QMessageBox.information(self, "Update Successful", "gallery-dl has been updated successfully!")
            self.refresh_version_info()
        else:
            QMessageBox.critical(self, "Update Failed", "Failed to update gallery-dl. Your previous version has been restored.")

    def rollback_version(self):
        reply = QMessageBox.question(
            self, "Confirm Rollback",
            "This will restore the previous version of gallery-dl.\n\nContinue?",
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
        if self.changelog_url:
            webbrowser.open(self.changelog_url)
        else:
            webbrowser.open(self.manager.changelog_base_url)

    # ── App update methods ─────────────────────────────────────────────

    def check_app_updates(self):
        self.check_app_btn.setEnabled(False)
        self.check_app_btn.setText("Checking...")
        self.app_update_thread = AppUpdateCheckerThread(self.app_updater)
        self.app_update_thread.finished.connect(self._on_app_check_complete)
        self.app_update_thread.start()

    def _on_app_check_complete(self, result):
        self.check_app_btn.setEnabled(True)
        self.check_app_btn.setText("Check for App Updates")
        if not result:
            QMessageBox.warning(self, "Check Failed", "Failed to check for app updates.")
            return
        latest = result.get("latest", "")
        self.app_latest_label.setText(f"v{latest}" if latest else "Unknown")
        if result.get("update_available"):
            self._app_update_info = result
            self.app_latest_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            if self.app_updater.is_frozen():
                self.update_app_btn.setEnabled(True)
            QMessageBox.information(
                self, "App Update Available",
                f"FanFan Gallery-DL v{latest} is available!\n\n"
                f"Current: v{result['current']}\n"
                f"Latest: v{latest}\n\n"
                f"Click 'Update App Now' to download and install."
            )
        else:
            self.app_latest_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.update_app_btn.setEnabled(False)
            QMessageBox.information(self, "Up to Date", f"You're already on the latest version (v{result.get('current', APP_VERSION)}).")

    def update_app_now(self):
        if not self.app_updater.is_frozen():
            return

        reply = QMessageBox.question(
            self, "Confirm Update",
            "This will download and install the latest version of FanFan Gallery-DL.\n"
            "The app will restart after the update is applied.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        progress = QProgressDialog("Downloading update...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        self.app_download_thread = AppUpdaterThread(self.app_updater)
        self.app_download_thread.progress.connect(lambda msg: progress.setLabelText(msg))
        self.app_download_thread.finished.connect(lambda ok: self._on_app_download_done(ok, progress))
        self.app_download_thread.start()

    def _on_app_download_done(self, success: bool, progress):
        progress.close()
        if not success:
            QMessageBox.critical(self, "Download Failed", "Failed to download the update. Please try again later.")
            return
        reply = QMessageBox.question(
            self, "Restart to Update",
            "Update downloaded successfully!\n\n"
            "The app needs to restart to apply the update.\n\nRestart now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.app_updater.apply_update()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_version_info()
