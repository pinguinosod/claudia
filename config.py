"""User configuration — key bindings and other preferences."""

import json
import os
import tempfile

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_DEFAULT: dict = {
    "lane_keys": ["d", "f", "j", "k"],
}


def load() -> dict:
    """Return config dict, falling back to defaults for missing keys."""
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return {**_DEFAULT, **data}
        except Exception:
            pass
    return dict(_DEFAULT)


def save(cfg: dict) -> None:
    """Write atomically via temp file + rename."""
    dir_ = os.path.dirname(CONFIG_PATH)
    try:
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass
