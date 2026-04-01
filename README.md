# FanFan Gallery-DL

**Stop losing content. Stop re-downloading everything. Stop guessing what you're missing.**

FanFan Gallery-DL is a desktop app that gives you full control over your Fanbox and Fantia downloads — scan, select, download, and verify, all from one interface.

Built on [gallery-dl](https://github.com/mikf/gallery-dl). Designed for people who actually care about their collections.

---

## The Problem

You subscribe to creators on Fanbox and Fantia. You download their content. But then:

- You can't remember what you already have
- You accidentally re-download files you already saved
- A creator posts 50 things and you only want 3 — but the tools download everything or nothing
- You delete some files, and now you've lost track of what's missing
- Your folders are a mess of random filenames that mean nothing

Sound familiar?

## The Solution

FanFan Gallery-DL fixes all of this.

**Scan before you download.** See every post a creator has made — with titles, dates, prices, and file counts — before downloading a single byte.

**Pick exactly what you want.** Check the posts you want, uncheck the rest. Filter by date, search by name, sort by tier or file count. Download only what you selected.

**Cross-Check what you have.** The killer feature: scan a creator, point to your download folder, and instantly see what's missing, what's present, and what's locked behind a paywall. Then download only the gaps.

**Universal Standard naming.** Every file you download gets a consistent, predictable name with the creator, date, title, and post ID baked in. This means:
- Your file explorer sorts everything chronologically, automatically
- You can trace any file back to its original post
- You'll never have duplicate files again
- And when the community adopts the same standard, comparing and sharing collections becomes effortless

---

## Supported Platforms

| Platform | Status |
|----------|--------|
| Pixiv Fanbox | Tested |
| Fantia | Tested |
| Patreon | Planned |
| SubscribeStar | Planned |

---

## Quick Start

1. Install [Python 3.9+](https://www.python.org/downloads/) — **check "Add to PATH"** during install
2. Double-click `Install Dependencies for FanFan Gallery-DL.bat`
3. Double-click `START FanFan Gallery-DL.bat`

Gallery-dl is auto-downloaded on first launch. No manual setup.

See `How to Install and Run.txt` for a detailed walkthrough.

---

## Features

### Download with Precision
- Scan creator pages and preview every post in a flat table with file counts
- Select posts by checkbox — expand any post to see its file list (videos, images, archives)
- Date range filters, name search, Post ID search, sort by date/title/tier/file count
- "Deselect image-only posts" toggle for video-focused downloading
- Color-coded posts: green = paid (accessible), orange = locked, black = free
- Locked/paid posts are still selectable if you're subscribed — the app won't block you

### Cross-Check (Never Miss Anything Again)
- Compare scanned posts against your local files
- Instantly see what's missing, present, or locked
- Download only the gaps with one click
- Works by matching `[P{post_id}]` in filenames — powered by Universal Standard naming

### Universal Standard Naming
- Every file named consistently: `Creator [Date] PostTitle Filename [PostID] [Platform].ext`
- Folders organized chronologically
- Post IDs embedded for traceability and cross-checking
- Community compatible — when everyone uses the same pattern, collections are interoperable

### Smart Organization
- Naming presets — save and switch between naming patterns
- ZIP auto-extraction with naming pattern applied to extracted files
- Per-creator download folders and per-post folder organization
- Default save folder auto-applied when adding new creators

### Cookie Authentication
- Step-by-step cookie guides for every platform
- Uses the Cookie-Editor browser extension (free, trusted)
- Cookies stored securely in Windows Credential Manager
- Per-platform test connection to verify setup

### Quality of Life
- Dashboard with creator stats, cookie health, and recent scans
- Creator management with multi-platform profiles
- **General settings** — notification sounds
- **Downloader settings** — default save folder, concurrent downloads, per-platform rate limit / sleep / retry controls
- Dual log panel (App Log + Raw Output) — App Log shows filenames and download speed as files complete
- Single download queue item per scan — one progress bar, accurate tracking
- Abort a download and re-download immediately from the same scan results — no rescan needed

---

## Known Limitations

These are constraints of gallery-dl (the download engine), not bugs in FanFan:

| Limitation | Details |
|-----------|---------|
| **No per-file filtering** | Gallery-dl downloads entire posts. You can select/deselect posts, but not individual files within a post. The file list under each post is for preview only. |
| **No file size info before download** | Gallery-dl's scan mode returns filenames and metadata but not file sizes. Size is only known after downloading. |
| **Downloads are slow by default — this is intentional** | Gallery-dl enforces sleep delays between requests to avoid getting your account flagged or rate-limited by the platform. Out of the box, Fanbox and Fantia use a 1.0s delay between files. A large post with 50 files will take ~50 seconds minimum. You can reduce this in Settings → Downloader, but do so at your own risk. |
| **Downloader performance settings are untested** | The per-platform rate limit, sleep, and retry controls in Settings → Downloader are new and have not been extensively tested. Use the defaults until you know what you're doing. |
| **One platform at a time** | Each scan/download targets one creator URL. Batch multi-creator downloads are planned but not yet implemented. |
| **Windows only** | Uses Windows Credential Manager for secure cookie storage and `winsound` for notifications. |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

---

## Why Universal Standard Matters

This is not just a naming convention. It's a system.

When your files are named `Whitefish しろサカナ [2026-02-24] PostTitle filename [P11458849] [Fanbox].mp4`, you get:

1. **Self-describing files** — move them anywhere and they still tell you everything
2. **Chronological sorting** — your OS sorts them by date automatically
3. **Cross-checking** — the app can match post IDs to find what's missing
4. **No duplicates** — identical content produces identical filenames
5. **Community compatibility** — share files with others and they slot right in

The more people who use Universal Standard, the more powerful it becomes.

---

## Requirements

- Python 3.9+
- Windows 10/11
- Active cookies/subscription for target platforms

---

## Credits

**Built on [gallery-dl](https://github.com/mikf/gallery-dl)** by mikf — the powerful download engine that handles all authentication and downloading. FanFan Gallery-DL is a GUI wrapper around gallery-dl. It would not exist without it.

**Inspired by [Cultured Downloader](https://github.com/KJHJason/Cultured-Downloader)** by KJHJason — the UI design and download workflow were inspired by this project.

---

## License

[MIT](LICENSE)
