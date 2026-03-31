# FanFan Gallery-DL

A PyQt6 desktop GUI for downloading media from creator subscription platforms using [gallery-dl](https://github.com/mikf/gallery-dl) as the backend.

## Supported Platforms

| Platform | Status |
|----------|--------|
| Pixiv Fanbox | Tested |
| Fantia | Tested |
| Patreon | Coming soon |
| SubscribeStar | Coming soon |

## Quick Start

1. Install [Python 3.9+](https://www.python.org/downloads/) (check "Add to PATH" during install)
2. Double-click `Install Dependencies for FanFan Gallery-DL.bat`
3. Double-click `START FanFan Gallery-DL.bat`

Gallery-dl is auto-downloaded on first launch.

## How to Use

1. **Store cookies** — Settings > Credentials, click "How to get cookies" for a step-by-step guide
2. **Add creators** — Creators tab, fill display name, Japanese name, platform URLs
3. **Scan** — Downloader tab, select a creator or paste URL, click Scan
4. **Select** — Check/uncheck posts in the tree. Color coding: green = paid accessible, orange = locked, black = free
5. **Download** — Click "Download Selected" to queue checked posts
6. **Cross-Check** — Compare scans vs downloaded files to find what's missing

## Features

- **Selective downloads** — Scan creator pages, preview posts with checklist, download only what you want
- **Cross-Check** — Compare what's online vs what's on your disk. Instantly find missing files
- **Universal Standard naming** — Consistent file naming pattern with post IDs for community compatibility
- **Color-coded tiers** — See at a glance what's free, paid, or locked (including Fantia mixed-tier posts)
- **Cookie-based auth** — Per-platform cookie guides with Cookie-Editor extension walkthrough
- **ZIP auto-extraction** — Fanbox ZIPs extracted and renamed automatically
- **Naming presets** — Save and load naming pattern combos
- **Sounds & Display** — Configurable notification beeps

## Requirements

- Python 3.9+
- Windows 10/11
- PyQt6, pykakasi, keyring, send2trash

## Why Universal Standard?

The default naming pattern embeds post IDs in filenames: `[P12345678]`. This enables:

- **Cross-checking** — instantly compare scans vs downloaded files
- **Community compatibility** — when everyone uses the same pattern, sharing and comparing collections is effortless
- **Traceability** — post IDs link directly back to the original post

Read more in the app: Naming Settings > click the `?` button on Universal Standard.

## Credits

- **Built on [gallery-dl](https://github.com/mikf/gallery-dl)** by mikf — handles all download and authentication logic. FanFan Gallery-DL would not exist without it.
- **Inspired by [Cultured Downloader](https://github.com/KJHJason/Cultured-Downloader)** by KJHJason — UI design and workflow inspiration.

## License

[MIT](LICENSE)
