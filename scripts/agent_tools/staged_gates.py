# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from .code_style_gate import verify_staged_code_style_ratchet
# 2026-11-26
# "Add PreToolUse and pre-commit gate for issue-comment placement":
# https://github.com/dmitry-ai/harness/issues/273
from .issue_comment_gate import verify_staged_issue_comment_placement
# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
from .repo_link_gate import verify_staged_repo_links
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
from .rules_audit import verify_staged_rules_audit
from .subprocess_hygiene_gate import verify_staged_subprocess_hygiene
# 2026-11-25
# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
# https://github.com/dmitry-ai/harness/issues/243
def verify_staged_extra_gates(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	violations = verify_staged_subprocess_hygiene(repo_root, staged_paths, use_index=use_index)
	violations.extend(verify_staged_code_style_ratchet(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26
	# "Add PreToolUse and pre-commit gate for issue-comment placement":
	# https://github.com/dmitry-ai/harness/issues/273
	violations.extend(verify_staged_issue_comment_placement(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26
	# "Add deterministic rules-audit CLI and aggregate budget enforcement":
	# https://github.com/dmitry-ai/harness/issues/244
	violations.extend(verify_staged_rules_audit(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
	violations.extend(verify_staged_repo_links(repo_root, staged_paths, use_index=use_index))
	return violations