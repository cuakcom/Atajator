"""
Hook global de ratón de bajo nivel para Windows.
Usa ctypes y Win32 API directamente, sin dependencias externas.
"""
import ctypes
import ctypes.wintypes

from logger import log

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SetWindowsHookExW.restype  = ctypes.wintypes.HHOOK
user32.CallNextHookEx.restype     = ctypes.c_int
user32.GetMessageW.restype        = ctypes.c_int
kernel32.GetModuleHandleW.restype = ctypes.wintypes.HMODULE


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
        self._hook_id  = None
        self._proc_ref = None

    def start(self):
        """Instala el hook y entra en el message loop. Bloqueante."""

        def _proc(nCode, wParam, lParam):
            if nCode >= 0 and wParam == WM_LBUTTONDOWN:
                try:
                    data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    self._callback(data.pt.x, data.pt.y)
                except Exception as e:
                    log(f"HOOK callback error: {type(e).__name__}: {e}")
            return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)

        self._proc_ref = HOOKPROC(_proc)
        self._hook_id = user32.SetWindowsHookExW(
            WH_MOUSE_LL,
            self._proc_ref,
            kernel32.GetModuleHandleW(None),
            0,
        )
        log(f"HOOK SetWindowsHookExW id={self._hook_id}")
        if not self._hook_id:
            err = kernel32.GetLastError()
            log(f"HOOK fallo al instalar, GetLastError={err}")
            raise OSError(f"SetWindowsHookExW fallo, error={err}")

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self):
        if self._hook_id:
            user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None
