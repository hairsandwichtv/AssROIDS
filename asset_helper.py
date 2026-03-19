import sys
import os

def asset_path(filename):
    """Return correct path to a read-only asset (works frozen or live)."""
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath(".")
    return os.path.join(base, filename)

def writable_path(filename):
    """Return correct path for persistent files (scores, settings).
    Uses %APPDATA%\\AssROIDS when frozen so Windows doesn't block writes."""
    if getattr(sys, "frozen", False):
        base = os.path.join(
            os.environ.get("APPDATA", os.path.dirname(sys.executable)), "AssROIDS"
        )
        os.makedirs(base, exist_ok=True)
    else:
        base = os.path.abspath(".")
    return os.path.join(base, filename)
