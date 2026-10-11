#!/usr/bin/env python3
"""Explicit entry point for record_step."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.cli import main
from agent_tools.journal import record_step, get_existing_step_ids

if __name__ == "__main__":
    raise SystemExit(main("record_step"))
