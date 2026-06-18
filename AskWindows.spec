# AskWindows.spec
#
# PyInstaller build spec — produces a single .exe with no installer required.
# Run with:  pyinstaller AskWindows.spec
#
# The output lands in dist/AskWindows/AskWindows.exe
# (onedir mode so the .exe is fast to launch — onefile is slower on Windows)
#

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        # customtkinter ships its own themes/assets that must travel with the exe.
        *collect_data_files('customtkinter'),
    ],
    hiddenimports=[
        # pyttsx3 drivers — include all so Windows SAPI works regardless of
        # which backend PyInstaller discovers at build time.
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'pyttsx3.drivers.nsss',
        'pyttsx3.drivers.espeak',
        # speech_recognition uses pkg_resources internally.
        'pkg_resources.py2_warn',
        *collect_submodules('speech_recognition'),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AskWindows',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no terminal window — clean GUI app
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # uncomment once you have an icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AskWindows',
)
