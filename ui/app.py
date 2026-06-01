from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

import config
from core.recorder import Recorder, SAMPLE_RATE
from core.transcriber import Transcriber, ModelLoader, TranscribeWorker
from core.typer import TextTyper
from core.hotkey import HotkeyManager
from ui.tray import TrayIcon


class Voice2TextApp(QObject):
    # Signals used to marshal hotkey callbacks onto the Qt main thread
    _sig_start = pyqtSignal()
    _sig_stop = pyqtSignal()

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.cfg = config.load()

        self.recorder = Recorder()
        self.transcriber = Transcriber()
        self.typer = TextTyper()
        self.hotkeys = HotkeyManager()
        self.tray = TrayIcon(self)

        self._recording = False
        self._busy = False
        self._worker: TranscribeWorker | None = None
        self._loader: ModelLoader | None = None

        self._sig_start.connect(self._on_start)
        self._sig_stop.connect(self._on_stop)

        self.tray.show()
        self._start_hotkeys()
        self._load_model()

    # ── model ──────────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        self.tray.set_status("loading")
        self._loader = ModelLoader(
            self.transcriber, self.cfg["model_size"], self.cfg["device"]
        )
        self._loader.done.connect(self._model_ready)
        self._loader.failed.connect(self._model_failed)
        self._loader.start()

    @pyqtSlot()
    def _model_ready(self) -> None:
        self.tray.set_status("ready")

    @pyqtSlot(str)
    def _model_failed(self, err: str) -> None:
        self.tray.set_status("error")
        self.tray.notify("Model Load Failed", err)

    # ── hotkeys ────────────────────────────────────────────────────────────────

    def _start_hotkeys(self) -> None:
        self.hotkeys.configure(self.cfg, self._sig_start.emit, self._sig_stop.emit)
        self.hotkeys.start()

    @pyqtSlot()
    def _on_start(self) -> None:
        if self._recording or self._busy:
            return
        if not self.transcriber.is_ready():
            self.tray.notify("Not Ready", "Model is still loading, please wait...")
            return
        try:
            self.recorder.start(device=self.cfg.get("audio_device_index"))
            self._recording = True
            self.tray.set_status("recording")
        except Exception as e:
            self.tray.notify("Recording Error", str(e))

    @pyqtSlot()
    def _on_stop(self) -> None:
        if not self._recording:
            return
        self._recording = False
        audio = self.recorder.stop()

        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            self.tray.set_status("ready")
            return

        self._busy = True
        self.tray.set_status("transcribing")
        self._worker = TranscribeWorker(self.transcriber, audio, self.cfg["language"])
        self._worker.done.connect(self._on_transcribed)
        self._worker.failed.connect(self._on_transcribe_failed)
        self._worker.start()

    @pyqtSlot(str)
    def _on_transcribed(self, text: str) -> None:
        self._busy = False
        self.tray.set_status("ready")
        if text:
            self.typer.type_text(text)

    @pyqtSlot(str)
    def _on_transcribe_failed(self, err: str) -> None:
        self._busy = False
        self.tray.set_status("ready")
        self.tray.notify("Transcription Failed", err)

    # ── public ─────────────────────────────────────────────────────────────────

    def reload_config(self) -> None:
        self.cfg = config.load()
        self.hotkeys.stop()
        self._start_hotkeys()
        self._load_model()

    def quit(self) -> None:
        self.hotkeys.stop()
        if self._recording:
            self.recorder.stop()
        self.app.quit()
