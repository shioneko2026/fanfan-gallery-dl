"""
Settings - Credentials management
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QScrollArea, QGroupBox, QComboBox,
                            QLineEdit, QTextEdit, QFrame, QMessageBox,
                            QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont
from core.credential_manager_simple import CredentialManager
from core.gallery_dl_runner import GalleryDLRunner
from datetime import datetime


class PlatformCredentialCard(QGroupBox):
    """Card for platform cookie management"""

    def __init__(self, platform_id, platform_name, cred_manager, parent=None):
        super().__init__(platform_name, parent)
        self.platform_id = platform_id
        self.platform_name = platform_name
        self.cred_manager = cred_manager
        self.gallery_dl_runner = GalleryDLRunner()
        self.init_ui()
        self.refresh_status()

    def get_main_window(self):
        """Get reference to main window for logging"""
        widget = self
        while widget:
            if widget.__class__.__name__ == 'MainWindow':
                return widget
            widget = widget.parent()
        return None

    def init_ui(self):
        """Initialize the card UI"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
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

        layout = QVBoxLayout(self)

        # Connection status
        self.status_label = QLabel("● No Cookies")
        self.status_label.setStyleSheet("color: #999; font-weight: normal;")
        layout.addWidget(self.status_label)

        # Cookie input — always visible
        cookie_label = QLabel("Cookies:")
        cookie_label.setStyleSheet("font-weight: normal;")
        layout.addWidget(cookie_label)

        # Cookie hint (platform-specific)
        hint = self.cred_manager.get_hint(self.platform_id)
        self.cookie_hint = QLabel(f"Paste your cookie string here. {hint}")
        self.cookie_hint.setStyleSheet("color: #1976d2; font-size: 11px; font-weight: normal; font-style: italic;")
        self.cookie_hint.setWordWrap(True)
        layout.addWidget(self.cookie_hint)

        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText("Paste cookie value here...")
        self.cookie_input.setStyleSheet("font-weight: normal; padding: 5px; font-family: 'Segoe UI';")
        self.cookie_input.setMaximumHeight(80)
        layout.addWidget(self.cookie_input)

        # Buttons row
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Cookies")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #1565c0; }
        """)
        self.save_btn.clicked.connect(self.on_save_cookies)

        self.help_btn = QPushButton("How to get cookies")
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                color: #1565c0;
                border: 1px solid #90caf9;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #bbdefb; }
        """)
        self.help_btn.clicked.connect(self.on_help_clicked)

        self.clear_cookies_btn = QPushButton("Clear Cookies")
        self.clear_cookies_btn.setStyleSheet("""
            QPushButton {
                color: #c62828;
                border: 1px solid #ef9a9a;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #ffebee; }
        """)
        self.clear_cookies_btn.clicked.connect(self.on_clear_clicked)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.help_btn)
        btn_layout.addWidget(self.clear_cookies_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Last saved timestamp
        self.timestamp_label = QLabel("Last saved: Never")
        self.timestamp_label.setStyleSheet("color: #999; font-size: 12px; font-weight: normal;")
        layout.addWidget(self.timestamp_label)

        # Test URL input with saved creators dropdown
        test_layout = QVBoxLayout()
        test_label = QLabel("Test URL:")
        test_label.setStyleSheet("font-weight: normal; font-size: 11px; color: #666;")
        test_hint = QLabel("Select a creator or paste a URL to test your cookies against")
        test_hint.setStyleSheet("font-weight: normal; font-size: 10px; color: #999; font-style: italic;")

        test_layout.addWidget(test_label)
        test_layout.addWidget(test_hint)

        test_input_layout = QHBoxLayout()

        self.test_creator_combo = QComboBox()
        self.test_creator_combo.setStyleSheet("""
            QComboBox { padding: 6px; font-size: 12px; font-family: 'Segoe UI'; font-weight: normal; }
            QComboBox QAbstractItemView {
                background-color: white;
                selection-background-color: #1976d2;
                selection-color: white;
                font-family: 'Segoe UI';
            }
        """)
        self.test_creator_combo.setMinimumWidth(200)
        self.test_creator_combo.addItem("— or type URL below —", "")
        self.test_creator_combo.currentIndexChanged.connect(self._on_test_creator_selected)

        self.test_url_input = QLineEdit()
        self.test_url_input.setPlaceholderText("e.g., https://creator-name.fanbox.cc/posts")
        self.test_url_input.setStyleSheet("font-weight: normal; padding: 6px; font-size: 12px; font-family: 'Segoe UI';")

        test_input_layout.addWidget(self.test_creator_combo)
        test_input_layout.addWidget(self.test_url_input, 1)

        test_layout.addLayout(test_input_layout)
        layout.addLayout(test_layout)

        # Test button
        action_layout = QHBoxLayout()

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setStyleSheet("font-weight: normal; padding: 6px 12px; font-family: 'Segoe UI';")
        self.test_btn.clicked.connect(self.on_test_clicked)

        action_layout.addWidget(self.test_btn)
        action_layout.addStretch()

        layout.addLayout(action_layout)

    def _on_test_creator_selected(self, index):
        """Fill test URL from selected creator"""
        url = self.test_creator_combo.itemData(index)
        if url:
            self.test_url_input.setText(url)

    def _populate_test_creators(self):
        """Populate test URL dropdown with saved creators for this platform"""
        self.test_creator_combo.blockSignals(True)
        # Keep first placeholder item, remove the rest
        while self.test_creator_combo.count() > 1:
            self.test_creator_combo.removeItem(1)

        try:
            # Get the parent CredentialsPage to access db
            parent = self.parent()
            while parent and not isinstance(parent, CredentialsPage):
                parent = parent.parent()
            if not parent:
                self.test_creator_combo.blockSignals(False)
                return

            db = parent.db
            creators = db.get_all_creators_with_platforms()
            for creator in creators:
                for p in creator['platform_entries']:
                    if p.get('platform', '').lower() == self.platform_id.lower():
                        label = creator['display_name']
                        url = p.get('profile_url', '')
                        if url:
                            self.test_creator_combo.addItem(label, url)
        except Exception:
            pass

        self.test_creator_combo.blockSignals(False)

    def on_save_cookies(self):
        """Save pasted cookies"""
        cookie_string = self.cookie_input.toPlainText().strip()

        if not cookie_string:
            QMessageBox.warning(self, "No Cookies", "Please paste cookies first.")
            return

        success = self.cred_manager.store_cookies(self.platform_id, cookie_string)

        if success:
            QMessageBox.information(
                self, "Cookies Saved",
                "Cookies saved successfully!\n\n"
                "Click 'Test Connection' to verify they work."
            )
            self.refresh_status()
        else:
            QMessageBox.warning(self, "Save Failed", "Failed to save cookies. Please try again.")

    def on_help_clicked(self):
        """Show cookie guide dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Get Cookies")
        dialog.setMinimumSize(650, 550)
        dialog.resize(700, 600)
        dialog.setStyleSheet("QDialog { background-color: #fafafa; }")

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(0, 0, 0, 12)
        dlg_layout.setSpacing(0)

        # Header
        header = QLabel("How to Get Your Cookies")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1565c0, stop:1 #0d47a1);
                color: white;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
                padding: 18px;
            }
        """)
        dlg_layout.addWidget(header)

        subtitle = QLabel("Using the Cookie-Editor browser extension (recommended)")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1565c0;
                font-size: 12px;
                font-family: 'Segoe UI';
                font-style: italic;
                padding: 6px;
                border-bottom: 1px solid #bbdefb;
            }
        """)
        dlg_layout.addWidget(subtitle)

        # Content
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setStyleSheet("""
            QTextEdit {
                font-size: 13px;
                font-family: 'Segoe UI';
                padding: 15px 25px;
                border: none;
                background-color: #fafafa;
                color: #333;
            }
        """)
        guide_text.setMarkdown(self._get_cookie_guide())
        dlg_layout.addWidget(guide_text)

        # Bottom bar
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color: #f5f5f5; border-top: 1px solid #e0e0e0;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 8, 20, 8)
        bottom_layout.addStretch()

        ok_btn = QPushButton("Got it")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565c0;
                color: white;
                border: none;
                padding: 8px 30px;
                border-radius: 4px;
                font-size: 13px;
                font-family: 'Segoe UI';
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976d2; }
        """)
        ok_btn.clicked.connect(dialog.accept)
        bottom_layout.addWidget(ok_btn)

        dlg_layout.addWidget(bottom_bar)
        dialog.exec()

    def _get_cookie_guide(self):
        """Return the cookie guide markdown, with platform-specific details"""
        platform_details = {
            "fanbox": {
                "name": "Pixiv Fanbox",
                "url": "fanbox.cc",
                "key_cookie": "FANBOXSESSID",
                "notes": (
                    "**Important:** You must be logged into **Pixiv** (not just Fanbox) "
                    "for the cookie to work. Fanbox uses your Pixiv session.\n\n"
                    "Make sure you can see subscriber-only post previews before exporting cookies. "
                    "If you see \"Please login\" on a creator's page, your session isn't active."
                ),
            },
            "fantia": {
                "name": "Fantia",
                "url": "fantia.jp",
                "key_cookie": "_session_id",
                "notes": (
                    "Fantia cookies tend to last a long time as long as you stay logged in.\n\n"
                    "If you see `[fantia][warning] Unable to download 'catchable' files` — "
                    "that's normal for paid content you haven't subscribed to. It doesn't mean "
                    "your cookies are broken."
                ),
            },
            "patreon": {
                "name": "Patreon",
                "url": "patreon.com",
                "key_cookie": "session_id",
                "notes": (
                    "Patreon cookies can expire quickly. If downloads fail with 401 errors, "
                    "re-export your cookies.\n\n"
                    "Make sure you're on the **main Patreon site** (not the mobile app) when exporting."
                ),
            },
            "subscribestar": {
                "name": "SubscribeStar",
                "url": "subscribestar.adult",
                "key_cookie": "_personalization_id",
                "notes": (
                    "SubscribeStar may use `subscribestar.adult` instead of `subscribestar.com` "
                    "for adult content creators. Make sure you export cookies from the correct domain.\n\n"
                    "Export cookies while viewing a creator's page you're subscribed to."
                ),
            },
        }

        p = platform_details.get(self.platform_id, {
            "name": self.platform_name,
            "url": "the platform website",
            "key_cookie": "(varies)",
            "notes": "",
        })

        return f"""## Step 1: Install Cookie-Editor

Install the **Cookie-Editor** extension for your browser:

- **Chrome / Edge / Brave:** Search "Cookie-Editor" in the Chrome Web Store
- **Firefox:** Search "Cookie-Editor" in Firefox Add-ons

This is a free, trusted extension that lets you export your browser cookies.

---

## Step 2: Log into {p['name']}

1. Open your browser and go to **{p['url']}**
2. Log in with your account
3. Navigate to a creator's page you're subscribed to
4. Make sure you can see subscriber content — this confirms your session is active

---

## Step 3: Export your cookies

1. While on **{p['url']}**, click the **Cookie-Editor** icon in your toolbar
2. Click the **Export** button at the bottom of the popup
3. Make sure the format is **"Netscape / HTTP Cookie File"**
4. The cookies are now **copied to your clipboard**

The key cookie gallery-dl needs is **`{p['key_cookie']}`** — Cookie-Editor will include it automatically along with all other cookies.

---

## Step 4: Paste into this app

1. Come back to this **Credentials** page
2. **Paste** (Ctrl+V) into the cookie text box above
3. Click **Save Cookies**
4. Click **Test Connection** to verify everything works

---

## {p['name']}-Specific Notes

{p['notes']}

---

## Troubleshooting

- **401 / 403 errors?** Your cookies have expired. Log into {p['url']} again and re-export.
- **Cookies not working?** Make sure you exported from the right site ({p['url']}), not a different tab.
- **Still failing?** Close your browser completely, reopen, log in fresh, and re-export.
- **Rate limit (429)?** You're making too many requests. Wait an hour and try again.
"""

    def on_test_clicked(self):
        """Test platform connection by calling gallery-dl in background thread"""
        from core.gallery_dl_thread import GalleryDLThread

        test_url = self.test_url_input.text().strip()

        if not test_url:
            QMessageBox.warning(
                self, "No Test URL",
                "Please paste a creator URL to test against.\n\n"
                "Example: https://creator-name.fanbox.cc/posts"
            )
            return

        main_window = self.get_main_window()

        if main_window:
            main_window.clear_log()
            main_window.log(f"=== Testing {self.platform_name} Connection ===")
            main_window.log(f"Platform: {self.platform_id}")
            main_window.log(f"Test URL: {test_url}")
            main_window.log("")

        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")

        self.test_thread = GalleryDLThread(
            url=test_url,
            platform=self.platform_id,
            simulate=True,
            verbose=False,
            test_mode=True
        )

        def on_output(line):
            if main_window:
                main_window.log(line)

        def on_finished(result):
            if main_window:
                main_window.log("")
                main_window.log(f"Result: {result['message']}", is_error=not result["success"])

            if result["success"]:
                if main_window:
                    main_window.log("")
                    main_window.log("Warning: Don't test repeatedly — rate limits apply")

                QMessageBox.information(
                    self, "Connection Test",
                    f"{result['message']}\n\n"
                    f"Gallery-dl successfully authenticated!\n\n"
                    f"Don't test repeatedly — rate limits apply."
                )
                self.status_label.setText("● Verified")
                self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            else:
                QMessageBox.warning(
                    self, "Connection Test",
                    f"{result['message']}\n\nCheck the log for details."
                )

            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Connection")

        def on_error(error_msg):
            if main_window:
                main_window.log(f"Error: {error_msg}", is_error=True)

            QMessageBox.warning(self, "Test Error", f"An error occurred:\n\n{error_msg}")

            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Connection")

        self.test_thread.output_line.connect(on_output)
        self.test_thread.finished.connect(on_finished)
        self.test_thread.error.connect(on_error)
        self.test_thread.start()

    def on_clear_clicked(self):
        """Clear stored credentials"""
        reply = QMessageBox.question(
            self, "Confirm Clear",
            f"Clear stored cookies for {self.platform_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.cred_manager.delete_cookies(self.platform_id)
            if success:
                QMessageBox.information(self, "Cleared", "Cookies cleared successfully!")
                self.refresh_status()
            else:
                QMessageBox.warning(self, "Clear Failed", "Failed to clear cookies.")

    def refresh_status(self):
        """Refresh connection status display"""
        self._populate_test_creators()
        has_cookies = self.cred_manager.has_cookies(self.platform_id)

        if has_cookies:
            self.status_label.setText("● Cookies Stored (click Test Connection to verify)")
            self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            self.timestamp_label.setText("Last saved: Recently")
        else:
            self.status_label.setText("● No Cookies")
            self.status_label.setStyleSheet("color: #999; font-weight: normal;")
            self.timestamp_label.setText("Last saved: Never")


class CredentialsPage(QWidget):
    """Credentials management settings page"""

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

        # Page title
        title = QLabel("Credentials Settings")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Store cookies for each platform. Cookies are stored securely in Windows Credential Manager."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Scrollable platform cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setSpacing(15)

        # Platform cards
        platforms = [
            ("fanbox", "Pixiv Fanbox"),
            ("fantia", "Fantia"),
            ("patreon", "Patreon"),
            ("subscribestar", "SubscribeStar")
        ]

        self.cards = []
        for platform_id, platform_name in platforms:
            card = PlatformCredentialCard(platform_id, platform_name, self.cred_manager, self)
            scroll_layout.addWidget(card)
            self.cards.append(card)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_container)

        layout.addWidget(scroll_area, 1)

        # Clear All button
        clear_all_btn = QPushButton("Clear All Credentials")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        clear_all_btn.clicked.connect(self.on_clear_all)
        layout.addWidget(clear_all_btn)

    def on_clear_all(self):
        """Clear all stored cookies"""
        reply = QMessageBox.warning(
            self, "Confirm Clear All",
            "This will clear ALL stored cookies for all platforms.\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for platform_id in self.cred_manager.PLATFORMS.keys():
                self.cred_manager.delete_cookies(platform_id)

            QMessageBox.information(self, "Cleared", "All cookies cleared successfully!")

            for card in self.cards:
                card.refresh_status()

    def showEvent(self, event):
        """Refresh status when page is shown"""
        super().showEvent(event)
        for card in self.cards:
            card.refresh_status()
