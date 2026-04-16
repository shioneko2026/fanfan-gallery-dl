"""
Centralized theme constants for FanFan Gallery-DL UI.
Single source of truth for colors, fonts, and common styles.

Usage:
    from ui.theme import COLORS, FONTS, STYLES
    label.setStyleSheet(f"color: {COLORS['primary']};")
"""

COLORS = {
    # Brand / accent
    "primary": "#1976d2",
    "primary_dark": "#1565c0",
    "primary_light": "#42a5f5",

    # Status
    "success": "#2e7d32",
    "warning": "#e65100",
    "error": "#c62828",
    "locked": "#757575",

    # Sidebar / navigation
    "sidebar_bg": "#fafafa",
    "sidebar_hover": "#e3f2fd",
    "sidebar_active": "#bbdefb",
    "sidebar_text": "#555",
    "sidebar_active_text": "#1976d2",

    # Content area
    "content_bg": "#ffffff",
    "text_primary": "#333333",
    "text_secondary": "#666666",
    "text_hint": "#888888",
    "text_muted": "#999999",
    "border": "#e0e0e0",

    # Log panel (dark theme)
    "log_bg": "#1e1e1e",
    "log_text": "#d4d4d4",
    "log_tab_bg": "#2d2d2d",
    "log_tab_border": "#3c3c3c",
    "log_tab_text": "#aaaaaa",
    "log_button_bg": "#3d3d3d",

    # File type colors
    "file_video": "#00acc1",
    "file_image": "#888888",
    "file_zip": "#e65100",

    # Update banner
    "banner_bg": "#e3f2fd",
    "banner_text": "#1565c0",
}

FONTS = {
    "ui": "Segoe UI",
    "monospace": "Consolas",
    "monospace_fallback": "Courier New",
}

# Common reusable style fragments
STYLES = {
    "group_box": """
        QGroupBox {
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-top: 10px;
            padding: 14px 12px 10px 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 6px;
        }
    """,
    "page_title": f"font-size: 24px; font-weight: bold; color: {COLORS['text_primary']};",
    "page_desc": f"color: {COLORS['text_secondary']}; font-size: 12px;",
    "hint_label": f"color: {COLORS['text_hint']}; font-weight: normal;",
}
