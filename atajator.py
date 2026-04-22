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
from panel            import ControlPanel
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
        self.panel    = ControlPanel(self.root)
        self.panel.set_matcher(self.matcher)
        self.panel.set_toggle_callback(self._on_toggle)

        self.hook = MouseHook(self._on_click_thread)
        self._hook_thread = threading.Thread(
            target=self._run_hook, daemon=True, name="mouse-hook"
        )

        self.tray = TrayIcon(
            tooltip   = "Atajator — clic derecho para opciones",
            on_toggle = self._on_toggle,
            on_exit   = self._on_exit,
            on_panel  = self._on_open_panel,
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
            info     = self.detector.get_info(x, y)
            shortcut = self.matcher.find(info)

            proc   = info.get("process", "?")
            region = info.get("region", "?")

            if shortcut:
                log(f"MATCH [{proc}] {region} → {shortcut['shortcut']} ({shortcut['action']})")
                self.overlay.show(shortcut)
            else:
                log(f"skip  [{proc}] {region} — sin match")

            self.panel.add_detection(info, shortcut)

        except Exception as e:
            log(f"ERROR en click: {type(e).__name__}: {e}")

    def _on_toggle(self, enabled: bool):
        self._enabled = enabled
        self.panel.set_active(enabled)
        log(f"{'Activado' if enabled else 'Pausado'}")

    def _on_exit(self):
        log("Cerrando Atajator")
        self.hook.stop()
        self.root.after(0, self.root.quit)

    def _on_open_panel(self):
        self.root.after(0, self.panel.show)

    def run(self):
        log("=" * 40)
        log(f"Atajator iniciado")
        self._hook_thread.start()
        self.tray.start()
        self.root.mainloop()
        log("Atajator terminado")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Atajator solo funciona en Windows.")
        sys.exit(1)
    Atajator().run()
