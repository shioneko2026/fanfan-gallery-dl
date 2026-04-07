> For the user-facing README, see [README.md](README.md).

# FanFan Gallery-DL — Developer Reference

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.9+ |
| GUI | PyQt6 |
| Database | SQLite (`sqlite3` stdlib — no ORM) |
| Credential storage | `keyring` → Windows Credential Manager |
| Japanese transliteration | `pykakasi` |
| Download engine | `gallery-dl.exe` — always run as subprocess, never imported |
| Safe deletion | `send2trash` |

`gallery-dl.exe` is not bundled. It auto-downloads into `bin/` on first launch via the update check in `gallery_dl_manager.py`.

---

## Project structure

```
main.py                              # Entry point — boots QApplication, shows MainWindow
requirements.txt
START FanFan Gallery-DL.bat
Install Dependencies for FanFan Gallery-DL.bat

ui/
  main_window.py                     # Root window: sidebar nav, log panel, page stacking
  downloads.py                       # Downloader tab — scan initiation + post selection UI
  artists.py                         # Creators tab — creator CRUD, platform cards
  crosscheck.py                      # Cross-Check tab
  dashboard.py                       # Dashboard — stats, cookie status, recent scans
  download_queue_page.py             # Download Queue tab — live progress widgets
  log_viewer.py                      # Dual-tab log widget (App Log + Raw Output)
  settings/
    general.py                       # Notification sounds
    downloader.py                    # Save folder, concurrency, per-platform rate settings
    naming.py                        # Naming preset editor
    credentials.py                   # Cookie input + test connection UI
    updates.py
    data.py

core/
  download_queue.py                  # DownloadQueueManager + DownloadItem dataclass
  gallery_dl_runner.py               # CLI command builder + subprocess executor
  gallery_dl_thread.py               # QThread wrapper for scan (--dump-json) runs
  credential_manager_simple.py       # Keyring read/write for per-platform cookies
  zip_extractor.py                   # Post-download ZIP extraction (experimental)
  gallery_dl_manager.py              # gallery-dl binary download/update check
  logger.py                          # Logging helpers

db/
  database.py                        # All SQLite schema definitions + queries

bin/                                 # gallery-dl.exe lives here (auto-downloaded)
config/                              # gallery-dl config files
Credentials and User Data/           # appdata.db + exported data
Screenshots/                         # Screenshots used in README.md
```

---

## How to run from source

```bash
# Clone and enter the repo
git clone https://github.com/shioneko2026/fanfan-gallery-dl.git
cd fanfan-gallery-dl

# Install dependencies
pip install PyQt6 pykakasi keyring send2trash

# Run
python main.py
```

gallery-dl.exe downloads itself into `bin/` on first launch.

---

## Architecture

### gallery-dl is always a subprocess

The app never imports gallery-dl as a Python module. All interaction goes through CLI flags. `GalleryDLRunner.build_command()` assembles the command; `GalleryDLRunner.run()` spawns it via `subprocess.Popen` and reads stdout line by line.

### Scan vs Download

| Mode | gallery-dl flags | Output handling |
|------|-----------------|-----------------|
| Scan | `--simulate --dump-json` | JSON array accumulated, parsed in `on_finished` after process exits |
| Download | `--verbose` | stdout lines parsed in real-time by `_parse_progress()` |

Scan output is parsed line by line in `on_output` for live App Log feedback (type 2 entries = post metadata). The full JSON is also accumulated for the final results tree.

### Thread model

- **Scan:** `GalleryDLThread(QThread)` — one thread per scan. Abort via `scan_thread.abort()` which calls `process.kill()` on the captured subprocess reference.
- **Downloads:** `DownloadQueueManager` spawns `threading.Thread` per download item (not QThread). Max concurrent controlled by `max_concurrent` (default: 2). Fanbox and Pixiv are hard-capped at 1 concurrent worker regardless of settings — API rate limit protection.

### Token resolution: app tokens vs gallery-dl tokens

Naming patterns contain two kinds of tokens:

- **App tokens** (`{creator_name}`, `{creator_jp}`, `{today}`) — resolved by the app before the command is built. Substituted as literal strings in the pattern. If the value is empty, the placeholder is replaced with `""` and double spaces are collapsed.
- **gallery-dl tokens** (`{title}`, `{date}`, `{filename}`, `{extension}`, `{category}`) — passed through as-is. gallery-dl resolves them from post metadata at download time.

**Platform substitutions** applied in `build_command()` before passing to gallery-dl:
- Fanbox/Pixiv: `{post_title}` → `{title}`, `{post_id}` → `{id}` (Fanbox uses different field names)
- Fantia: no substitution needed — natively has `{post_title}` and `{post_id}`

### Flat folder mode

`folder_pattern = ""` (empty string) → `cmd.extend(["-o", "directory=[]"])` → gallery-dl puts files flat in the output dir.

`folder_pattern = None` → default fallback pattern is applied.

**These are not the same.** The runner checks `if folder_pattern is None:` — not `if not folder_pattern:`. Empty string is a valid, intentional value meaning "no subdirectories". This distinction bit us once (files landing in `Fantia\None\None None\`).

### Selective download (post ID filter)

When specific posts are selected, the download uses the creator profile URL with a gallery-dl `--filter` expression:

```
--filter "str(post_id) in ('3985740', '3901234')"
```

Gallery-dl still walks the entire creator profile to evaluate the filter. Individual post URLs are not used because Fanbox returns 403 on direct post URLs. Side effect: gallery-dl reports locked-content warnings for every locked post it encounters, not just the selected ones. The app suppresses warnings for post IDs outside the selection.

### Cookie flow

Cookies are stored in Windows Credential Manager via `keyring` (service name: `"GalleryDL-GUI"`, username: platform key). Before each gallery-dl invocation, cookies are written to a temp file in Netscape format and passed via `--cookies`. The temp file is deleted in a `finally` block.

---

## Database schema

Single SQLite file: `Credentials and User Data/appdata.db`. Schema is created and migrated on every launch.

| Table | Purpose |
|-------|---------|
| `creators` | Creator entries (display name, romaji, Japanese name) |
| `creator_platforms` | Per-platform URLs and folders, linked to creators |
| `settings` | Key-value store for all app settings |
| `naming_presets` | Saved folder/file pattern presets; one marked `is_default = 1` |
| `scan_history` | Log of past scans (creator, platform, post/file counts) |
| `download_history` | Per-session download results linked to creator_platforms |
| `failed_downloads` | Individual failed files for potential retry |

**Migration pattern:** Each launch checks for schema or data conditions and applies `ALTER TABLE` / `UPDATE` as needed. Migrations are safe to re-run (idempotent). Currently migrated: `artists` → `creators` rename, `{artist_*}` token upgrade, `{post_title}` addition, `{post_title} - {filename}` dash separator.

---

## Settings keys (selected)

All stored in the `settings` table as `key / value` text pairs.

| Key | Default | Notes |
|-----|---------|-------|
| `default_save_folder` | `""` | Base download directory |
| `concurrent_downloads` | `"2"` | Max parallel downloads (platform caps may override) |
| `{platform}_rate_limit` | `""` | Blank = unlimited per-file bandwidth |
| `{platform}_sleep_request` | `"1.0"` / `"0.5"` | Seconds between requests — main rate-limit protection |
| `{platform}_retries` | `"4"` | gallery-dl `--retries` value |
| `beep_enabled` | `"true"` | Notification sound on scan/download complete |
| `beep_frequency` | `"800"` | Hz |
| `_flat_download` | `"false"` | Transient — set per download, not a persistent preference |

---

## Known issues and tech debt

| Issue | Location | Notes |
|-------|----------|-------|
| Verification count wrong when locked posts skipped | `core/download_queue.py` | `expected_files` comes from the scan checklist which includes locked posts. Count says "202/202" even if 20 were skipped. |
| ZIP extraction untested | `core/zip_extractor.py` | Feature exists, not validated in production. |
| Per-platform rate settings untested end-to-end | `core/download_queue.py`, `core/gallery_dl_runner.py` | Settings save/load works; actual gallery-dl behaviour with these flags not validated. |
| `gallery_dl_manager.py` role unclear | `core/gallery_dl_manager.py` | Handles binary auto-download; may have overlap with runner. |
| No automated tests | — | All testing is manual. |

---

## Credits

- **[gallery-dl](https://github.com/mikf/gallery-dl)** by mikf — the download engine. This app is a GUI wrapper around it.
- **[Cultured Downloader](https://github.com/KJHJason/Cultured-Downloader)** by KJHJason — UI/workflow inspiration.
