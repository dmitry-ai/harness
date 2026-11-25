# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
# https://github.com/dmitry-ai/harness/issues/243
from __future__ import annotations
from pathlib import Path
from .code_style_gate import verify_staged_code_style_ratchet
from .subprocess_hygiene_gate import verify_staged_subprocess_hygiene
def verify_staged_extra_gates(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	violations = verify_staged_subprocess_hygiene(repo_root, staged_paths, use_index=use_index)
	violations.extend(verify_staged_code_style_ratchet(repo_root, staged_paths, use_index=use_index))
	return violations