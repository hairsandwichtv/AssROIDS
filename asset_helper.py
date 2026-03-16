import sys
import os

def asset_path(filename):
    """Return correct path to asset whether running live or frozen by PyInstaller."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")
    return os.path.join(base, filename)
