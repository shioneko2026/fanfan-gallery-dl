"""
Download Queue page - shows active/completed/failed downloads
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QScrollArea, QFrame, QProgressBar,
                            QMessageBox)
from PyQt6.QtCore import Qt, pyqtSlot
from core.download_queue import DownloadQueueManager, DownloadStatus


class QueueItemWidget(QFrame):
    """Widget representing a single download in the queue"""

    def __init__(self, item_id, queue_manager, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.queue_manager = queue_manager
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 15px;
                margin: 5px 0;
            }
        """)

        layout = QVBoxLayout(self)

        # Header with artist name and status
        header_layout = QHBoxLayout()

        self.artist_label = QLabel()
        self.artist_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666;")

        header_layout.addWidget(self.artist_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Current file and progress
        self.file_label = QLabel()
        self.file_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.file_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Stats
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #999; font-size: 12px;")

        self.speed_label = QLabel()
        self.speed_label.setStyleSheet("color: #1976d2; font-size: 12px;")

        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.speed_label)

        layout.addLayout(stats_layout)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.on_pause)

        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self.on_resume)
        self.resume_btn.hide()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.on_cancel)

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.clicked.connect(self.on_retry)
        self.retry_btn.hide()

        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.resume_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.retry_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Initial update
        self.update_display()

    def update_display(self):
        """Update display from queue item"""
        item = self.queue_manager.get_item(self.item_id)
        if not item:
            return

        # Show display name if available, with creator ID as fallback
        display = item.creator_display_name or item.creator_name
        if item.creator_display_name and item.creator_name != item.creator_display_name:
            self.artist_label.setText(f"{display} [{item.creator_name}] ({item.platform})")
        else:
            self.artist_label.setText(f"{display} ({item.platform})")

        # Color-coded status
        status_colors = {
            'pending': '#ff9800',
            'downloading': '#1976d2',
            'paused': '#ff9800',
            'completed': '#4caf50',
            'partial': '#e65100',
            'failed': '#f44336',
            'cancelled': '#999',
        }
        color = status_colors.get(item.status.value, '#666')
        self.status_label.setText(item.status.value.upper())
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Current file
        if item.current_file:
            self.file_label.setText(f"Current: {item.current_file}")
        elif item.status == DownloadStatus.COMPLETED:
            self.file_label.setText("All files downloaded")
        elif item.status == DownloadStatus.PARTIAL:
            missing = item.expected_files - item.files_completed
            self.file_label.setText(f"{missing} file(s) missing — retry or check locked posts")
        else:
            self.file_label.setText("Waiting...")

        # Progress bar
        if item.files_total > 0:
            progress = int((item.files_completed / item.files_total) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"{item.files_completed}/{item.files_total} files - {progress}%")
        elif item.status == DownloadStatus.COMPLETED:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Complete")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Preparing...")

        # Stats
        stats_text = f"{item.files_completed}/{item.files_total} completed"
        if item.files_failed > 0:
            stats_text += f" | {item.files_failed} failed"
        if item.completed_at and item.started_at:
            duration = item.completed_at - item.started_at
            stats_text += f" | {str(duration).split('.')[0]}"
        self.stats_label.setText(stats_text)

        # Speed
        if item.current_speed:
            speed_text = f"{item.current_speed}"
            if item.eta:
                speed_text += f" | ETA: {item.eta}"
            self.speed_label.setText(speed_text)
        else:
            self.speed_label.setText("")

        # Button visibility
        if item.status == DownloadStatus.DOWNLOADING:
            self.pause_btn.show()
            self.resume_btn.hide()
            self.cancel_btn.show()
            self.retry_btn.hide()
        elif item.status == DownloadStatus.PAUSED:
            self.pause_btn.hide()
            self.resume_btn.show()
            self.cancel_btn.show()
            self.retry_btn.hide()
        elif item.status in [DownloadStatus.FAILED, DownloadStatus.CANCELLED, DownloadStatus.PARTIAL]:
            self.pause_btn.hide()
            self.resume_btn.hide()
            self.cancel_btn.hide()
            self.retry_btn.show()
        elif item.status == DownloadStatus.COMPLETED:
            self.pause_btn.hide()
            self.resume_btn.hide()
            self.cancel_btn.hide()
            self.retry_btn.hide()

    def on_pause(self):
        self.queue_manager.pause_download(self.item_id)

    def on_resume(self):
        self.queue_manager.resume_download(self.item_id)

    def on_cancel(self):
        self.queue_manager.cancel_download(self.item_id)

    def on_retry(self):
        self.queue_manager.retry_download(self.item_id)


class DownloadQueuePage(QWidget):
    """Download Queue page — shows all queued/active/completed downloads"""

    def __init__(self, queue_manager, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self.queue_widgets = {}
        self.init_ui()

        # Connect signals
        self.queue_manager.item_added.connect(self.on_item_added)
        self.queue_manager.item_status_changed.connect(self.on_status_changed)
        self.queue_manager.item_progress_updated.connect(self.on_progress_updated)
        self.queue_manager.item_completed.connect(self.on_item_completed)
        self.queue_manager.item_failed.connect(self.on_item_failed)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Download Queue")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Controls
        controls = QHBoxLayout()

        self.pause_all_btn = QPushButton("⏸ Pause All")
        self.pause_all_btn.clicked.connect(self.on_pause_all)

        self.abort_all_btn = QPushButton("✗ Abort All")
        self.abort_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.abort_all_btn.clicked.connect(self.on_abort_all)

        clear_btn = QPushButton("Clear Completed")
        clear_btn.clicked.connect(self.on_clear_completed)

        self.retry_all_btn = QPushButton("Retry All Failed")
        self.retry_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #e65100;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #bf360c; }
        """)
        self.retry_all_btn.clicked.connect(self.on_retry_all_failed)

        controls.addWidget(self.pause_all_btn)
        controls.addWidget(self.abort_all_btn)
        controls.addWidget(self.retry_all_btn)
        controls.addWidget(clear_btn)
        controls.addStretch()

        layout.addLayout(controls)

        # Queue items scroll area
        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.queue_container)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        layout.addWidget(scroll_area, 1)

        # Empty state
        self.empty_label = QLabel("No downloads in queue.\nGo to Downloader to scan and start downloads.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; padding: 50px; font-size: 16px;")
        self.queue_layout.addWidget(self.empty_label)

    def on_pause_all(self):
        self.queue_manager.pause_all()
        self.refresh_queue()

    def on_abort_all(self):
        reply = QMessageBox.warning(
            self, "Abort All Downloads",
            "This will cancel all active downloads. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.queue_manager.cancel_all()
            self.refresh_queue()

    def on_clear_completed(self):
        self.queue_manager.clear_completed()
        self.refresh_queue()

    def on_retry_all_failed(self):
        """Retry all failed and partial downloads"""
        retried = 0
        for item in self.queue_manager.get_all_items():
            if item.status in [DownloadStatus.FAILED, DownloadStatus.PARTIAL]:
                self.queue_manager.retry_download(item.id)
                retried += 1
        if retried > 0:
            self.refresh_queue()

    @pyqtSlot(str)
    def on_item_added(self, item_id):
        self.refresh_queue()

    @pyqtSlot(str, str)
    def on_status_changed(self, item_id, status):
        if item_id in self.queue_widgets:
            self.queue_widgets[item_id].update_display()

    @pyqtSlot(str, dict)
    def on_progress_updated(self, item_id, progress):
        if item_id in self.queue_widgets:
            self.queue_widgets[item_id].update_display()

    @pyqtSlot(str)
    def on_item_completed(self, item_id):
        if item_id in self.queue_widgets:
            self.queue_widgets[item_id].update_display()

    @pyqtSlot(str, str)
    def on_item_failed(self, item_id, error):
        if item_id in self.queue_widgets:
            self.queue_widgets[item_id].update_display()

    def refresh_queue(self):
        """Refresh queue display"""
        for widget in self.queue_widgets.values():
            widget.deleteLater()
        self.queue_widgets.clear()

        self.empty_label.hide()

        items = self.queue_manager.get_all_items()

        if not items:
            self.empty_label.show()
            return

        for item in items:
            widget = QueueItemWidget(item.id, self.queue_manager, self)
            self.queue_widgets[item.id] = widget
            self.queue_layout.addWidget(widget)

        self.queue_layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_queue()
