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

**Pick exactly what you want.** Check the posts you want, uncheck the rest. Filter by date, search by name, sort by tier. Download only what you selected.

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
| Patreon | Coming soon |
| SubscribeStar | Coming soon |

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
- Scan creator pages and preview every post in a checklist tree
- Select individual posts and files — no more all-or-nothing
- Date range filters, name search, Post ID search, tier sorting
- Color-coded posts: green = paid (accessible), orange = locked, black = free
- Fantia mixed-tier detection: shows `[FREE + 300JPY LOCKED]` for posts with both free and paid content

### Cross-Check (Never Miss Anything Again)
- Compare scanned posts against your local files
- Instantly see what's missing, present, or locked
- Download only the gaps with one click
- Works by matching `[P{post_id}]` in filenames — powered by Universal Standard naming

### Universal Standard Naming
- Every file named consistently: `Creator [Date] Title [PostID] [Platform].ext`
- Folders organized chronologically
- Post IDs embedded for traceability and cross-checking
- Community compatible — when everyone uses the same pattern, collections are interoperable

### Smart Organization
- Naming presets — save and switch between naming patterns
- ZIP auto-extraction with naming pattern applied to extracted files
- Category capitalization (`[Fanbox]` not `[fanbox]`)
- Per-creator download folders

### Cookie Authentication
- Step-by-step cookie guides for every platform
- Uses the Cookie-Editor browser extension (free, trusted)
- Cookies stored securely in Windows Credential Manager
- Per-platform test connection to verify setup

### Quality of Life
- Dashboard with creator stats, cookie health, and recent scans
- Creator management with multi-platform profiles
- Notification beeps with volume and pitch control
- Dual log panel (App Log + Raw Output) for transparency

---

## Why Universal Standard Matters

This is not just a naming convention. It's a system.

When your files are named `RIM しろサカナ [2026-02-24] PostTitle [P11458849] [Fanbox].mp4`, you get:

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
