"""
Dashboard page - shows creator stats, cookie health, and recent scans
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QFrame, QScrollArea, QPushButton, QGroupBox,
                            QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from core.credential_manager_simple import CredentialManager
from datetime import datetime


class StatCard(QFrame):
    """Card widget for displaying a statistic"""

    def __init__(self, title, value, color="#1976d2", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        self.setMinimumWidth(160)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 28px;
                font-weight: bold;
                color: {color};
                font-family: 'Segoe UI';
            }}
        """)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
                font-family: 'Segoe UI';
            }
        """)

        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def update_value(self, value):
        self.value_label.setText(str(value))


class CookieStatusCard(QFrame):
    """Card showing cookie health per platform"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("Cookie Status")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; font-family: 'Segoe UI';")
        layout.addWidget(title)

        self.status_layout = QVBoxLayout()
        self.status_layout.setSpacing(4)
        layout.addLayout(self.status_layout)

    def update_status(self, platform_statuses):
        """Update with dict of {platform_name: has_cookies}"""
        # Clear existing
        while self.status_layout.count():
            item = self.status_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for platform_name, has_cookies in platform_statuses.items():
            row = QHBoxLayout()
            dot = "●"
            if has_cookies:
                color = "#4caf50"
                status_text = "Ready"
            else:
                color = "#f44336"
                status_text = "No cookies"

            name_label = QLabel(platform_name)
            name_label.setStyleSheet("font-size: 13px; font-family: 'Segoe UI'; color: #333;")

            status_label = QLabel(f"{dot} {status_text}")
            status_label.setStyleSheet(f"font-size: 12px; font-family: 'Segoe UI'; color: {color}; font-weight: bold;")

            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(status_label)

            container = QWidget()
            container.setLayout(row)
            self.status_layout.addWidget(container)


class DashboardPage(QWidget):
    """Dashboard showing overview and recent activity"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.cred_manager = CredentialManager()
        self.setFont(QFont("Segoe UI", 10))
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Page title
        title = QLabel("Dashboard")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(title)

        # --- Top row: stat cards + cookie status ---
        top_row = QHBoxLayout()
        top_row.setSpacing(15)

        # Creator count card
        self.creators_card = StatCard("Creators Tracked", "0")
        top_row.addWidget(self.creators_card)

        # Platform breakdown card
        self.platform_card = StatCard("Platforms", "0", color="#ff9800")
        top_row.addWidget(self.platform_card)

        # Cookie status card
        self.cookie_card = CookieStatusCard()
        top_row.addWidget(self.cookie_card)

        top_row.addStretch()
        layout.addLayout(top_row)

        # --- Quick Actions ---
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)

        new_download_btn = QPushButton("New Download")
        new_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #1565c0; }
        """)
        new_download_btn.clicked.connect(self.go_to_downloads)

        manage_creators_btn = QPushButton("Manage Creators")
        manage_creators_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #f57c00; }
        """)
        manage_creators_btn.clicked.connect(self.go_to_creators)

        actions_layout.addWidget(new_download_btn)
        actions_layout.addWidget(manage_creators_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        # --- Last Scanned ---
        scan_group = QGroupBox("Recent Scans")
        scan_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI';
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

        scan_layout = QVBoxLayout()
        scan_group.setLayout(scan_layout)

        self.scan_container = QWidget()
        self.scan_layout = QVBoxLayout(self.scan_container)
        self.scan_layout.setSpacing(6)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.scan_container)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        scan_layout.addWidget(scroll_area)

        layout.addWidget(scan_group, 1)

        # Load data
        self.refresh_all()

    def refresh_all(self):
        """Refresh all dashboard data"""
        self.refresh_creator_stats()
        self.refresh_cookie_status()
        self.refresh_recent_scans()

    def refresh_creator_stats(self):
        """Refresh creator count and platform breakdown"""
        try:
            creators = list(self.db.get_all_creators())
            self.creators_card.update_value(str(len(creators)))

            # Count unique platforms
            platform_set = set()
            platform_counts = {}
            for a in creators:
                a_dict = dict(a)
                platforms_str = a_dict.get('platforms', '') or ''
                for p in platforms_str.split(','):
                    p = p.strip()
                    if p:
                        platform_set.add(p)
                        platform_counts[p] = platform_counts.get(p, 0) + 1

            # Build breakdown text
            if platform_counts:
                breakdown = ", ".join(f"{count} {name.title()}" for name, count in sorted(platform_counts.items()))
                self.platform_card.update_value(str(len(platform_set)))
                self.platform_card.title_label.setText(f"Platforms ({breakdown})")
            else:
                self.platform_card.update_value("0")
                self.platform_card.title_label.setText("Platforms")

        except Exception:
            self.creators_card.update_value("0")
            self.platform_card.update_value("0")

    def refresh_cookie_status(self):
        """Refresh cookie health indicators"""
        platforms = {
            "Fanbox": "fanbox",
            "Fantia": "fantia",
            "Patreon": "patreon",
            "SubscribeStar": "subscribestar",
        }

        statuses = {}
        for display_name, platform_id in platforms.items():
            statuses[display_name] = self.cred_manager.has_cookies(platform_id)

        self.cookie_card.update_status(statuses)

    def refresh_recent_scans(self):
        """Refresh recent scan history"""
        # Clear existing
        while self.scan_layout.count():
            item = self.scan_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            scans = self.db.get_recent_scans(limit=10)
        except Exception:
            scans = []

        if not scans:
            empty = QLabel("No scans yet. Go to Downloader to scan a creator.")
            empty.setStyleSheet("color: #999; padding: 20px; font-family: 'Segoe UI';")
            self.scan_layout.addWidget(empty)
            self.scan_layout.addStretch()
            return

        for scan in scans:
            item = self._create_scan_item(scan)
            self.scan_layout.addWidget(item)

        self.scan_layout.addStretch()

    def _create_scan_item(self, scan):
        """Create a scan history row"""
        item = QFrame()
        item.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 4px;
                padding: 8px 12px;
                border: 1px solid #eee;
            }
        """)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 6, 8, 6)

        # Creator name + platform
        name_label = QLabel(f"{scan['creator_name']}")
        name_label.setStyleSheet("font-weight: bold; font-size: 13px; font-family: 'Segoe UI'; color: #333;")

        platform_label = QLabel(f"[{scan['platform'].title()}]")
        platform_label.setStyleSheet("font-size: 12px; font-family: 'Segoe UI'; color: #1976d2;")

        # Stats
        stats_label = QLabel(f"{scan['post_count']} posts, {scan['file_count']} files")
        stats_label.setStyleSheet("font-size: 12px; font-family: 'Segoe UI'; color: #666;")

        # Date
        try:
            dt = datetime.fromisoformat(scan['scanned_at'])
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = scan.get('scanned_at', '')
        date_label = QLabel(date_str)
        date_label.setStyleSheet("font-size: 11px; font-family: 'Segoe UI'; color: #999;")

        layout.addWidget(name_label)
        layout.addWidget(platform_label)
        layout.addSpacing(10)
        layout.addWidget(stats_label)
        layout.addStretch()
        layout.addWidget(date_label)

        return item

    def go_to_downloads(self):
        """Navigate to Downloads page"""
        main_window = self.window()
        if hasattr(main_window, 'show_page'):
            main_window.show_page(1)

    def go_to_creators(self):
        """Navigate to Creators page"""
        main_window = self.window()
        if hasattr(main_window, 'show_page'):
            main_window.show_page(4)

    def showEvent(self, event):
        """Refresh data when page is shown"""
        super().showEvent(event)
        self.refresh_all()
