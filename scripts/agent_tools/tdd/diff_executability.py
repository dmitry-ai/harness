# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement diff executability classifier and automatic test skip":
# https://github.com/dmitry-ai/harness/issues/358
from __future__ import annotations
from pathlib import Path
from typing import Any
from .classifier import is_software_code_file
from .comment_diff import _git_read_text, classify_comment_or_whitespace_diff
from .mechanical import find_matching_mechanical_recipes, is_mechanical_diff_exempt, matches_any_mechanical_recipes
import os
import re
import subprocess
DEFAULT_MAX_REPORTED_FILES = 50
NON_EXECUTABLE_CATEGORIES = frozenset({'comment_only', 'mechanical_exempt', 'non_code', 'unchanged', 'whitespace_only'})
_NO_TESTS_SLOP_RE = re.compile(r'(?i)\b(?:hurry|faster|lazy|skip\s+tests?\s+(?:because|to\s+save)|bypass\s+(?:tdd|tests?|gate))\b')
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`_classify_modified_entry()`
# @used-by :func:`_classify_single_blob()`
# @used-by :func:`_git_diff_entries()`
def _git_read_bytes(repo: Path, args: list[str]) -> bytes | None:
	r = None
	if (repo / '.git').exists():
		proc = subprocess.run(
			['git', '--no-optional-locks', '-C', str(repo), *args],
			stdin=subprocess.DEVNULL,
			capture_output=True,
			env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
			timeout=30,
			check=False,
			creationflags=_NO_WINDOW,
		)
		if 0 == proc.returncode:
			r = proc.stdout
	return r
# @used-by :func:`classify_git_range()`
def _git_diff_entries(repo: Path, base_ref: str, head_ref: str) -> list[tuple[str, str, str | None]] | None:
	raw = _git_read_bytes(repo, ['diff', '--name-status', '-z', f'{base_ref}..{head_ref}'])
	if None is raw:
		r = None
	else:
		parts = [p.decode('utf-8', errors='replace') for p in raw.split(b'\x00') if p]
		out: list[tuple[str, str, str | None]] = []
		idx = 0
		while idx < len(parts):
			status = parts[idx]
			if status.startswith(('R', 'C')) and idx + 2 < len(parts):
				out.append((status, parts[idx + 1], parts[idx + 2]))
				idx += 3
			elif idx + 1 < len(parts):
				out.append((status, parts[idx + 1], None))
				idx += 2
			else:
				break
		r = out
	return r
# @used-by :func:`_classify_modified_entry()`
# @used-by :func:`_classify_single_blob()`
def _decode_git_blob(blob: bytes | None) -> str | None:
	r = None
	if None is not blob and b'\x00' not in blob:
		try:
			r = blob.decode('utf-8')
		except UnicodeDecodeError:
			r = None
	return r
# @used-by :func:`_classify_non_modified_entry()`
def _classify_single_blob(repo: Path, rel: str, ref: str) -> bool:
	return is_software_code_file(rel, content=_decode_git_blob(_git_read_bytes(repo, ['show', f'{ref}:{rel}'])))
# @used-by :func:`_classify_diff_entry()`
def _classify_modified_entry(repo: Path, rel: str, base_ref: str, head_ref: str, recipes: list[dict]) -> str:
	old_txt = _decode_git_blob(_git_read_bytes(repo, ['show', f'{base_ref}:{rel}']))
	new_txt = _decode_git_blob(_git_read_bytes(repo, ['show', f'{head_ref}:{rel}']))
	if not is_software_code_file(rel, content=new_txt if None is not new_txt else old_txt):
		r = 'non_code'
	elif None is old_txt or None is new_txt:
		r = 'executable'
	else:
		cw = classify_comment_or_whitespace_diff(rel, old_txt, new_txt)
		if None is not cw:
			r = cw
		elif recipes and matches_any_mechanical_recipes(old_txt, new_txt, recipes):
			r = 'mechanical_exempt'
		else:
			r = 'executable'
	return r
# @used-by :func:`_classify_diff_entry()`
def _classify_non_modified_entry(repo: Path, status: str, path_a: str, target: str, base_ref: str, head_ref: str) -> str:
	if status.startswith(('R', 'C')):
		is_code = _classify_single_blob(repo, path_a, base_ref) or _classify_single_blob(repo, target, head_ref)
	elif status in ('A', 'D'):
		is_code = _classify_single_blob(repo, target, head_ref if 'A' == status else base_ref)
	else:
		is_code = is_software_code_file(target)
	return 'executable' if is_code else 'non_code'
# @used-by :func:`classify_git_range()`
def _classify_diff_entry(repo: Path, status: str, path_a: str, path_b: str | None, base_ref: str, head_ref: str, recipes: list[dict]) -> tuple[str, str]:
	target = path_b if None is not path_b else path_a
	cat = _classify_modified_entry(repo, target, base_ref, head_ref, recipes) if 'M' == status else _classify_non_modified_entry(repo, status, path_a, target, base_ref, head_ref)
	return (target, cat)
# @used-by :func:`classify_git_range()`
def _resolve_range_recipes(repo: Path, base_ref: str, head_ref: str, message: str | None, project_root: Path | None) -> list[dict]:
	if None is not message:
		r = find_matching_mechanical_recipes(repo, message=message, project_root=project_root)
	else:
		all_recipes = find_matching_mechanical_recipes(repo, project_root=project_root)
		if not all_recipes:
			r = []
		else:
			raw_msgs = _git_read_text(repo, ['log', '--format=%B%x00', f'{base_ref}..{head_ref}']) or ''
			msgs = [m.strip() for m in raw_msgs.split('\x00') if m.strip()]
			r = [rec for msg in msgs for rec in find_matching_mechanical_recipes(repo, message=msg, project_root=project_root)]
	return r
# @used-by :func:`_summarize_categories()`
def _overall_classification(exec_files: list[str], counts: dict[str, int]) -> str:
	if exec_files:
		r = 'executable'
	elif not counts:
		r = 'unchanged'
	else:
		non_unch = [c for c in counts if 'unchanged' != c]
		r = non_unch[0] if 1 == len(non_unch) else ('unchanged' if not non_unch else 'mixed_non_executable')
	return r
# @used-by :func:`classify_git_range()`
def _summarize_categories(file_categories: dict[str, str]) -> dict[str, Any]:
	exec_files = sorted((p for p, c in file_categories.items() if c not in NON_EXECUTABLE_CATEGORIES))
	non_exec_files = sorted((p for p, c in file_categories.items() if c in NON_EXECUTABLE_CATEGORIES))
	counts: dict[str, int] = {}
	for cat in file_categories.values():
		counts[cat] = counts.get(cat, 0) + 1
	return {
		'category_counts': dict(sorted(counts.items())),
		'classification': _overall_classification(exec_files, counts),
		'executable_files': exec_files,
		'file_categories': dict(sorted(file_categories.items())),
		'is_executable': bool(exec_files),
		'non_executable_files': non_exec_files,
	}
# @used-by :func:`_classify_existing_git_path()`
# @used-by :func:`_classify_last_commit_path()`
# @used-by :func:`is_non_executable_diff()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_whitespace_only_and_indentation_sensitive_fail_closed()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_text_diff(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> str:
	hint = new_text if None is not new_text else old_text
	if not is_software_code_file(path, content=hint):
		r = 'non_code'
	elif None is old_text or None is new_text:
		r = 'executable'
	else:
		cw = classify_comment_or_whitespace_diff(path, old_text, new_text)
		if None is not cw:
			r = cw
		elif is_mechanical_diff_exempt(old_text, new_text, repo_root=repo_root, message=message, project_root=project_root):
			r = 'mechanical_exempt'
		else:
			r = 'executable'
	return r
# @used-by :func:`_classify_existing_git_path()`
def _classify_last_commit_path(repo: Path, rel_posix: str, project_root: Path | None) -> str:
	sha_raw = _git_read_text(repo, ['log', '-n', '1', '--format=%H', '--', f':(literal){rel_posix}'])
	sha = (sha_raw or '').strip()
	if not sha:
		r = 'executable' if is_software_code_file(rel_posix) else 'non_code'
	else:
		prev_txt = _git_read_text(repo, ['show', f'{sha}^:{rel_posix}'])
		curr_txt = _git_read_text(repo, ['show', f'{sha}:{rel_posix}'])
		msg = _git_read_text(repo, ['log', '-n', '1', '--format=%B', sha])
		r = classify_text_diff(repo / rel_posix, prev_txt, curr_txt, repo_root=repo, message=msg, project_root=project_root)
	return r
# @used-by :func:`classify_git_path()`
def _read_current_git_text(repo: Path, fpath: Path, rel_posix: str, disk_text: str | None, use_index: bool) -> str | None:
	if None is not disk_text:
		r = disk_text
	elif use_index:
		r = _git_read_text(repo, ['show', f':{rel_posix}'])
	else:
		r = fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None
	return r
# @used-by :func:`classify_git_path()`
def _classify_existing_git_path(repo: Path, fpath: Path, rel_posix: str, cur: str, message: str | None, project_root: Path | None) -> str:
	if not is_software_code_file(fpath, content=cur):
		r = 'non_code'
	else:
		head = _git_read_text(repo, ['show', f'HEAD:{rel_posix}'])
		if None is head:
			r = 'executable'
		elif head != cur:
			r = classify_text_diff(fpath, head, cur, repo_root=repo, message=message, project_root=project_root)
		else:
			r = _classify_last_commit_path(repo, rel_posix, project_root)
	return r
# @used-by :func:`is_git_path_non_executable()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_git_path(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> str:
	repo = Path(repo_root).resolve()
	fpath = repo / rel_posix
	cur = _read_current_git_text(repo, fpath, rel_posix, disk_text, use_index)
	if None is not cur:
		r = _classify_existing_git_path(repo, fpath, rel_posix, cur, message, project_root)
	else:
		is_code = is_software_code_file(fpath) or is_software_code_file(fpath, content=_git_read_text(repo, ['show', f'HEAD:{rel_posix}']))
		r = 'executable' if is_code else 'non_code'
	return r
# @used-by :func:`agent_tools.polyglot_land.run_polyglot_land_tests()`
# @used-by :func:`resolve_land_test_plan()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_git_range(repo_root: Path, base_ref: str, head_ref: str='HEAD', *, message: str | None=None, project_root: Path | None=None) -> dict[str, Any]:
	repo = Path(repo_root).resolve()
	entries = _git_diff_entries(repo, base_ref, head_ref)
	if None is entries:
		r: dict[str, Any] = {'category_counts': {'executable': 1}, 'classification': 'executable', 'error': f'Failed to compute git diff for {base_ref}..{head_ref}', 'executable_files': ['<git_diff_error>'], 'file_categories': {}, 'is_executable': True, 'non_executable_files': []}
	else:
		recipes = _resolve_range_recipes(repo, base_ref, head_ref, message, project_root)
		file_cats: dict[str, str] = {}
		for status, pa, pb in entries:
			target, cat = _classify_diff_entry(repo, status, pa, pb, base_ref, head_ref, recipes)
			file_cats[target] = cat
		r = _summarize_categories(file_cats)
	return r
# @used-by :func:`agent_tools.tdd.exemption.is_git_path_exempt()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_git_path_non_executable(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> bool:
	return classify_git_path(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root) in NON_EXECUTABLE_CATEGORIES
# @used-by :func:`agent_tools.tdd.exemption.is_diff_exempt()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_non_executable_diff(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> bool:
	return classify_text_diff(path, old_text, new_text, repo_root=repo_root, message=message, project_root=project_root) in NON_EXECUTABLE_CATEGORIES
# @used-by :func:`resolve_land_test_plan()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def validate_no_tests_override_reason(reason: str | None) -> tuple[bool, str | None]:
	cleaned = ' '.join((reason or '').strip().split())
	if 30 > len(cleaned):
		r: tuple[bool, str | None] = (False, 'Using --no-tests on an executable diff requires an audited --no-tests-reason (>= 30 characters).')
	elif _NO_TESTS_SLOP_RE.search(cleaned):
		r = (False, 'Audited --no-tests-reason cannot be a test-bypass excuse; explain the concrete external verification basis.')
	else:
		r = (True, None)
	return r
# @used-by :func:`agent_tools.worktree_flow._run_land_checks()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def resolve_land_test_plan(wt_path: Path, target_branch: str, *, run_tests: bool, no_tests_reason: str | None=None, project_root: Path | None=None) -> dict[str, Any]:
	diff_info = classify_git_range(wt_path, target_branch, 'HEAD', project_root=project_root)
	blocked_err: str | None = None
	if diff_info['is_executable']:
		if run_tests:
			should_run, skip_reason = (True, None)
		else:
			ok_r, err_r = validate_no_tests_override_reason(no_tests_reason)
			should_run, skip_reason, blocked_err = (False, 'audited_no_tests_override' if ok_r else None, None if ok_r else err_r)
	else:
		should_run, skip_reason = (False, f"non_executable_diff:{diff_info['classification']}")
	return {'blocked_error': blocked_err, 'diff_info': diff_info, 'should_run_post_health': should_run, 'should_run_tests': should_run, 'test_skip_reason': skip_reason}
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`agent_tools.worktree_flow._attach_land_telemetry()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_format_land_diff_telemetry_truncates_and_preserves_counts()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def format_land_diff_telemetry(plan: dict[str, Any] | None, *, max_files: int=DEFAULT_MAX_REPORTED_FILES) -> dict[str, Any]:
	if None is plan:
		r: dict[str, Any] = {}
	else:
		info = plan.get('diff_info') or {}
		cap = max(0, int(max_files))
		exec_files = sorted(info.get('executable_files') or ())
		non_exec = sorted(info.get('non_executable_files') or ())
		counts = dict(sorted((info.get('category_counts') or {}).items()))
		r = {'diff_category_counts': counts, 'diff_classification': info.get('classification'), 'executable_file_count': len(exec_files), 'executable_files': exec_files[:cap], 'non_executable_file_count': len(non_exec), 'non_executable_files': non_exec[:cap], 'test_skip_reason': plan.get('test_skip_reason')}
	return r
__all__ = [
	'DEFAULT_MAX_REPORTED_FILES',
	'NON_EXECUTABLE_CATEGORIES',
	'classify_git_path',
	'classify_git_range',
	'classify_text_diff',
	# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
	'format_land_diff_telemetry',
	'is_git_path_non_executable',
	'is_non_executable_diff',
	'resolve_land_test_plan',
	'validate_no_tests_override_reason',
]
