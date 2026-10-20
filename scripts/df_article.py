#!/usr/bin/env python3
"""Explicit entry point for df_article (skill /df-article): lint, source, render, replay, response."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.article import main

if __name__ == "__main__":
    raise SystemExit(main())
