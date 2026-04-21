"""
Icono en la bandeja del sistema usando Win32 API y ctypes.
Sin dependencias externas (no usa pystray).
"""
import ctypes
import ctypes.wintypes
import threading

from logger import log

shell32  = ctypes.windll.shell32
user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ── Constantes ────────────────────────────────────────────────────────
WM_USER          = 0x0400
TRAY_MSG         = WM_USER + 1
NIM_ADD          = 0x00000000
NIM_DELETE       = 0x00000002
NIF_MESSAGE      = 0x00000001
NIF_ICON         = 0x00000002
NIF_TIP          = 0x00000004
WM_RBUTTONUP     = 0x0205
WM_LBUTTONUP     = 0x0202
WM_DESTROY       = 0x0002
WM_COMMAND       = 0x0111
MF_STRING        = 0x00000000
MF_SEPARATOR     = 0x00000800
TPM_BOTTOMALIGN  = 0x0020
TPM_RIGHTALIGN   = 0x0008
IDI_APPLICATION  = 32512
ID_TOGGLE        = 1001
ID_EXIT          = 1002

# ── Estructuras y tipos — deben ir ANTES de usarlos en argtypes ───────
WNDPROC_TYPE = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.wintypes.HWND,
    ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style",         ctypes.wintypes.UINT),
        ("lpfnWndProc",   WNDPROC_TYPE),
        ("cbClsExtra",    ctypes.c_int),
        ("cbWndExtra",    ctypes.c_int),
        ("hInstance",     ctypes.wintypes.HINSTANCE),
        ("hIcon",         ctypes.wintypes.HICON),
        ("hCursor",       ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName",  ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize",           ctypes.wintypes.DWORD),
        ("hWnd",             ctypes.wintypes.HWND),
        ("uID",              ctypes.wintypes.UINT),
        ("uFlags",           ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon",            ctypes.wintypes.HICON),
        ("szTip",            ctypes.c_wchar * 128),
        ("dwState",          ctypes.wintypes.DWORD),
        ("dwStateMask",      ctypes.wintypes.DWORD),
        ("szInfo",           ctypes.c_wchar * 256),
        ("uVersion",         ctypes.wintypes.UINT),
        ("szInfoTitle",      ctypes.c_wchar * 64),
        ("dwInfoFlags",      ctypes.wintypes.DWORD),
        ("guidItem",         GUID),
        ("hBalloonIcon",     ctypes.wintypes.HICON),
    ]


# ── Declarar restype/argtypes DESPUÉS de definir los tipos ────────────
user32.CreateWindowExW.restype  = ctypes.wintypes.HWND
user32.CreateWindowExW.argtypes = [
    ctypes.wintypes.DWORD,
    ctypes.wintypes.LPCWSTR,
    ctypes.wintypes.LPCWSTR,
    ctypes.wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.wintypes.HWND,
    ctypes.wintypes.HMENU,
    ctypes.wintypes.HINSTANCE,
    ctypes.c_void_p,
]
user32.RegisterClassW.restype  = ctypes.wintypes.ATOM
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.LoadIconW.restype       = ctypes.wintypes.HICON
user32.LoadIconW.argtypes      = [ctypes.wintypes.HINSTANCE, ctypes.wintypes.LPCWSTR]
user32.CreatePopupMenu.restype = ctypes.wintypes.HMENU
user32.DefWindowProcW.restype  = ctypes.c_long
user32.DefWindowProcW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]
kernel32.GetModuleHandleW.restype  = ctypes.wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]


# ── Clase principal ───────────────────────────────────────────────────
class TrayIcon:
    def __init__(self, tooltip: str, on_toggle, on_exit):
        self._tooltip   = tooltip
        self._on_toggle = on_toggle
        self._on_exit   = on_exit
        self._hwnd      = None
        self._nid       = None
        self._enabled   = True
        self._thread    = threading.Thread(target=self._run_safe, daemon=True)

    def start(self):
        self._thread.start()

    def _run_safe(self):
        try:
            self._run()
        except Exception as e:
            log(f"TRAY ERROR: {type(e).__name__}: {e}")

    def _run(self):
        self._wndproc_ref = WNDPROC_TYPE(self._wndproc)
        self._class_name  = "AtajatorTrayClass"

        wc = WNDCLASSW()
        wc.lpfnWndProc   = self._wndproc_ref
        wc.hInstance     = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = self._class_name
        atom = user32.RegisterClassW(ctypes.byref(wc))
        log(f"TRAY RegisterClassW atom={atom}")

        self._hwnd = user32.CreateWindowExW(
            0, self._class_name, "Atajator",
            0, 0, 0, 0, 0, 0, 0,
            kernel32.GetModuleHandleW(None), None,
        )
        log(f"TRAY CreateWindowExW hwnd={self._hwnd}")
        if not self._hwnd:
            err = kernel32.GetLastError()
            log(f"TRAY CreateWindowExW fallo, GetLastError={err}")
            return

        self._add_icon()

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _add_icon(self):
        nid = NOTIFYICONDATAW()
        nid.cbSize           = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd             = self._hwnd
        nid.uID              = 1
        nid.uFlags           = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = TRAY_MSG
        nid.hIcon            = user32.LoadIconW(None, IDI_APPLICATION)
        nid.szTip            = self._tooltip
        self._nid            = nid
        ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        log(f"TRAY Shell_NotifyIconW ok={ok} cbSize={nid.cbSize}")

    def _remove_icon(self):
        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))

    def _show_menu(self):
        hmenu = user32.CreatePopupMenu()
        label = "Activo (clic para pausar)" if self._enabled else "Pausado (clic para activar)"
        user32.AppendMenuW(hmenu, MF_STRING, ID_TOGGLE, label)
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, ID_EXIT, "Salir")

        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self._hwnd)
        user32.TrackPopupMenu(
            hmenu, TPM_BOTTOMALIGN | TPM_RIGHTALIGN,
            pt.x, pt.y, 0, self._hwnd, None,
        )
        user32.DestroyMenu(hmenu)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == TRAY_MSG:
            if lparam == WM_RBUTTONUP or lparam == WM_LBUTTONUP:
                self._show_menu()
                return 0
        elif msg == WM_COMMAND:
            cmd = wparam & 0xFFFF
            if cmd == ID_TOGGLE:
                self._enabled = not self._enabled
                self._on_toggle(self._enabled)
            elif cmd == ID_EXIT:
                self._remove_icon()
                self._on_exit()
        elif msg == WM_DESTROY:
            self._remove_icon()
            user32.PostQuitMessage(0)
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
