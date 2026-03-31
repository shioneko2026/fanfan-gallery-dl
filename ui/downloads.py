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

        self.init_ui()

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

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.scan_btn)

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

        # Selection controls — row 1: buttons
        sel_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.select_all_btn.setStyleSheet("padding: 4px 12px;")
        self.select_all_btn.setVisible(False)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        self.deselect_all_btn.setStyleSheet("padding: 4px 12px;")
        self.deselect_all_btn.setVisible(False)

        self.selected_count_label = QLabel("")
        self.selected_count_label.setStyleSheet("color: #666; font-size: 12px;")

        sel_layout.addWidget(self.select_all_btn)
        sel_layout.addWidget(self.deselect_all_btn)
        sel_layout.addStretch()
        sel_layout.addWidget(self.selected_count_label)

        layout.addLayout(sel_layout)

        # Selection controls — row 2: toggles and sort
        toggle_layout = QHBoxLayout()

        self.skip_images_check = QCheckBox("Skip images (videos only)")
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
            "Sort: Tier (free first)", "Sort: Tier (expensive first)"
        ])
        self.sort_combo.setVisible(False)
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)

        toggle_layout.addWidget(self.skip_images_check)
        toggle_layout.addWidget(self.flat_videos_check)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.name_filter)
        toggle_layout.addWidget(self.post_id_filter)
        toggle_layout.addWidget(self.sort_combo)

        layout.addLayout(toggle_layout)

        # Tree widget for post/file checklist
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Title", "Date", "Post ID", "Type"])
        self.results_tree.setColumnCount(4)
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.results_tree.setColumnWidth(0, 300)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.setColumnWidth(2, 100)
        self.results_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px 2px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f7ff;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: inherit;
            }
        """)
        self.results_tree.setVisible(False)
        self.results_tree.itemChanged.connect(self._on_tree_item_changed)
        layout.addWidget(self.results_tree, 1)

        # Download button
        action_layout = QHBoxLayout()

        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.download_btn.clicked.connect(self.on_download)
        self.download_btn.setEnabled(False)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
        """)
        self.clear_btn.clicked.connect(self.on_clear)

        action_layout.addStretch()
        action_layout.addWidget(self.clear_btn)
        action_layout.addWidget(self.download_btn)

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
            main_window.log(f"Scanning {platform}...")
            main_window.log(f"URL: {url}")
            main_window.log("")
        
        # Disable scan and download buttons during scan
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.download_btn.setEnabled(False)

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
            # Update scan progress — count JSON entries that look like post metadata
            if '"title"' in line or '"post_title"' in line:
                self._scan_item_count += 1
                self.scan_btn.setText(f"Scanning... ({self._scan_item_count} items)")
        
        def on_finished(result):
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
                        post_id = str(meta.get('id') or meta.get('post_id', 'unknown'))
                        post_title = meta.get('title') or meta.get('post_title', '')

                        # Detect which metadata field holds the post ID
                        # (used later for --filter when downloading selected posts)
                        if not hasattr(self, '_post_id_field') or self._post_id_field == 'id':
                            if 'id' in meta and meta['id']:
                                self._post_id_field = 'id'
                            elif 'post_id' in meta and meta['post_id']:
                                self._post_id_field = 'post_id'
                            elif 'num' in meta and meta['num']:
                                self._post_id_field = 'num'

                        # Fee: Fanbox uses feeRequired, Fantia uses plan.price
                        fee = meta.get('feeRequired', 0)
                        if not fee and isinstance(meta.get('plan'), dict):
                            fee = meta['plan'].get('price', 0)

                        # Restricted: Fanbox uses isRestricted, Fantia uses content_category
                        restricted = meta.get('isRestricted', False)
                        # For Fantia, "catchable"/"uncatchable" content_category means locked
                        content_cat = meta.get('content_category', '')
                        if content_cat in ('catchable', 'uncatchable'):
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
                            if content_cat in ('catchable', 'uncatchable'):
                                post['has_locked_content'] = True
                            if not post['title'] and post_title:
                                post['title'] = post_title
                            if not post.get('post_url') and post_url:
                                post['post_url'] = post_url

                    elif item_type == 3 and len(item) >= 3:
                        # File entry — has [3, url, metadata]
                        meta = item[2] if isinstance(item[2], dict) else {}
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

        # Platform-specific download strategy:
        # - Fanbox: individual post URLs cause 403, so use creator URL + post ID filter
        # - Fantia/others: individual post URLs work fine, so use them directly (much faster)
        use_filter = platform_id in ('fanbox',)

        # Count expected files and build post title map from the scan tree
        expected_files, post_titles = self._count_checked_files_and_titles()

        if use_filter:
            # Fanbox: single download with creator URL + filter
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
            if main_window:
                main_window.log(f"Queued: {scan_url} ({len(checked_post_ids)} posts selected, {expected_files} files expected)")
        else:
            # Fantia/others: queue each post URL individually (fast, no full crawl)
            checked_urls = self._get_checked_post_urls()
            for post_url in checked_urls:
                # Count files for this specific post
                post_file_count = self._count_files_for_post_url(post_url)
                item_id = self.queue_manager.add_download(
                    url=post_url,
                    output_dir=output_path,
                    creator_name=creator_id,
                    platform=platform_id,
                    expected_files=post_file_count,
                    post_titles=post_titles
                )
                if main_window:
                    main_window.log(f"Queued: {post_url} ({post_file_count} files expected)")

        # Disable download button until next scan
        self.download_btn.setEnabled(False)

        # Switch to queue tab
        if main_window and hasattr(main_window, 'show_page'):
            main_window.log(f"Added {len(checked_post_ids)} posts to queue")
            main_window.log("Downloads will start automatically — check Download Queue tab")
            main_window.show_page(2)

    def _populate_results_tree(self, posts, json_data):
        """Build the checklist tree from scan results"""
        self.results_tree.blockSignals(True)
        self.results_tree.clear()

        # Store file URL mapping: tree item -> file URL
        self._file_url_map = {}
        self._scan_posts = posts

        VIDEO_EXTS = {'mp4', 'webm', 'mkv', 'avi', 'mov', 'm4v', 'flv', 'wmv'}

        # Build a map of post_id -> list of file URLs from JSON data
        post_file_urls = {}
        for item in json_data:
            if not isinstance(item, list) or len(item) < 3 or item[0] != 3:
                continue
            file_url = item[1]
            meta = item[2] if isinstance(item[2], dict) else {}
            post_id = str(meta.get('id', 'unknown'))
            is_cover = meta.get('isCoverImage', False)
            if is_cover:
                continue
            if post_id not in post_file_urls:
                post_file_urls[post_id] = []
            post_file_urls[post_id].append({
                'url': file_url,
                'filename': meta.get('filename', '?'),
                'extension': meta.get('extension', ''),
            })

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

            post_item = QTreeWidgetItem()
            post_item.setText(0, f"{title_str}")
            post_item.setText(1, date_str)
            post_item.setText(2, f"P{post_id}")
            post_item.setText(3, fee_str)
            post_item.setToolTip(0, title_str)
            post_item.setData(0, Qt.ItemDataRole.UserRole, post_id)
            post_item.setData(0, Qt.ItemDataRole.UserRole + 1, post.get('post_url', ''))
            post_item.setData(0, Qt.ItemDataRole.UserRole + 2, max_fee)

            # Color coding
            if has_locked and not has_files:
                # Fully locked — orange
                orange = QBrush(QColor("#e65100"))
                for col in range(4):
                    post_item.setForeground(col, orange)
                post_item.setCheckState(0, Qt.CheckState.Unchecked)
                post_item.setFlags(post_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            elif has_locked and has_files:
                # Mixed: has free files + locked content — orange-green
                # Show as checkable (can download the free parts)
                green = QBrush(QColor("#2e7d32"))
                orange = QBrush(QColor("#e65100"))
                post_item.setForeground(0, green)
                post_item.setForeground(1, green)
                post_item.setForeground(2, green)
                post_item.setForeground(3, orange)  # Fee label in orange to show locked portion
                post_item.setCheckState(0, Qt.CheckState.Checked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            elif max_fee > 0 and has_files:
                # Paid but fully accessible — green
                green = QBrush(QColor("#2e7d32"))
                for col in range(4):
                    post_item.setForeground(col, green)
                post_item.setCheckState(0, Qt.CheckState.Checked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            elif has_files:
                # Free with files — black (default)
                post_item.setCheckState(0, Qt.CheckState.Checked)
                post_item.setFlags(post_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            else:
                # Empty post — grey
                grey = QBrush(QColor("#999999"))
                for col in range(4):
                    post_item.setForeground(col, grey)
                post_item.setCheckState(0, Qt.CheckState.Unchecked)

            # Add file children
            file_urls = post_file_urls.get(post_id, [])
            url_idx = 0

            for f in post['videos']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "VIDEO")
                child.setForeground(3, Qt.GlobalColor.cyan)
                if not post['restricted']:
                    child.setCheckState(0, Qt.CheckState.Checked)
                    if url_idx < len(file_urls):
                        self._file_url_map[id(child)] = file_urls[url_idx]['url']
                        url_idx += 1

            for f in post['images']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "IMAGE")
                if not post['restricted']:
                    child.setCheckState(0, Qt.CheckState.Checked)
                    if url_idx < len(file_urls):
                        self._file_url_map[id(child)] = file_urls[url_idx]['url']
                        url_idx += 1

            for f in post['archives']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "ZIP")
                if not post['restricted']:
                    child.setCheckState(0, Qt.CheckState.Checked)
                    if url_idx < len(file_urls):
                        self._file_url_map[id(child)] = file_urls[url_idx]['url']
                        url_idx += 1

            for f in post['other']:
                child = QTreeWidgetItem(post_item)
                child.setText(0, f)
                child.setToolTip(0, f)
                child.setText(3, "FILE")
                if not post['restricted']:
                    child.setCheckState(0, Qt.CheckState.Checked)
                    if url_idx < len(file_urls):
                        self._file_url_map[id(child)] = file_urls[url_idx]['url']
                        url_idx += 1

            self.results_tree.addTopLevelItem(post_item)

        self.results_tree.expandAll()
        self.results_tree.blockSignals(False)

        # Show controls
        self.results_tree.setVisible(True)
        self.select_all_btn.setVisible(True)
        self.deselect_all_btn.setVisible(True)
        self.skip_images_check.setVisible(True)
        self.flat_videos_check.setVisible(True)
        self.sort_combo.setVisible(True)
        self.post_id_filter.setVisible(True)
        self.name_filter.setVisible(True)
        self.results_label.setText("Select posts and files to download:")
        self._update_selected_count()

    def _on_tree_item_changed(self, item, column):
        """Handle checkbox changes — propagate parent/child state"""
        self.results_tree.blockSignals(True)

        if item.childCount() > 0:
            # Parent toggled — set all children to same state
            state = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    child.setCheckState(0, state)
        else:
            # Child toggled — update parent state
            parent = item.parent()
            if parent:
                checked = 0
                total = 0
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                        total += 1
                        if child.checkState(0) == Qt.CheckState.Checked:
                            checked += 1

                if checked == 0:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                elif checked == total:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                else:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

        self.results_tree.blockSignals(False)
        self._update_selected_count()

    def _set_all_checked(self, checked):
        """Check or uncheck all items"""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.results_tree.blockSignals(True)
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if post_item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                post_item.setCheckState(0, state)
                for j in range(post_item.childCount()):
                    child = post_item.child(j)
                    if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                        child.setCheckState(0, state)
        self.results_tree.blockSignals(False)
        self._update_selected_count()

    def _update_selected_count(self):
        """Update the selected file count label"""
        total = 0
        selected = 0
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            for j in range(post_item.childCount()):
                child = post_item.child(j)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    total += 1
                    if child.checkState(0) == Qt.CheckState.Checked:
                        selected += 1

        self.selected_count_label.setText(f"{selected}/{total} files selected")
        self.download_btn.setEnabled(selected > 0)
        self.download_btn.setText(f"Download Selected ({selected})")

    def _get_selected_file_urls(self):
        """Get URLs of all checked files"""
        urls = []
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            for j in range(post_item.childCount()):
                child = post_item.child(j)
                if (child.flags() & Qt.ItemFlag.ItemIsUserCheckable and
                        child.checkState(0) == Qt.CheckState.Checked):
                    url = self._file_url_map.get(id(child))
                    if url:
                        urls.append(url)
        return urls

    def _on_skip_images_toggled(self, checked):
        """Toggle image files on/off in the checklist"""
        self.results_tree.blockSignals(True)
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            for j in range(post_item.childCount()):
                child = post_item.child(j)
                file_type = child.text(1)
                if file_type == "IMAGE":
                    if checked:
                        child.setCheckState(0, Qt.CheckState.Unchecked)
                    else:
                        child.setCheckState(0, Qt.CheckState.Checked)
        self.results_tree.blockSignals(False)
        # Update parent states
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if post_item.childCount() > 0:
                self._on_tree_item_changed(post_item.child(0), 0)
        self._update_selected_count()

    def _on_sort_changed(self, index):
        """Sort the tree by date, title, post ID, or tier"""
        if index == 0:  # Newest first
            self.results_tree.sortItems(1, Qt.SortOrder.DescendingOrder)
        elif index == 1:  # Oldest first
            self.results_tree.sortItems(1, Qt.SortOrder.AscendingOrder)
        elif index == 2:  # Title A-Z
            self.results_tree.sortItems(0, Qt.SortOrder.AscendingOrder)
        elif index == 3:  # Post ID
            self.results_tree.sortItems(2, Qt.SortOrder.AscendingOrder)
        elif index in (4, 5):  # Tier sort
            # Custom sort by fee stored in UserRole+2
            items = []
            while self.results_tree.topLevelItemCount() > 0:
                items.append(self.results_tree.takeTopLevelItem(0))
            reverse = (index == 5)  # expensive first
            items.sort(key=lambda x: x.data(0, Qt.ItemDataRole.UserRole + 2) or 0, reverse=reverse)
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
        """Count total checked files and build post_id -> title mapping from tree"""
        total_files = 0
        post_titles = {}
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            post_id = post_item.data(0, Qt.ItemDataRole.UserRole)
            post_title = post_item.text(0).split(']')[-1].strip() if ']' in post_item.text(0) else post_item.text(0)
            if post_id:
                post_titles[str(post_id)] = post_title
            if post_item.checkState(0) in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                # Count checked child items (files)
                for j in range(post_item.childCount()):
                    child = post_item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        total_files += 1
        return total_files, post_titles

    def _count_files_for_post_url(self, post_url):
        """Count checked files for a specific post URL"""
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            item_url = post_item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_url == post_url:
                count = 0
                for j in range(post_item.childCount()):
                    child = post_item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        count += 1
                return count
        return 0

    def _get_checked_post_urls(self):
        """Get URLs of all checked posts (legacy — kept for compatibility)"""
        urls = []
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if post_item.checkState(0) in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                post_url = post_item.data(0, Qt.ItemDataRole.UserRole + 1)
                if post_url:
                    urls.append(post_url)
        return urls

    def _get_checked_post_ids(self):
        """Get IDs of all checked posts (for filter-based selective downloading)"""
        ids = []
        for i in range(self.results_tree.topLevelItemCount()):
            post_item = self.results_tree.topLevelItem(i)
            if post_item.checkState(0) in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
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
            creators = list(self.db.get_all_creators())
            for a in creators:
                a_dict = dict(a)
                platforms = self.db.get_creator_platforms(a_dict['id'])
                for p in platforms:
                    p_dict = dict(p)
                    label = f"{a_dict['display_name']} ({p_dict['platform'].title()})"
                    self.creator_combo.addItem(label, {
                        'profile_url': p_dict.get('profile_url', ''),
                        'local_folder': p_dict.get('local_folder', ''),
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
        self.select_all_btn.setVisible(False)
        self.deselect_all_btn.setVisible(False)
        self.skip_images_check.setVisible(False)
        self.flat_videos_check.setVisible(False)
        self.sort_combo.setVisible(False)
        self.post_id_filter.setVisible(False)
        self.name_filter.setVisible(False)
        self.post_id_filter.clear()
        self.name_filter.clear()
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
        creators = list(self.db.get_all_creators())
        for creator in creators:
            platforms = self.db.get_creator_platforms(creator['id'])
            for p in platforms:
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
