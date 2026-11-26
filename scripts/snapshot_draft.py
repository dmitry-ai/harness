# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import sys
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.cli import main
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
if '__main__' == __name__:
	raise SystemExit(main('snapshot_draft'))
