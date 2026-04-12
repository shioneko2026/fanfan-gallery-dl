"""
FanFan Gallery-DL Application
Main entry point
"""
import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from ui.main_window import MainWindow


def main():
    try:
        # Enable high DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("FanFan Gallery-DL")
        app.setOrganizationName("GalleryDL")

        window = MainWindow()
        window.show()

        # Startup update check — 2s delay so window renders first
        QTimer.singleShot(2000, window.run_startup_update_check)

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        print("\nFull traceback:")
        traceback.print_exc()

        # Try to show error dialog if QApplication exists
        try:
            if QApplication.instance():
                QMessageBox.critical(
                    None,
                    "Startup Error",
                    f"Failed to start FanFan Gallery-DL:\n\n{str(e)}\n\nCheck console for details."
                )
        except:
            pass

        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
