"""
ZIP extraction and file routing for downloaded content
Handles automatic extraction of ZIP archives from Fanbox and other platforms.
Parses metadata from gallery-dl's folder names to rename extracted files
using the user's naming pattern.
"""
import re
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from send2trash import send2trash


class ZipExtractor:
    """Handles ZIP extraction with naming-pattern-aware renaming"""

    # Video file extensions
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg'}

    # Supported platforms for auto-extraction
    SUPPORTED_PLATFORMS = {'fanbox', 'pixiv fanbox'}

    def __init__(self, db):
        self.db = db
        self.enabled = self._get_setting("zip_auto_extract", True)
        self.non_video_folder_name = self._get_setting("non_video_folder_name", "[Non-Video Content]")

    def _get_setting(self, key: str, default):
        value = self.db.get_setting(key)
        if value is None:
            return default
        if isinstance(default, bool):
            return value in [True, "true", "True", "1", 1]
        return value

    def is_video_file(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in self.VIDEO_EXTENSIONS

    def should_extract(self, filepath: Path, platform: str) -> bool:
        """Check if a file should be auto-extracted"""
        if not self.enabled:
            return False
        if filepath.suffix.lower() != '.zip':
            return False
        return platform.lower() in self.SUPPORTED_PLATFORMS

    def parse_folder_metadata(self, folder_name: str) -> Dict[str, str]:
        """
        Parse metadata from a gallery-dl-named folder.

        Expected pattern (from user's folder naming):
        {creator_name} {creator_jp} [{date:%Y-%m-%d}] {post_title} [P{post_id}] [{category}]

        Example: "RIMの部屋 RIM [2026-02-24] 女の子二人にもてあそばれる [P11458849] [fanbox]"

        Returns dict with: date, post_title, post_id, category (all strings, empty if not found)
        """
        result = {'date': '', 'post_title': '', 'post_id': '', 'category': ''}

        # Extract date: [YYYY-MM-DD]
        date_match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', folder_name)
        if date_match:
            result['date'] = date_match.group(1)

        # Extract post_id: [P12345]
        pid_match = re.search(r'\[P(\d+)\]', folder_name)
        if pid_match:
            result['post_id'] = pid_match.group(1)

        # Extract category: last [word] bracket
        cat_match = re.search(r'\[(\w+)\]\s*$', folder_name)
        if cat_match:
            result['category'] = cat_match.group(1)

        # Extract post_title: text between date bracket and [P...] bracket
        if date_match and pid_match:
            between = folder_name[date_match.end():pid_match.start()]
            result['post_title'] = between.strip()

        return result

    def _build_filename(self, file_path: Path, temp_root: Path,
                        file_pattern: str, app_tokens: Dict[str, str],
                        folder_meta: Dict[str, str]) -> str:
        """
        Build a renamed filename for an extracted file using the user's file pattern.

        The {filename} token is replaced with: {post_title} - {relative_path_parts}
        where relative path parts are the folder/subfolder/filename joined with " - "
        """
        # Build the relative path parts (folders + stem, no extension)
        rel_path = file_path.relative_to(temp_root)
        parts = list(rel_path.parts)
        # Last part is the filename — use stem (no extension)
        parts[-1] = file_path.stem

        # Build the {filename} replacement: post_title - folder - subfolder - stem
        filename_parts = []
        if folder_meta.get('post_title'):
            filename_parts.append(folder_meta['post_title'])
        filename_parts.extend(parts)
        filename_value = ' - '.join(filename_parts)

        # Start with the user's file pattern
        result = file_pattern

        # Replace app tokens
        for token, value in app_tokens.items():
            result = result.replace(f'{{{token}}}', value or '')

        # Replace gallery-dl tokens with parsed folder metadata
        date_val = folder_meta.get('date', '')
        # Handle {date:%Y-%m-%d} format — replace the whole token including format spec
        result = re.sub(r'\{date:[^}]+\}', date_val, result)
        result = result.replace('{date}', date_val)

        result = result.replace('{post_id}', folder_meta.get('post_id', ''))
        result = result.replace('{category}', folder_meta.get('category', ''))
        result = result.replace('{filename}', filename_value)
        result = result.replace('{extension}', file_path.suffix.lstrip('.'))

        # Clean up any remaining unreplaced tokens
        result = re.sub(r'\{[^}]+\}', '', result)

        # Clean up multiple spaces and trim
        result = re.sub(r'  +', ' ', result).strip()

        return result

    def extract_and_route(
        self,
        zip_path: Path,
        platform: str,
        app_tokens: Optional[Dict[str, str]] = None,
        file_pattern: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Extract ZIP file and rename contents using the user's naming pattern.
        Metadata is parsed from the ZIP's parent folder name.

        Args:
            zip_path: Path to ZIP file
            platform: Platform identifier
            app_tokens: Dict with creator_name, creator_jp, creator_romaji
            file_pattern: User's file naming pattern string

        Returns:
            Dict with extraction results
        """
        empty_result = {
            'success': False,
            'extracted_files': [],
            'video_files': [],
            'non_video_files': [],
            'error': None
        }

        if not self.enabled:
            empty_result['error'] = 'ZIP auto-extraction is disabled'
            return empty_result

        if not zip_path.exists():
            empty_result['error'] = f'ZIP file not found: {zip_path}'
            return empty_result

        # The post folder is the ZIP's parent directory
        post_folder = zip_path.parent

        # Parse metadata from the post folder name
        folder_meta = self.parse_folder_metadata(post_folder.name)

        temp_extract_dir = None
        try:
            # Extract to temp directory
            temp_extract_dir = post_folder / f".temp_extract_{zip_path.stem}"
            temp_extract_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            # Get all extracted files (skip directories, skip junk like __MACOSX)
            extracted_files = [
                f for f in temp_extract_dir.rglob('*')
                if f.is_file() and '__MACOSX' not in str(f) and not f.name.startswith('.')
            ]

            video_files = []
            non_video_files = []

            for file_path in extracted_files:
                # Build new filename
                if file_pattern and app_tokens:
                    new_filename = self._build_filename(
                        file_path, temp_extract_dir,
                        file_pattern, app_tokens, folder_meta
                    )
                else:
                    # Fallback: ZIP stem + original name
                    rel_parts = list(file_path.relative_to(temp_extract_dir).parts)
                    rel_parts[-1] = file_path.stem
                    new_filename = f"{zip_path.stem} - {' - '.join(rel_parts)}{file_path.suffix}"

                # Determine destination based on file type
                is_video = self.is_video_file(file_path)

                if is_video:
                    dest_path = post_folder / new_filename
                    video_files.append(dest_path)
                else:
                    non_video_folder = post_folder / self.non_video_folder_name
                    non_video_folder.mkdir(parents=True, exist_ok=True)
                    dest_path = non_video_folder / new_filename
                    non_video_files.append(dest_path)

                # Handle filename conflicts
                if dest_path.exists():
                    stem = dest_path.stem
                    ext = dest_path.suffix
                    parent = dest_path.parent
                    counter = 1
                    while dest_path.exists():
                        dest_path = parent / f"{stem} ({counter}){ext}"
                        counter += 1

                # Move file to destination
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_path))

            # Clean up temp directory
            shutil.rmtree(temp_extract_dir)
            temp_extract_dir = None

            # Send ZIP to recycle bin
            try:
                send2trash(str(zip_path))
            except Exception as e:
                print(f"Warning: Failed to send ZIP to recycle bin: {e}")

            return {
                'success': True,
                'extracted_files': video_files + non_video_files,
                'video_files': video_files,
                'non_video_files': non_video_files,
                'error': None
            }

        except Exception as e:
            # Clean up on error
            if temp_extract_dir and temp_extract_dir.exists():
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception:
                    pass

            empty_result['error'] = str(e)
            return empty_result

    def process_download_folder(
        self,
        folder: Path,
        platform: str,
        app_tokens: Optional[Dict[str, str]] = None,
        file_pattern: Optional[str] = None
    ) -> List[Dict]:
        """
        Find and extract all ZIP files recursively in a download folder.

        Returns list of extraction results.
        """
        results = []

        if not folder.exists():
            return results

        # Find all ZIP files recursively (they may be in post subfolders)
        zip_files = list(folder.rglob('*.zip'))

        for zip_file in zip_files:
            if self.should_extract(zip_file, platform):
                result = self.extract_and_route(
                    zip_path=zip_file,
                    platform=platform,
                    app_tokens=app_tokens,
                    file_pattern=file_pattern
                )
                results.append({
                    'zip_file': zip_file,
                    'result': result
                })

        return results
