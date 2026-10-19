"""
conftest.py
-----------
Global pytest configuration and root path resolution fixture.
"""

import sys
import os

# Ensure project root directory is always on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
