"""
Gallery-DL Thread Runner
Runs gallery-dl in a background thread to prevent UI freezing
"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional, Dict, Callable
from pathlib import Path
from core.gallery_dl_runner import GalleryDLRunner


class GalleryDLThread(QThread):
    """Background thread for running gallery-dl without blocking UI"""
    
    # Signals
    output_line = pyqtSignal(str)      # Emits each line of output (App Log)
    raw_output_line = pyqtSignal(str)  # Emits raw/debug output (Raw Output tab)
    finished = pyqtSignal(dict)        # Emits result when done
    error = pyqtSignal(str)            # Emits error message
    
    def __init__(
        self,
        url: str,
        platform: str,
        output_dir: Optional[Path] = None,
        simulate: bool = False,
        verbose: bool = False,
        test_mode: bool = False,
        dump_json: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ):
        super().__init__()
        self.url = url
        self.platform = platform
        self.output_dir = output_dir
        self.simulate = simulate
        self.verbose = verbose
        self.test_mode = test_mode
        self.dump_json = dump_json
        self.date_from = date_from
        self.date_to = date_to
        self.runner = GalleryDLRunner()
        self._process = None
        self._aborted = False
        
    def run(self):
        """Run gallery-dl in background thread"""
        try:
            # Callback for output lines
            def output_callback(line: str):
                self.output_line.emit(line)

            # Capture process reference so abort() can kill it
            def process_callback(process):
                self._process = process

            # Callback for raw output lines (JSON, debug data → Raw Output tab)
            def raw_output_callback(line: str):
                self.raw_output_line.emit(line)

            if self.test_mode:
                # Test connection mode (no timeout - runs until complete)
                result = self.runner.test_connection(
                    platform=self.platform,
                    test_url=self.url,
                    log_callback=output_callback,
                    raw_log_callback=raw_output_callback
                )
            else:
                # Regular run mode
                result = self.runner.run(
                    url=self.url,
                    platform=self.platform,
                    output_dir=self.output_dir,
                    simulate=self.simulate,
                    verbose=self.verbose,
                    dump_json=self.dump_json,
                    date_from=self.date_from,
                    date_to=self.date_to,
                    progress_callback=output_callback,
                    process_callback=process_callback
                )
            
            # Emit finished signal with result
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))

    def abort(self):
        """Stop the running gallery-dl process and mark as aborted"""
        self._aborted = True
        if self._process:
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except Exception:
                    self._process.kill()
            except Exception:
                pass
