#!/usr/bin/env python3
"""Internal agent entrypoint for deterministic capture and project initialization."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.upwork_project import main

if __name__ == '__main__':
    raise SystemExit(main())
