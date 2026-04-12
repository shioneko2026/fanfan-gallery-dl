# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for FanFan Gallery-DL
# Build: pyinstaller fanfan.spec
# Output: dist/FanFan Gallery-DL.exe
#

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundled read-only assets (accessed via get_resource())
        ('config/universal_standard_info.md', 'config'),
    ],
    hiddenimports=[
        # keyring Windows backend (not auto-detected by PyInstaller)
        'keyring.backends.Windows',
        'keyring.backends.fail',
        # PyQt6 modules
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.QtMultimedia',
        'PyQt6.sip',
        # Other dependencies
        'pykakasi',
        'send2trash',
        'requests',
        'requests.adapters',
        'requests.packages',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages to keep binary size down
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'sklearn',
        'tensorflow',
        'torch',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FanFan Gallery-DL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # No terminal window shown to users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Uncomment and add icon file when available
)

# NOTE: The following folders are created at runtime NEXT TO the .exe,
# not inside the bundle. This is intentional — they are writable:
#   bin/                    — gallery-dl.exe (auto-downloaded)
#   Credentials and User Data/  — appdata.db (SQLite)
# Access via core.paths.get_data_dir(), not sys._MEIPASS.
