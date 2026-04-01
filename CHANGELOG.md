# Changelog

## v0.8 — 2026-04-01

### Bug Fixes
- **Abort race condition** — Clicking abort while a download was starting up could leave the process running. Process is now killed immediately the moment it starts if abort was already clicked.
- **Download button stays greyed after abort** — After aborting, the Download button no longer requires a rescan to become clickable again. It re-enables automatically when the download ends (cancelled, failed, or complete).

### Features
- **New Downloader settings tab** — Replaces the download preferences that were in General. Contains: default save folder, concurrent downloads, and per-platform performance controls (rate limit, sleep between requests, retries) for Fanbox, Fantia, Pixiv, Patreon, and SubscribeStar. ⚠ These controls are new and untested — use defaults until you know what you're doing.
- **Per-platform rate controls** — Set different speed and sleep settings for each platform. Defaults are conservative (Fanbox/Fantia: 1.0s sleep, others: 0.5s) to avoid triggering rate limits. Downloads will be slow at defaults — this is intentional.
- **Speed in App Log** — Files listed in the App Log now show download speed in parentheses when gallery-dl reports it, e.g. `[1] filename.mp4  (1.2 MB/s)`.
- **General tab simplified** — Now contains only Notification Sounds. Download preferences moved to the new Downloader tab.

### Naming
- **Universal Standard file pattern updated** — Now includes `{post_title}` before `{filename}`:
  `{creator_name} {creator_jp} [{date:%Y-%m-%d}] {post_title} {filename} [P{post_id}] [{category}].{extension}`
- Existing installs auto-migrate to the new pattern on next launch.

---

## v0.7 — 2026-04-01

### Bug Fixes
- **Skip images checkbox** — was checking the wrong column (Date instead of Type), now works correctly. Renamed to "Deselect image-only posts".
- **Multiple queue items per download** — Fantia downloads no longer spawn one queue entry per post. All platforms now use a single download with post ID filtering.
- **Locked post detection on Fantia** — `catchable` content (paid, accessible) was incorrectly flagged as locked. Only `uncatchable` content is now marked as locked.
- **Locked posts not selectable** — Paid/locked posts now have checkboxes (unchecked by default) so subscribers can opt-in to download them.
- **Progress bar going past 100%** — Double-counting bug in output parsing resolved (`if` → `elif` for skip detection).
- **Fantia downloads getting 0 files** — Post ID type mismatch in gallery-dl filter (int vs string) now handled with `str()` conversion.
- **Fantia post ID field detection** — Hardcoded `post_id` for Fantia instead of auto-detecting (which could pick the wrong field).

### UI Changes
- **Flat table view** — Downloader results now show a flat table matching Cross-Check style, with expandable file lists per post.
- **Files column** — New column showing file count per post. Sortable by file count.
- **Expand All / Collapse All** button to toggle file list visibility across all posts.
- **Layout cleanup** — Select All / Deselect All / Clear buttons moved below the table. Sort dropdown moved to toolbar row.
- **Post-level selection only** — File-level checkboxes removed (gallery-dl can't filter individual files within a post). File list is display-only.
- **Selection summary** — Shows post count, file count, and type breakdown (e.g., "5/12 posts, 42 files (18 images, 12 videos)").

### Settings
- **New General tab** — Download Preferences (default folder, concurrent downloads) and Notification Sounds consolidated into one settings page.
- **Removed Sounds & Display tab** — Merged into General.
- **Auto-fill default folder** — New creators automatically get the default save folder pre-filled.

---

## v0.6 — 2026-03-26

**Integration fixes (8 issues resolved):**
- Credential management fixes
- Download queue stability
- UI consistency improvements
