import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "sesyaz"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "model": "gpt-4o-mini-transcribe",
    "output_mode": "clipboard",  # "clipboard" | "paste" | "clipboard+paste"
    "language": "",              # empty = auto-detect; ISO 639-1 e.g. "tr", "en"
    "stay_open": False,          # keep overlay open after transcription for editing
    "window_x": None,            # saved drag position (None = center-bottom default)
    "window_y": None,
    "first_run": True,
}


class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data = dict(DEFAULTS)
        if CONFIG_FILE.exists():
            try:
                self._data.update(json.loads(CONFIG_FILE.read_text()))
            except (json.JSONDecodeError, OSError):
                pass

    def get(self, key: str, fallback=None):
        return self._data.get(key, fallback)

    def set(self, key: str, value):
        self._data[key] = value
        CONFIG_FILE.write_text(json.dumps(self._data, indent=2))
