"""
Icono en la bandeja del sistema usando Win32 API y ctypes.
Sin dependencias externas (no usa pystray).
"""
import ctypes
import ctypes.wintypes
import threading

shell32  = ctypes.windll.shell32
user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_USER          = 0x0400
TRAY_MSG         = WM_USER + 1
NIM_ADD          = 0x00000000
NIM_DELETE       = 0x00000002
NIF_MESSAGE      = 0x00000001
NIF_ICON         = 0x00000002
NIF_TIP          = 0x00000004
WM_RBUTTONUP     = 0x0205
WM_DESTROY       = 0x0002
WM_COMMAND       = 0x0111
MF_STRING        = 0x00000000
MF_SEPARATOR     = 0x00000800
TPM_BOTTOMALIGN  = 0x0020
TPM_RIGHTALIGN   = 0x0008
IDI_APPLICATION  = 32512

ID_TOGGLE = 1001
ID_EXIT   = 1002


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


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize",           ctypes.wintypes.DWORD),
        ("hWnd",             ctypes.wintypes.HWND),
        ("uID",              ctypes.wintypes.UINT),
        ("uFlags",           ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon",            ctypes.wintypes.HICON),
        ("szTip",            ctypes.c_wchar * 128),
    ]


class TrayIcon:
    def __init__(self, tooltip: str, on_toggle, on_exit):
        self._tooltip   = tooltip
        self._on_toggle = on_toggle
        self._on_exit   = on_exit
        self._hwnd      = None
        self._nid       = None
        self._enabled   = True
        self._thread    = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        self._wndproc_ref = WNDPROC_TYPE(self._wndproc)

        wc = WNDCLASSW()
        wc.lpfnWndProc   = self._wndproc_ref
        wc.hInstance     = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "AtajatorTray"
        user32.RegisterClassW(ctypes.byref(wc))

        self._hwnd = user32.CreateWindowExW(
            0, "AtajatorTray", "Atajator",
            0, 0, 0, 0, 0, 0, 0,
            kernel32.GetModuleHandleW(None), 0,
        )
        self._add_icon()

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _add_icon(self):
        nid = NOTIFYICONDATAW()
        nid.cbSize           = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd             = self._hwnd
        nid.uID              = 1
        nid.uFlags           = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = TRAY_MSG
        nid.hIcon            = user32.LoadIconW(0, IDI_APPLICATION)
        nid.szTip            = self._tooltip
        self._nid            = nid
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _remove_icon(self):
        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))

    def _show_menu(self):
        hmenu = user32.CreatePopupMenu()
        label = "✓ Activo" if self._enabled else "  Pausado"
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
            if lparam == WM_RBUTTONUP:
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
