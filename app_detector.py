"""
Detecta la aplicación activa, la región clickeada y el control bajo el cursor.
Usa Win32 API a través de ctypes. Sin dependencias externas.
"""
import ctypes
import ctypes.wintypes
import os

# Definir estructuras ANTES de usarlas en argtypes
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Sin restype explícito ctypes devuelve c_int (32 bits), truncando HWNDs en x64.
user32.GetForegroundWindow.restype  = ctypes.wintypes.HWND
user32.WindowFromPoint.restype      = ctypes.wintypes.HWND
user32.WindowFromPoint.argtypes     = [ctypes.wintypes.POINT]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]
user32.GetWindowTextW.argtypes      = [ctypes.wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.argtypes       = [ctypes.wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowRect.argtypes       = [ctypes.wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
kernel32.OpenProcess.restype        = ctypes.wintypes.HANDLE
kernel32.OpenProcess.argtypes       = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.c_wchar_p,
    ctypes.POINTER(ctypes.wintypes.DWORD),
]
kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
kernel32.GetModuleHandleW.restype   = ctypes.wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes  = [ctypes.wintypes.LPCWSTR]

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _get_process_name(hwnd: int) -> str:
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf  = ctypes.create_unicode_buffer(512)
        size = ctypes.wintypes.DWORD(512)
        kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        return os.path.basename(buf.value).lower()
    finally:
        kernel32.CloseHandle(h)


def _get_window_rect(hwnd: int) -> RECT:
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect


def _get_window_text(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(hwnd) + 1
    buf = ctypes.create_unicode_buffer(n)
    user32.GetWindowTextW(hwnd, buf, n)
    return buf.value.strip()


def _get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _classify_region(hwnd: int, x: int, y: int) -> str:
    """Clasifica la zona de la ventana donde ocurrió el click."""
    rect = _get_window_rect(hwnd)
    width  = rect.right  - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return "content"

    rel_x = (x - rect.left)  / width
    rel_y = (y - rect.top)   / height

    if rel_y < 0.0:
        return "outside"
    if rel_y < 0.04:
        return "titlebar"
    if rel_y < 0.09:
        return "menubar"
    if rel_y < 0.16:
        return "toolbar"
    if rel_y > 0.96:
        return "statusbar"
    if rel_x < 0.05:
        return "sidebar_left"
    if rel_x > 0.95:
        return "sidebar_right"
    return "content"


class AppDetector:
    def get_info(self, x: int, y: int) -> dict:
        """
        Retorna un dict con toda la información relevante del contexto del click.
        Claves: process, window_title, control_text, class_name, region
        """
        fg_hwnd = user32.GetForegroundWindow()
        if not fg_hwnd:
            return {}

        process       = _get_process_name(fg_hwnd)
        window_title  = _get_window_text(fg_hwnd)
        region        = _classify_region(fg_hwnd, x, y)

        ctrl_hwnd     = user32.WindowFromPoint(ctypes.wintypes.POINT(x, y))
        control_text  = _get_window_text(ctrl_hwnd) if ctrl_hwnd else ""
        class_name    = _get_class_name(ctrl_hwnd)  if ctrl_hwnd else ""

        return {
            "process":       process,
            "window_title":  window_title,
            "control_text":  control_text,
            "class_name":    class_name,
            "region":        region,
        }
