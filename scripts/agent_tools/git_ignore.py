# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.GlobalIgnoreSyncer import GIT_IGNORE_END, GIT_IGNORE_START, HARNESS_GLOBAL_IGNORE_PATTERNS, GlobalIgnoreSyncer
from Df.Harness.Git.WorktreeExcludeManager import WorktreeExcludeManager
from Df.Harness.lib.worktree import dfh_prepare_worktrees_base_dir
from .path_cache import resolve_code_anchor
from .shell_audit import normalize_host_path
import os
import subprocess
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_MODULE_PRIMARY = Path(__file__).resolve().parents[2]
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`resolve_managed_git_ignore_target()`
def _is_canonical_primary(primary: Path) -> bool:
	return resolve_code_anchor(primary) == resolve_code_anchor(_MODULE_PRIMARY)
# @used-by :func:`finalize_install_result()`
def _skipped_git_ignore_report() -> dict:
	return {'valid': True, 'skipped': True, 'reason': 'isolated_primary', 'path': None, 'changed': False, 'patterns': list(HARNESS_GLOBAL_IGNORE_PATTERNS), 'issues': []}
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_ensure_worktree_dir_ignored_handles_non_git_directory()`
# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_ensure_worktree_dir_ignored_skips_exclude_edit_when_already_ignored()`
def ensure_worktree_dir_ignored(base_dir: Path | str) -> dict:
	return WorktreeExcludeManager(base_dir).ensure()
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
def finalize_install_result(result: dict, all_declared: list, names: list, primary: Path, *, check: bool=False, git_ignore_path: Path | str | None=None) -> dict:
	result['skipped_disabled'] = [name for name in all_declared if name not in names]
	target = resolve_managed_git_ignore_target(primary, git_ignore_path=git_ignore_path)
	gi = _skipped_git_ignore_report() if None is target else sync_global_git_ignore(check=check, ignore_path=target)
	result['git_ignore'] = gi
	if gi.get('changed') and gi.get('path'):
		result.setdefault('written', []).append(gi['path'])
	if not gi.get('valid'):
		result['valid'] = False
		result.setdefault('issues', []).extend(gi.get('issues') or [])
	from .runtime_snapshot import finalize_native_install
	return finalize_native_install(result, primary, check=check)
# @used-by unused
def merge_managed_git_ignore(existing_text: str, *, patterns: tuple[str, ...]=HARNESS_GLOBAL_IGNORE_PATTERNS) -> str:
	nl = '\r\n' if '\r\n' in existing_text else '\n'
	block = render_managed_git_ignore_block(patterns, newline=nl)
	has_start, has_end = (GIT_IGNORE_START in existing_text, GIT_IGNORE_END in existing_text)
	if (not has_start) and (not has_end):
		sep = '' if (not existing_text) or existing_text.endswith(('\n', '\r')) else nl
		r = f'{existing_text}{sep}{block}{nl}'
	elif 1 != existing_text.count(GIT_IGNORE_START) or 1 != existing_text.count(GIT_IGNORE_END) or existing_text.index(GIT_IGNORE_START) > existing_text.index(GIT_IGNORE_END):
		raise ValueError('Malformed Harness global Git ignore block; user file preserved')
	else:
		r = existing_text[:existing_text.index(GIT_IGNORE_START)] + block + existing_text[existing_text.index(GIT_IGNORE_END) + len(GIT_IGNORE_END):]
	return r
# @used-by unused
def prepare_worktrees_base_dir(repo: Path | str, *, worktrees_dir: Path | str | None=None) -> tuple[Path, dict]:
	return dfh_prepare_worktrees_base_dir(repo, worktrees_dir=worktrees_dir)
# @used-by :func:`merge_managed_git_ignore()`
def render_managed_git_ignore_block(patterns: tuple[str, ...]=HARNESS_GLOBAL_IGNORE_PATTERNS, *, newline: str='\n') -> str:
	return newline.join((GIT_IGNORE_START, *patterns, GIT_IGNORE_END))
# @used-by :func:`resolve_managed_git_ignore_target()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_resolve_global_git_ignore_path_precedence()`
def resolve_global_git_ignore_path(*, env: dict[str, str] | None=None, explicit_path: Path | str | None=None) -> Path:
	if None is not explicit_path:
		r = normalize_host_path(str(explicit_path)).resolve()
	else:
		proc = subprocess.run(['git', 'config', '--global', '--path', '--get', 'core.excludesFile'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, check=False, creationflags=_NO_WINDOW)
		raw = (proc.stdout or '').strip() if 0 == proc.returncode else ''
		if raw:
			r = normalize_host_path(raw).resolve()
		else:
			eff_env = os.environ if None is env else env
			xdg = (eff_env.get('XDG_CONFIG_HOME') or '').strip()
			home = (eff_env.get('HOME') or '').strip()
			r = (normalize_host_path(xdg) / 'git/ignore').resolve() if xdg else ((normalize_host_path(home) / '.config/git/ignore').resolve() if home else (Path.home() / '.config/git/ignore').resolve())
	return r
# @used-by :func:`finalize_install_result()`
def resolve_managed_git_ignore_target(primary: Path | str, *, git_ignore_path: Path | str | None=None, env: dict[str, str] | None=None) -> Path | None:
	if None is not git_ignore_path:
		r = normalize_host_path(str(git_ignore_path)).resolve()
	elif _is_canonical_primary(Path(primary)):
		r = resolve_global_git_ignore_path(env=env)
	else:
		r = None
	return r
# @used-by :func:`finalize_install_result()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_malformed_managed_markers_fail_without_corrupting_file()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_real_git_ignores_embedded_worktree_via_global_ignore()`
def sync_global_git_ignore(*, check: bool=False, ignore_path: Path | str | None=None, env: dict[str, str] | None=None) -> dict:
	return GlobalIgnoreSyncer(check=check, ignore_path=ignore_path, env=env).sync()
