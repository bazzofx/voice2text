import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._active = False

    def start(self, device=None) -> None:
        with self._lock:
            self._frames = []
        self._active = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=device,
            callback=self._cb,
            blocksize=1024,
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status) -> None:
        if self._active:
            with self._lock:
                self._frames.append(indata[:, 0].copy())

    def stop(self) -> np.ndarray | None:
        self._active = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            return np.concatenate(self._frames) if self._frames else None

    @staticmethod
    def list_devices() -> list[dict]:
        return [
            {"index": i, "name": d["name"]}
            for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0
        ]
