# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out":
# https://github.com/dmitry-ai/harness/issues/351
from __future__ import annotations
from pathlib import Path
from .classifier import resolve_code_scope
import re
_GIT_C_WT_RE = re.compile(r'(?:-C|--work-tree)(?:=|\s+)(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
_RUNNER_SCRIPT_NAMES = frozenset({'df_github_issue.py', 'harness.py', 'safe_commit.py', 'upwork_project.py'})
_WT_KEY_SEP = '::wt:'
# @used-by :func:`scope_matches_commit()`
def _commit_worktree_id(commit_scope: str | None, event: dict | None) -> str | None:
	r = extract_worktree_scope_id(commit_scope)
	if None is r and isinstance(event, dict):
		r = extract_worktree_scope_id(event.get('cwd'))
		if None is r:
			for match in _GIT_C_WT_RE.finditer(str(event.get('cmd') or '')):
				raw = next((g for g in match.groups() if g), '')
				r = extract_worktree_scope_id(raw)
				if None is not r:
					break
	return r
# @used-by :func:`scope_matches_commit()`
def _norm_lower(path: Path) -> str:
	return path.resolve().as_posix().lower()
# @used-by :func:`agent_tools.tdd.evaluator._command_matches_scope()`
# @used-by :func:`agent_tools.tdd.evaluator._is_exempt_cached()`
# @used-by :func:`agent_tools.tdd.evaluator._update_scope_from_test_cmd()`
def canonical_scope_path(scope_key: str) -> Path:
	base, wt_id = split_tdd_scope_key(scope_key)
	return resolve_code_scope(base / '_wt_scope_probe') if (not base.exists()) and None is not wt_id else base
# @used-by :func:`worktree_command_matches()`
def extract_command_worktree_ids(event: dict) -> set[str]:
	found: set[str] = set()
	cwd_wt = extract_worktree_scope_id(event.get('cwd'))
	if None is not cwd_wt:
		found.add(cwd_wt.lower())
	for tp in (event.get('test_info') or {}).get('target_paths') or ():
		if Path(str(tp)).name.lower() in _RUNNER_SCRIPT_NAMES:
			continue
		tp_wt = extract_worktree_scope_id(tp)
		if None is not tp_wt:
			found.add(tp_wt.lower())
	return found
# @used-by :func:`_commit_worktree_id()`
# @used-by :func:`extract_command_worktree_ids()`
# @used-by :func:`resolve_tdd_scope_key()`
# @used-by :func:`split_tdd_scope_key()`
def extract_worktree_scope_id(path: str | Path | None) -> str | None:
	r: str | None = None
	if path:
		parts = Path(str(path)).parts
		for idx in range(len(parts) - 3):
			if ('\ua616', 'data', 'worktrees') == (parts[idx], parts[idx + 1].lower(), parts[idx + 2].lower()) and parts[idx + 3].strip():
				r = parts[idx + 3].strip()
				break
	return r
# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_code_write()`
# @used-by :func:`agent_tools.tdd.enforcement._eval_shell_prod_writes()`
# @used-by :func:`agent_tools.tdd.evaluator._apply_file_write_event()`
def resolve_tdd_scope_key(path: str | Path, scope: str | Path) -> str:
	scope_s = str(scope or '')
	if (not scope_s) or _WT_KEY_SEP in scope_s:
		r = scope_s
	else:
		wt_id = extract_worktree_scope_id(path)
		scope_wt = extract_worktree_scope_id(scope_s)
		r = f'{scope_s}{_WT_KEY_SEP}{wt_id}' if None is not wt_id and (None is scope_wt or scope_wt.lower() != wt_id.lower()) else scope_s
	return r
# @used-by :func:`agent_tools.tdd.evaluator._apply_commit_reset()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
def scope_matches_commit(scope_key: str, commit_scope: str | None, event: dict | None=None) -> bool:
	base, sk_wt = split_tdd_scope_key(scope_key)
	c_wt = _commit_worktree_id(commit_scope, event)
	if None is not c_wt:
		r = None is not sk_wt and c_wt.lower() == sk_wt.lower()
	elif None is commit_scope:
		r = True
	elif _WT_KEY_SEP in scope_key:
		r = False
	else:
		r = _norm_lower(base) == _norm_lower(Path(commit_scope))
	return r
# @used-by :func:`canonical_scope_path()`
# @used-by :func:`scope_matches_commit()`
# @used-by :func:`worktree_command_matches()`
def split_tdd_scope_key(scope_key: str) -> tuple[Path, str | None]:
	if _WT_KEY_SEP in scope_key:
		raw_base, raw_wt = scope_key.rsplit(_WT_KEY_SEP, 1)
		r: tuple[Path, str | None] = (Path(raw_base).resolve(), raw_wt or None)
	else:
		p = Path(scope_key).resolve()
		r = (p, extract_worktree_scope_id(p))
	return r
# @used-by :func:`agent_tools.tdd.evaluator._command_matches_scope()`
def worktree_command_matches(event: dict, scope_key: str, is_full_cmd: bool) -> bool | None:
	_, sk_wt = split_tdd_scope_key(scope_key)
	cmd_wts = extract_command_worktree_ids(event)
	if None is sk_wt:
		r: bool | None = False if cmd_wts else None
	elif cmd_wts:
		r = None if sk_wt.lower() in cmd_wts else False
	else:
		r = False if _WT_KEY_SEP in scope_key and (not is_full_cmd) else None
	return r
