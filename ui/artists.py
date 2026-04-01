"""
Artists page - manages artist list and profiles
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QScrollArea, QFrame, QLineEdit,
                            QComboBox, QDialog, QFormLayout, QMessageBox,
                            QDialogButtonBox)
from PyQt6.QtCore import Qt
from functools import partial


class AddEditArtistDialog(QDialog):
    """Dialog for adding or editing an artist"""

    def __init__(self, db, artist=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.artist = artist  # None for new, dict for edit
        self.setWindowTitle("Edit Creator" if artist else "Add Creator")
        self.setMinimumWidth(450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Creator display name or Romaji name")
        self.name_input.setStyleSheet("padding: 8px;")
        form.addRow("Display Name:", self.name_input)

        self.japanese_input = QLineEdit()
        self.japanese_input.setPlaceholderText("Japanese name (optional)")
        self.japanese_input.setStyleSheet("padding: 8px;")
        form.addRow("Japanese Name:", self.japanese_input)

        # Platform URL inputs
        self.platform_inputs = {}
        platforms = [
            ("fanbox", "Fanbox URL"),
            ("pixiv", "Pixiv URL"),
            ("patreon", "Patreon URL"),
            ("fantia", "Fantia URL"),
            ("subscribestar", "SubscribeStar URL"),
        ]
        for platform_id, label in platforms:
            inp = QLineEdit()
            inp.setPlaceholderText(f"https://...")
            inp.setStyleSheet("padding: 8px;")
            form.addRow(f"{label}:", inp)
            self.platform_inputs[platform_id] = inp

        # Download folder
        from PyQt6.QtWidgets import QFileDialog

        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Default download folder for this creator (optional)")
        self.folder_input.setStyleSheet("padding: 8px;")
        folder_browse = QPushButton("Browse")
        folder_browse.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(folder_browse)
        form.addRow("Download Folder:", folder_layout)

        layout.addLayout(form)

        # Pre-fill default save folder for new creators
        if not self.artist:
            default_folder = self.db.get_setting("default_save_folder", "")
            if default_folder:
                self.folder_input.setText(default_folder)

        # Pre-fill if editing
        if self.artist:
            self.name_input.setText(self.artist['display_name'])
            self.japanese_input.setText(self.artist['japanese_name'] or '')

            # Load platform URLs and folder
            platforms_data = self.db.get_creator_platforms(self.artist['id'])
            for p in platforms_data:
                platform = p['platform'].lower()
                if platform in self.platform_inputs:
                    self.platform_inputs[platform].setText(p['profile_url'])
                # Use folder from first platform that has one set
                if p['local_folder'] and not self.folder_input.text():
                    self.folder_input.setText(p['local_folder'])

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_folder(self):
        """Browse for download folder"""
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self.folder_input.text() or ""
        )
        if folder:
            self.folder_input.setText(folder)

    def get_data(self):
        """Return the form data"""
        return {
            'display_name': self.name_input.text().strip(),
            'japanese_name': self.japanese_input.text().strip() or None,
            'download_folder': self.folder_input.text().strip() or None,
            'platforms': {
                pid: inp.text().strip()
                for pid, inp in self.platform_inputs.items()
                if inp.text().strip()
            }
        }


class ArtistsPage(QWidget):
    """Artists listing and management page"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_filter = "All Platforms"
        self.current_sort = "Sort by Name"
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Creators")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)

        add_artist_btn = QPushButton("+ Add Creator")
        add_artist_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_artist_btn.clicked.connect(self.on_add_artist)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_artist_btn)

        layout.addLayout(header_layout)

        # Filters
        filter_layout = QHBoxLayout()

        self.platform_filter = QComboBox()
        self.platform_filter.addItems(["All Platforms", "Pixiv", "Fanbox", "Patreon", "Fantia", "SubscribeStar"])
        self.platform_filter.currentTextChanged.connect(self.on_filter_changed)

        self.sort_by = QComboBox()
        self.sort_by.addItems(["Sort by Name", "Sort by Last Updated"])
        self.sort_by.currentTextChanged.connect(self.on_sort_changed)

        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.platform_filter)
        filter_layout.addWidget(QLabel("Sort:"))
        filter_layout.addWidget(self.sort_by)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Artist list
        self.artist_container = QWidget()
        self.artist_layout = QVBoxLayout(self.artist_container)
        self.artist_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.artist_container)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        layout.addWidget(scroll_area, 1)

        # Load artists
        self.refresh_artists()

    def refresh_artists(self):
        """Refresh the artist list with current filters"""
        # Clear existing items
        while self.artist_layout.count():
            item = self.artist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get all artists
        artists = list(self.db.get_all_creators())

        # Apply platform filter
        if self.current_filter != "All Platforms":
            filter_name = self.current_filter.lower()
            artists = [
                a for a in artists
                if a['platforms'] and filter_name in a['platforms'].lower()
            ]

        # Apply sort
        if self.current_sort == "Sort by Last Updated":
            artists.sort(key=lambda a: a['last_download'] or '', reverse=True)
        # Default "Sort by Name" is already the DB order

        if not artists:
            no_artists = QLabel("No creators yet. Click '+ Add Creator' to get started.")
            no_artists.setStyleSheet("color: #999; padding: 50px; font-size: 16px;")
            no_artists.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.artist_layout.addWidget(no_artists)
            return

        for artist in artists:
            card = self.create_artist_card(artist)
            self.artist_layout.addWidget(card)

        self.artist_layout.addStretch()

    def create_artist_card(self, artist):
        """Create an artist card widget"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
            }
            QFrame:hover {
                border-color: #1976d2;
            }
        """)

        layout = QHBoxLayout(card)

        # Artist info
        info_layout = QVBoxLayout()

        name_label = QLabel(artist['display_name'])
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        platforms = artist['platforms'] if artist['platforms'] else "No platforms"
        platform_label = QLabel(f"Platforms: {platforms}")
        platform_label.setStyleSheet("color: #666;")

        last_download = artist['last_download'] if artist['last_download'] else "Never"
        date_label = QLabel(f"Last downloaded: {last_download}")
        date_label.setStyleSheet("color: #999; font-size: 12px;")

        info_layout.addWidget(name_label)
        info_layout.addWidget(platform_label)
        info_layout.addWidget(date_label)

        layout.addLayout(info_layout, 1)

        # Action buttons
        action_layout = QVBoxLayout()

        artist_id = artist['id']

        # Platform source dropdown — only shown when artist has multiple platforms
        platforms_data = self.db.get_creator_platforms(artist_id)
        platform_combo = QComboBox()
        platform_combo.setStyleSheet("padding: 4px 8px;")

        for p in platforms_data:
            label = p['platform'].capitalize()
            platform_combo.addItem(label, p)  # Store full platform data

        if len(platforms_data) <= 1:
            platform_combo.setVisible(False)  # Hide if only one platform

        # Restore last selected platform for this creator
        last_platform = self.db.get_setting(f"last_platform_{artist_id}", "")
        if last_platform:
            for i in range(platform_combo.count()):
                data = platform_combo.itemData(i)
                if data and data['platform'] == last_platform:
                    platform_combo.setCurrentIndex(i)
                    break

        # Save selection when changed
        platform_combo.currentIndexChanged.connect(
            lambda idx, combo=platform_combo, aid=artist_id:
                self.db.set_setting(f"last_platform_{aid}",
                    combo.itemData(idx)['platform'] if combo.itemData(idx) else "")
        )

        action_layout.addWidget(platform_combo)

        # Button row
        btn_layout = QHBoxLayout()

        download_btn = QPushButton("Download")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        download_btn.clicked.connect(partial(self.on_download_artist, artist_id, platform_combo))

        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda checked, aid=artist_id: self.on_edit_artist(aid))

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                color: #f44336;
                border: 1px solid #f44336;
                padding: 8px 16px;
                border-radius: 4px;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #ffebee;
            }
        """)
        delete_btn.clicked.connect(lambda checked, aid=artist_id: self.on_delete_artist(aid))

        crosscheck_btn = QPushButton("Cross-Check")
        crosscheck_btn.setStyleSheet("""
            QPushButton {
                background-color: #e65100;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #bf360c; }
        """)
        crosscheck_btn.clicked.connect(partial(self.on_crosscheck_artist, artist_id, platform_combo))

        btn_layout.addWidget(download_btn)
        btn_layout.addWidget(crosscheck_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)

        action_layout.addLayout(btn_layout)
        layout.addLayout(action_layout)

        return card

    def on_add_artist(self):
        """Show add artist dialog"""
        dialog = AddEditArtistDialog(self.db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['display_name']:
                QMessageBox.warning(self, "Missing Name", "Please enter a display name.")
                return

            creator_id = self.db.add_creator(
                data['display_name'],
                None,
                data['japanese_name']
            )

            # Add platform URLs with download folder
            for platform, url in data['platforms'].items():
                self.db.add_creator_platform(creator_id, platform, url,
                                            local_folder=data.get('download_folder'))

            self.refresh_artists()

    def on_edit_artist(self, artist_id):
        """Show edit artist dialog"""
        artist = self.db.get_creator(artist_id)
        if not artist:
            return

        dialog = AddEditArtistDialog(self.db, artist=artist, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['display_name']:
                QMessageBox.warning(self, "Missing Name", "Please enter a display name.")
                return

            self.db.update_creator(
                artist_id,
                data['display_name'],
                None,
                data['japanese_name']
            )

            # Update platforms
            for platform, url in data['platforms'].items():
                self.db.add_creator_platform(artist_id, platform, url,
                                            local_folder=data.get('download_folder'))

            self.refresh_artists()

    def on_delete_artist(self, artist_id):
        """Delete an artist after confirmation"""
        artist = self.db.get_creator(artist_id)
        if not artist:
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Delete creator '{artist['display_name']}'?\n\n"
            "This will remove all platform profiles and download history for this creator.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_creator(artist_id)
            self.refresh_artists()

    def on_download_artist(self, artist_id, platform_combo):
        """Navigate to downloads page with the selected platform URL"""
        platforms = self.db.get_creator_platforms(artist_id)
        if not platforms:
            QMessageBox.information(
                self,
                "No Platforms",
                "This creator has no platform URLs configured.\nEdit the creator to add URLs first."
            )
            return

        # Use selected platform from dropdown (or first if only one)
        selected = platform_combo.currentData()
        if selected:
            url = selected['profile_url']
            local_folder = selected['local_folder'] or ''
        else:
            url = platforms[0]['profile_url']
            local_folder = platforms[0]['local_folder'] or ''

        main_window = self.window()
        if hasattr(main_window, 'show_page'):
            main_window.show_page(1)  # Downloader page
            if hasattr(main_window, 'downloader_page'):
                main_window.downloader_page.url_input.setText(url)
                if local_folder:
                    main_window.downloader_page.output_dir.setText(local_folder)

    def on_crosscheck_artist(self, artist_id, platform_combo):
        """Navigate to cross-check page with the selected creator preloaded"""
        platforms = self.db.get_creator_platforms(artist_id)
        if not platforms:
            QMessageBox.information(
                self, "No Platforms",
                "This creator has no platform URLs configured.\nEdit the creator to add URLs first."
            )
            return

        selected = platform_combo.currentData()
        if selected:
            url = selected['profile_url']
            local_folder = selected['local_folder'] or ''
        else:
            url = platforms[0]['profile_url']
            local_folder = platforms[0]['local_folder'] or ''

        main_window = self.window()
        if hasattr(main_window, 'show_page'):
            main_window.show_page(3)  # Cross-Check page
            if hasattr(main_window, 'crosscheck_page'):
                main_window.crosscheck_page.url_input.setText(url)
                if local_folder:
                    main_window.crosscheck_page.folder_input.setText(local_folder)

    def on_filter_changed(self, text):
        """Handle platform filter change"""
        self.current_filter = text
        self.refresh_artists()

    def on_sort_changed(self, text):
        """Handle sort change"""
        self.current_sort = text
        self.refresh_artists()

    def showEvent(self, event):
        """Refresh artist list when page is shown"""
        super().showEvent(event)
        self.refresh_artists()
