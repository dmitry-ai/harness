# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
# https://github.com/dmitry-ai/harness/issues/186
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
from __future__ import annotations
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid
from .runtime_launchers import GIT_HOOK_LAUNCHER_HEADER, HOOK_RUNNER_HEADER, git_hook_launcher_source, git_hook_shell_wrapper, harness_hook_runner_source
from .storage import data_dir_for, locked, replace_bytes
DEFAULT_KEEP_RELEASES = 5
GIT_HOOK_NAMES = ('pre-commit', 'commit-msg', 'pre-push')
REQUIRED_ENTRYPOINTS = ('check_markdown_slop.py', 'check_rules_and_server_gate.py', 'check_pre_invocation.py', 'check_stop_gate.py', 'git_shim.py')
_ARCHIVE_TARGETS = ('scripts', 'paths.json', 'runtime.json')
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_VALIDATION_PROBE = (
	'import compileall, importlib, importlib.util, json, pathlib, sys\n'
	'staging = pathlib.Path(sys.argv[1]).resolve()\n'
	'canon = pathlib.Path(sys.argv[2]).resolve()\n'
	'eps = json.loads(sys.argv[3])\n'
	"sdir = staging / 'scripts'\n"
	'if not compileall.compile_dir(str(sdir), quiet=1, force=True):\n'
	"\traise SystemExit('compileall failed')\n"
	'sys.path.insert(0, str(sdir))\n'
	'for idx, name in enumerate(eps):\n'
	'\tep = sdir / name\n'
	'\tif not ep.is_file():\n'
	"\t\traise SystemExit(f'missing entrypoint: {name}')\n"
	"\tspec = importlib.util.spec_from_file_location(f'_snap_probe_{idx}_{ep.stem}', ep)\n"
	'\tif None is spec or None is spec.loader:\n'
	"\t\traise SystemExit(f'unresolvable entrypoint: {name}')\n"
	'\tmod = importlib.util.module_from_spec(spec)\n'
	'\tspec.loader.exec_module(mod)\n'
	"if (sdir / 'agent_tools/gates/__init__.py').is_file():\n"
	"\tgates_mod = importlib.import_module('agent_tools.gates')\n"
	"\tif hasattr(gates_mod, 'discover_pre_tool_gates'):\n"
	'\t\tgates_mod.discover_pre_tool_gates()\n'
	"if (sdir / 'agent_tools/path_registry.py').is_file():\n"
	"\tpr = importlib.import_module('agent_tools.path_registry')\n"
	'\tif pr._CODE_ANCHOR.resolve() != canon:\n'
	"\t\traise SystemExit(f'anchor mismatch: {pr._CODE_ANCHOR} != {canon}')\n"
	"if (sdir / 'agent_tools/python_integrity.py').is_file():\n"
	"\tpi = importlib.import_module('agent_tools.python_integrity')\n"
	'\tpi_errs = pi.verify_directory_python_integrity(sdir)\n'
	'\tif pi_errs:\n'
	"\t\traise SystemExit('; '.join(pi_errs[:5]))\n"
)
def _activate_release(prim_p: Path, store: Path, staging: Path, sha: str, *, keep: int, configure_repo_hooks: bool) -> dict:
	releases_dir = store / 'releases'
	releases_dir.mkdir(parents=True, exist_ok=True)
	release_dir = releases_dir / sha
	if not release_dir.exists():
		os.replace(staging, release_dir)
	prior = _read_pointer(store)
	old_cur = str(prior.get('current') or '').strip() or None
	old_prev = str(prior.get('previous') or '').strip() or None
	new_prev = old_cur if (old_cur and old_cur != sha) else old_prev
	ptr_payload = {'canonical_primary': prim_p.as_posix(), 'current': sha, 'previous': new_prev, 'updated_at': datetime.now(timezone.utc).isoformat(), 'version': 1}
	replace_bytes(store / 'current.json', (json.dumps(ptr_payload, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
	gh_dir = _deploy_git_hooks(store, prim_p)
	if configure_repo_hooks:
		_set_local_hooks_path(prim_p, gh_dir)
	protected = {s for s in (sha, new_prev) if s}
	pruned = _rotate_releases(releases_dir, keep, protected)
	return {'valid': True, 'promoted': True, 'commit_sha': sha, 'previous': new_prev, 'release_dir': release_dir.as_posix(), 'store_dir': store.as_posix(), 'git_hooks_dir': gh_dir.as_posix(), 'pruned': pruned}
def _deploy_git_hooks(store: Path, primary: Path) -> Path:
	gh_dir = store / 'git_hooks'
	gh_dir.mkdir(parents=True, exist_ok=True)
	launcher = gh_dir / 'harness_git_hook_launcher.py'
	replace_bytes(launcher, git_hook_launcher_source(primary, store_dir=store).encode('utf-8'))
	for hname in GIT_HOOK_NAMES:
		hp = gh_dir / hname
		replace_bytes(hp, git_hook_shell_wrapper(hname).encode('utf-8'))
		try:
			hp.chmod(hp.stat().st_mode | 0o755)
		except OSError:
			pass
	return gh_dir
def _export_git_archive(repo: Path, staging: Path) -> str:
	head_proc = _git_read(repo, 'rev-parse', '--verify', 'HEAD')
	sha = head_proc.stdout.decode('utf-8', errors='replace').strip()
	tree_proc = _git_read(repo, 'ls-tree', '--name-only', 'HEAD')
	present = [t for t in _ARCHIVE_TARGETS if t in set(tree_proc.stdout.decode('utf-8', errors='replace').splitlines())]
	if 'scripts' not in present:
		raise ValueError(f'HEAD in {repo} has no tracked scripts/ directory')
	arc_proc = _git_read(repo, 'archive', '--format=tar', 'HEAD', '--', *present)
	staging.mkdir(parents=True, exist_ok=True)
	with tarfile.open(fileobj=io.BytesIO(arc_proc.stdout), mode='r:') as tf:
		_safe_extract_tar(tf, staging)
	return sha
def _git_read(repo: Path, *args: str) -> subprocess.CompletedProcess:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, env=env, timeout=30, check=False, creationflags=_NO_WINDOW)
	if 0 != proc.returncode:
		raise RuntimeError(proc.stderr.decode('utf-8', errors='replace').strip() or f'git {" ".join(args)} failed')
	return proc
def _has_git_head(repo: Path) -> bool:
	r = False
	if (repo / '.git').exists():
		try:
			_git_read(repo, 'rev-parse', '--verify', 'HEAD')
			r = True
		except (OSError, RuntimeError, subprocess.SubprocessError):
			r = False
	return r
def _promote_locked(prim_p: Path, store: Path, *, keep: int, entrypoints: tuple[str, ...], configure_repo_hooks: bool) -> dict:
	staging = store / f'.staging-{uuid.uuid4().hex[:10]}'
	try:
		sha = _export_git_archive(prim_p, staging)
		meta = {'canonical_primary': prim_p.as_posix(), 'commit_sha': sha, 'created_at': datetime.now(timezone.utc).isoformat(), 'schema_version': 1}
		replace_bytes(staging / 'snapshot.json', (json.dumps(meta, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
		ok, detail = _validate_staged_release(staging, prim_p, entrypoints)
		if not ok:
			r = {'valid': False, 'promoted': False, 'commit_sha': sha, 'error': detail or 'Snapshot validation failed'}
		else:
			r = _activate_release(prim_p, store, staging, sha, keep=keep, configure_repo_hooks=configure_repo_hooks)
	finally:
		shutil.rmtree(staging, ignore_errors=True)
	return r
def _read_pointer(store: Path) -> dict:
	ptr_file = store / 'current.json'
	r: dict = {}
	if ptr_file.is_file():
		try:
			parsed = json.loads(ptr_file.read_text(encoding='utf-8-sig'))
			if isinstance(parsed, dict):
				r = parsed
		except (OSError, ValueError):
			r = {}
	return r
def _rotate_releases(releases_dir: Path, keep: int, protected: set[str]) -> list[str]:
	pruned: list[str] = []
	if releases_dir.is_dir():
		dirs = sorted((p for p in releases_dir.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime_ns, reverse=True)
		kept = set(protected)
		for cand in dirs:
			if len(kept) < max(1, int(keep)):
				kept.add(cand.name)
		for cand in dirs:
			if cand.name not in kept:
				shutil.rmtree(cand, ignore_errors=True)
				pruned.append(cand.name)
	return pruned
def _safe_extract_tar(tf: tarfile.TarFile, dest: Path) -> None:
	base = dest.resolve()
	for member in tf.getmembers():
		target = (base / member.name).resolve()
		if not target.is_relative_to(base):
			raise ValueError(f'Unsafe archive member path: {member.name}')
		if member.isdir():
			target.mkdir(parents=True, exist_ok=True)
		elif member.isfile():
			target.parent.mkdir(parents=True, exist_ok=True)
			src = tf.extractfile(member)
			if None is not src:
				target.write_bytes(src.read())
def _set_local_hooks_path(main_repo: Path, hooks_dir: Path) -> None:
	from .shell_audit import normalize_host_path
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(main_repo), 'config', '--local', '--get', 'core.hooksPath'], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False, creationflags=_NO_WINDOW)
	current = (proc.stdout or '').strip()
	if (not current) or normalize_host_path(current).resolve() != hooks_dir.resolve():
		subprocess.run(['git', '-C', str(main_repo), 'config', '--local', 'core.hooksPath', str(hooks_dir)], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=False, creationflags=_NO_WINDOW)
def _validate_staged_release(staging: Path, canonical_primary: Path, entrypoints: tuple[str, ...]) -> tuple[bool, str]:
	proc = subprocess.run([sys.executable, '-I', '-c', _VALIDATION_PROBE, str(staging), canonical_primary.as_posix(), json.dumps(list(entrypoints))], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60, check=False, creationflags=_NO_WINDOW)
	detail = (proc.stderr or proc.stdout or '').strip()
	return (0 == proc.returncode, detail)
def check_runtime_snapshot(primary: str | Path, *, store_dir: str | Path | None=None) -> dict:
	prim_p = Path(primary).resolve()
	store = runtime_store_dir(prim_p, store_dir=store_dir)
	ptr = _read_pointer(store)
	cur = ptr.get('current')
	prev = ptr.get('previous')
	cur_ok = bool(cur and (store / 'releases' / str(cur) / 'scripts').is_dir())
	head = _git_read(prim_p, 'rev-parse', 'HEAD').stdout.decode('utf-8', errors='replace').strip() if _has_git_head(prim_p) else None
	return {'valid': (not ptr) or cur_ok, 'active': cur_ok, 'current': cur, 'previous': prev, 'head': head, 'stale': bool(cur and head and cur != head), 'store_dir': store.as_posix()}
def effective_git_hooks_dir(fallback_dir: str | Path | None=None, *, store_dir: str | Path | None=None, primary: str | Path | None=None) -> Path:
	env_store = os.environ.get('HARNESS_RUNTIME_STORE')
	if None is not store_dir:
		store = Path(store_dir).resolve()
	elif env_store and env_store.strip():
		store = Path(env_store.strip()).resolve()
	else:
		store = runtime_store_dir(primary)
	cand = store / 'git_hooks'
	if (cand / 'harness_git_hook_launcher.py').is_file() and (cand / 'pre-commit').is_file():
		r = cand.resolve()
	elif None is not fallback_dir:
		r = Path(fallback_dir).resolve()
	else:
		from .path_registry import tool_path
		r = tool_path('git_hooks_dir').resolve()
	return r
def ensure_repo_git_hooks(repo_root: Path, main_repo: Path, fallback_dir: Path) -> Path | None:
	r = None
	hooks_dir = effective_git_hooks_dir(fallback_dir)
	if (repo_root / '.git').exists() and hooks_dir.is_dir():
		try:
			for hname in GIT_HOOK_NAMES:
				hp = hooks_dir / hname
				if hp.is_file():
					hp.chmod(hp.stat().st_mode | 0o755)
			_set_local_hooks_path(main_repo, hooks_dir)
			r = hooks_dir
		except OSError:
			r = None
	return r
def finalize_native_install(result: dict, primary: Path, *, check: bool) -> dict:
	if check:
		snap = check_runtime_snapshot(primary)
		result['runtime_snapshot'] = snap
		if not snap['valid']:
			result['valid'] = False
			result['issues'].append({'file': str(Path(snap['store_dir']) / 'current.json'), 'message': 'Active runtime snapshot pointer references a missing release directory'})
	elif result.get('valid'):
		snap = promote_runtime_snapshot(primary)
		result['runtime_snapshot'] = snap
		if not snap.get('valid'):
			result['valid'] = False
			result['issues'].append({'file': str(primary), 'message': f"Runtime snapshot promotion failed: {snap.get('error', 'unknown error')}"})
	return result
def is_harness_code_repo(repo: str | Path) -> bool:
	p = Path(repo).resolve()
	return (p / 'paths.json').is_file() and (p / 'runtime.json').is_file() and (p / 'scripts/check_rules_and_server_gate.py').is_file()
def promote_runtime_snapshot(primary: str | Path, *, store_dir: str | Path | None=None, keep: int=DEFAULT_KEEP_RELEASES, entrypoints: tuple[str, ...]=REQUIRED_ENTRYPOINTS, configure_repo_hooks: bool=True) -> dict:
	prim_p = Path(primary).resolve()
	if not _has_git_head(prim_p):
		r = {'valid': True, 'promoted': False, 'skipped': True, 'reason': 'not_a_git_repo'}
	else:
		store = runtime_store_dir(prim_p, store_dir=store_dir)
		store.mkdir(parents=True, exist_ok=True)
		with locked(store / 'promote.lock'):
			r = _promote_locked(prim_p, store, keep=keep, entrypoints=entrypoints, configure_repo_hooks=configure_repo_hooks)
	return r
def runtime_store_dir(primary: str | Path | None=None, *, store_dir: str | Path | None=None) -> Path:
	if None is not store_dir:
		r = Path(store_dir).resolve()
	else:
		if None is not primary:
			prim_p = Path(primary).resolve()
		else:
			from .runtime import PRIMARY
			prim_p = PRIMARY.resolve()
		r = (data_dir_for(prim_p) / 'runtime-snapshots').resolve()
	return r
__all__ = ['DEFAULT_KEEP_RELEASES', 'GIT_HOOK_LAUNCHER_HEADER', 'GIT_HOOK_NAMES', 'HOOK_RUNNER_HEADER', 'REQUIRED_ENTRYPOINTS', 'check_runtime_snapshot', 'effective_git_hooks_dir', 'ensure_repo_git_hooks', 'finalize_native_install', 'git_hook_launcher_source', 'git_hook_shell_wrapper', 'harness_hook_runner_source', 'is_harness_code_repo', 'promote_runtime_snapshot', 'runtime_store_dir']
