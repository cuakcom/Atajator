"""
Hook global de ratón de bajo nivel para Windows.
Usa ctypes y Win32 API directamente, sin dependencias externas.
"""
import ctypes
import ctypes.wintypes
import threading

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", ctypes.wintypes.POINT),
        ("mouseData", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)


class MouseHook:
    def __init__(self, on_left_click):
        self._callback = on_left_click
        self._hook_id = None
        self._proc_ref = None  # evitar GC del callback

    def start(self):
        """Instala el hook y entra en el message loop. Bloqueante."""

        def _proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam == WM_LBUTTONDOWN:
                data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                try:
                    self._callback(data.pt.x, data.pt.y)
                except Exception:
                    pass
            return ctypes.windll.user32.CallNextHookEx(
                self._hook_id, nCode, wParam, lParam
            )

        self._proc_ref = HOOKPROC(_proc)
        self._hook_id = ctypes.windll.user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            self._proc_ref,
            ctypes.windll.kernel32.GetModuleHandleW(None),
            0,
        )
        if not self._hook_id:
            raise OSError("No se pudo instalar el hook de ratón")

        msg = ctypes.wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        if self._hook_id:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None
            # Despertar el message loop para que termine
            ctypes.windll.user32.PostThreadMessageW(
                threading.current_thread().ident, 0x0012, 0, 0  # WM_QUIT
            )
