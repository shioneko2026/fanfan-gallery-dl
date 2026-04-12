"""
Gallery-DL Command Builder and Runner
Builds commands and executes gallery-dl as subprocess
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Callable
from core.credential_manager_simple import CredentialManager


class GalleryDLRunner:
    """Builds and executes gallery-dl commands"""

    def __init__(self, gallery_dl_path: Optional[Path] = None):
        """
        Initialize runner

        Args:
            gallery_dl_path: Path to gallery-dl executable (default: bin/gallery-dl.exe)
        """
        if gallery_dl_path is None:
            from core.paths import get_data_dir
            gallery_dl_path = get_data_dir() / "bin" / "gallery-dl.exe"

        self.gallery_dl_path = gallery_dl_path
        self.cred_manager = CredentialManager()

    def build_command(
        self,
        url: str,
        platform: str,
        output_dir: Optional[Path] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        simulate: bool = False,
        verbose: bool = False,
        dump_json: bool = False,
        app_tokens: Optional[Dict[str, str]] = None,
        folder_pattern: Optional[str] = None,
        file_pattern: Optional[str] = None,
        post_ids: Optional[List[str]] = None,
        post_id_field: str = "id",
        rate_limit: str = "",
        sleep_request: str = "",
        download_retries: int = 4
    ) -> tuple[List[str], Optional[Path]]:
        """
        Build gallery-dl command

        Args:
            url: URL to download
            platform: Platform identifier (for cookies)
            output_dir: Output directory
            date_from: Start date filter (YYYY-MM-DD)
            date_to: End date filter (YYYY-MM-DD)
            simulate: Just simulate, don't download
            verbose: Verbose output

        Returns:
            Tuple of (command list, cookie_file_path)
        """
        cmd = [str(self.gallery_dl_path)]

        # Handle authentication based on stored method
        cookie_file = None
        auth_method = self.cred_manager.get_auth_method(platform)

        if auth_method == "browser":
            # Use --cookies-from-browser flag
            browser = self.cred_manager.get_browser(platform)
            if browser:
                cmd.extend(["--cookies-from-browser", browser])
        elif auth_method == "username":
            # Use --username and --password flags
            creds = self.cred_manager.get_credentials(platform)
            if creds:
                cmd.extend(["--username", creds.get("username", "")])
                cmd.extend(["--password", creds.get("password", "")])
        elif auth_method == "cookies" or auth_method is None:
            # Cookie string - write to temp file
            cookie_string = self.cred_manager.get_cookies(platform)

            if cookie_string:
                cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                cookie_file.write("# Netscape HTTP Cookie File\n")

                # Write cookies
                for cookie in cookie_string.split("; "):
                    if "=" in cookie:
                        name, value = cookie.split("=", 1)
                        # Use platform-specific domain
                        domain = self._get_domain(platform)
                        cookie_file.write(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n")

                cookie_file.close()
                cmd.extend(["--cookies", cookie_file.name])

        # Output directory
        if output_dir:
            cmd.extend(["--destination", str(output_dir)])

        # Date filters — gallery-dl uses Python expressions in --filter
        filter_conditions = []
        if date_from or date_to:
            if date_from:
                # gallery-dl date filter: date >= datetime(Y,M,D)
                parts = ','.join(str(int(x)) for x in date_from.split('-'))
                filter_conditions.append(f"date >= datetime({parts})")
            if date_to:
                parts = ','.join(str(int(x)) for x in date_to.split('-'))
                filter_conditions.append(f"date <= datetime({parts},23,59,59)")

        # Post ID filter for selective downloading (uses creator URL + filter
        # instead of individual post URLs, which cause 403 on some platforms)
        if post_ids:
            # Use str() wrapper so the filter works whether gallery-dl stores
            # the ID as int (Fantia post_id) or str (Fanbox id)
            id_list = ', '.join(f'"{pid}"' for pid in post_ids)
            filter_conditions.append(f"str({post_id_field}) in ({id_list})")

        # Skip cover images (post thumbnails) — they inflate file counts
        # Fanbox uses isCoverImage, Fantia uses content_category == "thumb"
        if platform in ('fanbox',):
            filter_conditions.append("not isCoverImage")
        elif platform in ('fantia',):
            filter_conditions.append('content_category != "thumb"')

        if filter_conditions:
            cmd.extend(["--filter", " and ".join(filter_conditions)])

        # File/folder naming from settings (or sensible defaults)
        if not simulate and output_dir:
            # Use patterns passed in (read on main thread), or fall back to defaults
            if not file_pattern:
                file_pattern = "{filename}.{extension}"
            if folder_pattern is None:
                folder_pattern = "{category}/{creatorId}/{id} {title}"

            # Replace app-level tokens (resolved from artist DB) with literal values
            # These are NOT gallery-dl tokens — we resolve them ourselves
            if app_tokens:
                for token_name, token_value in app_tokens.items():
                    placeholder = "{" + token_name + "}"
                    value = token_value if token_value else ""
                    file_pattern = file_pattern.replace(placeholder, value)
                    folder_pattern = folder_pattern.replace(placeholder, value)

                # Clean up double spaces from empty tokens
                import re
                file_pattern = re.sub(r'  +', ' ', file_pattern).strip()
                folder_pattern = '/'.join(
                    re.sub(r'  +', ' ', part).strip() for part in folder_pattern.split('/')
                )

            # Resolve {today} and {today:FORMAT} tokens
            import re
            from datetime import datetime
            now = datetime.now()

            def replace_today(m):
                fmt = m.group(1)
                try:
                    return now.strftime(fmt)
                except ValueError:
                    return m.group(0)

            file_pattern = re.sub(r'\{today:([^}]+)\}', replace_today, file_pattern)
            folder_pattern = re.sub(r'\{today:([^}]+)\}', replace_today, folder_pattern)
            file_pattern = file_pattern.replace('{today}', now.strftime('%Y-%m-%d'))
            folder_pattern = folder_pattern.replace('{today}', now.strftime('%Y-%m-%d'))

            # Capitalize {category} — replace with title-cased platform name
            # e.g., [fanbox] -> [Fanbox], [fantia] -> [Fantia]
            platform_lower = platform.lower()
            capitalized_category = platform_lower.title()
            file_pattern = file_pattern.replace('{category}', capitalized_category)
            folder_pattern = folder_pattern.replace('{category}', capitalized_category)

            # Platform-aware token substitution:
            # Fanbox has {title} but not {post_title}
            # Fantia has {post_title} but not {title}
            # Map between them so one pattern works everywhere
            if platform_lower in ('fanbox', 'pixiv'):
                # For Fanbox: {post_title} -> {title}, {post_id} -> {id}
                file_pattern = file_pattern.replace('{post_title}', '{title}')
                folder_pattern = folder_pattern.replace('{post_title}', '{title}')
                file_pattern = file_pattern.replace('{post_id}', '{id}')
                folder_pattern = folder_pattern.replace('{post_id}', '{id}')
            # Fantia natively supports {post_title} and {post_id} — no substitution needed

            # File naming pattern
            cmd.extend(["-o", f"filename={file_pattern}"])

            # Disable gallery-dl's extension "adjustment" (e.g. .mp4 -> .m4v)
            cmd.extend(["-o", "adjust-extensions=false"])

            # Directory pattern — split on / to make gallery-dl's list format
            # Empty folder_pattern = flat download (no subdirectories)
            if folder_pattern:
                dir_parts = [p.strip() for p in folder_pattern.split('/') if p.strip()]
                dir_json = ', '.join(f'"{p}"' for p in dir_parts)
                cmd.extend(["-o", f"directory=[{dir_json}]"])
            else:
                cmd.extend(["-o", 'directory=[]'])

        # Simulate mode
        if simulate:
            cmd.append("--simulate")

        # JSON metadata output
        if dump_json:
            cmd.append("--dump-json")

        # Verbose mode
        if verbose:
            cmd.append("-v")
        
        # Rate limiting and sleep settings
        if rate_limit:
            cmd.extend(["--rate", rate_limit])
        if sleep_request:
            try:
                if float(sleep_request) > 0:
                    cmd.extend(["--sleep-request", sleep_request])
            except (ValueError, TypeError):
                pass
        if download_retries != 4:
            cmd.extend(["--retries", str(download_retries)])

        # URL
        cmd.append(url)

        return cmd, Path(cookie_file.name) if cookie_file else None

    # gallery-dl native tokens + app-level tokens that are valid in format strings
    VALID_GDL_TOKENS = {
        'category', 'subcategory', 'creatorId', 'id', 'title', 'date',
        'filename', 'extension', 'num', 'feeRequired', 'fileId',
        'user', 'name', 'userId', 'tags', 'type', 'text', 'excerpt',
        'post_id', 'post_title', 'fanclub_name', 'fanclub_id',  # Fantia-specific
        'content_title', 'content_filename', 'content_category',  # Fantia content
        'creator_name', 'creator_jp', 'today',  # app-level tokens
    }

    def _get_setting(self, key: str, default: str = "") -> str:
        """Read a setting from the database, validating it uses gallery-dl tokens"""
        try:
            from db.database import Database
            db = Database()
            value = db.get_setting(key, default)
            db.close()

            if not value:
                return default

            # Check for old-style tokens that gallery-dl doesn't understand
            # e.g. {artist}, {source}, {ext}, {date_latest} etc.
            # Allow format specs like {date:%Y-%m-%d} — extract just the token name
            import re
            tokens_used = re.findall(r'\{(\w+)(?:[^}]*)?\}', value)
            for token in tokens_used:
                if token not in self.VALID_GDL_TOKENS:
                    # Old/invalid pattern detected — use default instead
                    return default

            return value
        except Exception:
            return default

    def _get_domain(self, platform: str) -> str:
        """Get cookie domain for platform"""
        domains = {
            "fanbox": ".fanbox.cc",
            "pixiv": ".pixiv.net",
            "patreon": ".patreon.com",
            "fantia": ".fantia.jp",
            "subscribestar": ".subscribestar.com"
        }
        return domains.get(platform, ".example.com")

    def run(
        self,
        url: str,
        platform: str,
        output_dir: Optional[Path] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        simulate: bool = False,
        verbose: bool = False,
        dump_json: bool = False,
        app_tokens: Optional[Dict[str, str]] = None,
        folder_pattern: Optional[str] = None,
        file_pattern: Optional[str] = None,
        post_ids: Optional[List[str]] = None,
        post_id_field: str = "id",
        progress_callback: Optional[Callable[[str], None]] = None,
        process_callback: Optional[Callable] = None,
        rate_limit: str = "",
        sleep_request: str = "",
        download_retries: int = 4
    ) -> Dict[str, any]:
        """
        Run gallery-dl command

        Args:
            url: URL to download
            platform: Platform identifier
            output_dir: Output directory
            date_from: Start date filter
            date_to: End date filter
            simulate: Just simulate
            verbose: Verbose output
            progress_callback: Callback for progress updates (receives stdout lines)

        Returns:
            Dict with 'success', 'exit_code', 'stdout', 'stderr'
        """
        cmd, cookie_file = self.build_command(
            url=url,
            platform=platform,
            output_dir=output_dir,
            date_from=date_from,
            date_to=date_to,
            simulate=simulate,
            verbose=verbose,
            dump_json=dump_json,
            app_tokens=app_tokens,
            folder_pattern=folder_pattern,
            file_pattern=file_pattern,
            post_ids=post_ids,
            post_id_field=post_id_field,
            rate_limit=rate_limit,
            sleep_request=sleep_request,
            download_retries=download_retries
        )

        try:
            # Force UTF-8 output from gallery-dl (Python-based exe)
            import os
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'

            # Detect Windows OEM codepage for encoding fallback
            # PyInstaller-bundled gallery-dl may output in the system's OEM codepage
            oem_codepage = None
            try:
                import ctypes
                oem_cp = ctypes.windll.kernel32.GetOEMCP()
                oem_codepage = f'cp{oem_cp}'
            except Exception:
                pass

            # Build encoding fallback chain: UTF-8, then Japanese, then OEM, then ANSI
            import locale
            encodings = ['utf-8', 'cp932', 'shift_jis']
            if oem_codepage and oem_codepage not in encodings:
                encodings.append(oem_codepage)
            ansi_cp = locale.getpreferredencoding(False)
            if ansi_cp and ansi_cp.lower().replace('-', '') not in [e.lower().replace('-', '') for e in encodings]:
                encodings.append(ansi_cp)
            encodings.append('cp1252')  # Last resort Western European

            # Run gallery-dl in binary mode — read raw bytes and decode manually
            # PyInstaller-bundled gallery-dl may ignore PYTHONUTF8 on Windows,
            # so we try multiple encodings to handle Japanese filenames
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env
            )

            # Store process reference for external control (pause/cancel)
            if process_callback:
                process_callback(process)

            stdout_lines = []

            # Read all output in real-time as raw bytes
            while True:
                raw = process.stdout.readline()
                if raw == b'' and process.poll() is not None:
                    break
                if raw:
                    # Try each encoding in order — first successful decode wins
                    for encoding in encodings:
                        try:
                            line = raw.decode(encoding).rstrip('\n\r')
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue
                    else:
                        line = raw.decode('utf-8', errors='replace').rstrip('\n\r')

                    stdout_lines.append(line)
                    if progress_callback:
                        progress_callback(line)

            exit_code = process.poll()

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout_lines,
                "stderr": []
            }

        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": [],
                "stderr": [str(e)]
            }

        finally:
            # Clean up cookie file
            if cookie_file and cookie_file.exists():
                try:
                    cookie_file.unlink()
                except:
                    pass

    def test_connection(self, platform: str, test_url: Optional[str] = None, log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, any]:
        """
        Test if credentials work by running gallery-dl

        Args:
            platform: Platform identifier
            test_url: Optional test URL (uses default if not provided)
            log_callback: Callback for log output

        Returns:
            Dict with 'success' and 'message'
        """
        # Default test URLs
        test_urls = {
            "fanbox": "https://www.fanbox.cc/@support",
            "pixiv": "https://www.pixiv.net/",
            "patreon": "https://www.patreon.com/",
            "fantia": "https://fantia.jp/",
            "subscribestar": "https://www.subscribestar.com/"
        }

        url = test_url or test_urls.get(platform)
        if not url:
            return {"success": False, "message": "No test URL available"}

        if not self.cred_manager.has_cookies(platform):
            return {"success": False, "message": "No cookies stored"}

        # Build command - minimal test, respect rate limits
        cmd, cookie_file = self.build_command(
            url=url,
            platform=platform,
            simulate=True,
            verbose=False  # Less verbose for testing
        )
        
        # Limit to just 1 post for testing (max ~5 files)
        cmd.insert(-1, "--range")
        cmd.insert(-1, "1")

        try:
            if log_callback:
                log_callback(f"Running: {' '.join(cmd[:3])} ... --range 1 {cmd[-1]}")
                log_callback(f"Testing with 1 post only (respects rate limits)")
                log_callback(f"No timeout - will run until complete")
                log_callback("-" * 60)
            
            # Run with streaming output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1
            )

            output_lines = []
            
            # Read output indefinitely (no timeout)
            while True:
                # Read line
                line = process.stdout.readline()
                
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    if log_callback:
                        log_callback(line)
                
                # Check if process finished
                if process.poll() is not None:
                    break
            
            # Get exit code
            exit_code = process.poll()

            # Clean up cookie file
            if cookie_file and cookie_file.exists():
                try:
                    cookie_file.unlink()
                except:
                    pass

            if log_callback:
                log_callback("-" * 60)
                log_callback(f"Exit code: {exit_code}")

            if exit_code == 0:
                return {"success": True, "message": "✓ Connection successful! Cookies are valid."}
            else:
                # Check for authentication errors
                output_text = " ".join(output_lines)
                
                if "403" in output_text:
                    return {"success": False, "message": "✗ Authentication failed (403 Forbidden). You may not have access to this content."}
                elif "401" in output_text:
                    return {"success": False, "message": "✗ Authentication failed (401 Unauthorized). Cookies are invalid or expired."}
                elif "HttpError" in output_text:
                    return {"success": False, "message": f"✗ HTTP Error: Check your cookies"}
                else:
                    return {"success": False, "message": f"✗ Test failed (exit code: {exit_code})"}

        except Exception as e:
            # Clean up
            if cookie_file and cookie_file.exists():
                try:
                    cookie_file.unlink()
                except:
                    pass
            
            if log_callback:
                log_callback(f"✗ ERROR: {str(e)}")
            
            return {"success": False, "message": f"✗ Error: {str(e)}"}
