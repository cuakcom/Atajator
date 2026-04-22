"""
Logging a archivo + sistema de observadores para la UI en tiempo real.
"""
import os
import sys
import datetime
import threading

_lock      = threading.Lock()
_observers = []   # callbacks (msg: str) -> None


def _log_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "atajator.log")


LOG_PATH = _log_path()


def add_observer(callback):
    """Registra un callback que recibe cada línea de log en tiempo real."""
    _observers.append(callback)


def remove_observer(callback):
    try:
        _observers.remove(callback)
    except ValueError:
        pass


def log(msg: str):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with _lock, open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    for obs in list(_observers):
        try:
            obs(line)
        except Exception:
            pass
