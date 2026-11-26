# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import sys
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.harness_cli import main
if '__main__' == __name__:
	raise SystemExit(main())
