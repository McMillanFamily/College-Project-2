"""
StudyPilot - storage layer
==========================
Loads and saves the data file. To move to SQLite later, only this file
needs to change.
"""

import json
import os

import shutil

from logic import new_root

DATA_FILE = os.environ.get(
    "STUDYPILOT_DATA",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "studypilot_data.json"),
)


def load_data(path=None):
    """Load saved data. If the file is missing or damaged, start fresh."""
    path = path or DATA_FILE
    if not os.path.exists(path):
        return new_root()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("data file is not a JSON object")
        for key, default in new_root().items():
            data.setdefault(key, default)
        return data
    except (ValueError, OSError):  # JSONDecodeError is a ValueError
        try:  # keep the damaged file so the next save cannot overwrite it
            shutil.copy(path, path + ".bad")
        except OSError:
            pass
        return new_root()


def save_data(store, path=None):
    """Write to a temporary file first, then swap it in, so a crash mid-save cannot damage the data."""
    path = path or DATA_FILE
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)
    os.replace(tmp, path)
