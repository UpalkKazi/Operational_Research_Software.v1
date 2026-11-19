"""Pytest collection policy.

The phase files are interactive manual demos that read stdin at import time;
they are intentionally excluded from automated test collection.
"""

collect_ignore = [
    # Legacy AI tests assert generated Python execution, intentionally removed
    # from the production path. Keep the source modules for future optional work.
    "test_classifier.py",
    "test_llm_connect.py",
    # Interactive manual demos read stdin at import time.
    "test_phase2.py",
    "test_phase3.py",
    "test_phase4.py",
    "test_phase5.py",
]
