# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add sandboxed polyglot land tests and post-land health checks":
# https://github.com/dmitry-ai/harness/issues/304
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import shlex
import shutil
import subprocess
from .git_gate import GitRepoGate, _NO_WINDOW
from .path_registry import expand_template, load_registry, project_paths, tool_path
_STRUCTURAL_KEYS = ('errors', 'instance', 'pid', 'runtimePath', 'state', 'version')
# @used-by :func:`resolve_repo_verification_spec()`
def _auto_node_spec(wt_path: Path) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	for rel_dir in ('.', 'Upgrade'):
		pkg = wt_path / rel_dir / 'package.json'
		if pkg.is_file():
			try:
				data = json.loads(pkg.read_text(encoding='utf-8-sig'))
			except (OSError, ValueError):
				data = {}
			script = str(((data.get('scripts') if isinstance(data, dict) else None) or {}).get('test') or '').strip()
			if script:
				tokens = shlex.split(script, posix=True)
				if tokens and 'node' == tokens[0].lower():
					tokens[0] = _resolve_node_exe()
				r = {'test_cwd': rel_dir, 'test_command': tokens, 'watch_host_files': [], 'timeout_seconds': 180}
				break
	return r
# @used-by :func:`dirty_blocking_main_files()`
def _branch_touched_files(main_repo: Path, branch: str) -> set[str]:
	proc = GitRepoGate(main_repo).run_read(['diff', '--name-only', f'HEAD..{branch}'], check=False)
	raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
	return {ln.strip().replace('\\', '/').lstrip('./').casefold() for ln in raw.splitlines() if ln.strip()}
# @used-by :func:`_execute_polyglot_spec()`
def _diff_host_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
	return sorted((k for k in set(before) | set(after) if before.get(k) != after.get(k)))
# @used-by :func:`_expand_spec()`
def _expand_token(raw: str, reg) -> str:
	val = str(raw or '')
	if '${' in val or '%' in val:
		try:
			val = expand_template(val, reg.resolved_variables, env=reg.env, normalize=False)
		except Exception:
			val = os.path.expandvars(val)
	return val
# @used-by :func:`resolve_repo_verification_spec()`
def _expand_spec(raw_spec: dict[str, Any], reg) -> dict[str, Any]:
	out = dict(raw_spec)
	for key in ('test_command', 'health_command', 'watch_host_files'):
		vals = raw_spec.get(key)
		if isinstance(vals, list):
			out[key] = [_expand_token(str(v), reg) for v in vals]
	return out
# @used-by :func:`_interpret_health_proc()`
def _parse_health_state(stdout: str) -> str:
	r = ''
	text = (stdout or '').strip()
	if text:
		try:
			parsed = json.loads(text)
		except ValueError:
			parsed = None
		if isinstance(parsed, dict):
			r = str(parsed.get('state') or '').strip().lower()
	return r
# @used-by :func:`dirty_blocking_main_files()`
def _porcelain_paths(raw: str) -> list[str]:
	paths: list[str] = []
	for line in (raw or '').splitlines():
		if 4 <= len(line):
			entry = line[3:].strip()
			if ' -> ' in entry:
				entry = entry.split(' -> ', 1)[1].strip()
			clean = entry.strip('"').replace('\\', '/').lstrip('./')
			if clean:
				paths.append(clean)
	return paths
# @used-by :func:`_auto_node_spec()`
def _resolve_node_exe() -> str:
	try:
		cand = tool_path('node')
		r = str(cand) if cand.is_file() else 'node'
	except Exception:
		r = 'node'
	return r
# 2026-11-26 "Handle worktree-land gate timeouts cleanly and add cross-cutting boundary regressions": https://github.com/dmitry-ai/harness/issues/365
# @used-by :func:`_execute_polyglot_spec()`
def _run_polyglot_proc(cmd: list[str], cwd: Path, sandbox: Path, timeout: int) -> tuple[int, bool, str]:
	try:
		proc = subprocess.run(cmd, cwd=str(cwd), env=_sandbox_env(sandbox), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, check=False, creationflags=_NO_WINDOW)
		out = '\n'.join((p for p in (proc.stdout, proc.stderr) if p))[-4000:]
		r = (proc.returncode, False, out)
	except subprocess.TimeoutExpired as exc:
		r = (-1, True, f'Polyglot land tests timed out after {exc.timeout}s')
	finally:
		shutil.rmtree(sandbox, ignore_errors=True)
	return r
# @used-by :func:`_run_polyglot_proc()`
def _sandbox_env(sandbox_dir: Path) -> dict[str, str]:
	appdata = sandbox_dir / 'appdata'
	localappdata = sandbox_dir / 'localappdata'
	tools_state = sandbox_dir / 'tools-state'
	for sub in (appdata, localappdata, tools_state):
		sub.mkdir(parents=True, exist_ok=True)
	return {**os.environ, 'APPDATA': str(appdata), 'LOCALAPPDATA': str(localappdata), 'ANTIGRAVITY_TOOLS_STATE_DIR': str(tools_state), 'GIT_OPTIONAL_LOCKS': '0'}
# @used-by :func:`_execute_polyglot_spec()`
def _sandbox_root(main_repo: Path) -> Path:
	r: Path | None = None
	for anc in (main_repo, *main_repo.parents[:4]):
		cand = anc / '\ua616/data'
		if cand.is_dir():
			r = cand
			break
	return r if None is not r else project_paths(main_repo).data_dir
# @used-by :func:`_snapshot_host_files()`
def _snapshot_one_host_file(path: Path) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	if path.is_file():
		try:
			parsed = json.loads(path.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError):
			parsed = None
		if isinstance(parsed, dict):
			r = {'kind': 'json', 'fields': {k: parsed.get(k) for k in _STRUCTURAL_KEYS}}
		else:
			try:
				r = {'kind': 'bytes', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
			except OSError:
				r = {'kind': 'unreadable'}
	return r
# @used-by :func:`_execute_polyglot_spec()`
def _snapshot_host_files(paths: list[Path]) -> dict[str, Any]:
	return {p.as_posix(): _snapshot_one_host_file(p) for p in paths}
# @used-by :func:`run_repo_health_check()`
def _interpret_health_proc(proc: subprocess.CompletedProcess, eff: dict[str, Any]) -> dict[str, Any]:
	ok_codes = set(eff.get('health_ok_exit_codes') or (0,))
	skip_codes = set(eff.get('health_skip_exit_codes') or (2,))
	skip_states = {str(s).strip().lower() for s in (eff.get('health_skip_states') or ('unavailable', 'waiting-for-sign-in'))}
	state = _parse_health_state(proc.stdout)
	if proc.returncode in ok_codes:
		r = {'ok': True, 'skipped': False, 'state': state or 'ready', 'exit_code': proc.returncode, 'error': ''}
	elif proc.returncode in skip_codes and state in skip_states:
		r = {'ok': True, 'skipped': True, 'state': state, 'exit_code': proc.returncode, 'error': ''}
	else:
		detail = (proc.stderr or proc.stdout or f'health command exited {proc.returncode}').strip()
		r = {'ok': False, 'skipped': False, 'state': state or 'error', 'exit_code': proc.returncode, 'error': detail[:600]}
	return r
# @used-by :func:`agent_tools.worktree_flow._land_under_lease()`
# @used-by :func:`agent_tools.worktree_land_flow._phase2_commit_under_lease()`
# @used-by :mod:`agent_tools.polyglot_land`
def dirty_blocking_main_files(main_repo: Path, branch: str) -> list[str]:
	from .addon_observability import is_live_runtime_data_file
	raw = GitRepoGate(main_repo).git('status', '--porcelain').decode('utf-8', errors='replace')
	dirty = _porcelain_paths(raw)
	if not dirty:
		r: list[str] = []
	else:
		touched = _branch_touched_files(main_repo, branch)
		r = [rel for rel in dirty if rel.casefold() in touched or (not is_live_runtime_data_file(main_repo, rel))]
	return r
# @used-by :func:`run_polyglot_land_tests()`
# @used-by :func:`run_repo_health_check()`
# @used-by :mod:`agent_tools.polyglot_land`
def resolve_repo_verification_spec(main_repo: Path, wt_path: Path | None=None, *, slug: str | None=None) -> dict[str, Any] | None:
	from .issues.workspace import IssueEvidenceWorkspace
	reg = load_registry()
	eff_slug = (slug or IssueEvidenceWorkspace.origin_repo_slug(main_repo) or '').strip().lower()
	raw_map = reg.raw.get('repo_verification') or {}
	found: dict[str, Any] | None = None
	if eff_slug and isinstance(raw_map, dict):
		for key, val in raw_map.items():
			if str(key).strip().lower() == eff_slug and isinstance(val, dict):
				found = _expand_spec(val, reg)
				break
	return found if None is not found else (_auto_node_spec(wt_path) if None is not wt_path else None)
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# 2026-11-26 "Handle worktree-land gate timeouts cleanly and add cross-cutting boundary regressions": https://github.com/dmitry-ai/harness/issues/365
# @used-by :func:`run_polyglot_land_tests()`
def _execute_polyglot_spec(main_repo: Path, wt_path: Path, eff: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
	sandbox = _sandbox_root(main_repo) / 'test-sandbox' / wt_path.name
	watch = [Path(p) for p in (eff.get('watch_host_files') or ()) if str(p).strip()]
	before = _snapshot_host_files(watch)
	cwd = (wt_path / str(eff.get('test_cwd') or '.')).resolve()
	timeout = max(5, int(eff.get('timeout_seconds') or 180))
	rc, timed_out, out = _run_polyglot_proc(list(eff['test_command']), cwd, sandbox, timeout)
	mutated = _diff_host_snapshots(before, _snapshot_host_files(watch))
	ok = (0 == rc) and (not timed_out) and (not mutated)
	stage = 'host_mutation' if mutated else (None if ok else 'tests')
	return (ok, {'ok': ok, 'runner': 'polyglot', 'failure_stage': stage, 'timed_out': timed_out, 'mutated_host_files': mutated, 'exit_code': rc, 'output': out})
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :func:`agent_tools.worktree_flow._run_land_tests()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_host_state_mutation_fails_closed_while_heartbeat_timestamp_is_ignored()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :mod:`agent_tools.polyglot_land`
def run_polyglot_land_tests(main_repo: Path, wt_path: Path, *, spec: dict[str, Any] | None=None, base_ref: str | None=None) -> tuple[bool, dict[str, Any] | None]:
	from .tdd.diff_executability import classify_git_range
	if None is not base_ref and (not classify_git_range(wt_path, base_ref, 'HEAD')['is_executable']):
		r: tuple[bool, dict[str, Any] | None] = (True, None)
	else:
		eff = spec if None is not spec else resolve_repo_verification_spec(main_repo, wt_path)
		r = (True, None) if (None is eff or (not eff.get('test_command'))) else _execute_polyglot_spec(main_repo, wt_path, eff)
	return r
# @used-by :func:`agent_tools.addon_observability.check_close_companion_health()`
# @used-by :func:`agent_tools.worktree_flow._post_merge_checks()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
# @used-by :mod:`agent_tools.polyglot_land`
def run_repo_health_check(code_repo: Path, *, slug: str | None=None, spec: dict[str, Any] | None=None, force: bool=False) -> dict[str, Any]:
	eff = spec if None is not spec else resolve_repo_verification_spec(code_repo, slug=slug)
	if None is eff or (not eff.get('health_command')):
		r: dict[str, Any] = {'ok': True, 'skipped': True, 'state': 'none', 'error': ''}
	elif (not force) and '1' == str(os.environ.get('HARNESS_TEST_NO_FSYNC') or '').strip() and '1' != str(os.environ.get('HARNESS_RUN_LIVE_HEALTH') or '').strip():
		r = {'ok': True, 'skipped': True, 'state': 'test_isolated', 'error': ''}
	else:
		try:
			proc = subprocess.run(list(eff['health_command']), cwd=str(Path(code_repo).resolve()), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=False, creationflags=_NO_WINDOW)
		except (OSError, subprocess.SubprocessError) as exc:
			r = {'ok': False, 'skipped': False, 'state': 'error', 'exit_code': -1, 'error': str(exc)}
		else:
			r = _interpret_health_proc(proc, eff)
	return r
__all__ = ['dirty_blocking_main_files', 'resolve_repo_verification_spec', 'run_polyglot_land_tests', 'run_repo_health_check']