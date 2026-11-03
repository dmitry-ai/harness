# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.cli import main
from agent_tools.context import resolve_letter_file
if '__main__' == __name__:
	raise SystemExit(main('generate_context'))
