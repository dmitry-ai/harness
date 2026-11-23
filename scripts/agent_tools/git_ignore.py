# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Auto-exclude worktrees_dir in enclosing repo info/exclude on worktree creation":
# https://github.com/dmitry-ai/harness/issues/201
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Manage Harness ephemeral Git exclusions in install-global and doctor":
# https://github.com/dmitry-ai/harness/issues/198
from __future__ import annotations
from pathlib import Path
import os
import subprocess
from .path_cache import resolve_code_anchor
from .shell_audit import normalize_host_path
from .storage import replace_bytes
GIT_IGNORE_END = '# <<< harness:ephemeral-ignore:end <<<'
GIT_IGNORE_START = '# >>> harness:ephemeral-ignore:start >>>'
HARNESS_GLOBAL_IGNORE_PATTERNS = ('\ua616/data/worktrees/', '\ua616/data/scratch/', '\ua616/data/browser-locks/', '\ua616/data/repo-leases/', '**/*.lock')
_MODULE_PRIMARY = Path(__file__).resolve().parents[2]
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
def _append_exclude_pattern(exclude_file: Path, pattern: str) -> bool:
	existing = exclude_file.read_text(encoding='utf-8') if exclude_file.is_file() else ''
	if pattern in existing.splitlines():
		r = False
	else:
		nl = '\r\n' if '\r\n' in existing else '\n'
		sep = '' if not existing or existing.endswith(('\n', '\r')) else nl
		replace_bytes(exclude_file, f'{existing}{sep}{pattern}{nl}'.encode('utf-8'))
		r = True
	return r
def _configured_excludes_file(env: dict[str, str] | None) -> Path | None:
	proc = subprocess.run(['git', 'config', '--global', '--path', '--get', 'core.excludesFile'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, check=False, creationflags=_NO_WINDOW)
	raw = (proc.stdout or '').strip() if 0 == proc.returncode else ''
	return normalize_host_path(raw).resolve() if raw else None
def _detect_enclosing_repo(base_dir: Path) -> tuple[Path, Path, str] | None:
	proc = _git_read(base_dir, 'rev-parse', '--show-toplevel', '--git-common-dir')
	lines = [ln.strip() for ln in (proc.stdout or '').splitlines() if ln.strip()] if 0 == proc.returncode else []
	if 2 > len(lines):
		r = None
	else:
		toplevel = normalize_host_path(lines[0]).resolve()
		raw_common = normalize_host_path(lines[1])
		common = raw_common.resolve() if raw_common.is_absolute() else (base_dir / raw_common).resolve()
		try:
			rel = base_dir.relative_to(toplevel).as_posix()
		except ValueError:
			rel = ''
		r = (toplevel, common, rel) if rel and '.' != rel else None
	return r
def _git_ignore_issue(target: Path, message: str) -> dict:
	return {'file': str(target), 'message': message}
def _git_read(cwd: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '--no-optional-locks', '-C', str(cwd), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, check=False, creationflags=_NO_WINDOW)
def _is_canonical_primary(primary: Path) -> bool:
	return resolve_code_anchor(primary) == resolve_code_anchor(_MODULE_PRIMARY)
def _is_path_ignored(toplevel: Path, rel_probe: str) -> bool:
	return 0 == _git_read(toplevel, 'check-ignore', '-q', '--no-index', '--', rel_probe).returncode
def _merge_managed_block(existing: str, block: str, *, newline: str) -> str:
	has_start, has_end = (GIT_IGNORE_START in existing, GIT_IGNORE_END in existing)
	if not has_start and (not has_end):
		sep = '' if not existing or existing.endswith(('\n', '\r')) else newline
		r = f'{existing}{sep}{block}{newline}'
	elif 1 != existing.count(GIT_IGNORE_START) or 1 != existing.count(GIT_IGNORE_END) or existing.index(GIT_IGNORE_START) > existing.index(GIT_IGNORE_END):
		raise ValueError('Malformed Harness global Git ignore block; user file preserved')
	else:
		start_idx = existing.index(GIT_IGNORE_START)
		end_idx = existing.index(GIT_IGNORE_END) + len(GIT_IGNORE_END)
		r = existing[:start_idx] + block + existing[end_idx:]
	return r
def _plan_global_git_ignore(target: Path) -> tuple[str | None, str | None, str | None]:
	if target.exists() and (not target.is_file()):
		r = (None, None, 'Global Git ignore target is not a regular file; preserved')
	else:
		try:
			existing = target.read_text(encoding='utf-8') if target.exists() else ''
			desired = merge_managed_git_ignore(existing)
			r = (existing, desired, None)
		except (OSError, UnicodeDecodeError, ValueError) as exc:
			r = (None, None, str(exc))
	return r
def _skipped_git_ignore_report() -> dict:
	return {'valid': True, 'skipped': True, 'reason': 'isolated_primary', 'path': None, 'changed': False, 'patterns': list(HARNESS_GLOBAL_IGNORE_PATTERNS), 'issues': []}
def _tracked_worktree_entries(toplevel: Path, rel: str) -> tuple[list[dict], list[str], list[str]]:
	proc = _git_read(toplevel, '-c', 'core.quotePath=false', 'ls-files', '--stage', '--', rel)
	entries, gitlinks, warnings = ([], [], [])
	if 0 == proc.returncode:
		for line in (proc.stdout or '').splitlines():
			meta, sep, path = line.partition('\t')
			parts = meta.split()
			if sep and 2 <= len(parts) and path:
				mode, sha = (parts[0], parts[1])
				entries.append({'mode': mode, 'sha': sha, 'path': path})
				if '160000' == mode:
					gitlinks.append(path)
				warnings.append(f'Enclosing repo {toplevel.as_posix()} already tracks {path} (mode {mode}); untrack via: git -C "{toplevel.as_posix()}" rm --cached "{path}"')
	return (entries, gitlinks, warnings)
def _write_verified_ignore(target: Path, desired: str) -> str | None:
	payload = desired.encode('utf-8')
	try:
		replace_bytes(target, payload)
		err = None if target.read_bytes() == payload else 'Global Git ignore read-back verification failed'
	except OSError as exc:
		err = str(exc)
	return err
def ensure_worktree_dir_ignored(base_dir: Path | str) -> dict:
	target = normalize_host_path(str(base_dir)).resolve()
	target.mkdir(parents=True, exist_ok=True)
	enclosing = _detect_enclosing_repo(target)
	if None is enclosing:
		r = {'enclosing_repo': None, 'already_ignored': False, 'excluded': False, 'exclude_file': None, 'pattern': None, 'tracked_entries': [], 'tracked_gitlinks': [], 'warnings': []}
	else:
		toplevel, common_dir, rel = enclosing
		pattern = f'/{rel}/'
		exclude_file = common_dir / 'info/exclude'
		already = _is_path_ignored(toplevel, f'{rel}/probe')
		excluded = False if already else _append_exclude_pattern(exclude_file, pattern)
		entries, gitlinks, warnings = _tracked_worktree_entries(toplevel, rel)
		r = {'enclosing_repo': toplevel.as_posix(), 'already_ignored': already, 'excluded': excluded, 'exclude_file': exclude_file.as_posix(), 'pattern': pattern, 'tracked_entries': entries, 'tracked_gitlinks': gitlinks, 'warnings': warnings}
	return r
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
	return result
def merge_managed_git_ignore(existing_text: str, *, patterns: tuple[str, ...]=HARNESS_GLOBAL_IGNORE_PATTERNS) -> str:
	nl = '\r\n' if '\r\n' in existing_text else '\n'
	block = render_managed_git_ignore_block(patterns, newline=nl)
	return _merge_managed_block(existing_text, block, newline=nl)
def prepare_worktrees_base_dir(repo: Path | str, *, worktrees_dir: Path | str | None=None) -> tuple[Path, dict]:
	from .path_registry import project_paths
	base = normalize_host_path(str(worktrees_dir)).resolve() if None is not worktrees_dir else project_paths(Path(repo).resolve()).worktrees_dir.resolve()
	return (base, ensure_worktree_dir_ignored(base))
def render_managed_git_ignore_block(patterns: tuple[str, ...]=HARNESS_GLOBAL_IGNORE_PATTERNS, *, newline: str='\n') -> str:
	return newline.join((GIT_IGNORE_START, *patterns, GIT_IGNORE_END))
def resolve_global_git_ignore_path(*, env: dict[str, str] | None=None, explicit_path: Path | str | None=None) -> Path:
	if None is not explicit_path:
		r = normalize_host_path(str(explicit_path)).resolve()
	else:
		configured = _configured_excludes_file(env)
		if None is not configured:
			r = configured
		else:
			eff_env = os.environ if None is env else env
			xdg = (eff_env.get('XDG_CONFIG_HOME') or '').strip()
			home = (eff_env.get('HOME') or '').strip()
			if xdg:
				r = (normalize_host_path(xdg) / 'git/ignore').resolve()
			elif home:
				r = (normalize_host_path(home) / '.config/git/ignore').resolve()
			else:
				r = (Path.home() / '.config/git/ignore').resolve()
	return r
def resolve_managed_git_ignore_target(primary: Path | str, *, git_ignore_path: Path | str | None=None, env: dict[str, str] | None=None) -> Path | None:
	if None is not git_ignore_path:
		r = normalize_host_path(str(git_ignore_path)).resolve()
	elif _is_canonical_primary(Path(primary)):
		r = resolve_global_git_ignore_path(env=env)
	else:
		r = None
	return r
def sync_global_git_ignore(*, check: bool=False, ignore_path: Path | str | None=None, env: dict[str, str] | None=None) -> dict:
	target = resolve_global_git_ignore_path(env=env, explicit_path=ignore_path)
	existing, desired, plan_err = _plan_global_git_ignore(target)
	if None is not plan_err:
		r = {'valid': False, 'path': target.as_posix(), 'changed': False, 'patterns': list(HARNESS_GLOBAL_IGNORE_PATTERNS), 'issues': [_git_ignore_issue(target, plan_err)]}
	else:
		needs_write = (not target.exists()) or existing != desired
		if not needs_write:
			r = {'valid': True, 'path': target.as_posix(), 'changed': False, 'patterns': list(HARNESS_GLOBAL_IGNORE_PATTERNS), 'issues': []}
		elif check:
			r = {'valid': False, 'path': target.as_posix(), 'changed': False, 'patterns': list(HARNESS_GLOBAL_IGNORE_PATTERNS), 'issues': [_git_ignore_issue(target, 'Global Git ignore file is missing or stale Harness ephemeral block; run harness.py install-global')]}
		else:
			write_err = _write_verified_ignore(target, desired or '')
			issues = [] if None is write_err else [_git_ignore_issue(target, write_err)]
			r = {'valid': None is write_err, 'path': target.as_posix(), 'changed': None is write_err, 'patterns': list(HARNESS_GLOBAL_IGNORE_PATTERNS), 'issues': issues}
	return r
