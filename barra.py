#!/usr/bin/env python3
"""Lanzador del status line. Claude Code ejecuta este archivo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from barra_de_uso.principal import principal  # noqa: E402

if __name__ == "__main__":
    sys.exit(principal())
