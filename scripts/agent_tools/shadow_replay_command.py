# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add mutating command execution mode to shadow-replay with isolated native profiles":
# https://github.com/dmitry-ai/harness/issues/289
from __future__ import annotations
from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess
import sys
from Df.Core.lib.time import df_utc_iso
from .journal import resolve_journal_dir, state_dir
from .path_registry import project_paths
from .project_rename import _infer_daily_root, rename_project
from .project_rename_verify import capture_pre_rename_snapshot, infer_launcher_root, verify_post_rename
from .shadow_replay_clone import _path_pairs, _rewrite_json_file, clone_project_tree
from .storage import replace_bytes
HARNESS_PY = Path(__file__).resolve().parents[1] / 'harness.py'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`_run_generic_command()`
def _build_command_argv(command_spec: str, shadow_project: Path, shadow_launcher: Path | None) -> list[str]:
	tokens = shlex.split(command_spec, posix=True)
	if tokens and Path(tokens[0]).name.lower() in ('python', 'python.exe', 'python3', 'py'):
		tokens = tokens[1:]
	if tokens and 'harness.py' == Path(tokens[0]).name.lower():
		tokens = tokens[1:]
	l_str = str(shadow_launcher) if None is not shadow_launcher else ''
	mapped = [t.replace('{project}', str(shadow_project)).replace('{launcher}', l_str) for t in tokens]
	return [sys.executable, str(HARNESS_PY), *mapped]
# @used-by :func:`_stage_ag_from_receipt()`
# @used-by :func:`_stage_folders_json()`
def _copy_native_profile(src_file: Path, dst_file: Path, pairs: list[tuple[str, str]]) -> None:
	dst_file.parent.mkdir(parents=True, exist_ok=True)
	if src_file.is_file():
		shutil.copy2(src_file, dst_file)
		_rewrite_json_file(dst_file, pairs)
# @used-by :func:`persist_shadow_replay_receipt()`
def _harness_repo_head() -> str | None:
	repo = Path(__file__).resolve().parents[2]
	r = None
	try:
		proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'rev-parse', 'HEAD'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=10, creationflags=_NO_WINDOW, check=False)
		if 0 == proc.returncode and proc.stdout.strip():
			r = proc.stdout.strip()
	except OSError:
		r = None
	return r
# @used-by :func:`_run_generic_command()`
def _iso_cmd_env(shadow_root: Path) -> dict[str, str]:
	home = shadow_root / 'native-home'
	(home / 'AppData/Roaming').mkdir(parents=True, exist_ok=True)
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
# @used-by :func:`_run_generic_command()`
def _parse_json_stdout(text: str) -> dict | None:
	r = None
	raw = (text or '').strip()
	if raw.startswith('{'):
		try:
			val = json.loads(raw)
			r = val if isinstance(val, dict) else None
		except ValueError:
			r = None
	return r
# @used-by :func:`execute_shadow_command()`
def _run_exec_rename_domain(shadow_project: Path, shadow_launcher: Path | None, shadow_daily: Path | None, shadow_root: Path, domain: str, pairs: list[tuple[str, str]], checks: dict, verified: list[str], errors: list[str]) -> Path:
	ag_dirs, folders = _stage_ag_from_receipt(shadow_project, shadow_root / 'native-profiles', pairs)
	final_dir = shadow_project
	try:
		res = rename_project(shadow_project, domain=domain, daily_root=shadow_daily, register_native=True, antigravity_projects_dirs=ag_dirs, antigravity_folders_json=folders, targets=['antigravity'], launcher_root=shadow_launcher)
		checks['command_exec'] = {'mode': 'exec_rename_domain', 'domain': domain, 'valid': bool(res.get('valid')), 'renamed': bool(res.get('renamed')), 'project_dir': res.get('project_dir')}
		post_ver = res.get('post_verification') or {}
		checks['post_rename_verify'] = post_ver
		if res.get('valid') and post_ver.get('valid'):
			verified.extend(('command_exec', 'post_rename_verify'))
			final_dir = Path(str(res['project_dir'])).resolve()
		else:
			errors.extend(res.get('errors') or ['rename-project failed validation'])
	except (OSError, ValueError) as exc:
		checks['command_exec'] = {'mode': 'exec_rename_domain', 'domain': domain, 'valid': False, 'error': str(exc)}
		errors.append(f'exec_rename_domain: {exc}')
	return final_dir
# @used-by :func:`execute_shadow_command()`
def _run_generic_command(shadow_project: Path, shadow_launcher: Path | None, shadow_root: Path, command_spec: str, checks: dict, verified: list[str], errors: list[str]) -> Path:
	pre_snap = capture_pre_rename_snapshot(shadow_project)
	argv = _build_command_argv(command_spec, shadow_project, shadow_launcher)
	proc = subprocess.run(argv, cwd=str(shadow_root), env=_iso_cmd_env(shadow_root), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=90, creationflags=_NO_WINDOW, check=False)
	payload = _parse_json_stdout(proc.stdout)
	ok = 0 == proc.returncode and (not isinstance(payload, dict) or False is not payload.get('valid'))
	checks['command_exec'] = {'mode': 'command', 'command': command_spec, 'returncode': proc.returncode, 'valid': ok, 'stderr': (proc.stderr or '').strip()[:400]}
	final_dir = Path(str(payload['project_dir'])).resolve() if isinstance(payload, dict) and payload.get('project_dir') and Path(str(payload['project_dir'])).is_dir() else shadow_project
	if ok:
		verified.append('command_exec')
		_verify_shadow_command_post(shadow_project, final_dir, pre_snap, shadow_launcher, checks, verified, errors)
	else:
		msg = (proc.stderr or proc.stdout or '').strip()[:300]
		errors.append(f'command failed (exit={proc.returncode}): {msg}')
	return final_dir
# @used-by :func:`_run_exec_rename_domain()`
def _stage_ag_from_receipt(shadow_project: Path, native_root: Path, pairs: list[tuple[str, str]]) -> tuple[dict[str, Path], Path]:
	regs_f = project_paths(shadow_project, exact_root=True).registrations_json
	ag_data = json.loads(regs_f.read_text(encoding='utf-8-sig')).get('antigravity') if regs_f.is_file() else {}
	insts = (ag_data or {}).get('instances') or {}
	ag_dirs: dict[str, Path] = {}
	src_folders = Path(str(ag_data['folders_json'])) if isinstance(ag_data, dict) and ag_data.get('folders_json') else None
	for iid, rec in insts.items():
		if isinstance(rec, dict) and rec.get('project_file'):
			p_src = Path(str(rec['project_file']))
			dst_dir = native_root / 'antigravity' / str(iid) / 'projects'
			_copy_native_profile(p_src, dst_dir / p_src.name, pairs)
			ag_dirs[str(iid)] = dst_dir
			src_folders = Path(str(rec['folders_json'])) if None is src_folders and rec.get('folders_json') else src_folders
	if not ag_dirs:
		ag_dirs['A0'] = native_root / 'antigravity/A0/projects'
		ag_dirs['A0'].mkdir(parents=True, exist_ok=True)
	dst_folders = native_root / 'antigravity/folders.json'
	_stage_folders_json(src_folders, dst_folders, pairs)
	return (ag_dirs, dst_folders)
# @used-by :func:`_stage_ag_from_receipt()`
def _stage_folders_json(src_folders: Path | None, dst_folders: Path, pairs: list[tuple[str, str]]) -> None:
	dst_folders.parent.mkdir(parents=True, exist_ok=True)
	if None is not src_folders and src_folders.is_file():
		_copy_native_profile(src_folders, dst_folders, pairs)
	else:
		dst_folders.write_text('{"folders":[],"projectFolderMap":{}}\n', encoding='utf-8')
# @used-by :func:`stage_command_shadow_copies()`
def _stage_shadow_launcher(src_launcher: Path | None, shadow_root: Path, daily_layout: bool) -> tuple[Path | None, dict[Path, Path], dict[str, Path]]:
	relocs: dict[Path, Path] = {}
	states: dict[str, Path] = {}
	shadow_launcher = None
	if None is not src_launcher:
		shadow_launcher = shadow_root / ('proposals/init' if daily_layout else 'launcher')
		clone_project_tree(src_launcher, shadow_launcher, hardlink_evidence=False)
		states['launcher'] = state_dir(resolve_journal_dir(src_launcher))
		relocs[src_launcher] = shadow_launcher
	return (shadow_launcher, relocs, states)
# @used-by :func:`_run_generic_command()`
def _verify_shadow_command_post(shadow_project: Path, final_dir: Path, pre_snap: dict, shadow_launcher: Path | None, checks: dict, verified: list[str], errors: list[str]) -> None:
	post_ver = verify_post_rename(shadow_project, final_dir, pre_snap, launcher_root=shadow_launcher)
	checks['post_rename_verify'] = post_ver
	if post_ver['valid']:
		verified.append('post_rename_verify')
	else:
		errors.extend(post_ver['errors'])
# @used-by :func:`agent_tools.shadow_replay._run_shadow_mode()`
# @used-by :mod:`agent_tools.shadow_replay_command`
def execute_shadow_command(src_project: Path, shadow_project: Path, shadow_launcher: Path | None, shadow_daily: Path | None, shadow_root: Path, *, exec_rename_domain: str | None, command: str | None, checks: dict, verified: list[str], errors: list[str]) -> Path:
	pairs = _path_pairs(((src_project, shadow_project),))
	if exec_rename_domain:
		r = _run_exec_rename_domain(shadow_project, shadow_launcher, shadow_daily, shadow_root, exec_rename_domain, pairs, checks, verified, errors)
	else:
		r = _run_generic_command(shadow_project, shadow_launcher, shadow_root, str(command or ''), checks, verified, errors)
	return r
# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
# @used-by :mod:`agent_tools.shadow_replay_command`
def persist_shadow_replay_receipt(ws_root: Path, src_project: Path, report: dict, *, exec_rename_domain: str | None, command: str | None) -> str | None:
	r = None
	if ws_root.resolve() != src_project.resolve():
		dest = project_paths(ws_root, exact_root=True).data_dir / 'shadow-replay-receipt.json'
		mode = 'exec_rename_domain' if exec_rename_domain else ('command' if command else 'replay')
		# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
		payload = {'schema_version': 1, 'recorded_at': df_utc_iso(), 'repo_head': _harness_repo_head(), 'valid': bool(report.get('valid')), 'exit_code': 0 if report.get('valid') else 2, 'mode': mode, 'project': str(src_project), 'exec_rename_domain': exec_rename_domain, 'command': command, 'stages_verified': list(report.get('stages_verified') or ()), 'errors': list(report.get('errors') or ())}
		replace_bytes(dest, (json.dumps(payload, ensure_ascii=False, indent='\t') + '\n').encode('utf-8'))
		r = str(dest)
	return r
# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
# @used-by :mod:`agent_tools.shadow_replay_command`
def resolve_shadow_launcher(src_project: Path, launcher: str | Path | None) -> Path | None:
	explicit = Path(launcher).resolve() if None is not launcher else None
	return infer_launcher_root(src_project, _infer_daily_root(src_project, None), explicit)
# @used-by :func:`agent_tools.shadow_replay._prepare_shadow_stage()`
# @used-by :mod:`agent_tools.shadow_replay_command`
def stage_command_shadow_copies(src_project: Path, src_launcher: Path | None, shadow_root: Path) -> tuple[Path, Path | None, dict[Path, Path], dict[str, Path], Path | None]:
	daily = _infer_daily_root(src_project, None)
	shadow_daily = shadow_root / 'proposals/daily' if None is not daily else None
	shadow_project = shadow_daily / src_project.relative_to(daily) if None is not shadow_daily and None is not daily else shadow_root / 'projects' / src_project.name
	clone_project_tree(src_project, shadow_project, hardlink_evidence=True)
	if None is not daily and None is not shadow_daily and (daily / '\ua616/data/projects.json').is_file():
		(shadow_daily / '\ua616/data').mkdir(parents=True, exist_ok=True)
		shutil.copy2(daily / '\ua616/data/projects.json', shadow_daily / '\ua616/data/projects.json')
	old_states = {'project': state_dir(resolve_journal_dir(src_project))}
	relocations = {src_project: shadow_project}
	shadow_launcher, l_relocs, l_states = _stage_shadow_launcher(src_launcher, shadow_root, None is not shadow_daily)
	relocations.update(l_relocs)
	old_states.update(l_states)
	return (shadow_project, shadow_launcher, relocations, old_states, shadow_daily)
__all__ = ['execute_shadow_command', 'persist_shadow_replay_receipt', 'resolve_shadow_launcher', 'stage_command_shadow_copies']