"""
Download queue management system
Handles concurrent downloads with progress tracking
"""
import re
from pathlib import Path
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
from queue import Queue
from PyQt6.QtCore import QObject, pyqtSignal
from core.zip_extractor import ZipExtractor


def _graceful_kill(process):
    """Terminate a subprocess gracefully: terminate first, kill if it doesn't stop."""
    if process is None:
        return
    try:
        process.terminate()
        try:
            process.wait(timeout=3)
        except Exception:
            process.kill()
    except Exception:
        pass


@dataclass
class DownloadError:
    """Individual download error"""
    file: str
    message: str
    timestamp: datetime
    retryable: bool = False  # Whether error is retryable (network vs parse errors)


class DownloadStatus(Enum):
    """Download item status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadItem:
    """Individual download item"""
    id: str
    url: str
    output_dir: Path
    creator_name: str
    platform: str
    creator_platform_id: Optional[int] = None

    # Creator display info (for app-level naming tokens)
    creator_display_name: str = ""
    creator_romaji_name: str = ""
    creator_japanese_name: str = ""

    # Naming patterns (read from DB on main thread, used on download thread)
    folder_pattern: str = ""
    file_pattern: str = ""

    # Filtering
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    selected_files: Optional[List[str]] = None  # List of file URLs to download
    post_ids: Optional[List[str]] = None  # Post IDs for selective download (filter-based)
    post_id_field: str = "id"  # Metadata field name for post ID (varies by platform)

    # Expected content (from scan)
    expected_files: int = 0  # Total files expected from scan checklist
    post_titles: Dict[str, str] = field(default_factory=dict)  # post_id -> title mapping for error reporting

    # Progress tracking
    status: DownloadStatus = DownloadStatus.PENDING
    current_file: str = ""
    files_completed: int = 0
    files_total: int = 0
    files_failed: int = 0
    current_speed: str = ""
    eta: str = ""
    error_message: str = ""
    errors: List[DownloadError] = field(default_factory=list)  # Collection of all errors

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Internal
    thread: Optional[threading.Thread] = None
    process: Optional[object] = None  # subprocess.Popen reference
    stop_flag: bool = False
    pause_flag: bool = False


class DownloadQueueManager(QObject):
    """Manages download queue with concurrent downloads"""

    # Signals for UI updates
    item_added = pyqtSignal(str)  # item_id
    item_status_changed = pyqtSignal(str, str)  # item_id, status
    item_progress_updated = pyqtSignal(str, dict)  # item_id, progress_dict
    item_completed = pyqtSignal(str)  # item_id
    item_failed = pyqtSignal(str, str)  # item_id, error
    item_output = pyqtSignal(str, str)  # item_id, raw output line (for Raw Output tab)
    item_log = pyqtSignal(str, str)    # item_id, parsed message (for App Log tab)
    # Signal to ask user for confirmation (item_id, question_text)
    # Connect to a slot that calls confirm_response(item_id, True/False)
    confirm_needed = pyqtSignal(str, str)

    # Platform-specific worker limits (CRITICAL for API safety)
    # Pixiv/Fanbox are VERY strict and WILL ban if you exceed rate limits
    PLATFORM_WORKERS = {
        'fanbox': 1,          # Pixiv Fanbox - MUST be 1 (strict API)
        'Fanbox': 1,
        'Pixiv Fanbox': 1,
        'pixiv': 1,           # Pixiv - MUST be 1 (strict API)
        'Pixiv': 1,
        'patreon': 2,         # Patreon - more permissive
        'Patreon': 2,
        'fantia': 2,          # Fantia - more permissive
        'Fantia': 2,
        'subscribestar': 2,   # SubscribeStar - more permissive
        'SubscribeStar': 2,
    }

    def __init__(self, db, max_concurrent=2, runner=None):
        """
        Initialize download queue manager

        Args:
            db: Database instance
            max_concurrent: Maximum concurrent downloads (global limit, overridden by platform limits)
            runner: Optional GalleryDLRunner instance (created automatically if not provided)
        """
        super().__init__()
        self.db = db
        self.max_concurrent = max_concurrent

        if runner is None:
            from core.gallery_dl_runner import GalleryDLRunner
            runner = GalleryDLRunner()
        self.runner = runner

        self.items: Dict[str, DownloadItem] = {}
        self.queue = Queue()
        self.active_downloads = 0
        self.queue_lock = threading.Lock()

        # Track active workers per platform
        self.active_workers: Dict[str, int] = {}
        self.worker_lock = threading.Lock()

        # Confirmation system: download thread waits for UI response
        self._confirm_events: Dict[str, threading.Event] = {}
        self._confirm_responses: Dict[str, bool] = {}

        # Start queue processor thread
        self.processor_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processor_thread.start()

    def _ask_confirmation(self, item_id: str, question: str) -> bool:
        """Ask user for confirmation from download thread. Blocks until response."""
        event = threading.Event()
        self._confirm_events[item_id] = event
        self._confirm_responses[item_id] = False
        self.confirm_needed.emit(item_id, question)
        event.wait()  # Block until UI calls confirm_response()
        result = self._confirm_responses.pop(item_id, False)
        self._confirm_events.pop(item_id, None)
        return result

    def confirm_response(self, item_id: str, accepted: bool):
        """Called by UI to respond to a confirmation request"""
        self._confirm_responses[item_id] = accepted
        event = self._confirm_events.get(item_id)
        if event:
            event.set()  # Unblock the download thread

    def _is_retryable_error(self, error_msg: str) -> bool:
        """
        Check if an error is retryable (network errors vs parsing errors)

        Args:
            error_msg: Error message

        Returns:
            True if error is retryable
        """
        retryable_keywords = [
            'timeout', 'connection', 'network', 'timed out',
            'failed to connect', 'unable to connect',
            'temporary failure', 'rate limit', 'too many requests'
        ]

        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in retryable_keywords)

    def _get_platform_worker_limit(self, platform: str) -> int:
        """Get worker limit for a platform"""
        return self.PLATFORM_WORKERS.get(platform, 1)  # Default to 1 (safe)

    def _can_start_download(self, platform: str) -> bool:
        """
        Check if we can start a new download for this platform

        Args:
            platform: Platform identifier

        Returns:
            True if worker slot available
        """
        with self.worker_lock:
            max_workers = self._get_platform_worker_limit(platform)
            current_workers = self.active_workers.get(platform, 0)
            return current_workers < max_workers

    def _increment_platform_worker(self, platform: str):
        """Increment active worker count for platform"""
        with self.worker_lock:
            self.active_workers[platform] = self.active_workers.get(platform, 0) + 1

    def _decrement_platform_worker(self, platform: str):
        """Decrement active worker count for platform"""
        with self.worker_lock:
            if platform in self.active_workers:
                self.active_workers[platform] -= 1
                if self.active_workers[platform] <= 0:
                    del self.active_workers[platform]

    def add_download(
        self,
        url: str,
        output_dir: Path,
        creator_name: str,
        platform: str,
        creator_platform_id: Optional[int] = None,
        date_min: Optional[str] = None,
        date_max: Optional[str] = None,
        selected_files: Optional[List[str]] = None,
        post_ids: Optional[List[str]] = None,
        post_id_field: str = "id",
        expected_files: int = 0,
        post_titles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Add a download to the queue

        Args:
            url: Creator profile URL
            output_dir: Output directory
            creator_name: Creator display name
            platform: Platform name
            creator_platform_id: Optional creator platform ID for DB tracking
            date_min: Optional minimum date (YYYYMMDD)
            date_max: Optional maximum date (YYYYMMDD)
            selected_files: Optional list of specific file URLs to download

        Returns:
            Download item ID
        """
        # Generate unique ID
        item_id = f"{creator_name}_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Look up creator display info from DB for naming tokens
        display_name = creator_name
        romaji_name = ""
        japanese_name = ""
        try:
            creators = list(self.db.get_all_creators())
            found = False
            for creator in creators:
                if found:
                    break
                platforms = self.db.get_creator_platforms(creator['id'])
                for p in platforms:
                    profile_url = (p['profile_url'] or '').strip()
                    if not profile_url:
                        continue
                    # Primary match: stored URL is substring of download URL (or vice versa)
                    if profile_url in url or url in profile_url:
                        a = dict(creator)
                        display_name = a.get('display_name', creator_name) or creator_name
                        romaji_name = a.get('romaji_name', '') or ''
                        japanese_name = a.get('japanese_name', '') or ''
                        found = True
                        break
            # Fallback: match by creator_name against IDs in stored URLs
            # Handles Fantia case where creator_name is fanclub ID (e.g. "75198")
            # and stored URL contains it (e.g. "fantia.jp/fanclubs/75198/posts")
            if not found and creator_name:
                for creator in creators:
                    if found:
                        break
                    platforms = self.db.get_creator_platforms(creator['id'])
                    for p in platforms:
                        profile_url = (p['profile_url'] or '').strip()
                        if profile_url and creator_name in profile_url:
                            a = dict(creator)
                            display_name = a.get('display_name', creator_name) or creator_name
                            romaji_name = a.get('romaji_name', '') or ''
                            japanese_name = a.get('japanese_name', '') or ''
                            found = True
                            break
        except Exception as e:
            # Log the error instead of silently swallowing it
            print(f"[DownloadQueue] Creator lookup failed: {e}")

        # Read naming patterns from DB NOW (main thread — thread-safe)
        folder_pattern = self.db.get_setting("folder_pattern", "{category}/{creatorId}/{id} {title}")
        file_pattern = self.db.get_setting("file_pattern", "{filename}.{extension}")

        # If flat download mode, use empty directory (files go directly into output_dir)
        flat_download = self.db.get_setting("_flat_download", "false")
        if flat_download == "true":
            folder_pattern = ""

        # Create download item
        item = DownloadItem(
            id=item_id,
            url=url,
            output_dir=output_dir,
            creator_name=creator_name,
            platform=platform,
            creator_platform_id=creator_platform_id,
            creator_display_name=display_name,
            creator_romaji_name=romaji_name,
            creator_japanese_name=japanese_name,
            folder_pattern=folder_pattern,
            file_pattern=file_pattern,
            date_min=date_min,
            date_max=date_max,
            selected_files=selected_files,
            post_ids=post_ids,
            post_id_field=post_id_field,
            expected_files=expected_files or 0,
            post_titles=post_titles or {},
            files_total=expected_files or 0,
        )

        with self.queue_lock:
            self.items[item_id] = item
            self.queue.put(item_id)

        self.item_added.emit(item_id)
        return item_id

    def _process_queue(self):
        """Background thread that processes the download queue"""
        while True:
            # Wait for available slot (global or platform-specific)
            while self.active_downloads >= self.max_concurrent:
                threading.Event().wait(0.5)

            # Get next item (non-blocking peek)
            try:
                item_id = self.queue.get(timeout=1)
            except Exception:
                continue

            with self.queue_lock:
                if item_id not in self.items:
                    continue

                item = self.items[item_id]

                # Skip if cancelled
                if item.status == DownloadStatus.CANCELLED:
                    continue

                # Check platform-specific worker limit
                if not self._can_start_download(item.platform):
                    # Put back in queue and wait
                    self.queue.put(item_id)
                    threading.Event().wait(1.0)  # Wait longer before retry
                    continue

                # Start download in new thread
                self.active_downloads += 1
                self._increment_platform_worker(item.platform)

                item.thread = threading.Thread(
                    target=self._download_item,
                    args=(item_id,),
                    daemon=True
                )
                item.thread.start()

    def _download_item(self, item_id: str):
        """Download a single item"""
        item = self.items[item_id]

        try:
            # Update status
            item.status = DownloadStatus.DOWNLOADING
            item.started_at = datetime.now()
            self.item_status_changed.emit(item_id, item.status.value)

            # Log start to App Log
            self.item_log.emit(item_id, "")
            self.item_log.emit(item_id, f"{'=' * 55}")
            display = item.creator_display_name or item.creator_name
            creator_str = f"{display} [{item.creator_name}]" if display != item.creator_name else item.creator_name
            self.item_log.emit(item_id, f"  DOWNLOADING: {creator_str} ({item.platform})")
            self.item_log.emit(item_id, f"  URL: {item.url}")
            self.item_log.emit(item_id, f"  Save to: {item.output_dir}")
            self.item_log.emit(item_id, f"{'=' * 55}")
            self.item_log.emit(item_id, "")

            # Prepare output callback — streams to both parser and log panel
            def output_callback(line: str):
                if item.stop_flag or item.pause_flag:
                    # Stop the subprocess when pause/cancel is requested
                    _graceful_kill(item.process)
                    return

                # Stream raw output to log panel
                self.item_output.emit(item_id, line)
                # Also parse for progress tracking
                self._parse_progress(item_id, line)

            # Store subprocess reference for pause/cancel
            def process_callback(process):
                item.process = process
                # Stop immediately if cancel was clicked before process started
                if item.stop_flag or item.pause_flag:
                    _graceful_kill(process)

            # App-level token replacements for naming patterns
            app_tokens = {
                'creator_name': item.creator_display_name,
                'creator_jp': item.creator_japanese_name,
            }

            # Read platform-specific performance settings
            platform_key = item.platform.lower()
            rate_limit = self.db.get_setting(f"{platform_key}_rate_limit", "")
            sleep_request = self.db.get_setting(f"{platform_key}_sleep_request", "0.5")
            download_retries = int(self.db.get_setting(f"{platform_key}_retries", "4"))
            skip_abort_threshold = int(self.db.get_setting("skip_abort_threshold", "0"))

            # Execute download via runner (handles cookies automatically)
            # verbose=True so raw gallery-dl output is captured for the Raw Output tab
            # Pass naming patterns directly (read on main thread, thread-safe)
            max_retries = 3
            result = None

            for attempt in range(1, max_retries + 1):
                if item.stop_flag or item.pause_flag:
                    break

                if attempt > 1:
                    import time
                    delay = attempt * 10  # 20s, 30s
                    self.item_log.emit(item_id, f"  Retry {attempt}/{max_retries} in {delay}s...")
                    time.sleep(delay)
                    # Reset progress for retry
                    item.files_completed = 0
                    item.files_failed = 0

                result = self.runner.run(
                    url=item.url,
                    platform=item.platform.lower(),
                    output_dir=item.output_dir,
                    date_from=item.date_min,
                    date_to=item.date_max,
                    verbose=True,
                    app_tokens=app_tokens,
                    folder_pattern=item.folder_pattern,
                    file_pattern=item.file_pattern,
                    post_ids=item.post_ids,
                    post_id_field=item.post_id_field,
                    progress_callback=output_callback,
                    process_callback=process_callback,
                    rate_limit=rate_limit,
                    sleep_request=sleep_request,
                    download_retries=download_retries,
                    skip_abort_threshold=skip_abort_threshold
                )

                if result["success"]:
                    # If post filter was used and 0 files processed:
                    # - Exit code 0 = gallery-dl ran fine, files likely already exist → "up to date"
                    # - Exit code != 0 = something went wrong → ask user
                    if item.post_ids and item.files_completed == 0:
                        exit_code = result.get("exit_code", 0)
                        if exit_code == 0:
                            self.item_log.emit(item_id, "")
                            self.item_log.emit(item_id, "  All files are up to date — nothing new to download.")
                        else:
                            self.item_log.emit(item_id, "")
                            self.item_log.emit(item_id, "  ⚠ Post filter matched 0 files.")
                            if self._ask_confirmation(
                                item_id,
                                "Post filter returned 0 files. Download ALL posts from this creator instead?"
                            ):
                                self.item_log.emit(item_id, "  Retrying without filter (downloading all posts)...")
                                item.post_ids = None
                                continue
                            else:
                                self.item_log.emit(item_id, "  Download cancelled by user.")
                                item.status = DownloadStatus.CANCELLED
                                self.item_status_changed.emit(item_id, item.status.value)
                                return
                    break  # Done

                # Failed — check if retryable
                if not self._is_retryable_error(str(result.get("stderr", ""))):
                    break  # Non-retryable error, don't retry

            if result is None:
                result = {"success": False, "exit_code": -1, "stdout": [], "stderr": ["Download was interrupted"]}

            # Calculate duration
            duration = datetime.now() - item.started_at
            duration_str = str(duration).split('.')[0]  # Remove microseconds

            # Check if paused or cancelled
            if item.pause_flag:
                item.status = DownloadStatus.PAUSED
                self.item_log.emit(item_id, f"\n⏸ Download PAUSED after {duration_str}")
                self.item_status_changed.emit(item_id, item.status.value)
            elif item.stop_flag:
                item.status = DownloadStatus.CANCELLED
                self.item_log.emit(item_id, f"\n✗ Download CANCELLED after {duration_str}")
                self.item_status_changed.emit(item_id, item.status.value)
            elif result["success"]:
                item.completed_at = datetime.now()

                # --- Post-download ZIP extraction ---
                try:
                    zip_extractor = ZipExtractor(self.db)
                    if zip_extractor.enabled:
                        zip_results = zip_extractor.process_download_folder(
                            folder=item.output_dir,
                            platform=item.platform,
                            app_tokens=app_tokens,
                            file_pattern=item.file_pattern
                        )
                        for zr in zip_results:
                            zres = zr['result']
                            zip_name = zr['zip_file'].name
                            if zres['success']:
                                count = len(zres['extracted_files'])
                                vids = len(zres['video_files'])
                                other = len(zres['non_video_files'])
                                self.item_log.emit(item_id, f"  📦 Extracted {zip_name}: {count} files ({vids} video, {other} other)")
                            else:
                                self.item_log.emit(item_id, f"  ⚠ Failed to extract {zip_name}: {zres['error']}")
                except Exception as e:
                    self.item_log.emit(item_id, f"  ⚠ ZIP extraction error: {e}")

                # --- Post-download verification ---
                files_str = f"{item.files_completed} files"
                if item.expected_files > 0:
                    files_str = f"{item.files_completed}/{item.expected_files}"
                    if item.files_completed >= item.expected_files:
                        item.status = DownloadStatus.COMPLETED
                    elif item.files_completed > 0:
                        item.status = DownloadStatus.PARTIAL
                        item.error_message = f"{item.expected_files - item.files_completed} file(s) may be missing"
                    else:
                        item.status = DownloadStatus.FAILED
                        item.error_message = "No files downloaded"
                elif item.errors:
                    item.status = DownloadStatus.COMPLETED
                    item.error_message = f"Completed with {len(item.errors)} error(s)"
                else:
                    item.status = DownloadStatus.COMPLETED

                # Log completion to App Log
                self.item_log.emit(item_id, "")
                self.item_log.emit(item_id, f"{'=' * 55}")
                if item.status == DownloadStatus.COMPLETED:
                    self.item_log.emit(item_id, f"  ✓ DOWNLOAD COMPLETE")
                elif item.status == DownloadStatus.PARTIAL:
                    self.item_log.emit(item_id, f"  ⚠ DOWNLOAD PARTIAL")
                else:
                    self.item_log.emit(item_id, f"  ✗ DOWNLOAD FAILED")
                self.item_log.emit(item_id, f"  Creator: {creator_str}")
                self.item_log.emit(item_id, f"  Files: {files_str}")
                if item.files_failed > 0:
                    self.item_log.emit(item_id, f"  Failed: {item.files_failed}")
                self.item_log.emit(item_id, f"  Duration: {duration_str}")
                self.item_log.emit(item_id, f"  Saved to: {item.output_dir}")

                # Verification summary
                if item.expected_files > 0:
                    self.item_log.emit(item_id, "")
                    if item.files_completed >= item.expected_files:
                        self.item_log.emit(item_id, f"  VERIFICATION: {item.files_completed}/{item.expected_files} files — all accounted for")
                    else:
                        missing = item.expected_files - item.files_completed
                        self.item_log.emit(item_id, f"  VERIFICATION: {item.files_completed}/{item.expected_files} files — {missing} missing")
                        self.item_log.emit(item_id, f"  Check locked/subscriber-only posts or retry")

                # Show actionable exit code diagnostics if non-zero
                for level, msg in result.get("exit_messages", []):
                    self.item_log.emit(item_id, f"  → {msg}")

                # Failure report with post titles
                if item.errors:
                    self.item_log.emit(item_id, "")
                    self.item_log.emit(item_id, f"  ERRORS ({len(item.errors)}):")
                    for idx, err in enumerate(item.errors, 1):
                        # Try to find post title from error context
                        err_detail = err.message.strip()
                        # Extract post ID from error line if present
                        post_title_str = ""
                        for pid, ptitle in item.post_titles.items():
                            if pid in err.file or pid in err_detail:
                                post_title_str = f" 「{ptitle}」"
                                break
                        self.item_log.emit(item_id, f"  [{idx}] {err_detail}{post_title_str}")

                self.item_log.emit(item_id, f"{'=' * 55}")

                if item.status == DownloadStatus.COMPLETED:
                    self.item_completed.emit(item_id)
                elif item.status == DownloadStatus.PARTIAL:
                    self.item_status_changed.emit(item_id, item.status.value)
                    self.item_completed.emit(item_id)
                else:
                    self.item_failed.emit(item_id, item.error_message)

                self._save_to_history(item)

            else:
                # Failed entirely
                error_lines = result.get("stderr", [])
                error_msg = "\n".join(error_lines) if isinstance(error_lines, list) else str(error_lines)
                if not error_msg or error_msg == "[]":
                    error_msg = "Unknown error (check log for details)"
                item.status = DownloadStatus.FAILED
                item.error_message = error_msg

                item.errors.append(DownloadError(
                    file=item.current_file or "Unknown",
                    message=error_msg,
                    timestamp=datetime.now(),
                    retryable=self._is_retryable_error(error_msg)
                ))

                self.item_log.emit(item_id, "")
                self.item_log.emit(item_id, f"✗ DOWNLOAD FAILED: {error_msg}")

                # Show actionable exit code diagnostics
                for level, msg in result.get("exit_messages", []):
                    self.item_log.emit(item_id, f"  → {msg}")

                self.item_failed.emit(item_id, item.error_message)
                self._save_failed(item)

        except Exception as e:
            error_msg = str(e)
            item.status = DownloadStatus.FAILED
            item.error_message = error_msg

            item.errors.append(DownloadError(
                file=item.current_file or "Unknown",
                message=error_msg,
                timestamp=datetime.now(),
                retryable=self._is_retryable_error(error_msg)
            ))

            self.item_log.emit(item_id, f"✗ ERROR: {error_msg}")
            self.item_failed.emit(item_id, error_msg)
            self._save_failed(item)

        finally:
            self.active_downloads -= 1
            self._decrement_platform_worker(item.platform)

    def _parse_progress(self, item_id: str, line: str):
        """Parse gallery-dl output for progress information"""
        item = self.items[item_id]

        # Skip debug/info lines — they're not file downloads
        if "[debug]" in line or "[info]" in line:
            return

        # --- Structured --print output (preferred, unambiguous) ---
        if line.startswith("[DOWNLOADED]"):
            import os
            filepath = line[12:].strip()  # len("[DOWNLOADED]") == 12
            filename = os.path.basename(filepath)
            item.files_completed += 1
            item.current_file = filename
            speed_str = f"  ({item.current_speed})" if item.current_speed else ""
            self.item_log.emit(item_id, f"  [{item.files_completed}] {filename}{speed_str}")
        elif line.startswith("[SKIPPED]"):
            item.files_completed += 1
            self.item_log.emit(item_id, f"  [{item.files_completed}] (skipped - already exists)")

        # --- Fallback: legacy heuristic parsing for older gallery-dl versions ---
        else:
            # Detect saved file — gallery-dl outputs the full file path when a file is saved
            is_file_path = (
                (len(line) > 3 and line[1] == ':' and line[2] == '\\') or  # Windows: C:\...
                line.startswith('/')  # Unix: /home/...
            )

            if is_file_path:
                import os
                filepath = line.strip()
                filename = os.path.basename(filepath)
                item.files_completed += 1
                item.current_file = filename
                speed_str = f"  ({item.current_speed})" if item.current_speed else ""
                self.item_log.emit(item_id, f"  [{item.files_completed}] {filename}{speed_str}")

            elif "skipping" in line.lower() or ("already exists" in line.lower()):
                item.files_completed += 1
                self.item_log.emit(item_id, f"  [{item.files_completed}] (skipped - already exists)")

        # Detect errors
        if "[error]" in line.lower():
            item.files_failed += 1
            self.item_log.emit(item_id, f"  ✗ ERROR: {line}")
            item.errors.append(DownloadError(
                file=item.current_file or line.strip(),
                message=line.strip(),
                timestamp=datetime.now(),
                retryable=self._is_retryable_error(line)
            ))

        # Detect warnings (for catchable/uncatchable content)
        if "[warning]" in line.lower() and "unable to download" in line.lower():
            # Extract post ID from warning URL if possible
            import re as re_mod
            post_match = re_mod.search(r'/posts/(\d+)', line)
            post_id = post_match.group(1) if post_match else ""
            # Suppress warning if this post wasn't in the user's selection —
            # gallery-dl walks the whole profile to apply --filter, so it
            # encounters (and warns about) locked posts the user didn't select
            if item.post_ids and post_id and post_id not in item.post_ids:
                pass
            else:
                post_title = item.post_titles.get(post_id, "")
                title_str = f" 「{post_title}」" if post_title else ""
                self.item_log.emit(item_id, f"  ⚠ Locked content: Post {post_id}{title_str}")

        # Parse download speed and ETA (if gallery-dl shows progress bars)
        speed_match = re.search(r'(\d+\.?\d*\s?[KMG]?B/s)', line)
        if speed_match:
            item.current_speed = speed_match.group(1)

        eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
        if eta_match:
            item.eta = eta_match.group(1)

        # Emit progress update
        progress = {
            "current_file": item.current_file,
            "files_completed": item.files_completed,
            "files_total": item.files_total,
            "speed": item.current_speed,
            "eta": item.eta
        }
        self.item_progress_updated.emit(item_id, progress)

    def pause_download(self, item_id: str):
        """Pause a download"""
        if item_id in self.items:
            item = self.items[item_id]
            if item.status == DownloadStatus.DOWNLOADING:
                item.pause_flag = True
                _graceful_kill(item.process)

    def resume_download(self, item_id: str):
        """Resume a paused download"""
        if item_id in self.items:
            item = self.items[item_id]
            if item.status == DownloadStatus.PAUSED:
                item.pause_flag = False
                item.stop_flag = False
                # Re-add to queue
                with self.queue_lock:
                    self.queue.put(item_id)

    def cancel_download(self, item_id: str):
        """Cancel a download"""
        if item_id in self.items:
            item = self.items[item_id]
            item.stop_flag = True
            _graceful_kill(item.process)
            item.status = DownloadStatus.CANCELLED
            self.item_status_changed.emit(item_id, item.status.value)

    def retry_download(self, item_id: str):
        """Retry a failed download"""
        if item_id in self.items:
            item = self.items[item_id]
            if item.status in [DownloadStatus.FAILED, DownloadStatus.CANCELLED, DownloadStatus.PARTIAL]:
                # Reset state
                item.status = DownloadStatus.PENDING
                item.stop_flag = False
                item.pause_flag = False
                item.error_message = ""
                item.files_completed = 0
                item.current_file = ""
                item.errors = []  # Clear error history

                # Re-add to queue
                with self.queue_lock:
                    self.queue.put(item_id)

                self.item_status_changed.emit(item_id, item.status.value)

    def retry_failed_files(self, item_id: str):
        """
        Retry only the failed files from a download

        Args:
            item_id: Download item ID
        """
        if item_id not in self.items:
            return

        item = self.items[item_id]

        # Get retryable errors
        retryable_errors = [error for error in item.errors if error.retryable]

        if not retryable_errors:
            return

        # Create new download item with only failed files
        new_id = f"{item.creator_name}_{item.platform}_retry_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        retry_item = DownloadItem(
            id=new_id,
            url=item.url,
            output_dir=item.output_dir,
            creator_name=item.creator_name,
            platform=item.platform,
            creator_platform_id=item.creator_platform_id,
            date_min=item.date_min,
            date_max=item.date_max,
            # Note: selected_files would need to be populated with failed file URLs
            # This is a simplified version
        )

        with self.queue_lock:
            self.items[new_id] = retry_item
            self.queue.put(new_id)

        self.item_added.emit(new_id)

    def get_retryable_errors(self, item_id: str) -> List[DownloadError]:
        """
        Get retryable errors for a download item

        Args:
            item_id: Download item ID

        Returns:
            List of retryable errors
        """
        if item_id in self.items:
            return [error for error in self.items[item_id].errors if error.retryable]
        return []

    def get_item(self, item_id: str) -> Optional[DownloadItem]:
        """Get download item by ID"""
        return self.items.get(item_id)

    def get_all_items(self) -> List[DownloadItem]:
        """Get all download items"""
        return list(self.items.values())

    def get_pending_count(self) -> int:
        """Get count of pending downloads"""
        return sum(1 for item in self.items.values()
                  if item.status == DownloadStatus.PENDING)

    def get_platform_worker_status(self) -> Dict[str, Dict[str, int]]:
        """
        Get worker status for all platforms

        Returns:
            Dict with platform worker info:
            {
                'fanbox': {'active': 1, 'limit': 1},
                'patreon': {'active': 0, 'limit': 2},
                ...
            }
        """
        with self.worker_lock:
            status = {}
            for platform, limit in self.PLATFORM_WORKERS.items():
                active = self.active_workers.get(platform, 0)
                status[platform] = {
                    'active': active,
                    'limit': limit,
                    'available': limit - active
                }
            return status

    def pause_all(self):
        """Pause all active downloads"""
        for item in self.items.values():
            if item.status == DownloadStatus.DOWNLOADING:
                self.pause_download(item.id)

    def cancel_all(self):
        """Cancel all active and pending downloads"""
        for item in self.items.values():
            if item.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PENDING, DownloadStatus.PAUSED]:
                self.cancel_download(item.id)

    def clear_completed(self):
        """Remove completed items from queue"""
        to_remove = [
            item_id for item_id, item in self.items.items()
            if item.status == DownloadStatus.COMPLETED
        ]

        for item_id in to_remove:
            del self.items[item_id]

    def _save_to_history(self, item: DownloadItem):
        """Save successful download to history"""
        if item.creator_platform_id:
            self.db.add_download_history(
                creator_platform_id=item.creator_platform_id,
                files_downloaded=item.files_completed,
                files_skipped=0,
                files_failed=item.files_failed,
                date_from=item.date_min,
                date_to=item.date_max
            )

            # Update last downloaded date
            self.db.update_creator_platform(
                platform_id=item.creator_platform_id,
                last_downloaded_date=datetime.now().strftime("%Y-%m-%d")
            )

    def _save_failed(self, item: DownloadItem):
        """Save failed download to database"""
        if item.creator_platform_id:
            self.db.add_failed_download(
                creator_platform_id=item.creator_platform_id,
                file_url=item.url,
                filename=item.current_file or "Unknown",
                error_message=item.error_message
            )
