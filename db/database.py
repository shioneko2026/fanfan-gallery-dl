"""
SQLite database manager
"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "Credentials and User Data" / "appdata.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = None
        self.initialize()

    def initialize(self):
        """Initialize database connection and create tables if needed"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Create all required tables"""
        cursor = self.conn.cursor()

        # Creators table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                romaji_name TEXT,
                japanese_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Platform profiles per creator
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_platforms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER REFERENCES creators(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                profile_url TEXT NOT NULL,
                local_folder TEXT,
                last_downloaded_date TEXT,
                folder_name_override TEXT,
                file_name_override TEXT,
                UNIQUE(creator_id, platform)
            )
        """)

        # Download history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_platform_id INTEGER REFERENCES creator_platforms(id) ON DELETE CASCADE,
                session_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                files_downloaded INTEGER DEFAULT 0,
                files_skipped INTEGER DEFAULT 0,
                files_failed INTEGER DEFAULT 0,
                date_from_filter TEXT,
                date_to_filter TEXT
            )
        """)

        # Failed files for resume
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_platform_id INTEGER REFERENCES creator_platforms(id) ON DELETE CASCADE,
                file_url TEXT,
                filename TEXT,
                post_id TEXT,
                post_date TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # App settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Scan history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL,
                post_count INTEGER DEFAULT 0,
                file_count INTEGER DEFAULT 0,
                scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Naming presets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS naming_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                folder_pattern TEXT NOT NULL,
                file_pattern TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()
        self._migrate_artist_to_creator()
        self._initialize_default_settings()
        self._initialize_default_presets()

    def _migrate_artist_to_creator(self):
        """Migrate old 'artists'/'artist_platforms' tables to 'creators'/'creator_platforms' naming"""
        try:
            cursor = self.conn.cursor()
            old_table = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='artists'"
            ).fetchone()
            if old_table:
                cursor.execute("ALTER TABLE artists RENAME TO creators")
                cursor.execute("ALTER TABLE artist_platforms RENAME TO creator_platforms")
                cursor.execute("ALTER TABLE creator_platforms RENAME COLUMN artist_id TO creator_id")
                cursor.execute("ALTER TABLE download_history RENAME COLUMN artist_platform_id TO creator_platform_id")
                cursor.execute("ALTER TABLE failed_downloads RENAME COLUMN artist_platform_id TO creator_platform_id")
                self.conn.commit()
        except Exception:
            # Safe to ignore — migration already applied or not needed
            pass

    def _initialize_default_settings(self):
        """Set default settings if not already set"""
        defaults = {
            "folder_pattern": "{artist} [{date_latest}] [{source}]",
            "file_pattern": "{artist} [{date}] {title} [{source}].{ext}",
            "date_format": "YYYY-MM-DD",
            "conflict_action": "append_number",
            "concurrent_downloads": "2",
            "auto_notify_updates": "true",
            "default_save_folder": ""
        }

        cursor = self.conn.cursor()
        for key, value in defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        self.conn.commit()

    def _initialize_default_presets(self):
        """Seed the Universal Standard preset if not present, and migrate old tokens"""
        cursor = self.conn.cursor()

        us_folder = "{creator_name} {creator_jp} [{today}] [{category}]/{creator_name} {creator_jp} [{date:%Y-%m-%d}] {post_title} [P{post_id}] [{category}]"
        us_file = "{creator_name} {creator_jp} [{date:%Y-%m-%d}] {filename} [P{post_id}] [{category}].{extension}"

        existing = cursor.execute(
            "SELECT id, folder_pattern FROM naming_presets WHERE is_default = 1"
        ).fetchone()

        if not existing:
            cursor.execute(
                """INSERT INTO naming_presets (name, folder_pattern, file_pattern, is_default)
                   VALUES (?, ?, ?, 1)""",
                ("Universal Standard", us_folder, us_file)
            )
        elif existing and "{artist_" in (existing[1] or ""):
            # Migrate old {artist_*} tokens to {creator_*}
            cursor.execute(
                "UPDATE naming_presets SET folder_pattern = ?, file_pattern = ? WHERE id = ?",
                (us_folder, us_file, existing[0])
            )

        # Also migrate settings table patterns
        for key in ("folder_pattern", "file_pattern"):
            val = cursor.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if val and "{artist_" in (val[0] or ""):
                new_val = val[0].replace("{artist_name}", "{creator_name}").replace("{artist_jp}", "{creator_jp}").replace("{artist_romaji}", "{creator_romaji}")
                cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, key))

        self.conn.commit()

    # --- Preset CRUD ---

    def get_all_presets(self):
        """Get all naming presets, default first then alphabetical"""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM naming_presets ORDER BY is_default DESC, name ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_preset(self, preset_id):
        """Get a single preset by ID"""
        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT * FROM naming_presets WHERE id = ?", (preset_id,)
        ).fetchone()
        return dict(row) if row else None

    def add_preset(self, name, folder_pattern, file_pattern):
        """Add a new naming preset. Returns new ID or raises on duplicate."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO naming_presets (name, folder_pattern, file_pattern)
               VALUES (?, ?, ?)""",
            (name, folder_pattern, file_pattern)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_preset(self, preset_id, name=None, folder_pattern=None, file_pattern=None):
        """Update a preset. Cannot modify the default preset."""
        preset = self.get_preset(preset_id)
        if not preset or preset.get('is_default', 0) == 1:
            return False
        updates, values = [], []
        if name is not None:
            updates.append("name = ?")
            values.append(name)
        if folder_pattern is not None:
            updates.append("folder_pattern = ?")
            values.append(folder_pattern)
        if file_pattern is not None:
            updates.append("file_pattern = ?")
            values.append(file_pattern)
        if not updates:
            return False
        values.append(preset_id)
        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE naming_presets SET {', '.join(updates)} WHERE id = ?", values
        )
        self.conn.commit()
        return True

    def delete_preset(self, preset_id):
        """Delete a preset. Cannot delete the default preset."""
        preset = self.get_preset(preset_id)
        if not preset or preset.get('is_default', 0) == 1:
            return False
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM naming_presets WHERE id = ?", (preset_id,))
        self.conn.commit()
        return True

    # --- Scan History ---

    def add_scan_record(self, creator_name, platform, url, post_count=0, file_count=0):
        """Record a scan event"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO scan_history (creator_name, platform, url, post_count, file_count)
               VALUES (?, ?, ?, ?, ?)""",
            (creator_name, platform, url, post_count, file_count)
        )
        self.conn.commit()

    def get_recent_scans(self, limit=10):
        """Get recent scan history"""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            "SELECT * FROM scan_history ORDER BY scanned_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_setting(self, key, default=None):
        """Get a setting value"""
        cursor = self.conn.cursor()
        result = cursor.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return result[0] if result else default

    def set_setting(self, key, value):
        """Set a setting value"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def add_creator(self, display_name, romaji_name=None, japanese_name=None):
        """Add a new creator"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO creators (display_name, romaji_name, japanese_name)
               VALUES (?, ?, ?)""",
            (display_name, romaji_name, japanese_name)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_creator(self, creator_id, display_name, romaji_name=None, japanese_name=None):
        """Update a creator"""
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE creators
               SET display_name = ?, romaji_name = ?, japanese_name = ?
               WHERE id = ?""",
            (display_name, romaji_name, japanese_name, creator_id)
        )
        self.conn.commit()

    def delete_creator(self, creator_id):
        """Delete a creator and all associated data"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM creators WHERE id = ?", (creator_id,))
        self.conn.commit()

    def get_all_creators(self):
        """Get all creators with their platform data"""
        cursor = self.conn.cursor()
        return cursor.execute("""
            SELECT c.*,
                   GROUP_CONCAT(cp.platform) as platforms,
                   MAX(cp.last_downloaded_date) as last_download
            FROM creators c
            LEFT JOIN creator_platforms cp ON c.id = cp.creator_id
            GROUP BY c.id
            ORDER BY c.display_name
        """).fetchall()

    def get_creator(self, creator_id):
        """Get a single creator"""
        cursor = self.conn.cursor()
        return cursor.execute(
            "SELECT * FROM creators WHERE id = ?", (creator_id,)
        ).fetchone()

    def add_creator_platform(self, creator_id, platform, profile_url, local_folder=None):
        """Add a platform profile for a creator"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO creator_platforms
               (creator_id, platform, profile_url, local_folder)
               VALUES (?, ?, ?, ?)""",
            (creator_id, platform, profile_url, local_folder)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_creator_platform(self, platform_id, **kwargs):
        """Update creator platform fields"""
        allowed_fields = ['profile_url', 'local_folder', 'last_downloaded_date',
                         'folder_name_override', 'file_name_override']

        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return

        values.append(platform_id)
        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE creator_platforms SET {', '.join(updates)} WHERE id = ?",
            values
        )
        self.conn.commit()

    def get_creator_platforms(self, creator_id):
        """Get all platforms for a creator"""
        cursor = self.conn.cursor()
        return cursor.execute(
            "SELECT * FROM creator_platforms WHERE creator_id = ? ORDER BY platform",
            (creator_id,)
        ).fetchall()

    def get_creator_platform_by_url(self, url):
        """Find creator platform by profile URL"""
        cursor = self.conn.cursor()
        return cursor.execute(
            "SELECT * FROM creator_platforms WHERE profile_url = ?",
            (url,)
        ).fetchone()

    def add_download_history(self, creator_platform_id, files_downloaded=0,
                            files_skipped=0, files_failed=0,
                            date_from=None, date_to=None):
        """Add a download history entry"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO download_history
               (creator_platform_id, files_downloaded, files_skipped, files_failed,
                date_from_filter, date_to_filter)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (creator_platform_id, files_downloaded, files_skipped, files_failed,
             date_from, date_to)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_downloads(self, limit=10):
        """Get recent download history"""
        cursor = self.conn.cursor()
        return cursor.execute(
            """SELECT dh.*, c.display_name, cp.platform
               FROM download_history dh
               JOIN creator_platforms cp ON dh.creator_platform_id = cp.id
               JOIN creators c ON cp.creator_id = c.id
               ORDER BY dh.session_date DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()

    def add_failed_download(self, creator_platform_id, file_url, filename,
                           post_id=None, post_date=None, error_message=None):
        """Add a failed download entry"""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO failed_downloads
               (creator_platform_id, file_url, filename, post_id, post_date, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (creator_platform_id, file_url, filename, post_id, post_date, error_message)
        )
        self.conn.commit()

    def get_failed_downloads(self, creator_platform_id=None):
        """Get failed downloads, optionally filtered by creator platform"""
        cursor = self.conn.cursor()
        if creator_platform_id:
            return cursor.execute(
                "SELECT * FROM failed_downloads WHERE creator_platform_id = ?",
                (creator_platform_id,)
            ).fetchall()
        else:
            return cursor.execute("SELECT * FROM failed_downloads").fetchall()

    def clear_failed_download(self, failed_id):
        """Remove a failed download entry"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM failed_downloads WHERE id = ?", (failed_id,))
        self.conn.commit()

    def export_database(self, export_path):
        """Export database to a file"""
        import shutil
        self.conn.close()
        shutil.copy2(self.db_path, export_path)
        self.initialize()

    def import_database(self, import_path):
        """Import database from a file"""
        import shutil
        self.conn.close()
        shutil.copy2(import_path, self.db_path)
        self.initialize()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
