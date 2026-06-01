import ctypes
import time
import threading
import pyperclip

# ── Windows clipboard ──────────────────────────────────────────────────────────

def _copy_to_clipboard(text: str) -> None:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    data = (text + "\0").encode("utf-16-le")
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    user32.OpenClipboard(0)
    user32.EmptyClipboard()
    user32.SetClipboardData(CF_UNICODETEXT, h)
    user32.CloseClipboard()


# ── Windows SendInput ──────────────────────────────────────────────────────────

_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_VK_CONTROL = 0x11
_VK_V = 0x56


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUTunion)]


def _send_ctrl_v() -> None:
    inputs = (_INPUT * 4)(
        _INPUT(type=_INPUT_KEYBOARD, _input=_INPUTunion(ki=_KEYBDINPUT(wVk=_VK_CONTROL))),
        _INPUT(type=_INPUT_KEYBOARD, _input=_INPUTunion(ki=_KEYBDINPUT(wVk=_VK_V))),
        _INPUT(type=_INPUT_KEYBOARD, _input=_INPUTunion(ki=_KEYBDINPUT(wVk=_VK_V,       dwFlags=_KEYEVENTF_KEYUP))),
        _INPUT(type=_INPUT_KEYBOARD, _input=_INPUTunion(ki=_KEYBDINPUT(wVk=_VK_CONTROL, dwFlags=_KEYEVENTF_KEYUP))),
    )
    ctypes.windll.user32.SendInput(4, inputs, ctypes.sizeof(_INPUT))


# ── Public class ───────────────────────────────────────────────────────────────

class TextTyper:
    def type_text(self, text: str) -> None:
        if text:
            threading.Thread(target=self._paste, args=(text,), daemon=True).start()

    def _paste(self, text: str) -> None:
        # Wait for hotkey keys to fully release before injecting
        time.sleep(0.2)

        try:
            _copy_to_clipboard(text)
        except Exception:
            # Last-resort fallback via pyperclip
            try:
                pyperclip.copy(text)
            except Exception:
                return

        time.sleep(0.05)
        _send_ctrl_v()
