"""How the user's system writes a short date and a time (Windows regional settings), so the page shows dates the way the person reads
them: 18.11.2026, 11/18/2026, 2026-11-18. The page falls back on the browser's own locale where this gives nothing."""
from __future__ import annotations

import sys

LOCALE_SSHORTDATE = 0x1F
LOCALE_SSHORTTIME = 0x79


def _info(kind: int) -> str:
    import ctypes

    buf = ctypes.create_unicode_buffer(80)
    # LOCALE_NAME_USER_DEFAULT is a null name: the regional format the user chose, not the display language
    if not ctypes.windll.kernel32.GetLocaleInfoEx(None, kind, buf, len(buf)):
        return ""
    return buf.value


def formats() -> dict:
    """{"date": "dd.MM.yyyy", "time": "HH:mm"} in Windows' pattern letters; empty strings where the system does not say."""
    if sys.platform != "win32":
        return {"date": "", "time": ""}
    try:
        return {"date": _info(LOCALE_SSHORTDATE), "time": _info(LOCALE_SSHORTTIME)}
    except Exception:  # noqa: BLE001 - a missing format is not worth a failed page
        return {"date": "", "time": ""}
