"""
Centralised path resolution — works both in dev (python main.py)
and when frozen by PyInstaller into a single .exe.
"""
import sys
from pathlib import Path


def get_data_dir() -> Path:
    """
    Writable runtime data directory.
    - Frozen (.exe): folder containing the executable
    - Dev: project root (two levels above this file)
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_resource(relative_path: str) -> Path:
    """
    Bundled read-only asset (e.g. config files).
    - Frozen: sys._MEIPASS (PyInstaller temp extraction dir)
    - Dev: project root
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent.parent / relative_path
