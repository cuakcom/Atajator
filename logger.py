"""
Logging a archivo de texto junto al ejecutable.
Permite diagnosticar qué pasa cuando la app se ejecuta sin consola (--windowed).
"""
import os
import sys
import datetime
import threading

_lock = threading.Lock()


def _log_path() -> str:
    # Si corre empaquetado por PyInstaller, escribir junto al .exe
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "atajator.log")


LOG_PATH = _log_path()


def log(msg: str):
    try:
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}\n"
        with _lock, open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
