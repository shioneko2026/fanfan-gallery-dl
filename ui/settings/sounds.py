"""
Settings - Sounds & Display
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QCheckBox, QSlider, QGroupBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SoundsDisplayPage(QWidget):
    """Sounds & Display settings page"""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setFont(QFont("Segoe UI", 10))
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        # Page title
        title = QLabel("Sounds & Display")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        desc = QLabel("Configure notification sounds and display preferences.")
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)

        # --- Notification Sounds ---
        sound_group = QGroupBox("Notification Sounds")
        sound_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-family: 'Segoe UI';
                font-size: 13px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        sound_layout = QVBoxLayout()

        # Enable beep checkbox
        self.beep_enabled = QCheckBox("Play notification beep when scan or download completes")
        self.beep_enabled.setStyleSheet("font-weight: normal; padding: 5px;")
        self.beep_enabled.toggled.connect(self._on_beep_toggled)
        sound_layout.addWidget(self.beep_enabled)

        # Volume slider
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        volume_label.setStyleSheet("font-weight: normal;")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #e0e0e0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1976d2;
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #1976d2;
                border-radius: 3px;
            }
        """)

        self.volume_value_label = QLabel("50%")
        self.volume_value_label.setStyleSheet("font-weight: normal; min-width: 35px;")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_value_label.setText(f"{v}%")
        )

        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider, 1)
        volume_layout.addWidget(self.volume_value_label)

        sound_layout.addLayout(volume_layout)

        # Beep frequency (pitch)
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Pitch:")
        freq_label.setStyleSheet("font-weight: normal;")

        self.freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.freq_slider.setMinimum(300)
        self.freq_slider.setMaximum(2000)
        self.freq_slider.setValue(800)
        self.freq_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.freq_slider.setTickInterval(200)
        self.freq_slider.setStyleSheet(self.volume_slider.styleSheet())

        self.freq_value_label = QLabel("800 Hz")
        self.freq_value_label.setStyleSheet("font-weight: normal; min-width: 55px;")
        self.freq_slider.valueChanged.connect(
            lambda v: self.freq_value_label.setText(f"{v} Hz")
        )

        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_slider, 1)
        freq_layout.addWidget(self.freq_value_label)

        sound_layout.addLayout(freq_layout)

        # Test beep button
        test_btn = QPushButton("Test Beep")
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #1565c0; }
        """)
        test_btn.clicked.connect(self._test_beep)
        sound_layout.addWidget(test_btn)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        layout.addStretch()

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

    def _on_beep_toggled(self, checked):
        """Enable/disable volume and pitch sliders based on beep toggle"""
        self.volume_slider.setEnabled(checked)
        self.freq_slider.setEnabled(checked)

    def _test_beep(self):
        """Play a test beep with current settings"""
        if not self.beep_enabled.isChecked():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Beep Disabled", "Enable the beep checkbox first.")
            return

        freq = self.freq_slider.value()
        volume = self.volume_slider.value()
        # Duration scales with volume (50-300ms)
        duration = max(50, int(volume * 3))

        try:
            import winsound
            winsound.Beep(freq, duration)
        except Exception:
            from PyQt6.QtWidgets import QApplication
            QApplication.beep()

    def load_settings(self):
        """Load settings from database"""
        beep_enabled = self.db.get_setting("beep_enabled", "true")
        self.beep_enabled.setChecked(beep_enabled in ("true", "True", "1", True))

        volume = self.db.get_setting("beep_volume", "50")
        try:
            self.volume_slider.setValue(int(volume))
        except (ValueError, TypeError):
            self.volume_slider.setValue(50)

        freq = self.db.get_setting("beep_frequency", "800")
        try:
            self.freq_slider.setValue(int(freq))
        except (ValueError, TypeError):
            self.freq_slider.setValue(800)

        self._on_beep_toggled(self.beep_enabled.isChecked())

    def save_settings(self):
        """Save settings to database"""
        self.db.set_setting("beep_enabled", str(self.beep_enabled.isChecked()).lower())
        self.db.set_setting("beep_volume", str(self.volume_slider.value()))
        self.db.set_setting("beep_frequency", str(self.freq_slider.value()))

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Saved", "Sound settings saved successfully.")
