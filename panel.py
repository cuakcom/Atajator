"""
Panel de control de Atajator.
Muestra la app activa, últimas detecciones y logs en tiempo real.
"""
import tkinter as tk
from tkinter import font as tkfont
import ctypes
import ctypes.wintypes
import threading

import logger

# ── Colores (Catppuccin Mocha) ─────────────────────────────────────────
BG        = "#1e1e2e"
BG2       = "#181825"
BG3       = "#313244"
ACCENT    = "#89b4fa"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
YELLOW    = "#f9e2af"
TEXT      = "#cdd6f4"
SUBTEXT   = "#a6adc8"
MUTED     = "#585b70"

MAX_LOG_LINES   = 200
MAX_DETECTIONS  = 10

_user32 = ctypes.windll.user32
_user32.GetForegroundWindow.restype = ctypes.wintypes.HWND


def _current_process() -> str:
    """Devuelve el nombre del proceso en primer plano."""
    import os
    import ctypes.wintypes
    kernel32 = ctypes.windll.kernel32
    kernel32.GetModuleHandleW.restype  = ctypes.wintypes.HMODULE
    kernel32.OpenProcess.restype       = ctypes.wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = ctypes.wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return ""
    try:
        buf  = ctypes.create_unicode_buffer(512)
        size = ctypes.wintypes.DWORD(512)
        kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(h)


class ControlPanel:
    def __init__(self, root: tk.Tk):
        self.root        = root
        self._win        = None
        self._enabled    = True
        self._detections = []   # lista de dicts recientes
        self._log_buffer = []   # líneas de log

        logger.add_observer(self._on_log)

    # ── Mostrar / ocultar ─────────────────────────────────────────────
    def toggle(self):
        if self._win and self._win.winfo_exists():
            self._win.destroy()
            self._win = None
        else:
            self.show()

    def show(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build()

    def _build(self):
        win = tk.Toplevel(self.root)
        self._win = win
        win.title("Atajator — Panel de control")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.minsize(420, 500)

        # Posición: esquina inferior derecha
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"420x560+{sw - 440}+{sh - 610}")

        self._build_header(win)
        self._build_app_section(win)
        self._build_detections_section(win)
        self._build_log_section(win)

        self._schedule_refresh()

    def _build_header(self, parent):
        fr = tk.Frame(parent, bg=BG2, pady=10, padx=16)
        fr.pack(fill="x")

        tk.Label(fr, text="⌨  Atajator", font=("Segoe UI", 13, "bold"),
                 fg=ACCENT, bg=BG2).pack(side="left")

        self._lbl_status = tk.Label(fr, text="● Activo", font=("Segoe UI", 9),
                                    fg=GREEN, bg=BG2)
        self._lbl_status.pack(side="left", padx=(12, 0))

        self._btn_toggle = tk.Button(
            fr, text="Pausar", font=("Segoe UI", 8),
            bg=BG3, fg=TEXT, relief="flat", padx=8, pady=2,
            cursor="hand2", command=self._toggle_active,
            activebackground=ACCENT, activeforeground=BG,
        )
        self._btn_toggle.pack(side="right")

    def _build_app_section(self, parent):
        tk.Label(parent, text="APP EN PRIMER PLANO", font=("Segoe UI", 7),
                 fg=MUTED, bg=BG, anchor="w").pack(fill="x", padx=16, pady=(12, 2))

        fr = tk.Frame(parent, bg=BG3, padx=12, pady=8)
        fr.pack(fill="x", padx=12)
        self._lbl_app = tk.Label(fr, text="—", font=("Segoe UI", 10, "bold"),
                                  fg=TEXT, bg=BG3, anchor="w")
        self._lbl_app.pack(fill="x")

    def _build_detections_section(self, parent):
        tk.Label(parent, text="ÚLTIMAS DETECCIONES", font=("Segoe UI", 7),
                 fg=MUTED, bg=BG, anchor="w").pack(fill="x", padx=16, pady=(12, 2))

        fr = tk.Frame(parent, bg=BG2)
        fr.pack(fill="x", padx=12)
        self._det_frame = fr

        self._det_rows = []
        for _ in range(MAX_DETECTIONS):
            row = tk.Frame(fr, bg=BG2)
            ico = tk.Label(row, text=" ", font=("Segoe UI", 9),
                           fg=MUTED, bg=BG2, width=2)
            ico.pack(side="left")
            sc  = tk.Label(row, text="", font=("Segoe UI", 9, "bold"),
                           fg=ACCENT, bg=BG2, width=14, anchor="w")
            sc.pack(side="left")
            act = tk.Label(row, text="", font=("Segoe UI", 9),
                           fg=TEXT, bg=BG2, anchor="w")
            act.pack(side="left", fill="x", expand=True)
            app = tk.Label(row, text="", font=("Segoe UI", 7),
                           fg=MUTED, bg=BG2, anchor="e")
            app.pack(side="right")
            self._det_rows.append((row, ico, sc, act, app))

    def _build_log_section(self, parent):
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x", padx=12, pady=(12, 2))
        tk.Label(hdr, text="LOG EN VIVO", font=("Segoe UI", 7),
                 fg=MUTED, bg=BG, anchor="w").pack(side="left")
        tk.Button(hdr, text="Limpiar", font=("Segoe UI", 7),
                  bg=BG, fg=MUTED, relief="flat", cursor="hand2",
                  command=self._clear_log, activebackground=BG3,
                  activeforeground=TEXT).pack(side="right")

        frame = tk.Frame(parent, bg=BG2)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._log_text = tk.Text(
            frame, bg=BG2, fg=SUBTEXT, font=("Consolas", 8),
            relief="flat", wrap="word", state="disabled",
            selectbackground=BG3,
        )
        sb = tk.Scrollbar(frame, command=self._log_text.yview,
                          bg=BG3, troughcolor=BG2, relief="flat")
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True, padx=4, pady=4)

        # Cargar log existente
        for line in self._log_buffer[-MAX_LOG_LINES:]:
            self._append_log_text(line)

    # ── Actualizaciones periódicas ────────────────────────────────────
    def _schedule_refresh(self):
        if self._win and self._win.winfo_exists():
            self._refresh_app()
            self._refresh_detections()
            self._win.after(1000, self._schedule_refresh)

    def _refresh_app(self):
        try:
            proc = _current_process()
            self._lbl_app.configure(text=proc or "—")
        except Exception:
            pass

    def _refresh_detections(self):
        rows = list(reversed(self._detections))
        for i, (row, ico, sc, act, app) in enumerate(self._det_rows):
            if i < len(rows):
                d = rows[i]
                if not row.winfo_ismapped():
                    row.pack(fill="x", pady=1)
                ico.configure(text="✓" if d["match"] else "─",
                               fg=GREEN if d["match"] else MUTED)
                sc.configure(text=d.get("shortcut", "sin match"),
                              fg=ACCENT if d["match"] else MUTED)
                act.configure(text=d.get("action", ""),
                               fg=TEXT if d["match"] else MUTED)
                app.configure(text=d.get("app", ""))
            else:
                row.pack_forget()

    # ── Gestión del log ───────────────────────────────────────────────
    def _on_log(self, line: str):
        """Llamado desde cualquier hilo cuando hay nueva línea de log."""
        self._log_buffer.append(line)
        if len(self._log_buffer) > MAX_LOG_LINES:
            self._log_buffer.pop(0)
        if self._win and self._win.winfo_exists():
            self.root.after(0, self._append_log_text, line)

    def _append_log_text(self, line: str):
        try:
            t = self._log_text
            t.configure(state="normal")
            t.insert("end", line + "\n")
            if int(t.index("end-1c").split(".")[0]) > MAX_LOG_LINES:
                t.delete("1.0", "2.0")
            t.see("end")
            t.configure(state="disabled")
        except Exception:
            pass

    def _clear_log(self):
        try:
            self._log_text.configure(state="normal")
            self._log_text.delete("1.0", "end")
            self._log_text.configure(state="disabled")
        except Exception:
            pass

    # ── Registrar una detección ───────────────────────────────────────
    def add_detection(self, info: dict, shortcut: dict | None):
        entry = {
            "match":    shortcut is not None,
            "shortcut": shortcut["shortcut"] if shortcut else "",
            "action":   shortcut["action"]   if shortcut else "",
            "app":      shortcut["app"]      if shortcut else info.get("process", ""),
        }
        self._detections.append(entry)
        if len(self._detections) > MAX_DETECTIONS:
            self._detections.pop(0)

    # ── Pausar / reanudar ─────────────────────────────────────────────
    def _toggle_active(self):
        self._enabled = not self._enabled
        if self._lbl_status and self._lbl_status.winfo_exists():
            if self._enabled:
                self._lbl_status.configure(text="● Activo",  fg=GREEN)
                self._btn_toggle.configure(text="Pausar")
            else:
                self._lbl_status.configure(text="● Pausado", fg=RED)
                self._btn_toggle.configure(text="Reanudar")

    def set_active(self, enabled: bool):
        self._enabled = enabled
        if self._lbl_status and self._lbl_status.winfo_exists():
            if enabled:
                self._lbl_status.configure(text="● Activo",  fg=GREEN)
                self._btn_toggle.configure(text="Pausar")
            else:
                self._lbl_status.configure(text="● Pausado", fg=RED)
                self._btn_toggle.configure(text="Reanudar")

    @property
    def on_toggle_callback(self):
        return self._on_panel_toggle

    def _on_panel_toggle(self):
        self._toggle_active()
        return self._enabled
