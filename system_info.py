#
#  system_info.py
#  AskWindows
#
#  Reads the actual Windows version and turns it into a friendly name.
#  Mirrors SystemInfo.swift — same purpose, Windows edition.
#

import platform
import sys


def _windows_version() -> tuple[int, int, int]:
    """Return (major, minor, build) from the running Windows installation."""
    try:
        v = sys.getwindowsversion()
        return (v.major, v.minor, v.build)
    except AttributeError:
        # Non-Windows (dev/test environment)
        parts = platform.version().split(".")
        def _int(s):
            try: return int(s)
            except: return 0
        return (_int(parts[0]), _int(parts[1]) if len(parts) > 1 else 0,
                _int(parts[2]) if len(parts) > 2 else 0)


def _marketing_name(major: int, minor: int, build: int) -> str:
    """Map Windows version numbers to marketing names."""
    if major == 10 and build >= 22000:
        return "Windows 11"
    if major == 10:
        return "Windows 10"
    if major == 6 and minor == 3:
        return "Windows 8.1"
    if major == 6 and minor == 2:
        return "Windows 8"
    if major == 6 and minor == 1:
        return "Windows 7"
    return f"Windows {major}.{minor}"


class SystemInfo:

    _major, _minor, _build = _windows_version()

    @classmethod
    def version_string(cls) -> str:
        return f"{cls._major}.{cls._minor}.{cls._build}"

    @classmethod
    def marketing_name(cls) -> str:
        return _marketing_name(cls._major, cls._minor, cls._build)

    @classmethod
    def friendly_label(cls) -> str:
        """e.g. 'Windows 11 (10.0.26100)'"""
        return f"{cls.marketing_name()} ({cls.version_string()})"

    @classmethod
    def detected_os_value(cls) -> str:
        """Short string sent to the server, e.g. 'Windows 11 10.0.26100'"""
        return f"{cls.marketing_name()} {cls.version_string()}"
