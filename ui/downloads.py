"""
Downloader page - scan URLs and start downloads
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QDateEdit, QCheckBox,
                            QMessageBox, QTreeWidget, QTreeWidgetItem,
                            QHeaderView, QFrame, QComboBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush
from core.gallery_dl_manager import GalleryDLManager
from pathlib import Path


class DownloaderPage(QWidget):
    """Downloader page — scan URLs and queue downloads"""

    def __init__(self, db, queue_manager, parent=None):
        super().__init__(parent)
        self.db = db
        self.manager = GalleryDLManager()
        self.queue_manager = queue_manager
        self._current_item_id = None

        self.init_ui()
        self.queue_manager.item_status_changed.connect(self._on_item_status_changed)
        self.queue_manager.item_completed.connect(self._on_download_completed)

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(6)

        # Page title
        title = QLabel("Downloader")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        desc = QLabel("Scan a creator's page to preview and select posts for download.")
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)

        # Creator dropdown
        creator_layout = QHBoxLayout()
        creator_label = QLabel("Creator:")
        creator_label.setStyleSheet("font-weight: bold;")
        self.creator_combo = QComboBox()
        self.creator_combo.setMinimumWidth(300)
        self.creator_combo.setStyleSheet("""
            QComboBox { padding: 6px; font-family: 'Segoe UI'; }
            QComboBox QAbstractItemView {
                background-color: white;
                selection-background-color: #1976d2;
                selection-color: white;
                font-family: 'Segoe UI';
            }
        """)
        self.creator_combo.currentIndexChanged.connect(self._on_creator_selected)

        creator_layout.addWidget(creator_label)
        creator_layout.addWidget(self.creator_combo, 1)
        layout.addLayout(creator_layout)

        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        url_label.setStyleSheet("font-weight: bold;")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste creator profile URL or select from dropdown above...")
        self.url_input.setStyleSheet("padding: 8px; font-size: 13px;")

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #1565c0; }
        """)
        self.scan_btn.clicked.connect(self.on_scan)

        self.abort_scan_btn = QPushButton("Abort Scan")
        self.abort_scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #b71c1c; }
        """)
        self.abort_scan_btn.setVisible(False)
        self.abort_scan_btn.clicked.connect(self._abort_scan)

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.scan_btn)
        url_layout.addWidget(self.abort_scan_btn)

        layout.addLayout(url_layout)

        # Date filters
        date_group = QLabel("Date Range (optional) — Uncheck both to scan all:")
        date_group.setStyleSheet("color: #1976d2; font-weight: bold; font-size: 12px;")
        layout.addWidget(date_group)

        date_layout = QHBoxLayout()

        self.from_date_check = QCheckBox("From:")
        self.from_date_check.setChecked(False)
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setFixedWidth(150)
        self.from_date.setEnabled(False)
        self.from_date_check.toggled.connect(self.from_date.setEnabled)

        self.to_date_check = QCheckBox("To:")
        self.to_date_check.setChecked(False)
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setFixedWidth(150)
        self.to_date.setEnabled(False)
        self.to_date_check.toggled.connect(self.to_date.setEnabled)

        date_layout.addWidget(self.from_date_check)
        date_layout.addWidget(self.from_date)
        date_layout.addSpacing(15)
        date_layout.addWidget(self.to_date_check)
        date_layout.addWidget(self.to_date)
        date_layout.addStretch()

        layout.addLayout(date_layout)

        # Output directory — artist folder by default, manual override optional
        self.artist_folder_label = QLabel("Save to: (auto-detected from creator profile)")
        self.artist_folder_label.setStyleSheet("color: #666;")

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Creator folder will be used automatically...")
        self.output_dir.setStyleSheet("padding: 10px; font-size: 14px;")
        self.output_dir.setReadOnly(True)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_output_dir)

        self.override_check = QCheckBox("Manual override")
        self.override_check.setToolTip("Enable to manually set a download folder instead of the creator's configured folder")
        self.override_check.toggled.connect(self._on_override_toggled)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir, 1)
        output_layout.addWidget(browse_btn)
        output_layout.addWidget(self.override_check)

        layout.addWidget(self.artist_folder_label)
        layout.addLayout(output_layout)

        # Auto-detect artist folder when URL changes
        self.url_input.textChanged.connect(self._auto_detect_artist_folder)

        # Scan results tree — shows posts and files with checkboxes
        self.results_label = QLabel("Scan results will appear here after scanning.")
        self.results_label.setStyleSheet("color: #999; padding: 8px;")
        layout.addWidget(self.results_label)

        # Summary label (shows count + type breakdown after scan)
        self.selected_count_label = QLabel("")
        self.selected_count_label.setStyleSheet("color: #666; font-size: 12px;")
        self.selected_count_label.setVisible(False)

        # Toolbar — toggles, filters, sort (above tree)
        toggle_layout = QHBoxLayout()

        self.skip_images_check = QCheckBox("Deselect image-only posts")
        self.skip_images_check.setVisible(False)
        self.skip_images_check.toggled.connect(self._on_skip_images_toggled)

        self.flat_videos_check = QCheckBox("All videos to one folder")
        self.flat_videos_check.setVisible(False)
        self.flat_videos_check.setToolTip("Download all videos directly into the save folder, no post subfolders")

        self.name_filter = QLineEdit()
        self.name_filter.setPlaceholderText("Search by name...")
        self.name_filter.setFixedWidth(160)
        self.name_filter.setStyleSheet("padding: 4px 8px; font-size: 12px;")
        self.name_filter.setVisible(False)
        self.name_filter.textChanged.connect(self._on_name_filter)

        self.post_id_filter = QLineEdit()
        self.post_id_filter.setPlaceholderText("Filter by Post ID...")
        self.post_id_filter.setFixedWidth(140)
        self.post_id_filter.setStyleSheet("padding: 4px 8px; font-size: 12px;")
        self.post_id_filter.setVisible(False)
        self.post_id_filter.textChanged.connect(self._on_post_id_filter)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Sort: Newest first", "Sort: Oldest first",
            "Sort: Title A-Z", "Sort: Post ID",
            "Sort: Tier (free first)", "Sort: Tier (expensive first)",
            "Sort: Most files", "Sort: Fewest files"
        ])
        self.sort_combo.setVisible(False)
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)

        toggle_layout.addWidget(self.skip_images_check)
        toggle_layout.addWidget(self.flat_videos_check)
        toggle_layout.addWidget(self.sort_combo)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.selected_count_label)

        layout.addLayout(toggle_layout)

        # Results tree — expandable rows, matching crosscheck table style
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Title", "Date", "Post ID", "Type", "Files"])
        self.results_tree.setColumnCount(5)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setStyleSheet("""
            QTreeWidget {
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f7ff;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: inherit;
            }
        """)
        header = self.results_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.setColumnWidth(2, 100)
        self.results_tree.setColumnWidth(3, 140)
        self.results_tree.setColumnWidth(4, 60)
        self.results_tree.setVisible(False)
        self.results_tree.itemChanged.connect(self._on_tree_item_changed)
        layout.addWidget(self.results_tree, 1)

        # Action buttons — below tree, matching crosscheck layout
        action_layout = QHBoxLayout()

        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white; border: none;
                padding: 10px 20px; border-radius: 4px; font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; color: #888; }
        """)
        self.download_btn.clicked.connect(self.on_download)
        self.download_btn.setEnabled(False)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.setStyleSheet("padding: 10px 16px; font-family: 'Segoe UI';")
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setEnabled(False)
        self.deselect_all_btn.setStyleSheet("padding: 10px 16px; font-family: 'Segoe UI';")
        self.deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))

        self.expand_all_btn = QPushButton("Expand All")
        self.expand_all_btn.setEnabled(False)
        self.expand_all_btn.setStyleSheet("padding: 10px 16px; font-family: 'Segoe UI';")
        self.expand_all_btn.clicked.connect(self._on_toggle_expand)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("padding: 10px 20px; font-family: 'Segoe UI';")
        self.clear_btn.clicked.connect(self.on_clear)

        action_layout.addWidget(self.download_btn)
        action_layout.addWidget(self.select_all_btn)
        action_layout.addWidget(self.deselect_all_btn)
        action_layout.addWidget(self.expand_all_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.name_filter)
        action_layout.addWidget(self.post_id_filter)

        layout.addLayout(action_layout)

    def on_scan(self):
        """Scan URL to preview downloadable content with gallery-dl (background thread)"""
        from PyQt6.QtWidgets import QMessageBox
        from core.gallery_dl_thread import GalleryDLThread
        
        url = self.url_input.text().strip()

        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL to scan.")
            return

        # Detect platform
        platform = self.detect_platform(url)
        platform_id = platform.lower().replace(" ", "")
        
        # Get main window for logging
        main_window = self.window()
        
        if main_window:
            main_window.clear_log()
            main_window.log(f"# Scanning {platform}...")
            main_window.log(f"  URL: {url}")
            main_window.log("")

        # Disable scan and download buttons during scan; show Abort Scan
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.download_btn.setEnabled(False)
        self.abort_scan_btn.setVisible(True)

        # Track scan progress
        self._scan_item_count = 0
        
        # Collect raw output lines for JSON parsing at the end
        self._scan_raw_lines = []
        # Reset post ID field detection for new scan
        self._post_id_field = 'id'

        # Get date filters for scan
        scan_date_from = None
        scan_date_to = None
        if self.from_date_check.isChecked():
            scan_date_from = self.from_date.date().toString("yyyy-MM-dd")
        if self.to_date_check.isChecked():
            scan_date_to = self.to_date.date().toString("yyyy-MM-dd")

        # Create background thread (no timeout - runs until complete)
        self.scan_thread = GalleryDLThread(
            url=url,
            platform=platform_id,
            simulate=True,   # Don't download, just list files
            verbose=False,   # JSON mode handles output
            dump_json=True,  # Get full metadata with post titles
            date_from=scan_date_from,
            date_to=scan_date_to
        )

        # Connect signals
        def on_output(line):
            # Collect all lines for JSON parsing after completion
            self._scan_raw_lines.append(line)
            # Also show in Raw Output tab for debugging
            if main_window:
                main_window.log_panel.append_raw(line)

            # Parse JSON entry to show live post progress in App Log
            # gallery-dl --dump-json outputs one entry per line: [type, ...metadata...]
            stripped = line.strip().rstrip(',')
            if stripped.startswith('[2,') or stripped.startswith('[3,'):
                try:
                    import json as _j
                    entry = _j.loads(stripped)
                    if entry[0] == 2:
                        meta = entry[-1] if isinstance(entry[-1], dict) else {}
                        title = (meta.get('post_title') or meta.get('title') or '').strip()
                        date = str(meta.get('date', ''))[:10]
                        self._scan_item_count += 1
                        self.scan_btn.setText(f"Scanning... ({self._scan_item_count} posts)")
                        label = f'"{title}"' if title else f"Post #{self._scan_item_count}"
                        date_str = f" ({date})" if date and date != 'None' else ""
                        if main_window:
                            main_window.log(f"  [{self._scan_item_count}] {label}{date_str}")
                except Exception:
                    # Fallback: keyword heuristic for non-parseable lines
                    if '"title"' in line or '"post_title"' in line:
                        self._scan_item_count += 1
                        self.scan_btn.setText(f"Scanning... ({self._scan_item_count} items)")
            elif '"title"' in line or '"post_title"' in line:
                # Compact single-line format — heuristic fallback
                self._scan_item_count += 1
                self.scan_btn.setText(f"Scanning... ({self._scan_item_count} items)")
        
        def on_finished(result):
            self.abort_scan_btn.setVisible(False)

            # Check if user aborted the scan
            if getattr(self.scan_thread, '_aborted', False):
                if main_window:
                    main_window.log("")
                    main_window.log("Scan aborted.")
                self.scan_btn.setEnabled(True)
                self.scan_btn.setText("Scan")
                return

            if main_window:
                main_window.log("")
                main_window.log(f"Scan complete - Exit code: {result['exit_code']}")

            if result['success']:
                import json as _json
                from collections import OrderedDict

                VIDEO_EXTS = {'mp4', 'webm', 'mkv', 'avi', 'mov', 'm4v', 'flv', 'wmv'}
                IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff'}
                ARCHIVE_EXTS = {'zip', 'rar', '7z'}

                # Parse the full JSON output — it's one big JSON array
                # Some platforms (Fantia) output warning lines before the JSON,
                # so we need to find where the JSON array starts.
                # Look for a line that is just "[" (the JSON array opener),
                # not "[fantia][warning]" or similar bracket-prefixed log lines.
                json_lines = []
                json_started = False
                for line in self._scan_raw_lines:
                    if not json_started:
                        stripped = line.strip()
                        # JSON array starts with a standalone "[" or "[\n"
                        if stripped == '[':
                            json_started = True
                            json_lines.append(line)
                        # Or the entire output might start with "[[" (compact format)
                        elif stripped.startswith('[['):
                            json_started = True
                            json_lines.append(line)
                    else:
                        json_lines.append(line)

                raw_text = "\n".join(json_lines) if json_lines else "\n".join(self._scan_raw_lines)

                try:
                    json_data = _json.loads(raw_text)
                except _json.JSONDecodeError as e:
                    json_data = []
                    if main_window:
                        main_window.log(f"JSON parse error: {e}", is_error=True)
                        preview = raw_text[:500] if raw_text else "(empty)"
                        main_window.log(f"Raw output preview: {preview}", is_error=True)

                # gallery-dl --dump-json outputs: [[type, data], [type, url, data], ...]
                # type 2 = directory/post metadata (no file)
                # type 3 = file entry (has url + metadata with extension/filename)
                posts = OrderedDict()  # post_id -> {title, date, files[]}
                total_images = 0
                total_videos = 0
                total_archives = 0
                total_other = 0

                for item in json_data:
                    if not isinstance(item, list) or len(item) < 2:
                        continue

                    item_type = item[0]

                    if item_type == 2:
                        # Post directory entry — extract post info
                        # Handles both Fanbox (id, title, feeRequired) and
                        # Fantia (post_id, post_title, plan.price) field names
                        meta = item[1] if isinstance(item[1], dict) else {}
                        # Fantia uses post_id, Fanbox uses id — check platform first
                        category = meta.get('category', '').lower()
                        if category == 'fantia':
                            post_id = str(meta.get('post_id') or meta.get('id', 'unknown'))
                        else:
                            post_id = str(meta.get('id') or meta.get('post_id', 'unknown'))
                        post_title = meta.get('title') or meta.get('post_title', '')

                        # Detect which metadata field holds the post ID
                        # (used later for --filter when downloading selected posts)
                        # Platform-specific: Fantia uses post_id, Fanbox uses id
                        category = meta.get('category', '').lower()
                        if category == 'fantia':
                            self._post_id_field = 'post_id'
                        elif category == 'fanbox':
                            self._post_id_field = 'id'
                        elif not hasattr(self, '_post_id_field') or self._post_id_field == 'id':
                            if 'post_id' in meta and meta['post_id']:
                                self._post_id_field = 'post_id'
                            elif 'id' in meta and meta['id']:
                                self._post_id_field = 'id'
                            elif 'num' in meta and meta['num']:
                                self._post_id_field = 'num'

                        # Fee: Fanbox uses feeRequired, Fantia uses plan.price
                        fee = meta.get('feeRequired', 0)
                        if not fee and isinstance(meta.get('plan'), dict):
                            fee = meta['plan'].get('price', 0)

                        # Restricted: Fanbox uses isRestricted, Fantia uses content_category
                        restricted = meta.get('isRestricted', False)
                        # For Fantia, only "uncatchable" means locked
                        # "catchable" means accessible at your subscription tier
                        content_cat = meta.get('content_category', '')
                        if content_cat == 'uncatchable':
                            restricted = True

                        # Build post URL for selective downloading
                        post_url = meta.get('post_url', '')  # Fantia has this
                        if not post_url and meta.get('category') == 'fanbox':
                            creator = meta.get('creatorId', '')
                            if creator:
                                post_url = f"https://www.fanbox.cc/@{creator}/posts/{post_id}"

                        if post_id not in posts:
                            posts[post_id] = {
                                'title': post_title,
                                'date': meta.get('date', ''),
                                'fee': fee,
                                'max_fee': fee,
                                'restricted': restricted,
                                'has_locked_content': restricted,
                                'post_url': post_url,
                                'images': [], 'videos': [], 'archives': [], 'other': []
                            }
                        else:
                            # Fantia: multiple content sections per post at different tiers
                            # Update with highest fee and locked status
                            post = posts[post_id]
                            if fee > post.get('max_fee', 0):
                                post['max_fee'] = fee
                            if content_cat == 'uncatchable':
                                post['has_locked_content'] = True
                            if not post['title'] and post_title:
                                post['title'] = post_title
                            if not post.get('post_url') and post_url:
                                post['post_url'] = post_url

                    elif item_type == 3 and len(item) >= 3:
                        # File entry — has [3, url, metadata]
                        meta = item[2] if isinstance(item[2], dict) else {}
                        # Match post ID extraction to platform (same logic as type 2)
                        file_category = meta.get('category', '').lower()
                        if file_category == 'fantia':
                            post_id = str(meta.get('post_id') or meta.get('id', 'unknown'))
                        else:
                            post_id = str(meta.get('id') or meta.get('post_id', 'unknown'))
                        ext = meta.get('extension', '').lower().lstrip('.')
                        filename = meta.get('filename', '?')

                        # Skip cover/thumb images (Fanbox: isCoverImage, Fantia: content_category=thumb)
                        is_cover = meta.get('isCoverImage', False)
                        is_thumb = meta.get('content_category', '') == 'thumb'
                        if is_cover or is_thumb:
                            continue

                        full_name = f"{filename}.{ext}" if ext else filename

                        # Ensure post exists
                        if post_id not in posts:
                            posts[post_id] = {
                                'title': meta.get('title', ''),
                                'date': meta.get('date', ''),
                                'fee': meta.get('feeRequired', 0),
                                'restricted': meta.get('isRestricted', False),
                                'images': [], 'videos': [], 'archives': [], 'other': []
                            }

                        # Categorize
                        if ext in VIDEO_EXTS:
                            posts[post_id]['videos'].append(full_name)
                            total_videos += 1
                        elif ext in IMAGE_EXTS:
                            posts[post_id]['images'].append(full_name)
                            total_images += 1
                        elif ext in ARCHIVE_EXTS:
                            posts[post_id]['archives'].append(full_name)
                            total_archives += 1
                        else:
                            posts[post_id]['other'].append(full_name)
                            total_other += 1

                file_count = total_images + total_videos + total_archives + total_other

                # Build detailed log output
                if main_window:
                    main_window.log("")
                    main_window.log("=" * 55)
                    main_window.log(f"  SCAN SUMMARY")
                    main_window.log("=" * 55)
                    main_window.log(f"  Total files: {file_count}")
                    main_window.log(f"  Images:      {total_images}")
                    main_window.log(f"  Videos:      {total_videos}")
                    main_window.log(f"  Archives:    {total_archives}")
                    if total_other > 0:
                        main_window.log(f"  Other:       {total_other}")
                    main_window.log(f"  Posts:       {len(posts)}")
                    main_window.log("=" * 55)
                    main_window.log("")

                    # Per-post breakdown
                    for post_id, post in posts.items():
                        post_file_count = len(post['images']) + len(post['videos']) + len(post['archives']) + len(post['other'])

                        parts = []
                        if post['images']:
                            parts.append(f"{len(post['images'])} img")
                        if post['videos']:
                            parts.append(f"{len(post['videos'])} vid")
                        if post['archives']:
                            parts.append(f"{len(post['archives'])} zip")
                        if post['other']:
                            parts.append(f"{len(post['other'])} other")

                        title_str = post['title'] if post['title'] else 'Untitled'
                        date_str = post['date'][:10] if post['date'] else ''
                        fee_str = f"  [{post['fee']}JPY]" if post['fee'] > 0 else "  [FREE]"
                        locked = " LOCKED" if post['restricted'] else ""

                        main_window.log(f"  Post {post_id}{fee_str}{locked}")
                        main_window.log(f"    {title_str}")
                        if date_str:
                            main_window.log(f"    Date: {date_str}")

                        if post_file_count > 0:
                            main_window.log(f"    Files: {post_file_count} ({', '.join(parts)})")
                            for f in post['videos']:
                                main_window.log(f"      [VIDEO] {f}")
                            for f in post['images']:
                                main_window.log(f"      [IMAGE] {f}")
                            for f in post['archives']:
                                main_window.log(f"      [ZIP]   {f}")
                            for f in post['other']:
                                main_window.log(f"      [FILE]  {f}")
                        else:
                            main_window.log(f"    (no downloadable files — subscriber-only or empty)")

                        main_window.log("")

                # Build summary message
                summary_parts = []
                if total_images > 0:
                    summary_parts.append(f"{total_images} images")
                if total_videos > 0:
                    summary_parts.append(f"{total_videos} videos")
                if total_archives > 0:
                    summary_parts.append(f"{total_archives} archives (ZIP)")
                if total_other > 0:
                    summary_parts.append(f"{total_other} other files")

                summary = ", ".join(summary_parts) if summary_parts else "No downloadable files"

                # Count locked vs free
                locked_count = sum(1 for p in posts.values() if p['restricted'])
                free_count = len(posts) - locked_count

                lock_info = ""
                if locked_count > 0:
                    lock_info = f"\n({free_count} free, {locked_count} subscriber-only)"

                # Apply date filter in Python (gallery-dl --filter doesn't affect --dump-json)
                if scan_date_from or scan_date_to:
                    filtered_posts = OrderedDict()
                    for pid, post in posts.items():
                        post_date = post['date'][:10] if post['date'] else ''
                        if scan_date_from and post_date < scan_date_from:
                            continue
                        if scan_date_to and post_date > scan_date_to:
                            continue
                        filtered_posts[pid] = post
                    posts = filtered_posts

                    # Recount after filtering
                    total_images = sum(len(p['images']) for p in posts.values())
                    total_videos = sum(len(p['videos']) for p in posts.values())
                    total_archives = sum(len(p['archives']) for p in posts.values())
                    total_other = sum(len(p['other']) for p in posts.values())
                    file_count = total_images + total_videos + total_archives + total_other

                # Populate the checklist tree
                self._populate_results_tree(posts, json_data)

                self._last_scan_url = url
                self._last_scan_platform = platform

                # Record scan in history
                try:
                    creator_id = url.split('/')[-1].split('?')[0]
                    if '@' in url:
                        for part in url.split('/'):
                            if part.startswith('@'):
                                creator_id = part[1:]
                                break
                    self.db.add_scan_record(
                        creator_name=creator_id,
                        platform=platform,
                        url=url,
                        post_count=len(posts),
                        file_count=file_count
                    )
                except Exception:
                    pass

            else:
                error_msg = "\n".join(result['stderr'][:5]) if result['stderr'] else "Unknown error"
                QMessageBox.warning(
                    self,
                    "Scan Failed",
                    f"Failed to scan URL.\n\n{error_msg}\n\nCheck the log for details."
                )

            # Re-enable scan button
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("Scan")

            # Re-enable download button if we have results
            if self.results_tree.topLevelItemCount() > 0:
                self.download_btn.setEnabled(True)

            # Beep to notify user scan is complete (respects settings)
            self._play_beep()

        def on_error(error_msg):
            self.abort_scan_btn.setVisible(False)
            if main_window:
                main_window.log(f"Error: {error_msg}", is_error=True)

            QMessageBox.warning(
                self,
                "Scan Error",
                f"An error occurred while scanning:\n\n{error_msg}"
            )

            # Re-enable scan button, keep download disabled
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("Scan")
        
        self.scan_thread.output_line.connect(on_output)
        self.scan_thread.finished.connect(on_finished)
        self.scan_thread.error.connect(on_error)
        
        # Start the thread
        self.scan_thread.start()

    def on_download(self):
        """Add checked posts to the download queue (selective download)"""
        url = getattr(self, '_last_scan_url', '') or self.url_input.text().strip()
        platform = getattr(self, '_last_scan_platform', '') or self.detect_platform(url)

        if not url:
            QMessageBox.warning(self, "No URL", "Please scan a URL first.")
            return

        output_dir = self.output_dir.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "No Folder", "Please select a download folder first.")
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get checked post IDs for selective download
        checked_post_ids = self._get_checked_post_ids()

        if not checked_post_ids:
            QMessageBox.warning(self, "Nothing Selected", "No posts are checked. Select posts to download.")
            return

        # Use the ORIGINAL scan URL (creator page) — not individual post URLs
        # Individual post URLs cause 403 on Fanbox; creator URL always works
        scan_url = getattr(self, '_last_scan_url', url)
        creator_id = scan_url.split('/')[-1].split('?')[0]
        if '@' in scan_url:
            for part in scan_url.split('/'):
                if part.startswith('@'):
                    creator_id = part.lstrip('@')
                    break
        # For Fantia URLs like fantia.jp/fanclubs/XXXXX/posts, extract fanclub ID
        if 'fanclubs' in scan_url:
            parts = scan_url.split('/')
            for i, part in enumerate(parts):
                if part == 'fanclubs' and i + 1 < len(parts):
                    creator_id = parts[i + 1].split('?')[0]
                    break

        platform_id = platform.lower().replace(" ", "")

        main_window = self.window()

        # If "all videos to one folder" is checked, override folder pattern
        # to flatten everything into a single directory
        if self.flat_videos_check.isChecked():
            # Override the folder pattern in DB temporarily for this batch
            self.db.set_setting("_flat_download", "true")
        else:
            self.db.set_setting("_flat_download", "false")

        # Count expected files and build post title map from the scan tree
        expected_files, post_titles = self._count_checked_files_and_titles()

        # Single download with creator URL + post ID filter
        # This creates one queue item with one progress bar (no per-post spawning)
        post_id_field = getattr(self, '_post_id_field', 'id')
        item_id = self.queue_manager.add_download(
            url=scan_url,
            output_dir=output_path,
            creator_name=creator_id,
            platform=platform_id,
            post_ids=checked_post_ids,
            post_id_field=post_id_field,
            expected_files=expected_files,
            post_titles=post_titles
        )
        self._current_item_id = item_id
        if main_window:
            main_window.log(f"Queued: {scan_url} ({len(checked_post_ids)} posts selected, {expected_files} files expected)")

        # Disable download button until download finishes or is aborted
        self.download_btn.setEnabled(False)

        # Switch to queue tab
        if main_window and hasattr(main_window, 'show_page'):
            main_window.log(f"Added {len(checked_post_ids)} posts to queue")
            main_window.log("Downloads will start automatically — check Download Queue tab")
            main_window.show_page(2)

    def _on_item_status_changed(self, item_id: str, status: str):
        """Re-enable Download button when the active download ends"""
        if item_id != self._current_item_id:
            return
        terminal_statuses = {"cancelled", "failed", "completed", "partial"}
        if status.lower() in terminal_statuses:
            if self.results_tree.topLevelItemCount() > 0:
                self._update_selected_count()

    def _on_download_completed(self, item_id: str):
        """Play beep when the active download finishes"""
        if item_id == self._current_item_id:
            self._play_beep()

    def _abort_scan(self):
        """Kill the running scan process"""
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.scan_thread.abort()

    def _populate_results_tree(self, posts, json_data):
        """Build the checklist tree from scan results"""
        self.results_tree.blockSignals(True)
        self.results_tree.setUpdatesEnabled(False)
        self.results_tree.clear()

        self._scan_posts = posts

        _batch_items = []
        for post_id, post in posts.items():
            # Post row
            title_str = post['title'] if post['title'] else 'Untitled'
            date_str = post['date'][:10] if post['date'] else ''

            # Build fee/lock display — handles Fantia mixed-tier posts
            max_fee = post.get('max_fee', post.get('fee', 0))
            has_locked = post.get('has_locked_content', post.get('restricted', False))
            all_files = post['videos'] + post['images'] + post['archives'] + post['other']
            has_files = len(all_files) > 0

            if max_fee > 0 and has_locked and has_files:
                fee_str = f"[FREE + {max_fee}JPY LOCKED]"
            elif max_fee > 0 and has_locked:
                fee_str = f"[{max_fee}JPY] LOCKED"
            elif max_fee > 0 and has_files:
                fee_str = f"[{max_fee}JPY]"
            elif has_files:
                fee_str = "[FREE]"
            elif has_locked:
                fee_str = f"[{max_fee}JPY] LOCKED" if max_fee > 0 else "[LOCKED]"
            else:
                fee_str = "[FREE]"

            # File count and type breakdown for this post
            n_vid = len(post['videos'])
            n_img = len(post['images'])
            n_zip = len(post['archives'])
            n_other = len(post['other'])
            n_total = n_vid + n_img + n_zip + n_other

            # Build file list tooltip
            file_lines = []
            for f in post['videos']:
                file_lines.append(f"[VIDEO] {f}")
            for f in post['images']:
                file_lines.append(f"[IMAGE] {f}")
            for f in post['archives']:
                file_lines.append(f"[ZIP] {f}")
            for f in post['other']:
                file_lines.append(f"[FILE] {f}")
            file_tooltip = "\n".join(file_lines) if file_lines else "(no files)"

            post_item = QTreeWidgetItem()
            post_item.setText(0, f"{title_str}")
            post_item.setText(1, date_str)
            post_item.setText(2, f"P{post_id}")
            post_item.setText(3, fee_str)
            post_item.setText(4, str(n_total))
            post_item.setToolTip(0, title_str)
            post_item.setToolTip(4, file_tooltip)
            post_item.setData(0, Qt.ItemDataRole.UserRole, post_id)
            post_item.setData(0, Qt.ItemDataRole.UserRole + 1, post.get('post_url', ''))
            post_item.setData(0, Qt.ItemDataRole.UserRole + 2, max_fee)
            # Store file count for sorting
            post_item.setData(4, Qt.ItemDataRole.UserRole, n_total)
            # Store type counts for summary
            post_item.setData(4, Qt.ItemDataRole.UserRole + 1, n_img)
            post_item.setData(4, Qt.ItemDataRole.UserRole + 2, n_vid)
            post_item.setData(4, Qt.ItemDataRole.UserRole + 3, n_zip)
            post_item.setData(4, Qt.ItemDataRole.UserRole + 4, n_other)

            # Color coding
            if has_locked and not has_files:
                # Locked/paid — orange, but still selectable (user may be subscribed)
                orange = QBrush(QColor("#e65100"))
                for col in range(5):
                    post_item.setForeground(col, orange)
                post_item.setCheckState(0, Qt.CheckState.Unchecked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elif has_locked and has_files:
                # Mixed: has free files + locked content — orange-green
                green = QBrush(QColor("#2e7d32"))
                orange = QBrush(QColor("#e65100"))
                post_item.setForeground(0, green)
                post_item.setForeground(1, green)
                post_item.setForeground(2, green)
                post_item.setForeground(3, orange)
                post_item.setForeground(4, green)
                post_item.setCheckState(0, Qt.CheckState.Checked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elif max_fee > 0 and has_files:
                # Paid but fully accessible — green
                green = QBrush(QColor("#2e7d32"))
                for col in range(5):
                    post_item.setForeground(col, green)
                post_item.setCheckState(0, Qt.CheckState.Checked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elif has_files:
                # Free with files — black (default)
                post_item.setCheckState(0, Qt.CheckState.Checked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            else:
                # Empty post — grey
                grey = QBrush(QColor("#999999"))
                for col in range(5):
                    post_item.setForeground(col, grey)
                post_item.setCheckState(0, Qt.CheckState.Unchecked)

            # Add display-only file children (no checkboxes — post-level only)
            for f in post['videos']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "VIDEO")
                child.setForeground(3, QBrush(QColor("#00acc1")))

            for f in post['images']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "IMAGE")
                child.setForeground(3, QBrush(QColor("#888888")))

            for f in post['archives']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "ZIP")
                child.setForeground(3, QBrush(QColor("#e65100")))

            for f in post['other']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "FILE")

            _batch_items.append(post_item)
        self.results_tree.addTopLevelItems(_batch_items)
        self.results_tree.setUpdatesEnabled(True)
        self.results_tree.blockSignals(False)

        # Show controls
        self.results_tree.setVisible(True)
        self.selected_count_label.setVisible(True)
        self.skip_images_check.setVisible(True)
        self.flat_videos_check.setVisible(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.expand_all_btn.setEnabled(True)
        self.sort_combo.setVisible(True)
        self.post_id_filter.setVisible(True)
        self.name_filter.setVisible(True)
        self.results_label.setText("Select posts and files to download:")
        self._update_selected_count()

    def _on_toggle_expand(self):
        """Toggle expand/collapse all posts to show/hide file lists"""
        # Check if any item is currently expanded
        any_expanded = False
        for i in range(self.results_tree.topLevelItemCount()):
            if self.results_tree.topLevelItem(i).isExpanded():
                any_expanded = True
                break

        if any_expanded:
            self.results_tree.collapseAll()
            self.expand_all_btn.setText("Expand All")
        else:
            self.results_tree.expandAll()
            self.expand_all_btn.setText("Collapse All")

    def _on_tree_item_changed(self, item, column):
        """Handle post checkbox changes (file children have no checkboxes)"""
        self._update_selected_count()

    def _set_all_checked(self, checked):
        """Check or uncheck all post items"""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.results_tree.blockSignals(True)
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if post_item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                post_item.setCheckState(0, state)
        self.results_tree.blockSignals(False)
        self._update_selected_count()

    def _update_selected_count(self):
        """Update the selected file/post count label with type breakdown"""
        total_posts = 0
        selected_posts = 0
        selected_files = 0
        n_img = 0
        n_vid = 0
        n_zip = 0
        n_other = 0

        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if not (post_item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                continue
            total_posts += 1

            if post_item.checkState(0) == Qt.CheckState.Checked:
                selected_posts += 1
                file_count = post_item.data(4, Qt.ItemDataRole.UserRole) or 0
                selected_files += file_count
                n_img += post_item.data(4, Qt.ItemDataRole.UserRole + 1) or 0
                n_vid += post_item.data(4, Qt.ItemDataRole.UserRole + 2) or 0
                n_zip += post_item.data(4, Qt.ItemDataRole.UserRole + 3) or 0
                n_other += post_item.data(4, Qt.ItemDataRole.UserRole + 4) or 0

        # Build type breakdown string
        parts = []
        if n_img:
            parts.append(f"{n_img} images")
        if n_vid:
            parts.append(f"{n_vid} videos")
        if n_zip:
            parts.append(f"{n_zip} archives")
        if n_other:
            parts.append(f"{n_other} other")

        breakdown = f" ({', '.join(parts)})" if parts else ""
        self.selected_count_label.setText(
            f"{selected_posts}/{total_posts} posts, {selected_files} files{breakdown}"
        )
        self.download_btn.setEnabled(selected_posts > 0)
        self.download_btn.setText(f"Download Selected ({selected_posts} posts)")

    def _on_skip_images_toggled(self, checked):
        """Deselect posts that contain ONLY images (no videos, archives, or other files)"""
        self.results_tree.blockSignals(True)
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if not (post_item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                continue
            # Check if this post has only images (no videos, archives, or other)
            n_img = post_item.data(4, Qt.ItemDataRole.UserRole + 1) or 0
            n_vid = post_item.data(4, Qt.ItemDataRole.UserRole + 2) or 0
            n_zip = post_item.data(4, Qt.ItemDataRole.UserRole + 3) or 0
            n_other = post_item.data(4, Qt.ItemDataRole.UserRole + 4) or 0
            is_image_only = n_img > 0 and n_vid == 0 and n_zip == 0 and n_other == 0
            if is_image_only:
                if checked:
                    post_item.setCheckState(0, Qt.CheckState.Unchecked)
                else:
                    post_item.setCheckState(0, Qt.CheckState.Checked)
        self.results_tree.blockSignals(False)
        self._update_selected_count()

    def _on_sort_changed(self, index):
        """Sort the tree by date, title, post ID, tier, or file count"""
        if index == 0:  # Newest first
            self.results_tree.sortItems(1, Qt.SortOrder.DescendingOrder)
        elif index == 1:  # Oldest first
            self.results_tree.sortItems(1, Qt.SortOrder.AscendingOrder)
        elif index == 2:  # Title A-Z
            self.results_tree.sortItems(0, Qt.SortOrder.AscendingOrder)
        elif index == 3:  # Post ID
            self.results_tree.sortItems(2, Qt.SortOrder.AscendingOrder)
        elif index in (4, 5):  # Tier sort
            items = []
            while self.results_tree.topLevelItemCount() > 0:
                items.append(self.results_tree.takeTopLevelItem(0))
            reverse = (index == 5)  # expensive first
            items.sort(key=lambda x: x.data(0, Qt.ItemDataRole.UserRole + 2) or 0, reverse=reverse)
            for item in items:
                self.results_tree.addTopLevelItem(item)
        elif index in (6, 7):  # File count sort
            items = []
            while self.results_tree.topLevelItemCount() > 0:
                items.append(self.results_tree.takeTopLevelItem(0))
            reverse = (index == 6)  # most files first
            items.sort(key=lambda x: x.data(4, Qt.ItemDataRole.UserRole) or 0, reverse=reverse)
            for item in items:
                self.results_tree.addTopLevelItem(item)

    def _on_name_filter(self, text):
        """Filter tree items by title/name"""
        search = text.strip().lower()
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            if not search:
                item.setHidden(False)
            else:
                title_text = item.text(0).lower()
                item.setHidden(search not in title_text)

    def _on_post_id_filter(self, text):
        """Filter tree items by Post ID"""
        search = text.strip().upper()
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            if not search:
                item.setHidden(False)
            else:
                post_id_text = item.text(2).upper()
                item.setHidden(search not in post_id_text)

    def _count_checked_files_and_titles(self):
        """Count expected download files and build post_id -> title mapping from tree."""
        total_files = 0
        post_titles = {}
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            post_id = post_item.data(0, Qt.ItemDataRole.UserRole)
            post_title = post_item.text(0).split(']')[-1].strip() if ']' in post_item.text(0) else post_item.text(0)
            if post_id:
                post_titles[str(post_id)] = post_title
            if post_item.checkState(0) == Qt.CheckState.Checked:
                total_files += post_item.data(4, Qt.ItemDataRole.UserRole) or 0
        return total_files, post_titles

    def _get_checked_post_ids(self):
        """Get IDs of all checked posts (for filter-based selective downloading)"""
        ids = []
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if post_item.checkState(0) == Qt.CheckState.Checked:
                post_id = post_item.data(0, Qt.ItemDataRole.UserRole)
                if post_id:
                    ids.append(post_id)
        return ids

    def _populate_creator_dropdown(self):
        """Populate creator dropdown from DB"""
        self.creator_combo.blockSignals(True)
        self.creator_combo.clear()
        self.creator_combo.addItem("— Select a creator —", None)

        try:
            creators = self.db.get_all_creators_with_platforms()
            for creator in creators:
                for p in creator['platform_entries']:
                    label = f"{creator['display_name']} ({p['platform'].title()})"
                    self.creator_combo.addItem(label, {
                        'profile_url': p.get('profile_url', ''),
                        'local_folder': p.get('local_folder', ''),
                    })
        except Exception:
            pass

        self.creator_combo.blockSignals(False)

    def _on_creator_selected(self, index):
        """Auto-fill URL and folder from selected creator"""
        data = self.creator_combo.itemData(index)
        if not data:
            return
        self.url_input.setText(data.get('profile_url', ''))
        folder = data.get('local_folder', '')
        if folder:
            self.output_dir.setText(folder)
            self.artist_folder_label.setText(f"Save to: {data.get('profile_url', '').split('/')[-1]}'s folder")

    def showEvent(self, event):
        """Refresh creator dropdown when page is shown"""
        super().showEvent(event)
        self._populate_creator_dropdown()

    def on_clear(self):
        """Reset the downloader page to initial state"""
        self.results_tree.clear()
        self.results_tree.setVisible(False)
        self.results_label.setText("Scan results will appear here after scanning.")
        self.download_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)
        self.expand_all_btn.setEnabled(False)
        self.expand_all_btn.setText("Expand All")
        self.skip_images_check.setVisible(False)
        self.flat_videos_check.setVisible(False)
        self.sort_combo.setVisible(False)
        self.post_id_filter.setVisible(False)
        self.name_filter.setVisible(False)
        self.post_id_filter.clear()
        self.name_filter.clear()
        self.selected_count_label.setVisible(False)
        self.selected_count_label.setText("")
        self._scan_posts = None
        self._last_scan_url = ""
        self._last_scan_platform = ""

    def _play_beep(self):
        """Play notification beep respecting sound settings"""
        beep_enabled = self.db.get_setting("beep_enabled", "true")
        if beep_enabled not in ("true", "True", "1"):
            return
        try:
            import winsound
            freq = int(self.db.get_setting("beep_frequency", "800"))
            volume = int(self.db.get_setting("beep_volume", "50"))
            duration = max(50, int(volume * 3))
            winsound.Beep(freq, duration)
        except Exception:
            from PyQt6.QtWidgets import QApplication
            QApplication.beep()

    def detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        url_lower = url.lower()

        if "fanbox.cc" in url_lower:
            return "Fanbox"
        elif "pixiv.net" in url_lower:
            if "fanbox" in url_lower:
                return "Fanbox"
            return "Pixiv"
        elif "patreon.com" in url_lower:
            return "Patreon"
        elif "fantia.jp" in url_lower:
            return "Fantia"
        elif "subscribestar.com" in url_lower or "subscribestar.adult" in url_lower:
            return "SubscribeStar"

        return "Unknown"

    def clear_date_filter(self):
        """Clear date filter fields"""
        self.from_date_check.setChecked(False)
        self.to_date_check.setChecked(False)

    def _on_override_toggled(self, checked):
        """Toggle between artist folder and manual override"""
        self.output_dir.setReadOnly(not checked)
        if checked:
            self.artist_folder_label.setText("Save to: (manual override)")
            # Load default folder if override field is empty
            if not self.output_dir.text():
                default_folder = self.db.get_setting("default_save_folder", "")
                if default_folder:
                    self.output_dir.setText(default_folder)
        else:
            # Revert to artist folder
            self._auto_detect_artist_folder(self.url_input.text())

    def _auto_detect_artist_folder(self, url):
        """Look up artist folder from DB based on URL"""
        if self.override_check.isChecked():
            return  # Don't auto-detect when manual override is on

        url = url.strip()
        if not url:
            self.output_dir.setText("")
            self.artist_folder_label.setText("Save to: (enter a URL to auto-detect)")
            return

        # Search all creator platforms for a matching URL
        creators = self.db.get_all_creators_with_platforms()
        for creator in creators:
            for p in creator['platform_entries']:
                if p['profile_url'] and p['profile_url'].strip() in url:
                    folder = p['local_folder'] or ''
                    if folder:
                        self.output_dir.setText(folder)
                        self.artist_folder_label.setText(
                            f"Save to: {creator['display_name']}'s folder (auto)")
                        return

        # No match found — use default
        default_folder = self.db.get_setting("default_save_folder", "")
        self.output_dir.setText(default_folder)
        self.artist_folder_label.setText("Save to: (no creator folder found — using default)")

    def browse_output_dir(self):
        """Browse for output directory"""
        from PyQt6.QtWidgets import QFileDialog

        # Enable override when browsing
        self.override_check.setChecked(True)

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Download Folder",
            self.output_dir.text() or ""
        )

        if folder:
            self.output_dir.setText(folder)
