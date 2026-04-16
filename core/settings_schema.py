"""
Settings schema — defines types, defaults, and validation for all app settings.
Used by Database.get_typed_setting() to return correctly-typed values
with validation, eliminating scattered int()/float() conversions.
"""

SETTINGS_SCHEMA = {
    # General
    "folder_pattern": {"type": str, "default": "{artist} [{date_latest}] [{source}]"},
    "file_pattern": {"type": str, "default": "{artist} [{date}] {title} [{source}].{ext}"},
    "date_format": {"type": str, "default": "YYYY-MM-DD"},
    "conflict_action": {"type": str, "default": "append_number"},
    "default_save_folder": {"type": str, "default": ""},
    "gallery_dl_source": {"type": str, "default": "codeberg"},

    # Queue
    "concurrent_downloads": {"type": int, "default": 2, "min": 1, "max": 10},
    "skip_abort_threshold": {"type": int, "default": 0, "min": 0, "max": 100},

    # Notifications
    "auto_notify_updates": {"type": str, "default": "true"},

    # App updates
    "auto_check_app_updates": {"type": str, "default": "true"},
    "auto_update_app": {"type": str, "default": "false"},

    # Per-platform performance (generated dynamically for each platform)
    # Pattern: {platform}_rate_limit, {platform}_sleep_request, {platform}_retries
}

# Generate per-platform settings
_PLATFORMS = ["fanbox", "fantia", "pixiv", "patreon", "subscribestar"]
_SLEEP_DEFAULTS = {"fanbox": 1.0, "fantia": 1.0, "pixiv": 0.5, "patreon": 0.5, "subscribestar": 0.5}

for _p in _PLATFORMS:
    SETTINGS_SCHEMA[f"{_p}_rate_limit"] = {"type": str, "default": ""}
    SETTINGS_SCHEMA[f"{_p}_sleep_request"] = {"type": float, "default": _SLEEP_DEFAULTS.get(_p, 0.5), "min": 0.0}
    SETTINGS_SCHEMA[f"{_p}_retries"] = {"type": int, "default": 4, "min": 0, "max": 50}


def get_typed_value(raw_value, key):
    """Convert a raw string value to the correct type using the schema.

    Args:
        raw_value: The string value from the database (or None)
        key: The settings key name

    Returns:
        The correctly-typed value, or the schema default if conversion fails.
    """
    schema = SETTINGS_SCHEMA.get(key)
    if schema is None:
        return raw_value  # Unknown key, return as-is

    default = schema["default"]

    if raw_value is None:
        return default

    expected_type = schema["type"]

    try:
        if expected_type == int:
            val = int(raw_value)
            if "min" in schema:
                val = max(val, schema["min"])
            if "max" in schema:
                val = min(val, schema["max"])
            return val
        elif expected_type == float:
            val = float(raw_value)
            if "min" in schema:
                val = max(val, schema["min"])
            return val
        elif expected_type == str:
            return str(raw_value)
        else:
            return raw_value
    except (ValueError, TypeError):
        return default
