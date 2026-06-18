#
#  user_settings.py
#  AskWindows
#
#  Stores all user preferences to a local JSON file (AppData/Roaming/AskWindows).
#  Mirrors UserSettings.swift — same fields, same defaults.
#

import json
import os
from pathlib import Path


SKILL_OPTIONS  = ["Beginner", "Comfortable", "Pretty Handy"]
TONE_OPTIONS   = ["Friendly but efficient", "Warm and encouraging", "Casual and fun"]
INPUT_OPTIONS  = ["trackpad", "mouse", "unknown"]

INPUT_LABELS = {
    "trackpad": "Trackpad / touchpad",
    "mouse":    "Mouse",
    "unknown":  "Not sure / either",
}

DEFAULTS = {
    "invite_code":  "",
    "name":         "",
    "skill":        "Beginner",
    "tone":         "Friendly but efficient",
    "os_version":   "",
    "input_device": "unknown",
    "text_zoom":    1.2,
}

SERVER_URL = "https://askmac-server.morning-poetry-8fbb.workers.dev"


def _settings_path() -> Path:
    """Return the path to the settings JSON file, creating dirs if needed."""
    base = Path(os.environ.get("APPDATA", Path.home())) / "AskWindows"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


class UserSettings:
    """
    Observable-style settings bag. Load once at startup, save on every change.
    """

    def __init__(self):
        self._data: dict = dict(DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        path = _settings_path()
        if path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                for key, default in DEFAULTS.items():
                    self._data[key] = saved.get(key, default)
            except Exception:
                pass  # corrupt file — use defaults

    def save(self):
        path = _settings_path()
        path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Properties (getters + setters that auto-save)
    # ------------------------------------------------------------------

    def _get(self, key):
        return self._data[key]

    def _set(self, key, value):
        self._data[key] = value
        self.save()

    @property
    def invite_code(self) -> str:  return self._get("invite_code")
    @invite_code.setter
    def invite_code(self, v: str): self._set("invite_code", v)

    @property
    def name(self) -> str:  return self._get("name")
    @name.setter
    def name(self, v: str): self._set("name", v)

    @property
    def skill(self) -> str:  return self._get("skill")
    @skill.setter
    def skill(self, v: str): self._set("skill", v)

    @property
    def tone(self) -> str:  return self._get("tone")
    @tone.setter
    def tone(self, v: str): self._set("tone", v)

    @property
    def os_version(self) -> str:  return self._get("os_version")
    @os_version.setter
    def os_version(self, v: str): self._set("os_version", v)

    @property
    def input_device(self) -> str:  return self._get("input_device")
    @input_device.setter
    def input_device(self, v: str): self._set("input_device", v)

    @property
    def text_zoom(self) -> float:  return float(self._get("text_zoom"))
    @text_zoom.setter
    def text_zoom(self, v: float): self._set("text_zoom", round(v, 2))

    @property
    def is_set_up(self) -> bool:
        return bool(self.invite_code.strip())

    def reset(self):
        self._data = dict(DEFAULTS)
        self.save()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def user_context(self) -> str:
        """One-line summary sent to the server with every question."""
        parts = []
        if self.name:        parts.append(f"Name: {self.name}")
        if self.skill:       parts.append(f"Skill: {self.skill}")
        if self.tone:        parts.append(f"Tone: {self.tone}")
        if self.os_version:  parts.append(f"OS: {self.os_version}")
        if self.input_device and self.input_device != "unknown":
            parts.append(f"Input: {self.input_device}")
        return " | ".join(parts)
