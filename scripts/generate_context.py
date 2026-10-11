#!/usr/bin/env python3
"""Explicit entry point for generate_context."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.cli import main
from agent_tools.context import resolve_letter_file

if __name__ == "__main__":
    raise SystemExit(main("generate_context"))
