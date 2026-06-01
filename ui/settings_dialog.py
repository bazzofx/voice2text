import sounddevice as sd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QDialogButtonBox, QKeySequenceEdit,
)
from PyQt6.QtGui import QKeySequence
import config


_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
_LANGUAGES = [
    ("Auto-detect", "auto"),
    ("English",    "en"),
    ("Spanish",    "es"),
    ("French",     "fr"),
    ("German",     "de"),
    ("Italian",    "it"),
    ("Portuguese", "pt"),
    ("Dutch",      "nl"),
    ("Polish",     "pl"),
    ("Russian",    "ru"),
    ("Japanese",   "ja"),
    ("Chinese",    "zh"),
    ("Korean",     "ko"),
    ("Arabic",     "ar"),
]

# pynput ↔ Qt key-name mappings
_TO_QT = {
    "<ctrl>": "Ctrl", "<shift>": "Shift", "<alt>": "Alt", "<cmd>": "Meta",
    "<space>": "Space", "<tab>": "Tab", "<enter>": "Return",
    "<backspace>": "Backspace", "<delete>": "Delete", "<esc>": "Escape",
    "<up>": "Up", "<down>": "Down", "<left>": "Left", "<right>": "Right",
}
_TO_PYNPUT = {v.lower(): k for k, v in _TO_QT.items()}


def _pynput_to_qt(s: str) -> str:
    return "+".join(_TO_QT.get(p, p.capitalize()) for p in s.split("+"))


def _qt_to_pynput(s: str) -> str:
    parts = []
    for p in s.split("+"):
        low = p.strip().lower()
        if low in _TO_PYNPUT:
            parts.append(_TO_PYNPUT[low])
        elif len(low) == 1:
            parts.append(low)
        else:
            # Function keys (f1–f12) and other named keys become <name>
            parts.append(f"<{low}>")
    return "+".join(parts)


class SettingsDialog(QDialog):
    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.cfg = dict(controller.cfg)
        self.setWindowTitle("Voice2Text — Settings")
        self.setMinimumWidth(420)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        # ── Hotkey ──────────────────────────────────────────────────────────
        hk_box = QGroupBox("Hotkey")
        hk_form = QFormLayout(hk_box)

        self._hotkey_edit = QKeySequenceEdit(
            QKeySequence(_pynput_to_qt(self.cfg.get("hotkey", "<ctrl>+<shift>+<space>")))
        )
        hk_form.addRow("Shortcut:", self._hotkey_edit)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Toggle (press once to start, again to stop)", "toggle")
        self._mode_combo.addItem("Push-to-talk (hold to record, release to transcribe)", "push_to_talk")
        idx = self._mode_combo.findData(self.cfg.get("mode", "toggle"))
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)
        hk_form.addRow("Mode:", self._mode_combo)

        layout.addWidget(hk_box)

        # ── Model ────────────────────────────────────────────────────────────
        model_box = QGroupBox("Transcription Model")
        model_form = QFormLayout(model_box)

        self._model_combo = QComboBox()
        self._model_combo.addItems(_MODELS)
        current_model = self.cfg.get("model_size", "base")
        mi = _MODELS.index(current_model) if current_model in _MODELS else 1
        self._model_combo.setCurrentIndex(mi)
        model_form.addRow("Model size:", self._model_combo)

        self._lang_combo = QComboBox()
        for name, code in _LANGUAGES:
            self._lang_combo.addItem(name, code)
        lang = self.cfg.get("language", "auto")
        li = next((i for i, (_, c) in enumerate(_LANGUAGES) if c == lang), 0)
        self._lang_combo.setCurrentIndex(li)
        model_form.addRow("Language:", self._lang_combo)

        self._device_combo = QComboBox()
        self._device_combo.addItem("CPU (default)", "cpu")
        self._device_combo.addItem("CUDA GPU (requires CUDA Toolkit 12 installed)", "cuda")
        device = self.cfg.get("device", "auto")
        di = 1 if device == "cuda" else 0
        self._device_combo.setCurrentIndex(di)
        model_form.addRow("Device:", self._device_combo)

        layout.addWidget(model_box)

        # ── Audio input ───────────────────────────────────────────────────────
        audio_box = QGroupBox("Audio Input")
        audio_form = QFormLayout(audio_box)

        self._audio_combo = QComboBox()
        self._audio_combo.addItem("System default", None)
        try:
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0:
                    self._audio_combo.addItem(d["name"], i)
        except Exception:
            pass
        saved_dev = self.cfg.get("audio_device_index")
        if saved_dev is not None:
            for i in range(self._audio_combo.count()):
                if self._audio_combo.itemData(i) == saved_dev:
                    self._audio_combo.setCurrentIndex(i)
                    break
        audio_form.addRow("Microphone:", self._audio_combo)

        layout.addWidget(audio_box)

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save(self) -> None:
        seq = self._hotkey_edit.keySequence().toString()
        if seq:
            self.cfg["hotkey"] = _qt_to_pynput(seq)
        self.cfg["mode"] = self._mode_combo.currentData()
        self.cfg["model_size"] = self._model_combo.currentText()
        self.cfg["language"] = self._lang_combo.currentData()
        self.cfg["device"] = self._device_combo.currentData()
        self.cfg["audio_device_index"] = self._audio_combo.currentData()
        config.save(self.cfg)
        self.controller.reload_config()
        self.accept()
