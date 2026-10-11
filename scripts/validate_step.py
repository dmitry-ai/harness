#!/usr/bin/env python3
"""Explicit entry point for validate_step."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.cli import main
from agent_tools.journal import validate_step

if __name__ == "__main__":
    raise SystemExit(main("validate_step"))
