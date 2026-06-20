# Ask Windows

A friendly, voice-enabled AI helper for Windows, aimed at non-technical users
switching from Mac. Python + customtkinter front end talking to a shared
Cloudflare Worker backend.

## Requirements
- Python 3.12 (x64)
- Windows 10 or 11

## Development
    python -V:3.12-64 -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python main.py

## Build a distributable
    pip install pyinstaller
    pyinstaller AskWindows.spec

Output: dist/AskWindows/AskWindows.exe

See docs/ for full instructions and the user guide.

