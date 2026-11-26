# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
from __future__ import annotations
from pathlib import Path
from typing import Any
DIFF_EXECUTABILITY_GATES: dict[str, str] = {
	'PreToolUse': 'agent_tools.tdd.diff_executability.is_non_executable_diff',
	'polyglot_land': 'agent_tools.tdd.diff_executability.classify_git_range',
	'pre-commit': 'agent_tools.tdd.diff_executability.is_non_executable_diff',
	'runtime_snapshot': 'agent_tools.tdd.diff_executability.should_run_snapshot_canary',
	'tdd/evaluator.py': 'agent_tools.tdd.diff_executability.is_git_path_non_executable',
	'worktree_land': 'agent_tools.tdd.diff_executability.classify_git_range',
}
_SNAPSHOT_CONFIG_FILES = frozenset({'paths.json', 'runtime.json'})
# @used-by :func:`agent_tools.runtime_snapshot._promote_locked()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_contract_constants_declare_all_six_gates_and_land_stage_policies()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def should_run_snapshot_canary(repo_root: Path, base_ref: str | None=None, *, diff_info: dict[str, Any] | None=None) -> tuple[bool, str]:
	from . import diff_executability
	if None is diff_info and (not base_ref):
		r: tuple[bool, str] = (True, 'no_base_ref')
	else:
		info = diff_info if None is not diff_info else diff_executability.classify_git_range(repo_root, str(base_ref), 'HEAD')
		if info.get('is_executable'):
			r = (True, 'executable_diff')
		elif any((Path(p).name in _SNAPSHOT_CONFIG_FILES for p in (info.get('file_categories') or ()))):
			r = (True, 'runtime_config_changed')
		else:
			r = (False, f"non_executable_diff:{info.get('classification', 'non_code')}")
	return r
__all__ = ['DIFF_EXECUTABILITY_GATES', 'should_run_snapshot_canary']
