"""
Settings - Data management and backups
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from pathlib import Path
import json
from datetime import datetime


class DataPage(QWidget):
    """Data management and export/import settings page"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Data Management")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(title)

        # Database backup
        db_group = QGroupBox("Database Backup")
        db_group.setStyleSheet("""
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

        db_layout = QVBoxLayout()

        # Database location
        location_layout = QHBoxLayout()
        location_layout.addWidget(QLabel("Database location:"))
        self.db_location_label = QLabel(str(self.db.db_path))
        self.db_location_label.setStyleSheet("color: #666; font-weight: normal; font-family: monospace;")
        self.db_location_label.setWordWrap(True)
        location_layout.addWidget(self.db_location_label, 1)
        db_layout.addLayout(location_layout)

        # Export/Import buttons
        db_btn_layout = QHBoxLayout()

        export_db_btn = QPushButton("Export Database")
        export_db_btn.setStyleSheet("""
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
        export_db_btn.clicked.connect(self.export_database)

        import_db_btn = QPushButton("Import Database")
        import_db_btn.clicked.connect(self.import_database)

        db_btn_layout.addWidget(export_db_btn)
        db_btn_layout.addWidget(import_db_btn)
        db_btn_layout.addStretch()

        db_layout.addLayout(db_btn_layout)

        # Last export info
        self.last_export_label = QLabel("Last export: Never")
        self.last_export_label.setStyleSheet("color: #999; font-size: 12px; font-weight: normal;")
        db_layout.addWidget(self.last_export_label)

        # Open export folder
        open_export_btn = QPushButton("Open Export Folder")
        open_export_btn.clicked.connect(self.open_export_folder)
        db_layout.addWidget(open_export_btn)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # Settings backup
        settings_group = QGroupBox("Settings Backup")
        settings_group.setStyleSheet(db_group.styleSheet())

        settings_layout = QVBoxLayout()

        settings_desc = QLabel("Export/import naming patterns and preferences only (credentials are NOT included)")
        settings_desc.setWordWrap(True)
        settings_desc.setStyleSheet("color: #666; font-weight: normal; font-size: 12px;")
        settings_layout.addWidget(settings_desc)

        settings_btn_layout = QHBoxLayout()

        export_settings_btn = QPushButton("Export Settings")
        export_settings_btn.setStyleSheet(export_db_btn.styleSheet())
        export_settings_btn.clicked.connect(self.export_settings)

        import_settings_btn = QPushButton("Import Settings")
        import_settings_btn.clicked.connect(self.import_settings)

        settings_btn_layout.addWidget(export_settings_btn)
        settings_btn_layout.addWidget(import_settings_btn)
        settings_btn_layout.addStretch()

        settings_layout.addLayout(settings_btn_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Warning section
        warning_group = QGroupBox("⚠ Danger Zone")
        warning_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #f44336;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #ffebee;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #f44336;
            }
        """)

        warning_layout = QVBoxLayout()

        warning_text = QLabel("⚠ These actions cannot be undone. Make sure to backup your data first.")
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet("color: #d32f2f; font-weight: normal;")
        warning_layout.addWidget(warning_text)

        clear_all_btn = QPushButton("Clear All App Data")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        clear_all_btn.clicked.connect(self.clear_all_data)

        warning_layout.addWidget(clear_all_btn)

        warning_group.setLayout(warning_layout)
        layout.addWidget(warning_group)

        layout.addStretch()

        # Load last export timestamp
        self.load_export_info()

    def load_export_info(self):
        """Load last export timestamp"""
        last_export = self.db.get_setting("last_export_timestamp", "")
        if last_export:
            self.last_export_label.setText(f"Last export: {last_export}")
        else:
            self.last_export_label.setText("Last export: Never")

    def export_database(self):
        """Export full database"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Database",
            f"gallery-dl-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db",
            "Database Files (*.db)"
        )

        if file_path:
            try:
                self.db.export_database(file_path)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.set_setting("last_export_timestamp", timestamp)
                self.load_export_info()

                QMessageBox.information(self, "Export Successful", f"Database exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export database:\n{str(e)}")

    def import_database(self):
        """Import database from file"""
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            "Importing a database will replace all current data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Database",
                "",
                "Database Files (*.db)"
            )

            if file_path:
                try:
                    self.db.import_database(file_path)
                    QMessageBox.information(self, "Import Successful", "Database imported successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Import Failed", f"Failed to import database:\n{str(e)}")

    def export_settings(self):
        """Export settings only as JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            f"gallery-dl-settings-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                settings = {
                    "folder_pattern": self.db.get_setting("folder_pattern"),
                    "file_pattern": self.db.get_setting("file_pattern"),
                    "date_format": self.db.get_setting("date_format"),
                    "conflict_action": self.db.get_setting("conflict_action"),
                    "concurrent_downloads": self.db.get_setting("concurrent_downloads"),
                    "auto_notify_updates": self.db.get_setting("auto_notify_updates"),
                    "default_save_folder": self.db.get_setting("default_save_folder")
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2)

                QMessageBox.information(self, "Export Successful", f"Settings exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export settings:\n{str(e)}")

    def import_settings(self):
        """Import settings from JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                for key, value in settings.items():
                    if value is not None:
                        self.db.set_setting(key, value)

                QMessageBox.information(self, "Import Successful", "Settings imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"Failed to import settings:\n{str(e)}")

    def open_export_folder(self):
        """Open the default export folder in file explorer"""
        import os
        export_folder = Path.home() / "Documents" / "Gallery-DL Backups"
        export_folder.mkdir(parents=True, exist_ok=True)

        # Open in Windows Explorer
        os.startfile(str(export_folder))

    def clear_all_data(self):
        """Clear all app data with confirmation"""
        reply = QMessageBox.warning(
            self,
            "Confirm Clear All Data",
            "This will permanently delete ALL app data including:\n"
            "- All creator profiles\n"
            "- Download history\n"
            "- Settings\n\n"
            "Credentials stored in Windows Credential Manager will NOT be deleted.\n\n"
            "This action CANNOT be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear all tables
                cursor = self.db.conn.cursor()
                cursor.execute("DELETE FROM failed_downloads")
                cursor.execute("DELETE FROM download_history")
                cursor.execute("DELETE FROM creator_platforms")
                cursor.execute("DELETE FROM creators")
                cursor.execute("DELETE FROM settings")
                self.db.conn.commit()

                # Reinitialize default settings
                self.db._initialize_default_settings()

                QMessageBox.information(self, "Data Cleared", "All app data has been cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Clear Failed", f"Failed to clear data:\n{str(e)}")
