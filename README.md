# FanFan Gallery-DL

A desktop GUI application for downloading media from artist subscription platforms using gallery-dl.

## Features

- **Multi-platform support**: Pixiv, Pixiv Fanbox, Patreon, Fantia, SubscribeStar
- **Smart file organization**: Automatic folder and file naming with customizable patterns
- **Selective downloads**: Choose individual files from posts before downloading
- **Date filtering**: Download only content within specific date ranges
- **Artist management**: Track multiple artists across different platforms
- **Secure credential storage**: Credentials stored in Windows Credential Manager
- **Auto-updates**: Built-in gallery-dl update management
- **Romaji support**: Automatic Japanese name transliteration

## Installation

### Prerequisites

- Python 3.9 or higher
- Windows (currently Windows-only due to credential storage)

### Setup

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

On first launch, the app will automatically download the latest gallery-dl binary.

## Project Structure

```
FanFan Gallery-DL/
├── main.py                 # Application entry point
├── ui/                     # User interface modules
│   ├── main_window.py      # Main window with navigation
│   ├── dashboard.py        # Dashboard page
│   ├── downloads.py        # Downloads management
│   ├── artists.py          # Artist management
│   └── settings/           # Settings pages
│       ├── naming.py       # Naming pattern configuration
│       ├── credentials.py  # Credential management
│       ├── updates.py      # Update management
│       └── data.py         # Data backup/import
├── core/                   # Core functionality (to be implemented)
│   ├── gallery_dl_manager.py
│   ├── artist_manager.py
│   ├── download_queue.py
│   ├── naming_engine.py
│   └── credential_manager.py
├── db/                     # Database layer
│   └── database.py         # SQLite database manager
├── bin/                    # Binary files
│   └── gallery-dl.exe      # Auto-downloaded on first run
├── config/                 # Configuration files
├── data/                   # Application data
│   └── appdata.db          # SQLite database
└── requirements.txt        # Python dependencies
```

## Usage

### First Time Setup

1. **Configure Credentials** (Settings → Credentials)
   - Choose your auth method for each platform
   - Import cookies from browser or paste manually
   - Test connection to verify

2. **Set Naming Patterns** (Settings → Naming)
   - Customize folder and file naming patterns
   - Preview changes with example data
   - Available tokens: `{artist}`, `{date}`, `{source}`, `{title}`, etc.

3. **Set Download Preferences** (Settings → Updates)
   - Choose default save folder
   - Set concurrent download limit

### Downloading Content

1. **Paste Artist URL** (Downloads page)
   - Paste the artist's profile URL
   - Click "Scan" to fetch available content

2. **Select Files**
   - Expand posts to see individual files
   - Check/uncheck files to download
   - Use "Omit Non-Video" to filter media types

3. **Download**
   - Review selected files and destination
   - Click "Download Selected"
   - Monitor progress in the queue view

### Managing Artists

1. **Add Artist** (Artists page)
   - Click "+ Add Artist"
   - Enter artist details and platform URLs
   - Set custom naming overrides (optional)

2. **Update Artist**
   - Click "Update" on any artist card
   - Downloads new content since last update

### Backups

**Export Database** (Settings → Data)
- Exports full database including all artists and history
- Does NOT include credentials (stored separately in Windows Credential Manager)

**Export Settings** (Settings → Data)
- Exports only naming patterns and preferences as JSON
- Portable across installations

## Naming Patterns

### Default Patterns

**Folder**: `{artist} [{date_latest}] [{source}]`
Example: `pangdong パントン [2025-07-13] [Fanbox]`

**File**: `{artist} [{date}] {title} [{source}].{ext}`
Example: `pangdong パントン [2025-07-13] Some Video Title [Fanbox].mp4`

### Available Tokens

- `{artist}` - Artist name (romaji + Japanese)
- `{date}` - Post upload date
- `{date_latest}` - Latest downloaded post date (folders only)
- `{source}` - Platform name
- `{title}` - Post title
- `{post_id}` - Post ID
- `{num}` - File number within post
- `{ext}` - File extension

## Current Status

### Implemented ✅
- Project structure and database schema
- Main window with sidebar navigation
- Dashboard page with stats and activity
- Downloads page (UI only - functionality pending)
- Artists page (UI only - functionality pending)
- Settings pages (Naming, Credentials, Updates, Data)
- Database layer with full CRUD operations

### To Be Implemented 🚧
- Gallery-dl binary manager and integration
- Download queue and progress tracking
- File scanning and selection logic
- Artist edit panel
- Credential manager with keyring integration
- Romaji auto-detection with pykakasi
- Folder date detection and updates
- Auto-update checker
- PyInstaller packaging

## Development

### Running in Development Mode

```bash
python main.py
```

### Building Executable (Future)

```bash
pyinstaller --name="FanFan Gallery-DL" --windowed --onefile main.py
```

## Database Schema

The app uses SQLite with the following main tables:

- **artists** - Artist profiles
- **artist_platforms** - Platform-specific URLs and settings per artist
- **download_history** - Record of download sessions
- **failed_downloads** - Failed files for retry
- **settings** - App configuration

## License

For personal use. See technical brief for full project details.

## Credits

- **gallery-dl**: The powerful download engine powering this GUI
- **PyQt6**: Modern cross-platform GUI framework
- **pykakasi**: Japanese text transliteration
