# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.CanaryProbe import CanaryProbe
from Df.Harness.Runtime.LauncherRenderer import LauncherRenderer
from Df.Harness.lib.path_resolve import dfh_tool_path, dfh_var_value
from Df.Harness.lib.runtime_launcher_templates import dfh_git_hook_shell_wrapper
from Df.Harness.lib.storage import dfh_data_dir_for, dfh_replace_bytes
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
ARCHIVE_TARGETS = ('scripts', 'paths.json', 'runtime.json')
DEFAULT_KEEP_RELEASES = 5
GIT_HOOK_NAMES = ('pre-commit', 'commit-msg', 'pre-push')
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
REQUIRED_ENTRYPOINTS = ('check_markdown_slop.py', 'check_rules_and_server_gate.py', 'check_pre_invocation.py', 'check_stop_gate.py', 'git_shim.py')
VALIDATION_PROBE = (
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
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_runtime_status()`
# @used-by :func:`dfh_finalize_native_install()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def dfh_check_runtime_snapshot(primary: str | Path, *, store_dir: str | Path | None=None) -> dict:
	prim_p = Path(primary).resolve()
	store = dfh_runtime_store_dir(prim_p, store_dir=store_dir)
	ptr = dfh_read_pointer(store)
	cur, prev = (ptr.get('current'), ptr.get('previous'))
	cur_ok = bool(cur and (store / 'releases' / str(cur) / 'scripts').is_dir())
	head = dfh_git_read(prim_p, 'rev-parse', 'HEAD').stdout.decode('utf-8', errors='replace').strip() if dfh_has_git_head(prim_p) else None
	return {'active': cur_ok, 'current': cur, 'head': head, 'previous': prev, 'stale': bool(cur and head and cur != head), 'store_dir': store.as_posix(), 'valid': (not ptr) or cur_ok}
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__activate_release()`
def dfh_deploy_git_hooks(store: Path, primary: Path) -> Path:
	gh_dir = store / 'git_hooks'
	gh_dir.mkdir(parents=True, exist_ok=True)
	dfh_replace_bytes(gh_dir / 'harness_git_hook_launcher.py', LauncherRenderer(primary, store_dir=store, kind='git_hook').run().encode('utf-8'))
	for hname in GIT_HOOK_NAMES:
		hp = gh_dir / hname
		dfh_replace_bytes(hp, dfh_git_hook_shell_wrapper(hname).encode('utf-8'))
		try:
			hp.chmod(hp.stat().st_mode | 0o755)
		except OSError:
			pass
	return gh_dir
# @used-by :func:`dfh_ensure_repo_git_hooks()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def dfh_effective_git_hooks_dir(fallback_dir: str | Path | None=None, *, store_dir: str | Path | None=None, primary: str | Path | None=None) -> Path:
	env_store = os.environ.get('HARNESS_RUNTIME_STORE')
	if None is not store_dir:
		store = Path(store_dir).resolve()
	elif env_store and env_store.strip():
		store = Path(env_store.strip()).resolve()
	else:
		store = dfh_runtime_store_dir(primary)
	cand = store / 'git_hooks'
	if (cand / 'harness_git_hook_launcher.py').is_file() and (cand / 'pre-commit').is_file():
		r = cand.resolve()
	elif None is not fallback_dir:
		r = Path(fallback_dir).resolve()
	else:
		r = dfh_tool_path('git_hooks_dir').resolve()
	return r
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.ensure_hooks()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def dfh_ensure_repo_git_hooks(repo_root: Path, main_repo: Path, fallback_dir: Path) -> Path | None:
	r: Path | None = None
	hooks_dir = dfh_effective_git_hooks_dir(fallback_dir)
	if (repo_root / '.git').exists() and hooks_dir.is_dir():
		try:
			for hname in GIT_HOOK_NAMES:
				hp = hooks_dir / hname
				if hp.is_file():
					hp.chmod(hp.stat().st_mode | 0o755)
			dfh_set_local_hooks_path(main_repo, hooks_dir)
			r = hooks_dir
		except OSError:
			r = None
	return r
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__promote_locked()`
def dfh_export_git_archive(repo: Path, staging: Path) -> str:
	sha = dfh_git_read(repo, 'rev-parse', '--verify', 'HEAD').stdout.decode('utf-8', errors='replace').strip()
	present = [t for t in ARCHIVE_TARGETS if t in set(dfh_git_read(repo, 'ls-tree', '--name-only', 'HEAD').stdout.decode('utf-8', errors='replace').splitlines())]
	if 'scripts' not in present:
		raise ValueError(f'HEAD in {repo} has no tracked scripts/ directory')
	arc_proc = dfh_git_read(repo, 'archive', '--format=tar', 'HEAD', '--', *present)
	staging.mkdir(parents=True, exist_ok=True)
	with tarfile.open(fileobj=io.BytesIO(arc_proc.stdout), mode='r:') as tf:
		dfh_safe_extract_tar(tf, staging)
	return sha
# @used-by :func:`agent_tools.runtime_snapshot.finalize_native_install()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_finalize_native_install(result: dict, primary: Path, *, check: bool, promote_fn: Any=None) -> dict:
	if check:
		snap = dfh_check_runtime_snapshot(primary)
		result['runtime_snapshot'] = snap
		if not snap['valid']:
			result['valid'] = False
			result['issues'].append({'file': str(Path(snap['store_dir']) / 'current.json'), 'message': 'Active runtime snapshot pointer references a missing release directory'})
	elif result.get('valid'):
		from Df.Harness.Runtime.SnapshotPromoter import SnapshotPromoter
		snap = promote_fn(primary) if None is not promote_fn else SnapshotPromoter(primary).run()
		result['runtime_snapshot'] = snap
		if not snap.get('valid'):
			result['valid'] = False
			result['issues'].append({'file': str(primary), 'message': f"Runtime snapshot promotion failed: {snap.get('error', 'unknown error')}"})
	return result
# @used-by :func:`dfh_check_runtime_snapshot()`
# @used-by :func:`dfh_export_git_archive()`
# @used-by :func:`dfh_has_git_head()`
def dfh_git_read(repo: Path, *args: str) -> subprocess.CompletedProcess:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, env=env, timeout=30, check=False, creationflags=NO_WINDOW)
	if 0 != proc.returncode:
		joined = ' '.join(args)
		raise RuntimeError(proc.stderr.decode('utf-8', errors='replace').strip() or f'git {joined} failed')
	return proc
# @used-by :func:`dfh_check_runtime_snapshot()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.run()`
def dfh_has_git_head(repo: Path) -> bool:
	r = False
	if (repo / '.git').exists():
		try:
			dfh_git_read(repo, 'rev-parse', '--verify', 'HEAD')
			r = True
		except (OSError, RuntimeError, subprocess.SubprocessError):
			r = False
	return r
# @used-by :func:`agent_tools.worktree_flow._maybe_promote_snapshot()`
# @used-by :meth:`Df.Harness.Gate.WorktreeIsolationGate.WorktreeIsolationGate.__evaluate_main_checkout()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def dfh_is_harness_code_repo(repo: str | Path) -> bool:
	p = Path(repo).resolve()
	return (p / 'paths.json').is_file() and (p / 'runtime.json').is_file() and (p / 'scripts/check_rules_and_server_gate.py').is_file()
# @used-by :func:`dfh_check_runtime_snapshot()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__activate_release()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__promote_locked()`
def dfh_read_pointer(store: Path) -> dict:
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
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__activate_release()`
def dfh_rotate_releases(releases_dir: Path, keep: int, protected: set[str]) -> list[str]:
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
# @used-by :func:`dfh_check_runtime_snapshot()`
# @used-by :func:`dfh_effective_git_hooks_dir()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.run()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def dfh_runtime_store_dir(primary: str | Path | None=None, *, store_dir: str | Path | None=None) -> Path:
	if None is not store_dir:
		r = Path(store_dir).resolve()
	else:
		prim_p = Path(primary).resolve() if None is not primary else Path(dfh_var_value('HARNESS_CODE')).resolve()
		r = (dfh_data_dir_for(prim_p) / 'runtime-snapshots').resolve()
	return r
# @used-by :func:`dfh_export_git_archive()`
def dfh_safe_extract_tar(tf: tarfile.TarFile, dest: Path) -> None:
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
# @used-by :func:`dfh_ensure_repo_git_hooks()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__activate_release()`
def dfh_set_local_hooks_path(main_repo: Path, hooks_dir: Path) -> None:
	from agent_tools.shell_audit import normalize_host_path
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(main_repo), 'config', '--local', '--get', 'core.hooksPath'], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False, creationflags=NO_WINDOW)
	current = (proc.stdout or '').strip()
	if (not current) or normalize_host_path(current).resolve() != hooks_dir.resolve():
		subprocess.run(['git', '-C', str(main_repo), 'config', '--local', 'core.hooksPath', str(hooks_dir)], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=False, creationflags=NO_WINDOW)
# @used-by :func:`agent_tools.runtime_snapshot._validate_staged_release()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__promote_locked()`
def dfh_validate_staged_release(staging: Path, canonical_primary: Path, entrypoints: tuple[str, ...], *, run_canary: bool=True, canary_fn: Any=None) -> tuple[bool, str]:
	proc = subprocess.run([sys.executable, '-I', '-c', VALIDATION_PROBE, str(staging), canonical_primary.as_posix(), json.dumps(list(entrypoints))], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60, check=False, creationflags=NO_WINDOW)
	detail = (proc.stderr or proc.stdout or '').strip()
	if 0 != proc.returncode:
		r = (False, detail)
	elif not run_canary:
		r = (True, '')
	else:
		r = canary_fn(staging) if None is not canary_fn else CanaryProbe(staging).run()
	return r
