# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import sys
# 2026-10-14
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
from agent_tools.harness_cli import main
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
if '__main__' == __name__:
	raise SystemExit(main())
