# AskWindows — Project Instructions
**Last updated: June 2026 — v1.0**

This document is the master reference for the AskWindows project. It mirrors
AskMac_Instructions.md in structure and intent — one document to understand,
maintain, and extend the app.

---

## 1. What AskWindows Is

Ask Windows is the Windows companion to Ask Mac. It gives non-technical Windows
users a friendly, patient AI helper — the same concept and the same backend, just
native on Windows. Target user: someone switching from Mac to Windows, or anyone
who finds Windows unfamiliar and occasionally intimidating.

Same scope as Ask Mac: Windows and common consumer apps. Politely declines
questions outside that scope.

---

## 2. Repository

**GitHub:** https://github.com/kbell152/AskMac
*(Lives in the same repo as Ask Mac, in a sibling folder)*

**Structure:**
```
AskMac (repo root)
├── AskMac-App/                  ← macOS Swift app
├── AskWindows-App/              ← Windows Python app  ← YOU ARE HERE
│   ├── main.py                  ← Entry point
│   ├── chat_view.py             ← Main chat screen + settings sheet
│   ├── welcome_view.py          ← First-run setup screen
│   ├── mic_input.py             ← Microphone + speech-to-text
│   ├── speech.py                ← Text-to-speech (Windows SAPI)
│   ├── user_settings.py         ← Settings persistence (JSON in AppData)
│   ├── system_info.py           ← Windows version detection
│   ├── requirements.txt         ← pip dependencies
│   └── AskWindows.spec          ← PyInstaller build spec
├── server/
│   └── worker.js                ← Shared Cloudflare Worker (unchanged)
└── docs/
    ├── AskMac_Instructions.md
    ├── AskMac_UserGuide.md
    ├── AskWindows_Instructions.md   ← this file
    └── AskWindows_UserGuide.md
```

---

## 3. How the App Works (overview)

Identical flow to Ask Mac:

1. First launch → **Welcome screen** (invite code + personalisation).
2. Once set up → **Chat screen** (type or speak questions).
3. Questions sent to the **shared Cloudflare Worker** with user context.
4. Worker validates invite code, calls **Claude API**, returns answer.
5. Answer displayed in chat; can be **read aloud** via Windows SAPI.
6. **Conversation mode**: hands-free loop — listens, auto-sends after
   4 seconds of silence, speaks answer, re-arms mic.

Settings stored in `%APPDATA%\AskWindows\settings.json`.

---

## 4. Python Source Files

All files live in `AskWindows-App/`. Current version: **v1.0**

### main.py
App entry point. Creates `AskWindowsApp` (a `ctk.CTk` window), loads
`UserSettings`, and switches between `WelcomeView` and `ChatView` based on
`settings.is_set_up`. Mirrors `AskMacApp.swift`.

### chat_view.py
The main chat screen. Mirrors `ChatView` in `ContentView.swift`. Contains:
- `ChatView` — chat bubbles, input bar, voice buttons, conversation mode
- `SettingsSheet` — `ctk.CTkToplevel` for name/skill/tone + "Start over"

Conversation mode state machine mirrors Swift exactly:
1. Tap waveform → `_start_conversation_mode()` → `_start_conversation_listen()`
2. Each recognition segment calls `_on_conv_transcript()` → resets silence timer
3. After 4 s silence → `_on_silence_timeout()` → `_send_in_conversation_mode()`
4. Answer fetched → `speak(reply, on_done=_on_speech_done_in_conv_mode)`
5. Speech finishes → 800 ms pause → `_rearm_after_speech()` → listen again
6. Tap waveform again → `_stop_conversation_mode()`

### welcome_view.py
First-run setup screen in a `CTkScrollableFrame`. Same fields as
`WelcomeView.swift`. Windows version auto-detected via `SystemInfo`, shown
back to the user with a checkbox to override.

### mic_input.py
Microphone capture via `pyaudio` + `SpeechRecognition`. Background thread
continuously captures audio segments and sends them to Google Web Speech
(same reliability trade-off as AskMac's `requiresOnDeviceRecognition = false`).
Results are queued and drained on the UI thread via `drain_callbacks()` called
every 100 ms.

Key decisions:
- Google Web Speech used by default (`USE_OFFLINE = False`). Set to `True` to
  use Vosk for fully offline recognition, but this requires downloading a Vosk
  model — do not change without testing.
- `pause_threshold = 0.8` keeps recognition segments short; 4-second silence
  detection is handled by `chat_view.py`'s `_silence_timer`, not by the
  recogniser itself.
- `drain_callbacks()` pattern keeps all UI updates on the main thread —
  tkinter is not thread-safe.

### speech.py
TTS via `pyttsx3` (Windows SAPI backend). Background thread so the UI never
blocks. Mirrors `Speech.swift`:
- Auto-picks the best available English voice (prefers Zira/David/Mark/Aria).
- Rate set to 0.95× default for clarity.
- Strips markdown before speaking.
- `on_done` callback fires when an utterance finishes naturally — used by
  conversation mode to re-arm the mic.

### user_settings.py
Stores preferences in `%APPDATA%\AskWindows\settings.json`. Same fields as
`UserSettings.swift`: invite_code, name, skill, tone, os_version, input_device,
text_zoom. `is_set_up` property mirrors the Swift computed property.

### system_info.py
Reads Windows version via `sys.getwindowsversion()` and maps major/minor/build
to marketing names (Windows 11, Windows 10, etc.). Mirrors `SystemInfo.swift`.

---

## 5. The Server (Cloudflare Worker)

**Unchanged from Ask Mac.** The same worker serves both apps.

**URL:** https://askmac-server.morning-poetry-8fbb.workers.dev

The worker doesn't care whether the client is macOS or Windows — it only sees
`inviteCode`, `question`, and `userContext`. The Windows app sends the same
JSON shape as the Mac app.

For full server documentation, see `AskMac_Instructions.md §5`.

---

## 6. Development Setup

### Prerequisites
- Python 3.11 or later (3.12 recommended)
- Windows 10 or 11 (for full SAPI voice support)

### Install dependencies
```
cd AskWindows-App
pip install -r requirements.txt
```

**pyaudio on Windows:** If `pip install pyaudio` fails, download the
pre-built wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
and install with `pip install <wheel_file>.whl`.

### Run in development
```
python main.py
```

---

## 7. Building a Distributable .exe

Uses PyInstaller. Build on Windows (not WSL — PyInstaller must target the same
platform it runs on).

```
pip install pyinstaller
cd AskWindows-App
pyinstaller AskWindows.spec
```

Output: `dist/AskWindows/AskWindows.exe` (onedir mode — the whole folder is
the distributable). Zip the `dist/AskWindows/` folder and send it.

### Installing on a new Windows PC
1. Unzip the folder anywhere (Desktop is fine).
2. Double-click `AskWindows.exe`.
3. If Windows Defender SmartScreen appears, click **More info** → **Run anyway**.
   (Same situation as AskMac's right-click-to-open on macOS — no code signing.)

### Future: code signing
A code signing certificate removes the SmartScreen warning. Cost ~$100-$300/year
from a CA like DigiCert or Sectigo. Worth doing if distributing to more than a
handful of people.

---

## 8. Voice Features

### Text-to-speech (read aloud)
Every answer has a 🔊 button. Uses Windows SAPI via pyttsx3. Automatically
picks the best available English voice — if the user has downloaded high-quality
voices via Windows Settings → Time & Language → Speech, those will be used.

### Single-shot mic
Tap 🎤, speak, tap ⏹. Text appears in the input box. Press Enter or tap ➤.

### Conversation mode
Tap 〜 to start. Listens continuously. After 4 seconds of silence, sends
automatically, speaks the answer, then listens again. Tap 〜 to stop.
Tap 🎤 during conversation mode to mute/unmute.

Status label shows: **Listening… / Thinking… / Speaking… / Muted**

---

## 9. Text Zoom

- Ctrl + (or Ctrl =): make text bigger (max 2.0×)
- Ctrl -: make text smaller (min 0.8×)
- Ctrl 0: reset to default (1.2×)

Zoom level saved to settings.json and persists between launches.

---

## 10. Known Issues and Decisions

- **Google Web Speech**: requires an internet connection for mic input.
  Set `USE_OFFLINE = True` in `mic_input.py` + install Vosk for offline use,
  but test thoroughly — recognition quality varies.
- **pyaudio install**: can be tricky on Windows without a C compiler. Use the
  pre-built wheel from the Gohlke site if pip fails.
- **No app icon**: using default window icon. Add `icon='assets/icon.ico'`
  to `AskWindows.spec` once an icon exists.
- **SmartScreen warning**: users must click "More info → Run anyway" on first
  launch. Resolved by code signing.
- **pyttsx3 voice quality**: Windows SAPI voices vary by Windows version.
  Windows 11 ships with higher-quality neural voices (Aria, Guy, Jenny)
  that pyttsx3 can access. Windows 10 voices are more robotic.
- **Conversation mode + background noise**: same caveat as AskMac. The
  4-second silence timer helps but doesn't eliminate stray transcriptions.

---

## 11. Future Ideas (not built)

- Custom app icon (.ico)
- Code signing certificate to remove SmartScreen warning
- Offline speech recognition via Vosk
- Voice selection in Settings
- Interrupt speech immediately when user starts talking in conversation mode
- Cross-platform single codebase (already possible — swap SAPI for espeak
  on Linux, nsss on macOS inside speech.py)
