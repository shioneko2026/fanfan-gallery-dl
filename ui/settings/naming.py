"""
Settings - Naming patterns configuration
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QGroupBox, QComboBox,
                            QTextEdit, QRadioButton, QButtonGroup, QFrame,
                            QGridLayout, QApplication, QScrollArea, QLayout,
                            QInputDialog, QMessageBox, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QFont
from functools import partial
from pathlib import Path


class FlowLayout(QLayout):
    """Layout that wraps widgets to the next line when they don't fit"""

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def spacing(self):
        return self._spacing if self._spacing >= 0 else 6

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = effective.x(), effective.y()
        line_height = 0
        sp = self.spacing()

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if x + w > effective.right() + 1 and line_height > 0:
                x = effective.x()
                y += line_height + sp
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += w + sp
            line_height = max(line_height, h)

        return y + line_height - rect.y() + m.bottom()


class NamingPage(QWidget):
    """Naming patterns settings page"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        # Set font on the widget itself to prevent QFont::setPointSize warnings
        base_font = QFont("Segoe UI", 10)
        self.setFont(base_font)

        self._loading_preset = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        scroll.setWidget(container)
        outer.addWidget(scroll)

        # Page title
        title = QLabel("Naming Settings")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(title)

        # --- Naming Presets ---
        preset_group = QGroupBox("Naming Presets")
        preset_group.setStyleSheet("""
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
            QGroupBox * {
                font-family: 'Segoe UI';
            }
        """)

        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(250)
        self.preset_combo.setStyleSheet("""
            QComboBox { padding: 6px; font-size: 13px; font-family: 'Segoe UI'; }
            QComboBox QAbstractItemView {
                background-color: white;
                selection-background-color: #1976d2;
                selection-color: white;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
        """)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)

        # Info button (opens Universal Standard info dialog)
        self.preset_info_btn = QPushButton("?")
        self.preset_info_btn.setFixedSize(28, 28)
        self.preset_info_btn.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                color: #1565c0;
                border: 1px solid #90caf9;
                border-radius: 14px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #bbdefb; }
        """)
        self.preset_info_btn.setToolTip("Why Universal Standard?")
        self.preset_info_btn.clicked.connect(self._show_preset_info)

        self.preset_save_btn = QPushButton("Save As...")
        self.preset_save_btn.setStyleSheet("padding: 6px 12px; font-size: 12px; font-family: 'Segoe UI';")
        self.preset_save_btn.clicked.connect(self._save_as_preset)

        self.preset_rename_btn = QPushButton("Rename")
        self.preset_rename_btn.setStyleSheet("padding: 6px 12px; font-size: 12px; font-family: 'Segoe UI';")
        self.preset_rename_btn.clicked.connect(self._rename_preset)

        self.preset_delete_btn = QPushButton("Delete")
        self.preset_delete_btn.setStyleSheet("padding: 6px 12px; font-size: 12px; font-family: 'Segoe UI'; color: #c62828;")
        self.preset_delete_btn.clicked.connect(self._delete_preset)

        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.preset_info_btn)
        preset_layout.addWidget(self.preset_save_btn)
        preset_layout.addWidget(self.preset_rename_btn)
        preset_layout.addWidget(self.preset_delete_btn)
        preset_layout.addStretch()

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Folder pattern group
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
            QGroupBox * {
                font-family: 'Segoe UI';
            }
        """

        folder_group = QGroupBox("Folder Naming Pattern")
        folder_group.setStyleSheet(group_style)

        folder_layout = QVBoxLayout()

        self.folder_pattern_input = QLineEdit()
        self.folder_pattern_input.setPlaceholderText("Enter folder pattern...")
        self.folder_pattern_input.setStyleSheet("padding: 10px; font-size: 14px;")
        self.folder_pattern_input.textChanged.connect(self.update_preview)

        folder_layout.addWidget(self.folder_pattern_input)
        folder_group.setLayout(folder_layout)

        layout.addWidget(folder_group)

        # File pattern group
        file_group = QGroupBox("File Naming Pattern")
        file_group.setStyleSheet(folder_group.styleSheet())

        file_layout = QVBoxLayout()

        self.file_pattern_input = QLineEdit()
        self.file_pattern_input.setPlaceholderText("Enter file pattern...")
        self.file_pattern_input.setStyleSheet("padding: 10px; font-size: 14px;")
        self.file_pattern_input.textChanged.connect(self.update_preview)

        file_layout.addWidget(self.file_pattern_input)
        file_group.setLayout(file_layout)

        layout.addWidget(file_group)

        # Available tokens — clickable buttons that insert into the focused pattern field
        tokens_group = QGroupBox("Available Tokens (click to insert into focused field)")
        tokens_group.setStyleSheet(folder_group.styleSheet())

        tokens_layout = QVBoxLayout()

        # Track which field was last focused
        self._active_field = self.folder_pattern_input
        self.folder_pattern_input.installEventFilter(self)
        self.file_pattern_input.installEventFilter(self)

        # Token button style
        token_btn_style = """
            QPushButton {
                background-color: #e3f2fd;
                color: #1565c0;
                border: 1px solid #90caf9;
                padding: 4px 10px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bbdefb;
                border-color: #1976d2;
            }
        """
        app_token_btn_style = """
            QPushButton {
                background-color: #e8f5e9;
                color: #2e7d32;
                border: 1px solid #a5d6a7;
                padding: 4px 10px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
                border-color: #43a047;
            }
        """

        # Gallery-dl tokens section
        gdl_label = QLabel("Gallery-dl tokens (blue):")
        gdl_label.setStyleSheet("font-weight: normal; color: #666; font-size: 11px;")
        tokens_layout.addWidget(gdl_label)

        gdl_tokens = [
            ("{category}", "Platform (fanbox, fantia, pixiv...)"),
            ("{creatorId}", "Creator ID (Fanbox/Pixiv)"),
            ("{id}", "Post ID (Fanbox) — use {post_id} for Fantia"),
            ("{title}", "Post title (Fanbox only)"),
            ("{post_title}", "Post title (works on ALL platforms)"),
            ("{post_id}", "Post ID (works on ALL platforms)"),
            ("{filename}", "Original filename"),
            ("{extension}", "File extension"),
            ("{num}", "File number in post"),
            ("{date}", "Full date+time"),
            ("{date:%Y-%m-%d}", "Date only"),
            ("{date:%Y%m%d}", "Compact date"),
        ]

        gdl_flow = FlowLayout(spacing=6)
        for token, tooltip in gdl_tokens:
            btn = QPushButton(token)
            btn.setStyleSheet(token_btn_style)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._insert_token, token))
            gdl_flow.addWidget(btn)

        gdl_container = QWidget()
        gdl_container.setLayout(gdl_flow)
        tokens_layout.addWidget(gdl_container)

        # App-level tokens section (resolved from artist DB before download)
        tokens_layout.addSpacing(8)
        app_label = QLabel("App tokens (green) — resolved from your creator database:")
        app_label.setStyleSheet("font-weight: normal; color: #666; font-size: 11px;")
        tokens_layout.addWidget(app_label)

        app_tokens = [
            ("{creator_name}", "Display name from Creators tab"),
            ("{creator_jp}", "Japanese name from Creators tab"),
            ("{today}", "Today's date (YYYY-MM-DD)"),
            ("{today:%Y%m%d}", "Today's date compact (20250713)"),
        ]

        app_flow = FlowLayout(spacing=6)
        for token, tooltip in app_tokens:
            btn = QPushButton(token)
            btn.setStyleSheet(app_token_btn_style)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._insert_token, token))
            app_flow.addWidget(btn)

        app_container = QWidget()
        app_container.setLayout(app_flow)
        tokens_layout.addWidget(app_container)

        # Tip
        tip = QLabel("Click a token to insert it at the cursor position in the folder or file pattern field above.")
        tip.setStyleSheet("color: #999; font-size: 11px; font-weight: normal; padding-top: 4px;")
        tokens_layout.addWidget(tip)

        tokens_group.setLayout(tokens_layout)
        layout.addWidget(tokens_group)

        # File conflict options
        conflict_group = QGroupBox("On Filename Conflict")
        conflict_group.setStyleSheet(folder_group.styleSheet())

        conflict_layout = QVBoxLayout()

        self.conflict_group = QButtonGroup()
        self.conflict_append = QRadioButton("Append number (file.mp4, file (1).mp4, file (2).mp4)")
        self.conflict_skip = QRadioButton("Skip download")
        self.conflict_overwrite = QRadioButton("Overwrite existing file")

        self.conflict_group.addButton(self.conflict_append, 0)
        self.conflict_group.addButton(self.conflict_skip, 1)
        self.conflict_group.addButton(self.conflict_overwrite, 2)

        self.conflict_append.setChecked(True)

        conflict_layout.addWidget(self.conflict_append)
        conflict_layout.addWidget(self.conflict_skip)
        conflict_layout.addWidget(self.conflict_overwrite)

        conflict_group.setLayout(conflict_layout)
        layout.addWidget(conflict_group)

        # ZIP Auto-Extraction Settings
        zip_group = QGroupBox("ZIP Auto-Extraction (Fanbox)")
        zip_group.setStyleSheet(folder_group.styleSheet())

        zip_layout = QVBoxLayout()

        # Enable/Disable toggle
        from PyQt6.QtWidgets import QCheckBox
        self.zip_extract_enabled = QCheckBox("Automatically extract ZIP files from Fanbox")
        self.zip_extract_enabled.setChecked(True)
        self.zip_extract_enabled.setStyleSheet("font-weight: normal; padding: 5px;")

        zip_layout.addWidget(self.zip_extract_enabled)

        # Non-video folder name
        non_video_layout = QHBoxLayout()
        non_video_label = QLabel("Non-video content subfolder name:")
        non_video_label.setStyleSheet("font-weight: normal;")

        self.non_video_folder_input = QLineEdit()
        self.non_video_folder_input.setPlaceholderText("[Non-Video Content]")
        self.non_video_folder_input.setStyleSheet("padding: 8px; font-size: 14px;")

        non_video_layout.addWidget(non_video_label)
        non_video_layout.addWidget(self.non_video_folder_input)

        zip_layout.addLayout(non_video_layout)

        # Info text
        zip_info = QLabel(
            "ℹ️ When enabled, ZIP files from Fanbox will be automatically extracted. "
            "Video files stay in the main folder, while images and other files go into the subfolder. "
            "The ZIP file is sent to the recycle bin after extraction."
        )
        zip_info.setWordWrap(True)
        zip_info.setStyleSheet("color: #666; font-size: 12px; padding: 5px; font-weight: normal;")
        zip_layout.addWidget(zip_info)

        zip_group.setLayout(zip_layout)
        layout.addWidget(zip_group)

        # Preview section
        preview_group = QGroupBox("Preview")
        preview_group.setStyleSheet(folder_group.styleSheet())

        preview_layout = QVBoxLayout()

        self.folder_preview = QLabel()
        self.folder_preview.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                padding: 10px;
                font-family: monospace;
                color: #333;
            }
        """)
        self.folder_preview.setWordWrap(True)

        self.file_preview = QLabel()
        self.file_preview.setStyleSheet(self.folder_preview.styleSheet())
        self.file_preview.setWordWrap(True)

        preview_layout.addWidget(QLabel("Folder example:"))
        preview_layout.addWidget(self.folder_preview)
        preview_layout.addWidget(QLabel("File example:"))
        preview_layout.addWidget(self.file_preview)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.save_settings)

        layout.addWidget(save_btn)
        layout.addStretch()

        # Load current settings
        self.load_settings()

    def eventFilter(self, obj, event):
        """Track which pattern field was last focused"""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.FocusIn:
            if obj in (self.folder_pattern_input, self.file_pattern_input):
                self._active_field = obj
        return super().eventFilter(obj, event)

    def _insert_token(self, token: str):
        """Insert a token at the cursor position in the active pattern field"""
        field = self._active_field
        cursor_pos = field.cursorPosition()
        current_text = field.text()
        new_text = current_text[:cursor_pos] + token + current_text[cursor_pos:]
        field.setText(new_text)
        field.setCursorPosition(cursor_pos + len(token))
        field.setFocus()

    def load_settings(self):
        """Load current settings from database"""
        conflict_action = self.db.get_setting("conflict_action", "append_number")

        # ZIP extraction settings
        zip_extract_enabled = self.db.get_setting("zip_auto_extract", True)
        non_video_folder = self.db.get_setting("non_video_folder_name", "[Non-Video Content]")

        self.non_video_folder_input.setText(non_video_folder)

        # Set conflict action
        conflict_map = {
            "append_number": 0,
            "skip": 1,
            "overwrite": 2
        }
        button_id = conflict_map.get(conflict_action, 0)
        button = self.conflict_group.button(button_id)
        if button:
            button.setChecked(True)

        # Set ZIP extraction checkbox
        if isinstance(zip_extract_enabled, bool):
            self.zip_extract_enabled.setChecked(zip_extract_enabled)
        else:
            self.zip_extract_enabled.setChecked(zip_extract_enabled in [True, "true", "True", "1", 1])

        # Load presets and select Universal Standard (always resets on launch)
        self._load_presets()

        self.update_preview()

    def save_settings(self):
        """Save settings to database"""
        self.db.set_setting("folder_pattern", self.folder_pattern_input.text())
        self.db.set_setting("file_pattern", self.file_pattern_input.text())
        self.db.set_setting("date_format", "YYYY-MM-DD")

        # Save conflict action
        conflict_map = {
            0: "append_number",
            1: "skip",
            2: "overwrite"
        }
        conflict_action = conflict_map[self.conflict_group.checkedId()]
        self.db.set_setting("conflict_action", conflict_action)

        # Save ZIP extraction settings
        self.db.set_setting("zip_auto_extract", self.zip_extract_enabled.isChecked())
        non_video_folder = self.non_video_folder_input.text().strip()
        if not non_video_folder:
            non_video_folder = "[Non-Video Content]"
        self.db.set_setting("non_video_folder_name", non_video_folder)

        # Show confirmation
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Saved", "Naming settings saved successfully.")

    def update_preview(self):
        """Update the preview with example data"""
        import re
        from datetime import datetime

        # Example data using gallery-dl native + app tokens
        example_data = {
            "category": "Fanbox",
            "creatorId": "whitefish",
            "id": "12345678",
            "title": "Illustration Collection Vol.3",
            "post_id": "12345678",
            "post_title": "Illustration Collection Vol.3",
            "filename": "beautiful_artwork_01",
            "extension": "mp4",
            "num": "0",
            "creator_name": "WhiteFish",
            "creator_jp": "しろサカナ",
        }

        example_date = datetime(2025, 7, 13, 10, 30, 0)

        def resolve_pattern(pattern):
            """Replace tokens with example values, handling {date:format} syntax"""
            now = datetime.now()

            # Resolve {date:FORMAT} and {today:FORMAT} tokens
            def replace_date_fmt(m):
                token = m.group(1)
                fmt = m.group(2)
                dt = now if token == 'today' else example_date
                try:
                    return dt.strftime(fmt)
                except ValueError:
                    return m.group(0)

            result = re.sub(r'\{(date|today):([^}]+)\}', replace_date_fmt, pattern)

            # Replace plain {date} and {today}
            result = result.replace('{date}', '2025-07-13 10:30:00')
            result = result.replace('{today}', now.strftime('%Y-%m-%d'))

            # Replace all other tokens
            for key, val in example_data.items():
                result = result.replace('{' + key + '}', val)

            # Check for any unresolved tokens
            if re.search(r'\{[^}]+\}', result):
                unresolved = re.findall(r'\{[^}]+\}', result)
                return result + f"  (unknown: {', '.join(unresolved)})"

            return result

        # Generate folder preview
        folder_pattern = self.folder_pattern_input.text()
        self.folder_preview.setText(resolve_pattern(folder_pattern))

        # Generate file preview
        file_pattern = self.file_pattern_input.text()
        self.file_preview.setText(resolve_pattern(file_pattern))

    # --- Preset Methods ---

    def _load_presets(self):
        """Populate preset combo from DB, always select Universal Standard on launch"""
        self._loading_preset = True
        self.preset_combo.clear()

        presets = self.db.get_all_presets()
        for preset in presets:
            self.preset_combo.addItem(preset['name'], preset['id'])

        # Always select Universal Standard (index 0, since it's sorted first)
        if self.preset_combo.count() > 0:
            self.preset_combo.setCurrentIndex(0)
            preset = presets[0] if presets else None
            if preset:
                self.folder_pattern_input.setText(preset['folder_pattern'])
                self.file_pattern_input.setText(preset['file_pattern'])
                self.db.set_setting("folder_pattern", preset['folder_pattern'])
                self.db.set_setting("file_pattern", preset['file_pattern'])

        self._loading_preset = False
        self._update_preset_buttons()

    def _on_preset_selected(self, index):
        """Load selected preset's patterns into input fields"""
        if self._loading_preset or index < 0:
            return

        preset_id = self.preset_combo.itemData(index)
        if preset_id is None:
            return

        preset = self.db.get_preset(preset_id)
        if not preset:
            return

        self._loading_preset = True
        self.folder_pattern_input.setText(preset['folder_pattern'])
        self.file_pattern_input.setText(preset['file_pattern'])
        self.db.set_setting("folder_pattern", preset['folder_pattern'])
        self.db.set_setting("file_pattern", preset['file_pattern'])
        self._loading_preset = False

        self._update_preset_buttons()
        self.update_preview()

    def _update_preset_buttons(self):
        """Disable Rename/Delete for the default Universal Standard preset"""
        preset_id = self.preset_combo.currentData()
        if preset_id is None:
            return
        preset = self.db.get_preset(preset_id)
        is_default = preset and preset.get('is_default', 0) == 1
        self.preset_rename_btn.setEnabled(not is_default)
        self.preset_delete_btn.setEnabled(True)
        # Show info button only for Universal Standard
        self.preset_info_btn.setVisible(is_default)

    def _save_as_preset(self):
        """Save current patterns as a new preset"""
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Save Preset")
        dlg.setLabelText("Preset name:")
        dlg.resize(350, 120)
        ok = dlg.exec()
        name = dlg.textValue()
        if not ok or not name.strip():
            return
        name = name.strip()
        try:
            new_id = self.db.add_preset(
                name,
                self.folder_pattern_input.text(),
                self.file_pattern_input.text()
            )
        except Exception:
            QMessageBox.warning(self, "Error", f"A preset named '{name}' already exists.")
            return

        # Reload and select the new preset
        self._loading_preset = True
        self.preset_combo.clear()
        presets = self.db.get_all_presets()
        select_index = 0
        for i, p in enumerate(presets):
            self.preset_combo.addItem(p['name'], p['id'])
            if p['id'] == new_id:
                select_index = i
        self.preset_combo.setCurrentIndex(select_index)
        self._loading_preset = False
        self._update_preset_buttons()

    def _rename_preset(self):
        """Rename the selected preset"""
        preset_id = self.preset_combo.currentData()
        preset = self.db.get_preset(preset_id)
        if not preset or preset.get('is_default', 0) == 1:
            return

        dlg = QInputDialog(self)
        dlg.setWindowTitle("Rename Preset")
        dlg.setLabelText("New name:")
        dlg.setTextValue(preset['name'])
        dlg.resize(350, 120)
        ok = dlg.exec()
        name = dlg.textValue()
        if not ok or not name.strip():
            return
        name = name.strip()
        try:
            self.db.update_preset(preset_id, name=name)
        except Exception:
            QMessageBox.warning(self, "Error", f"A preset named '{name}' already exists.")
            return

        # Refresh combo
        current_index = self.preset_combo.currentIndex()
        self._loading_preset = True
        self.preset_combo.clear()
        for p in self.db.get_all_presets():
            self.preset_combo.addItem(p['name'], p['id'])
        self.preset_combo.setCurrentIndex(current_index)
        self._loading_preset = False

    def _delete_preset(self):
        """Delete the selected preset after confirmation"""
        preset_id = self.preset_combo.currentData()
        preset = self.db.get_preset(preset_id)
        if not preset:
            return
        if preset.get('is_default', 0) == 1:
            QMessageBox.information(
                self, "Cannot Delete",
                "Universal Standard is the default preset and cannot be deleted."
            )
            return

        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Delete preset '{preset['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.db.delete_preset(preset_id)

        # Reload and fall back to Universal Standard
        self._load_presets()

    def _show_preset_info(self):
        """Show Universal Standard info dialog from MD file"""
        from core.paths import get_resource
        md_path = get_resource("config/universal_standard_info.md")

        content = "Universal Standard naming preset information.\n\n(Content coming soon)"
        if md_path.exists():
            try:
                content = md_path.read_text(encoding='utf-8')
            except Exception:
                pass

        dialog = QDialog(self)
        dialog.setWindowTitle("Why Universal Standard?")
        dialog.setMinimumSize(700, 600)
        dialog.resize(750, 650)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #fafafa;
            }
        """)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(0, 0, 0, 12)
        dlg_layout.setSpacing(0)

        # Header banner
        header = QLabel("Why Universal Standard?")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1565c0, stop:1 #0d47a1);
                color: white;
                font-size: 22px;
                font-weight: bold;
                font-family: 'Segoe UI';
                padding: 20px;
            }
        """)
        dlg_layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("The naming pattern that makes your archive work for you.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1565c0;
                font-size: 13px;
                font-family: 'Segoe UI';
                font-style: italic;
                padding: 8px;
                border-bottom: 1px solid #bbdefb;
            }
        """)
        dlg_layout.addWidget(subtitle)

        # Content area
        text_view = QTextEdit()
        text_view.setReadOnly(True)
        text_view.setMarkdown(content)
        text_view.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                font-family: 'Segoe UI';
                line-height: 1.6;
                padding: 20px 30px;
                border: none;
                background-color: #fafafa;
                color: #333;
            }
        """)
        dlg_layout.addWidget(text_view)

        # Bottom bar with OK button
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
