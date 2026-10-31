# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.upwork_project import main
if '__main__' == __name__:
	raise SystemExit(main())
