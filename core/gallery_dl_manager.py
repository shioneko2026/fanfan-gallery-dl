"""
Gallery-DL binary management and execution
"""
import os
import subprocess
import json
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Callable
import requests


class GalleryDLManager:
    """Manages gallery-dl binary and execution"""

    def __init__(self, bin_dir: Optional[Path] = None):
        """
        Initialize the manager

        Args:
            bin_dir: Directory to store gallery-dl binary (defaults to project bin/)
        """
        if bin_dir is None:
            bin_dir = Path(__file__).parent.parent / "bin"

        self.bin_dir = Path(bin_dir)
        self.bin_dir.mkdir(parents=True, exist_ok=True)

        self.binary_path = self.bin_dir / "gallery-dl.exe"
        self.backup_path = self.bin_dir / "gallery-dl-prev.exe"

        self.github_api_url = "https://api.github.com/repos/mikf/gallery-dl/releases/latest"
        self.current_version = None

    def ensure_binary(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Ensure gallery-dl binary exists, download if missing

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            True if binary is ready, False if failed
        """
        if self.binary_path.exists():
            if progress_callback:
                progress_callback("gallery-dl binary found")
            return True

        if progress_callback:
            progress_callback("gallery-dl not found, downloading latest version...")

        return self.download_binary(progress_callback)

    def download_binary(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Download gallery-dl.exe from GitHub releases

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get latest release info from GitHub API
            if progress_callback:
                progress_callback("Fetching latest release info from GitHub...")

            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()

            # Find the .exe asset
            exe_asset = None
            for asset in release_data.get("assets", []):
                if asset["name"].endswith(".exe"):
                    exe_asset = asset
                    break

            if not exe_asset:
                if progress_callback:
                    progress_callback("Error: No .exe file found in latest release")
                return False

            download_url = exe_asset["browser_download_url"]
            version = release_data.get("tag_name", "unknown")

            if progress_callback:
                progress_callback(f"Downloading gallery-dl {version}...")

            # Download the binary
            response = requests.get(download_url, timeout=30, stream=True)
            response.raise_for_status()

            # Write to file
            with open(self.binary_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if progress_callback:
                progress_callback(f"Successfully downloaded gallery-dl {version}")

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"Error downloading gallery-dl: {str(e)}")
            return False

    def get_version(self) -> Optional[str]:
        """
        Get current gallery-dl version

        Returns:
            Version string or None if failed
        """
        if not self.binary_path.exists():
            return None

        try:
            result = subprocess.run(
                [str(self.binary_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse version from output
                # Can be "gallery-dl 1.26.0" or just "1.26.0"
                output = result.stdout.strip()

                # Try matching "gallery-dl X.Y.Z" format first
                match = re.search(r'gallery-dl (\d+\.\d+\.\d+)', output)
                if match:
                    self.current_version = match.group(1)
                    return self.current_version

                # Try matching just "X.Y.Z" format
                match = re.search(r'(\d+\.\d+\.\d+)', output)
                if match:
                    self.current_version = match.group(1)
                    return self.current_version

            return None

        except Exception as e:
            print(f"Error getting version: {e}")
            return None

    def check_for_updates(self) -> Optional[Dict[str, str]]:
        """
        Check if a newer version is available on GitHub

        Returns:
            Dict with 'current' and 'latest' versions, or None if failed
        """
        try:
            current = self.get_version()
            if not current:
                return None

            # Get latest release from GitHub
            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()

            latest = release_data.get("tag_name", "").lstrip('v')

            return {
                "current": current,
                "latest": latest,
                "update_available": self._compare_versions(current, latest) < 0,
                "changelog_url": release_data.get("html_url", "")
            }

        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]

            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1

            return 0
        except:
            return 0

    def update_binary(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Update gallery-dl to latest version

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        # Backup current binary
        if self.binary_path.exists():
            if progress_callback:
                progress_callback("Backing up current version...")

            if self.backup_path.exists():
                self.backup_path.unlink()

            shutil.copy2(self.binary_path, self.backup_path)
            self.binary_path.unlink()

        # Download new version
        success = self.download_binary(progress_callback)

        if success:
            # Test the new binary
            if progress_callback:
                progress_callback("Testing new binary...")

            new_version = self.get_version()
            if new_version:
                if progress_callback:
                    progress_callback(f"Update successful! Now running version {new_version}")
                return True
            else:
                # Rollback on failure
                if progress_callback:
                    progress_callback("New binary failed test, rolling back...")

                if self.backup_path.exists():
                    shutil.copy2(self.backup_path, self.binary_path)

                return False

        return False

    def rollback(self) -> bool:
        """
        Restore previous version from backup

        Returns:
            True if successful, False otherwise
        """
        if not self.backup_path.exists():
            return False

        if self.binary_path.exists():
            self.binary_path.unlink()

        shutil.copy2(self.backup_path, self.binary_path)
        return True

    def execute(
        self,
        args: List[str],
        output_callback: Optional[Callable[[str], None]] = None,
        working_dir: Optional[Path] = None
    ) -> Dict[str, any]:
        """
        Execute a gallery-dl command

        Args:
            args: Command arguments (without gallery-dl itself)
            output_callback: Optional callback for real-time output
            working_dir: Optional working directory

        Returns:
            Dict with 'success', 'stdout', 'stderr', 'return_code'
        """
        if not self.binary_path.exists():
            return {
                "success": False,
                "stdout": "",
                "stderr": "gallery-dl binary not found",
                "return_code": -1
            }

        cmd = [str(self.binary_path)] + args

        try:
            if output_callback:
                # Stream output in real-time
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=working_dir,
                    bufsize=1,
                    universal_newlines=True
                )

                stdout_lines = []
                stderr_lines = []

                # Read stdout
                for line in process.stdout:
                    line = line.rstrip()
                    stdout_lines.append(line)
                    output_callback(line)

                # Read stderr
                for line in process.stderr:
                    line = line.rstrip()
                    stderr_lines.append(line)
                    output_callback(f"ERROR: {line}")

                process.wait()

                return {
                    "success": process.returncode == 0,
                    "stdout": "\n".join(stdout_lines),
                    "stderr": "\n".join(stderr_lines),
                    "return_code": process.returncode
                }
            else:
                # Non-streaming execution
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=working_dir
                )

                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }

        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }

    def simulate(self, url: str, date_min: Optional[str] = None, date_max: Optional[str] = None) -> Dict[str, any]:
        """
        Simulate download to get file list without downloading

        Args:
            url: Artist profile URL
            date_min: Optional minimum date (YYYYMMDD)
            date_max: Optional maximum date (YYYYMMDD)

        Returns:
            Dict with 'success', 'files' (list of dicts), 'error'
        """
        args = ["--simulate", "--dump-json", url]

        if date_min:
            args.extend(["--date-min", date_min])
        if date_max:
            args.extend(["--date-max", date_max])

        result = self.execute(args)

        if not result["success"]:
            return {
                "success": False,
                "files": [],
                "error": result["stderr"]
            }

        # Parse JSON output (one JSON object per line)
        files = []
        for line in result["stdout"].strip().split('\n'):
            if line.strip():
                try:
                    file_data = json.loads(line)
                    files.append(file_data)
                except json.JSONDecodeError:
                    continue

        return {
            "success": True,
            "files": files,
            "error": None
        }

    def download(
        self,
        url: str,
        output_dir: Path,
        date_min: Optional[str] = None,
        date_max: Optional[str] = None,
        cookies_file: Optional[Path] = None,
        output_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, any]:
        """
        Download files from URL

        Args:
            url: Artist profile URL
            output_dir: Output directory
            date_min: Optional minimum date (YYYYMMDD)
            date_max: Optional maximum date (YYYYMMDD)
            cookies_file: Optional cookies file path
            output_callback: Optional callback for real-time output

        Returns:
            Dict with 'success', 'stdout', 'stderr'
        """
        args = [url, "-d", str(output_dir)]

        if date_min:
            args.extend(["--date-min", date_min])
        if date_max:
            args.extend(["--date-max", date_max])
        if cookies_file and cookies_file.exists():
            args.extend(["--cookies", str(cookies_file)])

        # Skip already downloaded files
        args.append("-C")

        return self.execute(args, output_callback=output_callback)
