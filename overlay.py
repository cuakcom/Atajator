"""
Overlay de notificación de atajos de teclado.
Usa tkinter (stdlib). No roba el foco.
"""
import ctypes
import tkinter as tk

GWL_EXSTYLE      = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

DARK_BG   = "#1e1e2e"
ACCENT    = "#89b4fa"
TEXT_MAIN = "#cdd6f4"
TEXT_SUB  = "#a6adc8"
TEXT_HINT = "#585b70"

SHOW_MS   = 3000
FADE_STEP = 0.09
FRAME_MS  = 16


class ShortcutOverlay:
    def __init__(self, root: tk.Tk):
        self.root   = root
        self._popup = None
        self._job_hide = None
        self._job_fade = None

    def show(self, info: dict):
        self._cancel_jobs()
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._build(info)

    def _cancel_jobs(self):
        for attr in ("_job_hide", "_job_fade"):
            job = getattr(self, attr)
            if job:
                self.root.after_cancel(job)
                setattr(self, attr, None)

    def _build(self, info: dict):
        popup = tk.Toplevel(self.root)
        self._popup = popup
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.attributes("-alpha", 0.0)
        popup.configure(bg=DARK_BG)

        outer = tk.Frame(popup, bg=DARK_BG, padx=18, pady=12)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="⌨  Atajo disponible",
                 font=("Segoe UI", 8), fg=TEXT_HINT, bg=DARK_BG).pack(anchor="w")

        tk.Label(outer, text=info["shortcut"],
                 font=("Segoe UI", 15, "bold"), fg=ACCENT, bg=DARK_BG).pack(anchor="w", pady=(2, 0))

        tk.Label(outer, text=info["action"],
                 font=("Segoe UI", 9), fg=TEXT_MAIN, bg=DARK_BG).pack(anchor="w")

        tk.Label(outer, text=info.get("app", ""),
                 font=("Segoe UI", 7), fg=TEXT_SUB, bg=DARK_BG).pack(anchor="w", pady=(4, 0))

        popup.update_idletasks()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        w  = popup.winfo_reqwidth()
        h  = popup.winfo_reqheight()
        popup.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 60}")

        self._no_activate(popup)
        self._fade_in(popup, 0.0)
        self._job_hide = self.root.after(SHOW_MS, self._begin_fade_out)

    @staticmethod
    def _no_activate(popup: tk.Toplevel):
        try:
            hwnd = popup.winfo_id()
            ex   = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass

    def _fade_in(self, popup: tk.Toplevel, alpha: float):
        if not (popup.winfo_exists() and self._popup is popup):
            return
        alpha = min(alpha + FADE_STEP, 0.93)
        popup.attributes("-alpha", alpha)
        if alpha < 0.93:
            self._job_fade = self.root.after(FRAME_MS, self._fade_in, popup, alpha)

    def _begin_fade_out(self):
        if self._popup and self._popup.winfo_exists():
            self._fade_out(self._popup, 0.93)

    def _fade_out(self, popup: tk.Toplevel, alpha: float):
        if not (popup.winfo_exists() and self._popup is popup):
            return
        alpha = max(alpha - FADE_STEP, 0.0)
        popup.attributes("-alpha", alpha)
        if alpha > 0.0:
            self._job_fade = self.root.after(FRAME_MS, self._fade_out, popup, alpha)
        else:
            popup.destroy()
            self._popup = None
