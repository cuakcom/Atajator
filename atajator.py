"""
Atajator - Sugeridor de atajos de teclado en tiempo real.
Monitorea clicks del ratón y muestra qué atajo de teclado
podrías haber usado en su lugar.

Uso: python atajator.py
Sin dependencias externas. Solo Python stdlib (ctypes + tkinter).
"""
import sys
import threading
import tkinter as tk

from logger           import log, LOG_PATH
from mouse_hook       import MouseHook
from app_detector     import AppDetector
from shortcut_matcher import ShortcutMatcher
from overlay          import ShortcutOverlay
from tray             import TrayIcon


class Atajator:
    def __init__(self):
        self._enabled = True

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Atajator")

        self.overlay  = ShortcutOverlay(self.root)
        self.detector = AppDetector()
        self.matcher  = ShortcutMatcher()

        self.hook = MouseHook(self._on_click_thread)
        self._hook_thread = threading.Thread(
            target=self._run_hook, daemon=True, name="mouse-hook"
        )

        self.tray = TrayIcon(
            tooltip   = "Atajator - clic derecho para opciones",
            on_toggle = self._on_toggle,
            on_exit   = self._on_exit,
        )

    def _run_hook(self):
        try:
            self.hook.start()
        except Exception as e:
            log(f"HOOK ERROR: {type(e).__name__}: {e}")

    def _on_click_thread(self, x: int, y: int):
        if self._enabled:
            self.root.after(0, self._process_click, x, y)

    def _process_click(self, x: int, y: int):
        try:
            info = self.detector.get_info(x, y)
            log(f"CLICK ({x},{y}) proc={info.get('process')!r} "
                f"region={info.get('region')!r} "
                f"ctrl_text={info.get('control_text')!r} "
                f"class={info.get('class_name')!r}")
            shortcut = self.matcher.find(info)
            if shortcut:
                log(f"MATCH {shortcut['shortcut']} - {shortcut['action']} (score={shortcut.get('confidence')})")
                self.overlay.show(shortcut)
            else:
                log("no match")
        except Exception as e:
            log(f"PROCESS CLICK ERROR: {type(e).__name__}: {e}")

    def _on_toggle(self, enabled: bool):
        self._enabled = enabled
        log(f"TOGGLE enabled={enabled}")

    def _on_exit(self):
        log("EXIT requested from tray")
        self.hook.stop()
        self.root.after(0, self.root.quit)

    def run(self):
        log("=" * 50)
        log(f"Atajator iniciado, log={LOG_PATH}")
        self._hook_thread.start()
        self.tray.start()
        self.root.mainloop()
        log("Atajator terminado")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Atajator solo funciona en Windows.")
        sys.exit(1)
    Atajator().run()
