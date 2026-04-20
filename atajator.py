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
            target=self.hook.start, daemon=True, name="mouse-hook"
        )

        self.tray = TrayIcon(
            tooltip   = "Atajator",
            on_toggle = self._on_toggle,
            on_exit   = self._on_exit,
        )

    def _on_click_thread(self, x: int, y: int):
        """Llamado desde el hilo del hook. Reenvía al hilo de tkinter."""
        if self._enabled:
            self.root.after(0, self._process_click, x, y)

    def _process_click(self, x: int, y: int):
        """Ejecutado en el hilo principal de tkinter."""
        info     = self.detector.get_info(x, y)
        shortcut = self.matcher.find(info)
        if shortcut:
            self.overlay.show(shortcut)

    def _on_toggle(self, enabled: bool):
        self._enabled = enabled

    def _on_exit(self):
        self.hook.stop()
        self.root.quit()

    def run(self):
        self._hook_thread.start()
        self.tray.start()
        self.root.mainloop()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Atajator solo funciona en Windows.")
        sys.exit(1)
    Atajator().run()
