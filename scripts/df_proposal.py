# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from agent_tools.text_cli import main
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
if '__main__' == __name__:
	raise SystemExit(main(default_kind='proposal'))
