import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._params: tuple | None = None

    def is_ready(self) -> bool:
        return self._model is not None

    def ensure_loaded(self, model_size: str, device: str) -> None:
        # "auto" always means CPU — CUDA requires a full CUDA Toolkit install
        # and must be explicitly selected by the user in Settings.
        if device in ("auto", "cpu"):
            device, compute_type = "cpu", "int8"
        else:
            compute_type = "int8"
        params = (model_size, device, compute_type)
        if params != self._params:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
            self._params = params

    def transcribe(self, audio: np.ndarray, language: str) -> str:
        assert self._model is not None, "Model not loaded"
        lang = None if language == "auto" else language
        segments, _ = self._model.transcribe(
            audio,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        return "".join(s.text for s in segments).strip()


class ModelLoader(QThread):
    done = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, transcriber: Transcriber, model_size: str, device: str) -> None:
        super().__init__()
        self.transcriber = transcriber
        self.model_size = model_size
        self.device = device

    def run(self) -> None:
        try:
            self.transcriber.ensure_loaded(self.model_size, self.device)
            self.done.emit()
        except Exception as e:
            self.failed.emit(str(e))


class TranscribeWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, transcriber: Transcriber, audio: np.ndarray, language: str) -> None:
        super().__init__()
        self.transcriber = transcriber
        self.audio = audio
        self.language = language

    def run(self) -> None:
        try:
            text = self.transcriber.transcribe(self.audio, self.language)
            self.done.emit(text)
        except Exception as e:
            self.failed.emit(str(e))
