"""
Settings - Downloader (Download Location + Per-Platform Performance)
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGroupBox, QLineEdit, QSpinBox,
                            QDoubleSpinBox, QFileDialog, QMessageBox,
                            QTabWidget, QFormLayout, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


PLATFORMS = ["fanbox", "fantia", "pixiv", "patreon", "subscribestar"]
PLATFORM_LABELS = {
    "fanbox": "Fanbox",
    "fantia": "Fantia",
    "pixiv": "Pixiv",
    "patreon": "Patreon",
    "subscribestar": "SubscribeStar",
}
PLATFORM_SLEEP_DEFAULTS = {
    "fanbox": 1.0,
    "fantia": 1.0,
    "pixiv": 0.5,
    "patreon": 0.5,
    "subscribestar": 0.5,
}


class DownloaderPage(QWidget):
    """Downloader settings — save location, concurrency, per-platform rate controls"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setFont(QFont("Segoe UI", 10))
        self._platform_widgets = {}  # {platform: {rate, sleep, retries}}
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        title = QLabel("Downloader")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        desc = QLabel("Download location, queue size, and per-platform rate controls.")
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)

        group_style = """
            QGroupBox {
                font-weight: bold;
                font-family: 'Segoe UI';
                font-size: 13px;
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

        # --- Download Location ---
        loc_group = QGroupBox("Download Location")
        loc_group.setStyleSheet(group_style)
        loc_layout = QVBoxLayout()

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Default save folder:"))

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select default download location...")
        self.folder_input.setStyleSheet("padding: 8px;")

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_folder)

        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(browse_btn)
        loc_layout.addLayout(folder_layout)
        loc_group.setLayout(loc_layout)
        layout.addWidget(loc_group)

        # --- Queue ---
        queue_group = QGroupBox("Queue")
        queue_group.setStyleSheet(group_style)
        queue_layout = QHBoxLayout()

        queue_layout.addWidget(QLabel("Concurrent downloads:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setMinimum(1)
        self.concurrent_spin.setMaximum(5)
        self.concurrent_spin.setValue(2)
        self.concurrent_spin.setStyleSheet("padding: 5px;")
        queue_layout.addWidget(self.concurrent_spin)

        queue_layout.addSpacing(20)
        hint = QLabel("How many creators can download in parallel.")
        hint.setStyleSheet("color: #888; font-weight: normal;")
        queue_layout.addWidget(hint)
        queue_layout.addStretch()

        queue_group.setLayout(queue_layout)
        layout.addWidget(queue_group)

        # --- Per-Platform Performance ---
        perf_group = QGroupBox("Per-Platform Performance")
        perf_group.setStyleSheet(group_style)
        perf_layout = QVBoxLayout()

        perf_note = QLabel(
            "Control how fast gallery-dl downloads from each site. "
            "Lower sleep = faster but higher ban risk. Leave rate blank for no limit."
        )
        perf_note.setWordWrap(True)
        perf_note.setStyleSheet("color: #666; font-weight: normal; font-size: 11px; padding: 4px 0;")
        perf_layout.addWidget(perf_note)

        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabBar::tab { padding: 6px 14px; font-family: 'Segoe UI'; }
            QTabBar::tab:selected { font-weight: bold; }
        """)

        for platform in PLATFORMS:
            tab = self._build_platform_tab(platform)
            tab_widget.addTab(tab, PLATFORM_LABELS[platform])

        perf_layout.addWidget(tab_widget)
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white; border: none;
                padding: 12px 30px; border-radius: 4px;
                font-weight: bold; font-size: 14px; font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _build_platform_tab(self, platform: str) -> QWidget:
        """Build the settings tab for one platform"""
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(16, 12, 16, 12)
        form.setSpacing(10)

        # Rate limit
        rate_input = QLineEdit()
        rate_input.setPlaceholderText("e.g. 1M, 500K — leave blank for unlimited")
        rate_input.setStyleSheet("padding: 6px;")
        form.addRow("Rate limit:", rate_input)

        # Sleep between requests
        sleep_spin = QDoubleSpinBox()
        sleep_spin.setMinimum(0.0)
        sleep_spin.setMaximum(30.0)
        sleep_spin.setSingleStep(0.5)
        sleep_spin.setDecimals(1)
        sleep_spin.setValue(PLATFORM_SLEEP_DEFAULTS.get(platform, 0.5))
        sleep_spin.setSuffix(" s")
        sleep_spin.setStyleSheet("padding: 5px;")
        sleep_spin.setFixedWidth(100)
        sleep_layout = QHBoxLayout()
        sleep_layout.addWidget(sleep_spin)
        sleep_layout.addWidget(QLabel("Sleep between requests"))
        sleep_layout.addStretch()
        form.addRow("Sleep:", sleep_layout)

        # Retries
        retries_spin = QSpinBox()
        retries_spin.setMinimum(1)
        retries_spin.setMaximum(10)
        retries_spin.setValue(4)
        retries_spin.setStyleSheet("padding: 5px;")
        retries_spin.setFixedWidth(80)
        form.addRow("Retries:", retries_spin)

        self._platform_widgets[platform] = {
            "rate": rate_input,
            "sleep": sleep_spin,
            "retries": retries_spin,
        }
        return widget

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Default Download Folder", self.folder_input.text() or ""
        )
        if folder:
            self.folder_input.setText(folder)

    def load_settings(self):
        self.folder_input.setText(self.db.get_setting("default_save_folder", ""))
        self.concurrent_spin.setValue(int(self.db.get_setting("concurrent_downloads", "2")))

        for platform in PLATFORMS:
            w = self._platform_widgets[platform]
            w["rate"].setText(self.db.get_setting(f"{platform}_rate_limit", ""))
            try:
                w["sleep"].setValue(float(self.db.get_setting(
                    f"{platform}_sleep_request",
                    str(PLATFORM_SLEEP_DEFAULTS.get(platform, 0.5))
                )))
            except (ValueError, TypeError):
                w["sleep"].setValue(PLATFORM_SLEEP_DEFAULTS.get(platform, 0.5))
            try:
                w["retries"].setValue(int(self.db.get_setting(f"{platform}_retries", "4")))
            except (ValueError, TypeError):
                w["retries"].setValue(4)

    def save_settings(self):
        self.db.set_setting("default_save_folder", self.folder_input.text())
        concurrent = self.concurrent_spin.value()
        self.db.set_setting("concurrent_downloads", str(concurrent))

        # Propagate concurrent downloads to active queue manager
        main_window = self.window()
        if hasattr(main_window, 'queue_manager'):
            main_window.queue_manager.max_concurrent = concurrent

        for platform in PLATFORMS:
            w = self._platform_widgets[platform]
            self.db.set_setting(f"{platform}_rate_limit", w["rate"].text().strip())
            self.db.set_setting(f"{platform}_sleep_request", str(w["sleep"].value()))
            self.db.set_setting(f"{platform}_retries", str(w["retries"].value()))

        QMessageBox.information(self, "Saved", "Settings saved successfully.")
