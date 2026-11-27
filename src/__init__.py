"""
OR Assistant - AI-Powered Operations Research Tool
"""

# PuLP >= 3.3.1 preloads highspy's C extension with RTLD_GLOBAL. On Linux that
# splits the C++ runtime state and OSQP then segfaults, taking the process down
# (reported by @harunpirim, Oct 2026). Loading OSQP first keeps its symbols intact.
# Every pulp import in this project goes through src.*, so this runs beforehand.
try:  # pragma: no cover - import-order guard, not logic
    import osqp  # noqa: F401
except Exception:  # pragma: no cover - OSQP is optional
    pass

__version__ = "0.1.0"
__author__ = "NDSU OR Assistant Team"
