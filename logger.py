"""
Logging module — active during development, stubbed for release.
Set LOG_ENABLED = True to re-enable disk logging for debugging.
"""

LOG_ENABLED = False

__all__ = ["log_state", "log_event"]


def log_state():
    """No-op in release build."""
    pass


def log_event(event_type, **details):
    """No-op in release build."""
    pass
