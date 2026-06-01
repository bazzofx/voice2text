import ctypes
import ctypes.wintypes as wintypes
import time
import threading
import pyperclip

# ── Windows clipboard ──────────────────────────────────────────────────────────

def _copy_to_clipboard(text: str) -> None:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE  = 0x0002
    data = (text + "\0").encode("utf-16-le")
    kernel32 = ctypes.windll.kernel32
    user32   = ctypes.windll.user32
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)
    user32.OpenClipboard(0)
    user32.EmptyClipboard()
    user32.SetClipboardData(CF_UNICODETEXT, h)
    user32.CloseClipboard()


# ── Windows SendInput (Ctrl+V) ─────────────────────────────────────────────────
#
# ULONG_PTR must be pointer-sized: c_size_t = 8 bytes on 64-bit Windows.
# Using c_ulong (4 bytes) makes sizeof(INPUT) = 20 instead of the required 40,
# causing SendInput to silently drop every call.
# MOUSEINPUT must be present in the union so ctypes calculates the correct size.

_ULONG_PTR = ctypes.c_size_t   # 8 bytes on 64-bit, 4 on 32-bit

class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         wintypes.WORD),
        ("wScan",       wintypes.WORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]

class _INPUTunion(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),   # largest member — sets correct union size
        ("ki", _KEYBDINPUT),
    ]

class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type",   wintypes.DWORD),
        ("_input", _INPUTunion),
    ]

_INPUT_KEYBOARD  = 1
_KEYEVENTF_KEYUP = 0x0002
_VK_CONTROL      = 0x11
_VK_V            = 0x56

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
    def type_text(self, text: str, target_hwnd: int = 0) -> None:
        if text:
            threading.Thread(target=self._paste, args=(text,), daemon=True).start()

    def _paste(self, text: str) -> None:
        try:
            _copy_to_clipboard(text)
        except Exception:
            try:
                pyperclip.copy(text)
            except Exception:
                return

        time.sleep(0.05)
        _send_ctrl_v()
