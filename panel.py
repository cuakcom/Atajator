"""
Panel de control de Atajator.
Pestaña Monitor: app activa, últimas detecciones, log en vivo.
Pestaña Atajos: editor completo de atajos personalizados.
"""
import tkinter as tk
from tkinter import messagebox
import ctypes
import ctypes.wintypes
import json
import os

import logger
from shortcut_matcher import PROCESS_MAP, SHORTCUTS_DIR

# ── Colores ────────────────────────────────────────────────────────────
BG      = "#1e1e2e"
BG2     = "#181825"
BG3     = "#313244"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
TEXT    = "#cdd6f4"
SUBTEXT = "#a6adc8"
MUTED   = "#585b70"

MAX_LOG  = 200
MAX_DET  = 10

_user32   = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_user32.GetForegroundWindow.restype       = ctypes.wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND,
                                              ctypes.POINTER(ctypes.wintypes.DWORD)]
_kernel32.OpenProcess.restype             = ctypes.wintypes.HANDLE
_kernel32.OpenProcess.argtypes            = [ctypes.wintypes.DWORD,
                                              ctypes.wintypes.BOOL,
                                              ctypes.wintypes.DWORD]
_kernel32.CloseHandle.argtypes            = [ctypes.wintypes.HANDLE]


def _current_process() -> str:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = ctypes.wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = _kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return ""
    try:
        buf  = ctypes.create_unicode_buffer(512)
        size = ctypes.wintypes.DWORD(512)
        _kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        return os.path.basename(buf.value)
    finally:
        _kernel32.CloseHandle(h)


# ══════════════════════════════════════════════════════════════════════
class ControlPanel:
    def __init__(self, root: tk.Tk):
        self.root        = root
        self._win        = None
        self._enabled    = True
        self._detections = []
        self._log_buffer = []
        logger.add_observer(self._on_log)

    # ── Mostrar / alternar ─────────────────────────────────────────────
    def toggle(self):
        if self._win and self._win.winfo_exists():
            self._win.destroy(); self._win = None
        else:
            self.show()

    def show(self):
        if self._win and self._win.winfo_exists():
            self._win.lift(); return
        self._build()

    # ── Construcción de la ventana ─────────────────────────────────────
    def _build(self):
        win = tk.Toplevel(self.root)
        self._win = win
        win.title("Atajator — Panel de control")
        win.configure(bg=BG)
        win.resizable(True, True)
        win.minsize(480, 540)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"480x580+{sw-500}+{sh-630}")

        self._build_header(win)
        self._build_tabs(win)

    # ── Cabecera ───────────────────────────────────────────────────────
    def _build_header(self, parent):
        fr = tk.Frame(parent, bg=BG2, pady=8, padx=16)
        fr.pack(fill="x")
        tk.Label(fr, text="⌨  Atajator", font=("Segoe UI", 12, "bold"),
                 fg=ACCENT, bg=BG2).pack(side="left")
        self._lbl_status = tk.Label(fr, text="● Activo",
                                    font=("Segoe UI", 9), fg=GREEN, bg=BG2)
        self._lbl_status.pack(side="left", padx=10)
        self._btn_toggle = _btn(fr, "Pausar", self._toggle_active, side="right")

    # ── Pestañas ───────────────────────────────────────────────────────
    def _build_tabs(self, parent):
        tab_bar = tk.Frame(parent, bg=BG3, height=30)
        tab_bar.pack(fill="x")

        self._content = tk.Frame(parent, bg=BG)
        self._content.pack(fill="both", expand=True)

        self._tabs     = {}
        self._tab_btns = {}

        for key, label in [("monitor", "Monitor"), ("atajos", "Atajos")]:
            frame = tk.Frame(self._content, bg=BG)
            self._tabs[key] = frame
            btn = tk.Button(
                tab_bar, text=label, font=("Segoe UI", 9),
                bg=BG3, fg=SUBTEXT, relief="flat",
                padx=16, pady=4, cursor="hand2",
                command=lambda k=key: self._switch_tab(k),
                activebackground=BG, activeforeground=TEXT,
            )
            btn.pack(side="left")
            self._tab_btns[key] = btn

        self._build_monitor(self._tabs["monitor"])
        self._build_editor(self._tabs["atajos"])
        self._switch_tab("monitor")

    def _switch_tab(self, key: str):
        for k, frame in self._tabs.items():
            frame.pack_forget()
            self._tab_btns[k].configure(bg=BG3, fg=SUBTEXT)
        self._tabs[key].pack(fill="both", expand=True)
        self._tab_btns[key].configure(bg=BG, fg=ACCENT)

    # ══════════════════════════════════════════════════════════════════
    # PESTAÑA MONITOR
    # ══════════════════════════════════════════════════════════════════
    def _build_monitor(self, parent):
        _section(parent, "APP EN PRIMER PLANO")
        fr = tk.Frame(parent, bg=BG3, padx=12, pady=8)
        fr.pack(fill="x", padx=12)
        self._lbl_app = tk.Label(fr, text="—", font=("Segoe UI", 10, "bold"),
                                  fg=TEXT, bg=BG3, anchor="w")
        self._lbl_app.pack(fill="x")

        _section(parent, "ÚLTIMAS DETECCIONES")
        det_fr = tk.Frame(parent, bg=BG2)
        det_fr.pack(fill="x", padx=12)
        self._det_rows = []
        for _ in range(MAX_DET):
            row = tk.Frame(det_fr, bg=BG2)
            ico = tk.Label(row, text=" ", font=("Segoe UI", 9),
                           fg=MUTED, bg=BG2, width=2)
            ico.pack(side="left")
            sc  = tk.Label(row, text="", font=("Segoe UI", 9, "bold"),
                           fg=ACCENT, bg=BG2, width=12, anchor="w")
            sc.pack(side="left")
            act = tk.Label(row, text="", font=("Segoe UI", 9),
                           fg=TEXT, bg=BG2, anchor="w")
            act.pack(side="left", fill="x", expand=True)
            app = tk.Label(row, text="", font=("Segoe UI", 7),
                           fg=MUTED, bg=BG2, anchor="e")
            app.pack(side="right")
            self._det_rows.append((row, ico, sc, act, app))

        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x", padx=12, pady=(10, 2))
        _section_label(hdr, "LOG EN VIVO")
        _btn(hdr, "Limpiar", self._clear_log, side="right", small=True)

        log_fr = tk.Frame(parent, bg=BG2)
        log_fr.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._log_text = tk.Text(log_fr, bg=BG2, fg=SUBTEXT,
                                  font=("Consolas", 8), relief="flat",
                                  wrap="word", state="disabled",
                                  selectbackground=BG3)
        sb = tk.Scrollbar(log_fr, command=self._log_text.yview,
                          bg=BG3, troughcolor=BG2, relief="flat")
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True, padx=4, pady=4)
        for line in self._log_buffer[-MAX_LOG:]:
            self._append_log_text(line)

        self._schedule_refresh()

    def _schedule_refresh(self):
        if self._win and self._win.winfo_exists():
            try:
                self._lbl_app.configure(text=_current_process() or "—")
            except Exception:
                pass
            self._refresh_detections()
            self._win.after(1000, self._schedule_refresh)

    def _refresh_detections(self):
        rows = list(reversed(self._detections))
        for i, (row, ico, sc, act, app) in enumerate(self._det_rows):
            if i < len(rows):
                d = rows[i]
                if not row.winfo_ismapped():
                    row.pack(fill="x", pady=1)
                matched = d["match"]
                ico.configure(text="✓" if matched else "─",
                               fg=GREEN if matched else MUTED)
                sc.configure(text=d.get("shortcut", "sin match"),
                              fg=ACCENT if matched else MUTED)
                act.configure(text=d.get("action", ""), fg=TEXT if matched else MUTED)
                app.configure(text=d.get("app", ""))
            else:
                row.pack_forget()

    def add_detection(self, info: dict, shortcut: dict | None):
        self._detections.append({
            "match":    shortcut is not None,
            "shortcut": shortcut["shortcut"] if shortcut else "",
            "action":   shortcut["action"]   if shortcut else "",
            "app":      shortcut["app"]      if shortcut else info.get("process", ""),
        })
        if len(self._detections) > MAX_DET:
            self._detections.pop(0)

    def _on_log(self, line: str):
        self._log_buffer.append(line)
        if len(self._log_buffer) > MAX_LOG:
            self._log_buffer.pop(0)
        if self._win and self._win.winfo_exists():
            self.root.after(0, self._append_log_text, line)

    def _append_log_text(self, line: str):
        try:
            t = self._log_text
            t.configure(state="normal")
            t.insert("end", line + "\n")
            if int(t.index("end-1c").split(".")[0]) > MAX_LOG:
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

    # ══════════════════════════════════════════════════════════════════
    # PESTAÑA EDITOR DE ATAJOS
    # ══════════════════════════════════════════════════════════════════
    def _build_editor(self, parent):
        # ── Selector de app ───────────────────────────────────────────
        top = tk.Frame(parent, bg=BG, padx=12, pady=8)
        top.pack(fill="x")
        tk.Label(top, text="Aplicación:", font=("Segoe UI", 9),
                 fg=SUBTEXT, bg=BG).pack(side="left")

        self._app_var = tk.StringVar()
        app_names = sorted(PROCESS_MAP.keys())
        self._app_menu = tk.OptionMenu(top, self._app_var, *app_names,
                                       command=self._load_shortcuts_list)
        self._app_menu.configure(bg=BG3, fg=TEXT, relief="flat",
                                  font=("Segoe UI", 9),
                                  activebackground=ACCENT, activeforeground=BG,
                                  highlightthickness=0)
        self._app_menu["menu"].configure(bg=BG3, fg=TEXT, font=("Segoe UI", 9))
        self._app_menu.pack(side="left", padx=(6, 0))

        btn_fr = tk.Frame(top, bg=BG)
        btn_fr.pack(side="right")
        _btn(btn_fr, "+ Añadir", self._open_add_form, side="left")
        self._btn_edit = _btn(btn_fr, "✏ Editar", self._open_edit_form, side="left")
        self._btn_del  = _btn(btn_fr, "✕ Eliminar", self._delete_shortcut, side="left", danger=True)

        # ── Lista de atajos ───────────────────────────────────────────
        list_fr = tk.Frame(parent, bg=BG2)
        list_fr.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        sb = tk.Scrollbar(list_fr, bg=BG3, troughcolor=BG2, relief="flat")
        sb.pack(side="right", fill="y")
        self._shortcut_list = tk.Listbox(
            list_fr, bg=BG2, fg=TEXT, font=("Segoe UI", 9),
            relief="flat", selectbackground=BG3, selectforeground=ACCENT,
            activestyle="none", yscrollcommand=sb.set,
        )
        sb.configure(command=self._shortcut_list.yview)
        self._shortcut_list.pack(fill="both", expand=True, padx=4, pady=4)
        self._shortcut_list.bind("<<ListboxSelect>>", self._on_list_select)

        # ── Formulario de edición ─────────────────────────────────────
        self._form_fr = tk.Frame(parent, bg=BG3, padx=12, pady=10)
        self._form_fr.pack(fill="x", padx=12, pady=(0, 12))
        self._form_visible = False
        self._build_form(self._form_fr)
        self._form_fr.pack_forget()

        # Cargar primera app
        if app_names:
            self._app_var.set(app_names[0])
            self._load_shortcuts_list(app_names[0])

    def _build_form(self, parent):
        fields = [
            ("Acción:",         "e_action",   "Ej: Nueva pestaña"),
            ("Atajo:",          "e_shortcut", "Ej: Ctrl+T"),
            ("Palabras clave:", "e_keywords", "Ej: nueva pestaña, new tab (comas)"),
            ("Class name Win32:","e_class",   "Opcional, ej: Chrome_OmniboxView"),
        ]
        for label, attr, placeholder in fields:
            row = tk.Frame(parent, bg=BG3)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 8),
                     fg=SUBTEXT, bg=BG3, width=16, anchor="w").pack(side="left")
            entry = tk.Entry(row, bg=BG2, fg=TEXT, insertbackground=TEXT,
                              font=("Segoe UI", 9), relief="flat")
            entry.pack(side="left", fill="x", expand=True)
            entry.insert(0, placeholder)
            entry.configure(fg=MUTED)
            entry.bind("<FocusIn>",  lambda e, ph=placeholder, en=entry: _placeholder_clear(e, ph, en))
            entry.bind("<FocusOut>", lambda e, ph=placeholder, en=entry: _placeholder_restore(e, ph, en))
            setattr(self, attr, entry)

        btn_row = tk.Frame(parent, bg=BG3)
        btn_row.pack(fill="x", pady=(8, 0))
        _btn(btn_row, "Guardar", self._save_form, side="left")
        _btn(btn_row, "Cancelar", self._hide_form, side="left")
        self._form_mode = "add"   # "add" o "edit"
        self._edit_index = None

    def _load_shortcuts_list(self, proc_key: str):
        self._shortcut_list.delete(0, "end")
        data = self._load_json(proc_key)
        for entry in data.get("shortcuts", []):
            self._shortcut_list.insert(
                "end",
                f"  {entry.get('shortcut','?'):15}  {entry.get('action','')}"
            )

    def _load_json(self, proc_key: str) -> dict:
        path = os.path.join(SHORTCUTS_DIR, f"{proc_key}.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"name": proc_key, "shortcuts": []}

    def _save_json(self, proc_key: str, data: dict):
        os.makedirs(SHORTCUTS_DIR, exist_ok=True)
        path = os.path.join(SHORTCUTS_DIR, f"{proc_key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _on_list_select(self, _event=None):
        pass  # reservado

    def _open_add_form(self):
        self._form_mode = "add"
        self._edit_index = None
        for attr, ph in [("e_action", "Ej: Nueva pestaña"),
                          ("e_shortcut", "Ej: Ctrl+T"),
                          ("e_keywords", "Ej: nueva pestaña, new tab (comas)"),
                          ("e_class", "Opcional, ej: Chrome_OmniboxView")]:
            e = getattr(self, attr)
            e.delete(0, "end")
            e.insert(0, ph)
            e.configure(fg=MUTED)
        self._show_form()

    def _open_edit_form(self):
        sel = self._shortcut_list.curselection()
        if not sel:
            messagebox.showinfo("Atajator", "Selecciona un atajo para editar.")
            return
        idx = sel[0]
        proc_key = self._app_var.get()
        data     = self._load_json(proc_key)
        entries  = data.get("shortcuts", [])
        if idx >= len(entries):
            return
        entry = entries[idx]
        self._form_mode  = "edit"
        self._edit_index = idx

        def _set(attr, val):
            e = getattr(self, attr)
            e.delete(0, "end")
            e.insert(0, val)
            e.configure(fg=TEXT)

        _set("e_action",   entry.get("action", ""))
        _set("e_shortcut", entry.get("shortcut", ""))
        _set("e_keywords", ", ".join(entry.get("keywords", [])))
        _set("e_class",    ", ".join(entry.get("class_names", [])))
        self._show_form()

    def _show_form(self):
        self._form_fr.pack(fill="x", padx=12, pady=(0, 12))

    def _hide_form(self):
        self._form_fr.pack_forget()

    def _save_form(self):
        def _val(attr, placeholder):
            v = getattr(self, attr).get().strip()
            return "" if v == placeholder else v

        action   = _val("e_action",   "Ej: Nueva pestaña")
        shortcut = _val("e_shortcut", "Ej: Ctrl+T")
        keywords_raw = _val("e_keywords", "Ej: nueva pestaña, new tab (comas)")
        class_raw    = _val("e_class",    "Opcional, ej: Chrome_OmniboxView")

        if not action or not shortcut:
            messagebox.showwarning("Atajator", "La acción y el atajo son obligatorios.")
            return

        keywords    = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        class_names = [c.strip() for c in class_raw.split(",") if c.strip()]

        new_entry = {
            "action":      action,
            "shortcut":    shortcut,
            "keywords":    keywords,
            "class_names": class_names,
            "regions":     [],
        }
        proc_key = self._app_var.get()
        data     = self._load_json(proc_key)
        entries  = data.setdefault("shortcuts", [])

        if self._form_mode == "edit" and self._edit_index is not None:
            entries[self._edit_index] = new_entry
        else:
            entries.append(new_entry)

        self._save_json(proc_key, data)
        self._load_shortcuts_list(proc_key)
        self._hide_form()

        # Recargar el matcher en el hilo de tkinter
        self.root.after(0, self._reload_matcher)
        logger.log(f"Atajo guardado: {shortcut} → {action} en {proc_key}")

    def _delete_shortcut(self):
        sel = self._shortcut_list.curselection()
        if not sel:
            messagebox.showinfo("Atajator", "Selecciona un atajo para eliminar.")
            return
        if not messagebox.askyesno("Atajator", "¿Eliminar este atajo?"):
            return
        idx      = sel[0]
        proc_key = self._app_var.get()
        data     = self._load_json(proc_key)
        entries  = data.get("shortcuts", [])
        if idx < len(entries):
            entries.pop(idx)
            self._save_json(proc_key, data)
            self._load_shortcuts_list(proc_key)
            self._reload_matcher()

    def _reload_matcher(self):
        """Recarga los JSON del ShortcutMatcher en caliente."""
        try:
            from shortcut_matcher import ShortcutMatcher
            # Acceder al matcher global a través del callback inyectado
            if self._matcher_ref:
                self._matcher_ref.reload()
        except Exception:
            pass

    def set_matcher(self, matcher):
        self._matcher_ref = matcher

    # ── Estado activo/pausado ──────────────────────────────────────────
    def _toggle_active(self):
        self._enabled = not self._enabled
        self._update_status_labels()
        if self._ext_toggle:
            self._ext_toggle(self._enabled)

    def set_active(self, enabled: bool):
        self._enabled = enabled
        self._update_status_labels()

    def _update_status_labels(self):
        if self._lbl_status.winfo_exists():
            if self._enabled:
                self._lbl_status.configure(text="● Activo",  fg=GREEN)
                self._btn_toggle.configure(text="Pausar")
            else:
                self._lbl_status.configure(text="● Pausado", fg=RED)
                self._btn_toggle.configure(text="Reanudar")

    def set_toggle_callback(self, cb):
        self._ext_toggle = cb

    _ext_toggle  = None
    _matcher_ref = None


# ── Utilidades UI ──────────────────────────────────────────────────────
def _btn(parent, text, command, side="left", small=False, danger=False):
    b = tk.Button(
        parent, text=text, command=command,
        font=("Segoe UI", 7 if small else 8),
        bg=RED if danger else BG3, fg=TEXT,
        relief="flat", padx=6, pady=2,
        cursor="hand2",
        activebackground=ACCENT, activeforeground=BG,
    )
    b.pack(side=side, padx=2)
    return b


def _section(parent, text):
    tk.Label(parent, text=text, font=("Segoe UI", 7),
             fg=MUTED, bg=BG, anchor="w").pack(fill="x", padx=16, pady=(10, 2))


def _section_label(parent, text):
    tk.Label(parent, text=text, font=("Segoe UI", 7),
             fg=MUTED, bg=BG, anchor="w").pack(side="left")


def _placeholder_clear(event, placeholder, entry):
    if entry.get() == placeholder:
        entry.delete(0, "end")
        entry.configure(fg=TEXT)


def _placeholder_restore(event, placeholder, entry):
    if not entry.get():
        entry.insert(0, placeholder)
        entry.configure(fg=MUTED)
