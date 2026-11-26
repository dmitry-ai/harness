# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
import os
import subprocess
DIFF_EXECUTABILITY_GATES: dict[str, str] = {
	'PreToolUse': 'agent_tools.tdd.diff_executability.is_non_executable_diff',
	'polyglot_land': 'agent_tools.tdd.diff_executability.classify_git_range',
	'pre-commit': 'agent_tools.tdd.diff_executability.is_non_executable_diff',
	'runtime_snapshot': 'agent_tools.tdd.diff_executability.should_run_snapshot_canary',
	'tdd/evaluator.py': 'agent_tools.tdd.diff_executability.is_git_path_non_executable',
	'worktree_land': 'agent_tools.tdd.diff_executability.classify_git_range',
}
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
MIXED_COMMIT_COMMENT_THRESHOLD = 20
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_SNAPSHOT_CONFIG_FILES = frozenset({'paths.json', 'runtime.json'})
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
# @used-by :func:`check_staged_mixed_commit_warning()`
# @used-by :func:`check_touched_mixed_commit_warning()`
def _git_batch_texts(repo: Path, specs: list[str]) -> dict[str, str | None]:
	r: dict[str, str | None] = {}
	if specs and (repo / '.git').exists():
		proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'cat-file', '--batch'], input=('\n'.join(specs) + '\n').encode('utf-8'), capture_output=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, timeout=30, check=False, creationflags=_NO_WINDOW)
		if 0 == proc.returncode:
			r = _parse_batch_blobs(proc.stdout, specs)
	return r
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
# @used-by :func:`_git_batch_texts()`
def _parse_batch_blobs(raw: bytes, specs: list[str]) -> dict[str, str | None]:
	out: dict[str, str | None] = {}
	pos, total = (0, len(raw))
	for spec in specs:
		nl = raw.find(b'\n', pos)
		if 0 > nl:
			break
		hdr = raw[pos:nl].decode('utf-8', errors='replace')
		pos = nl + 1
		parts = hdr.rsplit(' ', 2)
		if 3 == len(parts) and 'blob' == parts[1] and parts[2].isdigit():
			size = int(parts[2])
			blob = raw[pos:pos + size]
			pos = min(total, pos + size + 1)
			out[spec] = None if b'\x00' in blob else blob.decode('utf-8', errors='replace')
		else:
			out[spec] = None
	return out
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_detect_mixed_commit_warning_threshold_and_exports()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def check_staged_mixed_commit_warning(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
	paths = list(staged_paths or ())
	if len(paths) <= threshold:
		r: dict[str, Any] | None = None
	else:
		from . import diff_executability
		repo = Path(repo_root).resolve()
		specs = [f'HEAD:{rel}' for rel in paths] + ([f':{rel}' for rel in paths] if use_index else [])
		blobs = _git_batch_texts(repo, specs)
		cats: dict[str, str] = {}
		for rel in paths:
			cur = blobs.get(f':{rel}') if use_index else ((repo / rel).read_text(encoding='utf-8', errors='replace') if (repo / rel).is_file() else None)
			cats[rel] = diff_executability.classify_text_diff(repo / rel, blobs.get(f'HEAD:{rel}'), cur, repo_root=repo)
		r = detect_mixed_commit_warning(diff_executability._summarize_categories(cats), threshold=threshold)
	return r
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_repo_commits_and_files()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_detect_mixed_commit_warning_threshold_and_exports()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def check_touched_mixed_commit_warning(repo_root: Path, rel_paths: list[str], *, project_root: Path | None=None, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
	paths = list(rel_paths or ())
	if len(paths) <= threshold:
		r: dict[str, Any] | None = None
	else:
		from . import diff_executability
		repo = Path(repo_root).resolve()
		blobs = _git_batch_texts(repo, [f'HEAD:{rel}' for rel in paths] + [f'HEAD~1:{rel}' for rel in paths])
		cats: dict[str, str] = {}
		for rel in paths:
			cur = (repo / rel).read_text(encoding='utf-8', errors='replace') if (repo / rel).is_file() else None
			head = blobs.get(f'HEAD:{rel}')
			if None is not cur and cur == head:
				old = blobs.get(f'HEAD~1:{rel}')
				cats[rel] = diff_executability.classify_text_diff(repo / rel, old, cur, repo_root=repo, project_root=project_root) if old != cur else diff_executability.classify_git_path(repo, rel, disk_text=cur, project_root=project_root)
			else:
				cats[rel] = diff_executability.classify_text_diff(repo / rel, head, cur, repo_root=repo, project_root=project_root)
		r = detect_mixed_commit_warning(diff_executability._summarize_categories(cats), threshold=threshold)
	return r
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
# @used-by :func:`agent_tools.tdd.diff_executability.format_land_diff_telemetry()`
# @used-by :func:`check_staged_mixed_commit_warning()`
# @used-by :func:`check_touched_mixed_commit_warning()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_detect_mixed_commit_warning_threshold_and_exports()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def detect_mixed_commit_warning(diff_info: dict[str, Any] | None, *, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
	info = diff_info or {}
	counts = info.get('category_counts') or {}
	cmt_cnt = int(counts.get('comment_only') or 0)
	exec_cnt = len(info.get('executable_files') or ()) or int(counts.get('executable') or 0)
	if 1 > exec_cnt or threshold > cmt_cnt:
		r: dict[str, Any] | None = None
	else:
		msg = f'Mixed bulk comment-only ({cmt_cnt} files, threshold {threshold}) and executable ({exec_cnt} file(s)) changes in one commit; split executable fixes and runtime decorators (@override) from bulk comment-only annotation passes into separate child issues and commits.'
		r = {'code': 'MIXED_BULK_COMMENT_AND_EXECUTABLE_COMMIT', 'comment_only_file_count': cmt_cnt, 'executable_file_count': exec_cnt, 'message': msg, 'threshold': threshold}
	return r
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
__all__ = [
	'DIFF_EXECUTABILITY_GATES',
	# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
	'MIXED_COMMIT_COMMENT_THRESHOLD',
	'check_staged_mixed_commit_warning',
	'check_touched_mixed_commit_warning',
	'detect_mixed_commit_warning',
	'should_run_snapshot_canary',
]
