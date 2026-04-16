"""
App self-update manager.
Checks GitHub releases for a new version of FanFan Gallery-DL,
downloads it, and performs the Windows exe-swap via a helper bat.
"""
import sys
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, Callable

import requests

from version import APP_VERSION, GITHUB_REPO
from core.paths import get_data_dir
from core.logger import logger


class AppUpdater:
    """Manages FanFan Gallery-DL self-updates from GitHub releases."""

    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        self.app_dir = get_data_dir()
        self.update_exe = self.app_dir / "FanFan Gallery-DL_update.exe"
        self.updater_bat = self.app_dir / "updater.bat"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_frozen(self) -> bool:
        """True when running as a PyInstaller .exe."""
        return getattr(sys, 'frozen', False)

    def check_for_updates(self) -> Optional[Dict]:
        """
        Query GitHub releases API and compare to current version.

        Returns dict with keys:
            current, latest, update_available, download_url, changelog_url
        or None on failure.
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            release = response.json()

            latest = release.get("tag_name", "").lstrip("v")
            if not latest:
                return None

            # Find .exe asset
            download_url = ""
            for asset in release.get("assets", []):
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            return {
                "current": APP_VERSION,
                "latest": latest,
                "update_available": self._compare_versions(APP_VERSION, latest) < 0,
                "download_url": download_url,
                "changelog_url": release.get("html_url", ""),
            }

        except Exception as e:
            logger.warning(f"App update check failed: {e}")
            return None

    def download_update(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Download the new .exe to update_exe path.

        Returns True on success.
        """
        try:
            # Get download URL
            result = self.check_for_updates()
            if not result or not result.get("download_url"):
                if progress_callback:
                    progress_callback("Could not find download URL.")
                return False

            if not result["update_available"]:
                if progress_callback:
                    progress_callback("Already on the latest version.")
                return False

            download_url = result["download_url"]
            version = result["latest"]

            if progress_callback:
                progress_callback(f"Downloading FanFan Gallery-DL v{version}...")

            response = requests.get(download_url, timeout=60, stream=True)
            response.raise_for_status()

            with open(self.update_exe, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if progress_callback:
                progress_callback(f"Download complete — v{version} ready to install.")

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"Download failed: {e}")
            return False

    def apply_update(self) -> None:
        """
        Perform the exe swap and restart.

        Writes a bat file that (after a short delay) moves the downloaded
        exe over the running one, then relaunches. Only works when frozen.
        The current process exits immediately after launching the bat.
        """
        if not self.is_frozen():
            raise RuntimeError("apply_update() only works when running as a .exe")

        if not self.update_exe.exists():
            raise FileNotFoundError(f"Update file not found: {self.update_exe}")

        current_exe_name = Path(sys.executable).name

        bat_content = (
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
            f'move /y "FanFan Gallery-DL_update.exe" "{current_exe_name}"\n'
            f'start "" "{current_exe_name}"\n'
            'del "%~f0"\n'
        )

        self.updater_bat.write_text(bat_content, encoding="utf-8")

        subprocess.Popen(
            [str(self.updater_bat)],
            cwd=str(self.app_dir),
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )

        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def cleanup_update_files(self) -> None:
        """Remove leftover update/updater files from a previous run."""
        for f in [self.update_exe, self.updater_bat]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Return -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        try:
            def parse(v):
                return [int(x) for x in re.split(r"[.\-]", v) if x.isdigit()]
            p1, p2 = parse(v1), parse(v2)
            for a, b in zip(p1, p2):
                if a < b:
                    return -1
                if a > b:
                    return 1
            return 0 if len(p1) == len(p2) else (-1 if len(p1) < len(p2) else 1)
        except Exception:
            return 0
