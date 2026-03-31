"""
Cross-Check page — compare scan results against files on disk
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QDateEdit, QCheckBox,
                            QMessageBox, QTreeWidget, QTreeWidgetItem,
                            QHeaderView, QComboBox, QFileDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QBrush
from core.gallery_dl_manager import GalleryDLManager
from core.gallery_dl_thread import GalleryDLThread
from pathlib import Path
from collections import OrderedDict
from datetime import datetime
import re
import json as _json


class CrossCheckPage(QWidget):
    """Cross-Check page — compare scan results against files on disk"""

    def __init__(self, db, queue_manager, parent=None):
        super().__init__(parent)
        self.db = db
        self.queue_manager = queue_manager
        self.manager = GalleryDLManager()
        self.setFont(QFont("Segoe UI", 10))

        self._scan_posts = None
        self._scan_raw_lines = []
        self._last_report = None
        self._last_scan_url = ""
        self._last_scan_platform = ""
        self._post_id_field = "id"

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(10)

        # Title
        title = QLabel("Cross-Check")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        desc = QLabel("Compare a creator's posts against your downloaded files to find what's missing.")
        desc.setStyleSheet("color: #666; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Saved creator dropdown ---
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

        # --- URL input + Scan ---
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        url_label.setStyleSheet("font-weight: bold;")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste creator profile URL or select from dropdown above...")
        self.url_input.setStyleSheet("padding: 8px; font-size: 13px;")

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2; color: white; border: none;
                padding: 8px 20px; border-radius: 4px; font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #1565c0; }
        """)
        self.scan_btn.clicked.connect(self.on_scan)

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.scan_btn)
        layout.addLayout(url_layout)

        # --- Folder to check ---
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Folder:")
        folder_label.setStyleSheet("font-weight: bold;")
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select the folder where this creator's files are saved...")
        self.folder_input.setStyleSheet("padding: 8px; font-size: 13px;")

        browse_btn = QPushButton("Browse")
        browse_btn.setStyleSheet("padding: 8px 16px; font-family: 'Segoe UI';")
        browse_btn.clicked.connect(self._browse_folder)

        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(browse_btn)
        layout.addLayout(folder_layout)

        # --- Date range filter ---
        date_layout = QHBoxLayout()
        date_label = QLabel("Date Range (optional):")
        date_label.setStyleSheet("color: #1976d2; font-weight: bold; font-size: 12px;")
        layout.addWidget(date_label)

        self.from_date_check = QCheckBox()
        from_label = QLabel("From:")
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setEnabled(False)
        self.from_date_check.toggled.connect(self.from_date.setEnabled)

        self.to_date_check = QCheckBox()
        to_label = QLabel("To:")
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setEnabled(False)
        self.to_date_check.toggled.connect(self.to_date.setEnabled)

        date_layout.addWidget(self.from_date_check)
        date_layout.addWidget(from_label)
        date_layout.addWidget(self.from_date)
        date_layout.addSpacing(20)
        date_layout.addWidget(self.to_date_check)
        date_layout.addWidget(to_label)
        date_layout.addWidget(self.to_date)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        # --- Warning note ---
        warning = QLabel(
            "Cross-check requires the Universal Standard naming pattern with [P{post_id}] in filenames. "
            "Files without post IDs in their names will not be detected."
        )
        warning.setStyleSheet("color: #999; font-size: 11px; font-style: italic; padding: 2px 0;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # --- Cross-Check button ---
        self.crosscheck_btn = QPushButton("Cross-Check")
        self.crosscheck_btn.setEnabled(False)
        self.crosscheck_btn.setStyleSheet("""
            QPushButton {
                background-color: #e65100; color: white; border: none;
                padding: 10px 25px; border-radius: 4px; font-weight: bold;
                font-size: 14px; font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #bf360c; }
            QPushButton:disabled { background-color: #ccc; color: #888; }
        """)
        self.crosscheck_btn.clicked.connect(self.on_crosscheck)
        layout.addWidget(self.crosscheck_btn)

        # --- Results summary bar (hidden until cross-check runs) ---
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("""
            QLabel {
                background-color: #fff3e0;
                color: #e65100;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI';
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #ffe0b2;
            }
        """)
        self.summary_label.hide()
        layout.addWidget(self.summary_label)

        # --- Results tree ---
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Status", "Date", "Post ID", "Title", "Files"])
        self.results_tree.setRootIsDecorated(False)
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
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.results_tree.setColumnWidth(0, 80)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.setColumnWidth(2, 100)
        self.results_tree.setColumnWidth(4, 60)
        layout.addWidget(self.results_tree, 1)

        # --- Action buttons ---
        action_layout = QHBoxLayout()

        self.download_missing_btn = QPushButton("Download Missing")
        self.download_missing_btn.setEnabled(False)
        self.download_missing_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50; color: white; border: none;
                padding: 10px 20px; border-radius: 4px; font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; color: #888; }
        """)
        self.download_missing_btn.clicked.connect(self.on_download_missing)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.setStyleSheet("padding: 10px 16px; font-family: 'Segoe UI';")
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setEnabled(False)
        self.deselect_all_btn.setStyleSheet("padding: 10px 16px; font-family: 'Segoe UI';")
        self.deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("padding: 10px 20px; font-family: 'Segoe UI';")
        self.clear_btn.clicked.connect(self.on_clear)

        action_layout.addWidget(self.download_missing_btn)
        action_layout.addWidget(self.select_all_btn)
        action_layout.addWidget(self.deselect_all_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

    # --- Creator dropdown ---

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
                        'creator_id': a_dict['id'],
                        'display_name': a_dict['display_name'],
                        'profile_url': p_dict.get('profile_url', ''),
                        'local_folder': p_dict.get('local_folder', ''),
                        'platform': p_dict.get('platform', ''),
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
        self.folder_input.setText(data.get('local_folder', ''))

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.folder_input.setText(folder)

    # --- Platform detection (reused from Downloader) ---

    def detect_platform(self, url):
        url_lower = url.lower()
        if 'fanbox' in url_lower or '.fanbox.cc' in url_lower:
            return 'Fanbox'
        elif 'fantia' in url_lower:
            return 'Fantia'
        elif 'patreon' in url_lower:
            return 'Patreon'
        elif 'subscribestar' in url_lower:
            return 'SubscribeStar'
        elif 'pixiv' in url_lower:
            return 'Pixiv'
        return 'Unknown'

    # --- Scan ---

    def on_scan(self):
        """Scan the creator URL to get post list"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL or select a creator.")
            return

        platform = self.detect_platform(url)
        platform_id = platform.lower().replace(" ", "")

        main_window = self.window()
        if main_window:
            main_window.clear_log()
            main_window.log(f"Cross-Check: Scanning {platform}...")
            main_window.log(f"URL: {url}")
            main_window.log("")

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.crosscheck_btn.setEnabled(False)
        self._scan_raw_lines = []
        self._post_id_field = 'id'

        # Date filters
        scan_date_from = None
        scan_date_to = None
        if self.from_date_check.isChecked():
            scan_date_from = self.from_date.date().toString("yyyy-MM-dd")
        if self.to_date_check.isChecked():
            scan_date_to = self.to_date.date().toString("yyyy-MM-dd")

        self.scan_thread = GalleryDLThread(
            url=url, platform=platform_id,
            simulate=True, verbose=False, dump_json=True,
            date_from=scan_date_from, date_to=scan_date_to
        )

        def on_output(line):
            self._scan_raw_lines.append(line)
            if main_window:
                main_window.log_panel.append_raw(line)

        def on_finished(result):
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("Scan")

            if not result['success']:
                if main_window:
                    main_window.log("Scan failed.", is_error=True)
                return

            self._parse_scan_results(scan_date_from, scan_date_to)
            self._last_scan_url = url
            self._last_scan_platform = platform

            if self._scan_posts:
                self.crosscheck_btn.setEnabled(True)

                # Detailed scan summary in app log (same as Downloader)
                if main_window:
                    posts = self._scan_posts
                    total_files = sum(
                        len(p['images']) + len(p['videos']) + len(p['archives']) + len(p['other'])
                        for p in posts.values()
                    )
                    locked_count = sum(1 for p in posts.values() if p['restricted'])
                    free_count = len(posts) - locked_count

                    main_window.log("")
                    main_window.log("=" * 55)
                    main_window.log("  CROSS-CHECK SCAN SUMMARY")
                    main_window.log("=" * 55)
                    main_window.log(f"  Posts:       {len(posts)} ({free_count} free, {locked_count} locked)")
                    main_window.log(f"  Total files: {total_files}")
                    main_window.log("=" * 55)
                    main_window.log("")

                    for post_id, post in posts.items():
                        title_str = post['title'] or 'Untitled'
                        date_str = post['date'][:10] if post['date'] else ''
                        fee_str = f"  [{post['fee']}JPY]" if post['fee'] > 0 else "  [FREE]"
                        locked = " LOCKED" if post['restricted'] else ""
                        file_count = len(post['images']) + len(post['videos']) + len(post['archives']) + len(post['other'])
                        main_window.log(f"  Post {post_id}{fee_str}{locked}")
                        main_window.log(f"    {title_str}")
                        if date_str:
                            main_window.log(f"    Date: {date_str}")
                        if file_count > 0:
                            main_window.log(f"    Files: {file_count}")
                        else:
                            main_window.log(f"    (no downloadable files)")
                        main_window.log("")

                    main_window.log("Ready to cross-check. Click the Cross-Check button.")

                # Beep to notify scan complete (respects settings)
                self._play_beep()

        def on_error(msg):
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("Scan")
            if main_window:
                main_window.log(f"Scan error: {msg}", is_error=True)

        self.scan_thread.output_line.connect(on_output)
        self.scan_thread.finished.connect(on_finished)
        self.scan_thread.error.connect(on_error)
        self.scan_thread.start()

    def _parse_scan_results(self, date_from=None, date_to=None):
        """Parse raw JSON scan output into posts dict (same logic as Downloader)"""
        VIDEO_EXTS = {'mp4', 'webm', 'mkv', 'avi', 'mov', 'm4v', 'flv', 'wmv'}
        IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff'}
        ARCHIVE_EXTS = {'zip', 'rar', '7z'}

        json_lines = []
        json_started = False
        for line in self._scan_raw_lines:
            if not json_started:
                stripped = line.strip()
                if stripped == '[' or stripped.startswith('[['):
                    json_started = True
                    json_lines.append(line)
            else:
                json_lines.append(line)

        raw_text = "\n".join(json_lines) if json_lines else "\n".join(self._scan_raw_lines)

        try:
            json_data = _json.loads(raw_text)
        except _json.JSONDecodeError:
            self._scan_posts = None
            return

        posts = OrderedDict()

        for item in json_data:
            if not isinstance(item, list) or len(item) < 2:
                continue

            item_type = item[0]

            if item_type == 2:
                meta = item[1] if isinstance(item[1], dict) else {}
                post_id = str(meta.get('id') or meta.get('post_id', 'unknown'))
                post_title = meta.get('title') or meta.get('post_title', '')

                if 'id' in meta and meta['id']:
                    self._post_id_field = 'id'
                elif 'post_id' in meta and meta['post_id']:
                    self._post_id_field = 'post_id'

                fee = meta.get('feeRequired', 0)
                if not fee and isinstance(meta.get('plan'), dict):
                    fee = meta['plan'].get('price', 0)

                restricted = meta.get('isRestricted', False)
                content_cat = meta.get('content_category', '')
                if content_cat in ('catchable', 'uncatchable'):
                    restricted = True

                post_url = meta.get('post_url', '')
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
                meta = item[2] if isinstance(item[2], dict) else {}
                post_id = str(meta.get('id') or meta.get('post_id', 'unknown'))
                ext = meta.get('extension', '').lower().lstrip('.')
                filename = meta.get('filename', '?')

                is_cover = meta.get('isCoverImage', False)
                is_thumb = meta.get('content_category', '') == 'thumb'
                if is_cover or is_thumb:
                    continue

                full_name = f"{filename}.{ext}" if ext else filename

                if post_id not in posts:
                    posts[post_id] = {
                        'title': meta.get('title', ''),
                        'date': meta.get('date', ''),
                        'fee': meta.get('feeRequired', 0),
                        'restricted': meta.get('isRestricted', False),
                        'post_url': '',
                        'images': [], 'videos': [], 'archives': [], 'other': []
                    }

                if ext in VIDEO_EXTS:
                    posts[post_id]['videos'].append(full_name)
                elif ext in IMAGE_EXTS:
                    posts[post_id]['images'].append(full_name)
                elif ext in ARCHIVE_EXTS:
                    posts[post_id]['archives'].append(full_name)
                else:
                    posts[post_id]['other'].append(full_name)

        # Apply date filter
        if date_from or date_to:
            filtered = OrderedDict()
            for pid, post in posts.items():
                post_date = post['date'][:10] if post['date'] else ''
                if date_from and post_date < date_from:
                    continue
                if date_to and post_date > date_to:
                    continue
                filtered[pid] = post
            posts = filtered

        self._scan_posts = posts

    # --- Cross-Check ---

    def on_crosscheck(self):
        """Run the cross-check comparison"""
        if not self._scan_posts:
            QMessageBox.warning(self, "No Scan", "Please scan a creator URL first.")
            return

        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "No Folder", "Please select a folder to check against.")
            return

        folder_path = Path(folder)
        disk_ids = self._scan_disk_post_ids(folder_path)

        missing = []
        present = []
        locked = []

        for post_id, post in self._scan_posts.items():
            file_count = len(post['images']) + len(post['videos']) + len(post['archives']) + len(post['other'])

            entry = {
                'id': post_id,
                'title': post['title'],
                'date': post['date'],
                'file_count': file_count,
                'restricted': post.get('has_locked_content', post.get('restricted', False)),
            }

            if post.get('has_locked_content', post.get('restricted', False)) and file_count == 0:
                locked.append(entry)
            elif post_id in disk_ids:
                present.append(entry)
            elif file_count > 0:
                missing.append(entry)
            else:
                # No files and not restricted — empty post, skip
                pass

        # Update results tree
        self._populate_results_tree(missing, present, locked)

        # Update summary
        self.summary_label.setText(
            f"  {len(missing)} missing  |  {len(present)} present  |  {len(locked)} locked"
        )
        self.summary_label.show()

        # Enable action buttons
        self.download_missing_btn.setEnabled(len(missing) > 0)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)

        main_window = self.window()
        if main_window:
            main_window.log("")
            main_window.log("=" * 55)
            main_window.log("  CROSS-CHECK RESULTS")
            main_window.log("=" * 55)
            main_window.log(f"  Missing:  {len(missing)}")
            main_window.log(f"  Present:  {len(present)}")
            main_window.log(f"  Locked:   {len(locked)}")
            main_window.log("=" * 55)
            if missing:
                main_window.log("")
                main_window.log("  Missing posts:")
                for m in missing:
                    main_window.log(f"    P{m['id']}  {m['title']}")

    def _scan_disk_post_ids(self, folder_path):
        """Scan folder recursively for files/folders with [PXXXXXXX] in name"""
        found_ids = set()
        if not folder_path.exists():
            return found_ids

        pattern = re.compile(r'\[P(\d+)\]')
        for item in folder_path.rglob('*'):
            match = pattern.search(item.name)
            if match:
                found_ids.add(match.group(1))

        return found_ids

    def _populate_results_tree(self, missing, present, locked):
        """Populate the results tree with color-coded rows"""
        self.results_tree.clear()

        colors = {
            'missing': QColor("#c62828"),
            'present': QColor("#2e7d32"),
            'locked': QColor("#757575"),
        }

        def add_rows(items, status_text, color):
            for post in items:
                item = QTreeWidgetItem()
                item.setText(0, status_text)
                item.setText(1, post.get('date', '')[:10])
                item.setText(2, f"P{post['id']}")
                item.setText(3, post.get('title', ''))
                item.setText(4, str(post.get('file_count', 0)))
                item.setData(0, Qt.ItemDataRole.UserRole, post['id'])

                for col in range(5):
                    item.setForeground(col, QBrush(color))

                if status_text == "MISSING":
                    item.setCheckState(0, Qt.CheckState.Checked)
                elif status_text == "LOCKED":
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

                self.results_tree.addTopLevelItem(item)

        add_rows(missing, "MISSING", colors['missing'])
        add_rows(present, "PRESENT", colors['present'])
        add_rows(locked, "LOCKED", colors['locked'])

    # --- Actions ---

    def on_download_missing(self):
        """Queue checked missing posts for download"""
        if not self._scan_posts or not self._last_scan_url:
            return

        # Collect checked post IDs from results tree
        checked_ids = []
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                post_id = item.data(0, Qt.ItemDataRole.UserRole)
                if post_id:
                    checked_ids.append(post_id)

        if not checked_ids:
            QMessageBox.information(self, "Nothing Selected", "No missing posts are checked.")
            return

        url = self._last_scan_url
        platform = self._last_scan_platform
        platform_id = platform.lower().replace(" ", "")
        output_path = Path(self.folder_input.text().strip())

        # Extract creator name from URL
        creator_name = url.split('/')[-1].split('?')[0]
        if '@' in url:
            for part in url.split('/'):
                if part.startswith('@'):
                    creator_name = part[1:]
                    break

        # Build post titles map
        post_titles = {}
        for pid in checked_ids:
            if pid in self._scan_posts:
                post_titles[pid] = self._scan_posts[pid].get('title', '')

        # Queue the download
        self.queue_manager.add_download(
            url=url,
            output_dir=output_path,
            creator_name=creator_name,
            platform=platform_id,
            post_ids=checked_ids,
            post_id_field=self._post_id_field,
            expected_files=len(checked_ids),
            post_titles=post_titles,
        )

        main_window = self.window()
        if main_window:
            main_window.log(f"Queued {len(checked_ids)} missing posts for download")
            main_window.show_page(2)  # Navigate to Download Queue

    def _set_all_checked(self, checked):
        """Check or uncheck all checkable items in results tree"""
        self.results_tree.blockSignals(True)
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.results_tree.topLevelItemCount()):
            item = self.results_tree.topLevelItem(i)
            # Only modify items that have checkboxes (not locked)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(0, state)
        self.results_tree.blockSignals(False)

    def on_clear(self):
        """Reset everything"""
        self.results_tree.clear()
        self.summary_label.hide()
        self.download_missing_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)
        self._scan_posts = None
        self.crosscheck_btn.setEnabled(False)

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

    def showEvent(self, event):
        """Refresh creator dropdown when page is shown"""
        super().showEvent(event)
        self._populate_creator_dropdown()
