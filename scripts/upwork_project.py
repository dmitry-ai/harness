#!/usr/bin/env python3
"""CLI entrypoint for deterministic Upwork project initialization and .agents linking."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.upwork_project import main

if __name__ == '__main__':
    raise SystemExit(main())
