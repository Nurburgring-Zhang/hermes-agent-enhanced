try:
    from .lineworks_platform.adapter import register
except ImportError:  # pytest/import-from-directory fallback
    from lineworks_platform.adapter import register

__all__ = ["register"]
