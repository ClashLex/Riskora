"""Compatibility entrypoint for the Portfolio Lens API.

The canonical application lives in ``institutional_predictor.app``.
"""

import sys
from importlib import import_module
from pathlib import Path

repository_root = Path(__file__).resolve().parents[2]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

app = import_module("institutional_predictor.app").app

__all__ = ["app"]
