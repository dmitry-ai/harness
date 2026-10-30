#!/usr/bin/env python3
"""Deterministic GitHub Issue & Comment CLI; implementation lives in agent_tools.github_issue."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.github_issue import main

if __name__ == '__main__':
    raise SystemExit(main())
