import json
from pathlib import Path

_CONFIG_FILE = Path.home() / ".voice2text" / "config.json"

DEFAULTS: dict = {
    "hotkey": "<ctrl>+<shift>+<space>",
    "mode": "toggle",           # "toggle" or "push_to_talk"
    "model_size": "base",       # tiny | base | small | medium | large-v3
    "language": "auto",
    "device": "auto",           # auto | cpu | cuda
    "audio_device_index": None,
}


def load() -> dict:
    if _CONFIG_FILE.exists():
        try:
            stored = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            return {**DEFAULTS, **stored}
        except Exception:
            pass
    return DEFAULTS.copy()


def save(cfg: dict) -> None:
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
