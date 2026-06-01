import threading
from pynput import keyboard as kb


class HotkeyManager:
    def __init__(self) -> None:
        self._listener: kb.Listener | None = None
        self._hotkey: kb.HotKey | None = None
        self._ptt_keys: set = set()
        self._ptt_active: set = set()
        self._on_start = None
        self._on_stop = None
        self._mode = "toggle"
        self._recording = False
        self._lock = threading.Lock()

    def configure(self, cfg: dict, on_start, on_stop) -> None:
        self._on_start = on_start
        self._on_stop = on_stop
        self._mode = cfg.get("mode", "toggle")
        hotkey_str = cfg.get("hotkey", "<ctrl>+<shift>+<space>")
        parsed = kb.HotKey.parse(hotkey_str)

        if self._mode == "toggle":
            self._hotkey = kb.HotKey(parsed, self._handle_toggle)
            self._ptt_keys = set()
        else:
            self._hotkey = None
            self._ptt_keys = set(parsed)

    def _handle_toggle(self) -> None:
        with self._lock:
            if not self._recording:
                self._recording = True
                call = self._on_start
            else:
                self._recording = False
                call = self._on_stop
        call()

    def start(self) -> None:
        if self._listener:
            self._listener.stop()
        self._recording = False
        self._ptt_active = set()
        self._listener = kb.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def _on_press(self, key) -> None:
        canonical = self._listener.canonical(key)
        if self._hotkey:
            self._hotkey.press(canonical)
        if self._ptt_keys:
            self._ptt_active.add(canonical)
            if self._ptt_keys.issubset(self._ptt_active):
                with self._lock:
                    if not self._recording:
                        self._recording = True
                        threading.Thread(target=self._on_start, daemon=True).start()

    def _on_release(self, key) -> None:
        canonical = self._listener.canonical(key)
        if self._hotkey:
            self._hotkey.release(canonical)
        if self._ptt_keys:
            self._ptt_active.discard(canonical)
            with self._lock:
                if self._recording and not self._ptt_keys.issubset(self._ptt_active):
                    self._recording = False
                    threading.Thread(target=self._on_stop, daemon=True).start()

    def reset_state(self) -> None:
        with self._lock:
            self._recording = False

    def stop(self) -> None:
        with self._lock:
            self._recording = False
        if self._listener:
            self._listener.stop()
            self._listener = None
