# Architecture

## Overview

Voice2Text is a fully offline application after the first run. The only external connection it ever makes is a one-time model download from Hugging Face. Everything else — recording, transcription, and text injection — happens locally on the machine.

---

## External Connections

### Hugging Face — model download (first run only)

When the app starts for the first time, `faster-whisper` calls the Hugging Face Hub API to download the selected Whisper model weights:

```
https://huggingface.co/Systran/faster-whisper-{model_size}
```

The files are downloaded and cached locally at:

```
C:\Users\<you>\.cache\huggingface\hub\
```

On every subsequent launch the model is loaded from that local cache. No network connection is made again unless you switch to a different model size in Settings.

**No audio ever leaves your machine.** Transcription runs entirely on your CPU (or GPU if configured).

---

## Whisper Models

The app uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), which is an optimised reimplementation of OpenAI's Whisper using CTranslate2. It runs the same model weights as the original but faster and with lower memory usage.

| Model | Download size | RAM usage | Speed | Accuracy |
|-------|--------------|-----------|-------|----------|
| tiny | ~39 MB | ~200 MB | Fastest | Basic |
| base | ~74 MB | ~290 MB | Fast | Good (default) |
| small | ~244 MB | ~490 MB | Moderate | Better |
| medium | ~769 MB | ~1.5 GB | Slower | Very good |
| large-v3 | ~1.5 GB | ~3 GB | Slowest | Best |

Only one model is loaded at a time. Switching model size in Settings triggers a fresh download (if not already cached) and reloads the model into memory.

All models use `int8` quantisation, which halves memory usage with minimal accuracy loss compared to the original `float32` weights.

---

## Application Flow

```
User presses hotkey
        │
        ▼
HotkeyManager (pynput listener thread)
  Detects key combination → emits Qt signal
        │
        ▼ (Qt main thread, via queued signal)
Voice2TextApp._on_start()
  Recorder.start() → opens sounddevice InputStream at 16 kHz
        │
        │  [user speaks]
        │
User presses hotkey again
        │
        ▼
Voice2TextApp._on_stop()
  Recorder.stop() → returns numpy float32 array of raw audio
        │
        ▼
TranscribeWorker (QThread)
  Transcriber.transcribe(audio)
    → faster-whisper splits audio into segments
    → VAD filter removes silence (min 500 ms silence gap)
    → Whisper model runs inference on each segment
    → returns joined text string
        │
        ▼ (Qt main thread, via signal)
Voice2TextApp._on_transcribed(text)
  TextTyper.type_text(text)
        │
        ▼ (daemon thread)
  _copy_to_clipboard()  — writes text via Windows OpenClipboard / SetClipboardData
  _send_ctrl_v()        — fires Ctrl+V via Windows SendInput API
        │
        ▼
Text appears in the active window
```

---

## Threading Model

The app uses three threads to keep the UI responsive:

| Thread | What runs there |
|--------|----------------|
| Qt main thread | UI, tray icon, signal/slot callbacks |
| pynput listener thread | Global keyboard hook — detects hotkey presses |
| QThread (ModelLoader / TranscribeWorker) | Model loading and transcription |

Hotkey callbacks run in the pynput thread. They communicate to the Qt main thread by emitting Qt signals (`_sig_start`, `_sig_stop`), which are automatically queued and delivered safely.

---

## Key Files

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point — creates QApplication |
| `config.py` | Loads and saves settings from `~/.voice2text/config.json` |
| `core/recorder.py` | Opens microphone stream via sounddevice, collects float32 audio frames |
| `core/transcriber.py` | Wraps faster-whisper; handles model loading and inference |
| `core/hotkey.py` | Global hotkey listener via pynput; supports toggle and push-to-talk |
| `core/typer.py` | Writes text to Windows clipboard and fires Ctrl+V via SendInput |
| `ui/app.py` | Orchestrates all components; manages state machine |
| `ui/tray.py` | System tray icon with coloured status dot and right-click menu |
| `ui/settings_dialog.py` | Settings window — hotkey, model, language, device, microphone |

---

## Audio Format

The microphone is captured at **16 000 Hz, mono, float32**. This is the exact format Whisper was trained on so no resampling or conversion is needed before passing the audio to the model.
