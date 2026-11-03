"""
StudyPilot - storage layer
==========================
Loads and saves the data file. To move to SQLite later, only this file
needs to change.
"""

import json
import os

from logic import new_store

DATA_FILE = os.environ.get(
    "STUDYPILOT_DATA",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "studypilot_data.json"),
)


def load_data(path=None):
    """Load saved data. If the file is missing or damaged, start fresh."""
    path = path or DATA_FILE
    if not os.path.exists(path):
        return new_store()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, default in new_store().items():
            data.setdefault(key, default)
        return data
    except (json.JSONDecodeError, OSError, AttributeError):
        return new_store()


def save_data(store, path=None):
    """Write to a temporary file first, then swap it in, so a crash mid-save cannot damage the data."""
    path = path or DATA_FILE
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)
    os.replace(tmp, path)
