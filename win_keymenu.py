"""Stop Windows from hijacking Alt-key combos in the game window.

On Windows, Alt+Space (and tapping Alt on its own) opens the window's system
menu, which swallows the next keypress — so holding Left Alt to brake would eat
the Space shot. This hooks the window so that menu never opens. Alt+F4 and
Alt+Tab are unaffected. No-op on other platforms or if anything goes wrong.
"""
import sys
import pygame

WM_SYSCOMMAND = 0x0112
SC_KEYMENU    = 0xF100
GWLP_WNDPROC  = -4

_hooked = {}   # hwnd -> (callback, previous wndproc); keeps the callback alive


def block_alt_menu():
    """Call after every pygame.display.set_mode()."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = pygame.display.get_wm_info().get("window")
        if not hwnd or hwnd in _hooked:
            return

        user32  = ctypes.windll.user32
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                     wintypes.WPARAM, wintypes.LPARAM)
        user32.CallWindowProcW.argtypes  = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                            wintypes.WPARAM, wintypes.LPARAM]
        user32.CallWindowProcW.restype   = LRESULT
        user32.DefWindowProcW.argtypes   = [wintypes.HWND, wintypes.UINT,
                                            wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype    = LRESULT
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype  = ctypes.c_void_p

        prev = [None]

        @WNDPROC
        def proc(h, msg, wparam, lparam):
            if msg == WM_SYSCOMMAND and (wparam & 0xFFF0) == SC_KEYMENU:
                return 0
            if prev[0] is None:
                return user32.DefWindowProcW(h, msg, wparam, lparam)
            return user32.CallWindowProcW(prev[0], h, msg, wparam, lparam)

        prev[0] = user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC,
                                           ctypes.cast(proc, ctypes.c_void_p))
        if prev[0]:
            _hooked[hwnd] = (proc, prev[0])
    except Exception:
        pass
