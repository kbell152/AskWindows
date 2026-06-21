# AskWindows.spec
#
# PyInstaller build spec — produces a single .exe with no installer required.
# Run with:  pyinstaller AskWindows.spec
#
# Output lands in dist/AskWindows/AskWindows.exe
# (onedir mode — significantly faster launch than onefile on Windows)
#

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# block_cipher / cipher= removed: PyInstaller 6.x dropped bytecode encryption.

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        # customtkinter ships its own themes and image assets; must travel
        # with the exe or the UI falls back to a broken default appearance.
        *collect_data_files('customtkinter'),

        # SpeechRecognition bundles flac.exe (Windows) which it calls to
        # transcode WAV audio before sending to Google Web Speech.
        # Without this, microphone recognition silently returns nothing —
        # no crash, no error, just empty transcripts every time.
        *collect_data_files('speech_recognition'),
    ],
    hiddenimports=[
        # pyaudio is not always auto-discovered through static import
        # analysis because of its ctypes/extension-module loading pattern.
        'pyaudio',

        # pyttsx3 SAPI5 driver — the Windows TTS backend.
        # espeak is harmless to list (skipped if not installed).
        # nsss (macOS CoreTTS / AppKit) intentionally omitted: not on Windows.
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'pyttsx3.drivers.espeak',

        # SpeechRecognition Python submodules (data files handled above).
        *collect_submodules('speech_recognition'),
    ],
    # win_no_prefer_redirects and win_private_assemblies removed:
    # deprecated and removed in PyInstaller 5.3+; cause TypeError if passed.
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)
# cipher= removed from PYZ: encryption feature dropped in PyInstaller 6.0.

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AskWindows',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,

    # UPX disabled: it can corrupt .pyd extension binaries (pyaudio's
    # _portaudio.pyd, tkinter's _tkinter.pyd), producing a build that
    # appears fine but crashes on launch. The size saving isn't worth it.
    upx=False,

    # console=True during initial validation so any crash prints a traceback
    # to the terminal window.  Flip to False before zipping for distribution.
    console=True,

    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # Uncomment once assets/icon.ico exists (see make_icon.py).
    # icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,          # keep in sync with EXE setting above
    upx_exclude=[],
    name='AskWindows',
)
