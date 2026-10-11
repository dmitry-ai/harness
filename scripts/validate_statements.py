#!/usr/bin/env python3
"""Explicit entry point for validate_statements."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.cli import main

if __name__ == "__main__":
    raise SystemExit(main("validate_statements"))
