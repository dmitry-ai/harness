# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
import shutil
import subprocess
from .git_gate import GitRepoGate, _NO_WINDOW
from .git_ignore import ensure_worktree_dir_ignored, prepare_worktrees_base_dir
from .landing_lease import acquire_lease, release_lease
from .path_registry import project_paths
# 2026-11-23
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
_SAFE_TASK_RE = re.compile(r'[^A-Za-z0-9_.-]+')
def _apply_porcelain_line(cur: dict, line: str) -> None:
	if line.startswith('worktree '):
		cur['path'] = Path(line[9:].strip()).resolve().as_posix()
	elif line.startswith('HEAD '):
		cur['head'] = line[5:].strip()
	elif line.startswith('branch '):
		cur['branch'] = line[7:].strip().removeprefix('refs/heads/')
	elif 'detached' == line:
		cur['detached'] = True
def _current_branch(repo: Path) -> str:
	proc = GitRepoGate(repo).run_read(['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
	return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
# 2026-11-24
# "Remove landed worktrees by default and flag stale worktrees in worktree-status":
# https://github.com/dmitry-ai/harness/issues/203
def _enrich_worktree_entry(main_repo: Path, main_posix: str, base_ref: str, entry: dict) -> None:
	wp = Path(entry['path'])
	is_main = wp.resolve().as_posix() == main_posix
	entry['is_main'] = is_main
	if not wp.is_dir():
		entry.update(missing=True, dirty=False, ahead=0, behind=0, stale=not is_main)
	else:
		entry['dirty'] = bool(GitRepoGate(wp).run_read(['status', '--porcelain'], check=False).stdout.strip())
		if is_main:
			entry.update(ahead=0, behind=0, stale=False)
		else:
			ahead, behind = _rev_distance(main_repo, base_ref, str(entry.get('head') or ''))
			entry.update(ahead=ahead, behind=behind, stale=(not entry['dirty']) and 0 == ahead and 0 < behind)
def _fail_land(main_repo: Path, wt_path: Path, branch: str, stage: str, error: str, *, test_runs: int=0, test_result: dict | None=None) -> dict:
	return {'valid': False, 'landed': False, 'stage': stage, 'error': error, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': branch, 'test_runs': test_runs, 'test_result': test_result}
def _git_exec(repo: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '-C', str(Path(repo).resolve()), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, creationflags=_NO_WINDOW)
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
def _maybe_promote_snapshot(main_repo: Path, *, promote_snapshot: bool | None, snapshot_store: Path | None) -> dict | None:
	from .runtime_snapshot import is_harness_code_repo, promote_runtime_snapshot
	should = promote_snapshot if None is not promote_snapshot else is_harness_code_repo(main_repo)
	return promote_runtime_snapshot(main_repo, store_dir=snapshot_store) if should else None
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
# 2026-11-26 "Add sandboxed polyglot land tests and post-land health checks": https://github.com/dmitry-ai/harness/issues/304
def _merge_and_finalize(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, run_tests: bool=True, push: bool, remove: bool, test_runs: int, test_res: dict | None, post_merge_fn, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False) -> dict:
	ff = _git_exec(main_repo, 'merge', '--ff-only', branch)
	if 0 != ff.returncode:
		r = _fail_land(main_repo, wt_path, branch, 'ff_merge', ff.stderr.strip() or ff.stdout.strip(), test_runs=test_runs, test_result=test_res)
	else:
		if post_merge_fn:
			post_merge_fn(main_repo)
		snap, err_stage, err_msg = _post_merge_checks(main_repo, run_tests=run_tests, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store)
		if None is not err_stage:
			r = _fail_land(main_repo, wt_path, branch, err_stage, err_msg or 'Post-merge verification failed', test_runs=test_runs, test_result=test_res)
		else:
			r = _push_and_finish_land(main_repo, wt_path, branch, target_branch, push=push, remove=remove, test_runs=test_runs, test_res=test_res, snap=snap, tag=tag)
	return r
# 2026-11-26 "Add sandboxed polyglot land tests and post-land health checks": https://github.com/dmitry-ai/harness/issues/304
# @used-by :func:`_merge_and_finalize()`
def _post_merge_checks(main_repo: Path, *, run_tests: bool, promote_snapshot: bool | None, snapshot_store: Path | None) -> tuple[dict | None, str | None, str | None]:
	snap = _maybe_promote_snapshot(main_repo, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store)
	if None is not snap and (not snap.get('valid')):
		r = (snap, 'snapshot_promote', str(snap.get('error') or 'Runtime snapshot promotion failed'))
	elif run_tests:
		from .polyglot_land import run_repo_health_check
		health = run_repo_health_check(main_repo)
		r = (snap, None, None) if health.get('ok') else (snap, 'post_land_health', str(health.get('error') or 'Post-land repository health check failed'))
	else:
		r = (snap, None, None)
	return r
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
def _push_and_finish_land(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, push: bool, remove: bool, test_runs: int, test_res: dict | None, snap: dict | None, tag: bool=False) -> dict:
	p_err = ''
	if push:
		p_proc = _git_exec(main_repo, 'push')
		p_err = '' if 0 == p_proc.returncode else (p_proc.stderr.strip() or p_proc.stdout.strip())
	if p_err:
		r = _fail_land(main_repo, wt_path, branch, 'push', p_err, test_runs=test_runs, test_result=test_res)
	else:
		head = GitRepoGate(main_repo).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
		tag_name = _apply_land_tag(main_repo, head, push=push) if tag else None
		# 2026-11-26 "Block raw worktree removal and fail closed on locked cleanup": https://github.com/dmitry-ai/harness/issues/303
		cleanup = worktree_cleanup(main_repo, wt_path, force=True) if remove else None
		removed = bool(cleanup['valid']) if None is not cleanup else False
		ok_land = (None is cleanup) or removed
		r = {'valid': ok_land, 'landed': True, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': branch, 'target_branch': target_branch, 'head': head, 'tag': tag_name, 'test_runs': test_runs, 'test_result': test_res, 'pushed': push, 'removed': removed, 'runtime_snapshot': snap}
		if not ok_land and None is not cleanup:
			r.update(stage='worktree_cleanup', error=str(cleanup.get('error') or 'Worktree cleanup failed'), cleanup=cleanup)
	return r
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
def _apply_land_tag(main_repo: Path, head: str, *, push: bool) -> str:
	from .repo_tags import ensure_commit_tag
	return ensure_commit_tag(main_repo, commit=head, push=push)['tag']
def _parse_worktree_porcelain(text: str) -> list[dict]:
	entries: list[dict] = []
	cur: dict = {}
	for raw in (text or '').splitlines():
		line = raw.strip()
		if line:
			_apply_porcelain_line(cur, line)
		elif cur:
			entries.append(cur)
			cur = {}
	if cur:
		entries.append(cur)
	return entries
def _rebase_and_test(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, run_tests: bool, workers: int | None) -> tuple[dict | None, int, dict | None]:
	from .python_integrity import verify_worktree_python_changes
	reb = _git_exec(wt_path, 'rebase', target_branch)
	if 0 != reb.returncode:
		_git_exec(wt_path, 'rebase', '--abort')
		r = (_fail_land(main_repo, wt_path, branch, 'rebase', reb.stderr.strip() or reb.stdout.strip()), 0, None)
	else:
		# 2026-11-24
		# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
		# https://github.com/dmitry-ai/harness/issues/186
		py_errs = verify_worktree_python_changes(wt_path, target_branch)
		if py_errs:
			r = (_fail_land(main_repo, wt_path, branch, 'python_integrity', '; '.join(py_errs[:5])), 0, None)
		else:
			# 2026-11-26 "Add sandboxed polyglot land tests and post-land health checks": https://github.com/dmitry-ai/harness/issues/304
			ok_tests, test_runs, test_res = _run_land_tests(main_repo, wt_path, run_tests=run_tests, workers=workers)
			stage = str((test_res or {}).get('failure_stage') or 'tests')
			msg = 'Host state mutated during sandboxed tests' if 'host_mutation' == stage else 'Full test suite failed on rebased worktree'
			err = None if ok_tests else _fail_land(main_repo, wt_path, branch, stage, msg, test_runs=test_runs, test_result=test_res)
			r = (err, test_runs, test_res)
	return r
def _resolve_deleted_worktree_file(path: Path, is_tracked_fn) -> tuple[Path, str] | None:
	r = None
	parts = path.parts
	for idx in range(len(parts) - 3):
		if ('\ua616', 'data', 'worktrees') == parts[idx:idx + 3] and idx + 4 < len(parts):
			proj_root = Path(*parts[:idx]).resolve()
			rel = Path(*parts[idx + 4:]).as_posix()
			for cr in project_paths(proj_root).code_repos:
				if is_tracked_fn(cr) and (cr / rel).exists():
					r = (cr.resolve(), rel)
					break
			break
	return r
def _rev_distance(main_repo: Path, base_ref: str, head_sha: str) -> tuple[int, int]:
	r = (0, 0)
	if head_sha:
		proc = GitRepoGate(main_repo).run_read(['rev-list', '--left-right', '--count', f'{base_ref}...{head_sha}'], check=False)
		parts = proc.stdout.decode('utf-8', errors='replace').strip().split() if 0 == proc.returncode else []
		if 2 == len(parts) and parts[0].isdigit() and parts[1].isdigit():
			r = (int(parts[1]), int(parts[0]))
	return r
# 2026-11-26 "Add sandboxed polyglot land tests and post-land health checks": https://github.com/dmitry-ai/harness/issues/304
def _run_land_tests(main_repo: Path, wt_path: Path, *, run_tests: bool, workers: int | None) -> tuple[bool, int, dict | None]:
	tests_dir = wt_path / 'tests'
	if not run_tests:
		r = (True, 0, None)
	elif tests_dir.is_dir():
		from .parallel_runner import run_parallel_tests
		res = run_parallel_tests(tests_dir, workers=workers, failfast=True)
		r = (bool(res.get('ok')), 1, res)
	else:
		from .polyglot_land import run_polyglot_land_tests
		ok, res = run_polyglot_land_tests(main_repo, wt_path)
		r = (ok, 1 if None is not res else 0, res)
	return r
def _safe_task_id(task_id: str) -> str:
	clean = _SAFE_TASK_RE.sub('-', str(task_id or '').strip()).strip('-.')
	if not clean:
		raise ValueError('A non-empty task identifier is required')
	return clean[:48]
def git_config_file(code_repo: Path) -> Path:
	resolved = Path(code_repo).resolve()
	dot_git = resolved / '.git'
	return (GitRepoGate(resolved).main_repo() / '.git/config') if dot_git.is_file() else (dot_git / 'config')
def is_linked_worktree(path: Path | str) -> bool:
	return (Path(path).resolve() / '.git').is_file()
def prioritized_worktree_candidates(repo_root: str | Path | None=None, cwd: Path | None=None) -> list[Path]:
	cands: list[Path] = []
	if None is not repo_root and str(repo_root).strip():
		cands.append(Path(repo_root).resolve())
	eff_cwd = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	for anc in (eff_cwd, *eff_cwd.parents):
		if is_linked_worktree(anc):
			cands.append(anc)
			break
	return cands
def resolve_touched_repo_file(path: Path, is_tracked_fn) -> tuple[Path, str] | None:
	r = None
	for anc in (path, *path.parents):
		if is_tracked_fn(anc):
			try:
				rel = path.relative_to(anc).as_posix()
			except ValueError:
				break
			if rel and '.' != rel and (not rel.startswith(('.git/', '\ua616/', '\ua66e/', '_/', '\U0001f56e/', '\u2c0f/\u227a/', 'Artifacts/\u227a/'))):
				r = (anc, rel)
			break
	return r if None is not r else _resolve_deleted_worktree_file(path, is_tracked_fn)
def worktree_begin(repo: Path | str, task_id: str, *, base_ref: str='main', worktrees_dir: Path | str | None=None) -> dict:
	main_repo = GitRepoGate(Path(repo).resolve()).main_repo()
	safe_id = _safe_task_id(task_id)
	branch = f'task/{safe_id}'
	# 2026-11-24
	# "Auto-exclude worktrees_dir in enclosing repo info/exclude on worktree creation":
	# https://github.com/dmitry-ai/harness/issues/201
	base_dir, ignore_info = prepare_worktrees_base_dir(main_repo, worktrees_dir=worktrees_dir)
	wt_path = (base_dir / safe_id).resolve()
	if not (wt_path / '.git').exists():
		proc = _git_exec(main_repo, 'worktree', 'add', '-b', branch, str(wt_path), base_ref)
		if 0 != proc.returncode:
			raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f'git worktree add failed for {wt_path}')
	head = GitRepoGate(wt_path).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
	return {'valid': True, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': _current_branch(wt_path) or branch, 'base_ref': base_ref, 'head': head, 'enclosing_ignore': ignore_info}
# 2026-11-26 "Block raw worktree removal and fail closed on locked cleanup": https://github.com/dmitry-ai/harness/issues/303
def worktree_cleanup(repo: Path | str, target: Path | str, *, force: bool=False) -> dict:
	from .worktree_guard import remove_worktree_fail_closed
	main_repo = GitRepoGate(Path(repo).resolve()).main_repo()
	wt_path = Path(target).resolve()
	branch = _current_branch(wt_path) if (wt_path / '.git').exists() else ''
	outcome = remove_worktree_fail_closed(main_repo, wt_path, force=force, git_exec_fn=_git_exec)
	_git_exec(main_repo, 'worktree', 'prune')
	branch_deleted = False
	if outcome['ok'] and branch and branch.startswith('task/'):
		branch_deleted = 0 == _git_exec(main_repo, 'branch', '-D' if force else '-d', branch).returncode
	return {'valid': outcome['ok'], 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': branch, 'branch_deleted': branch_deleted, 'error': outcome['error'], 'removal_errors': outcome['removal_errors'], 'locking_processes': outcome['locking_processes']}
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
# 2026-11-26 "Add sandboxed polyglot land tests and post-land health checks": https://github.com/dmitry-ai/harness/issues/304
def _land_under_lease(main_repo: Path, wt_path: Path, branch: str, *, target_branch: str, run_tests: bool, push: bool, remove: bool, workers: int | None, post_merge_fn, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False) -> dict:
	from .polyglot_land import dirty_blocking_main_files
	if GitRepoGate(wt_path).git('status', '--porcelain').strip():
		r = _fail_land(main_repo, wt_path, branch, 'dirty_worktree', 'Worktree has uncommitted changes')
	elif dirty_blocking_main_files(main_repo, branch):
		r = _fail_land(main_repo, wt_path, branch, 'dirty_main', 'Main checkout has uncommitted changes')
	else:
		err, test_runs, test_res = _rebase_and_test(main_repo, wt_path, branch, target_branch, run_tests=run_tests, workers=workers)
		r = err if None is not err else _merge_and_finalize(main_repo, wt_path, branch, target_branch, run_tests=run_tests, push=push, remove=remove, test_runs=test_runs, test_res=test_res, post_merge_fn=post_merge_fn, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store, tag=tag)
	return r
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
def worktree_land(worktree: Path | str, *, target_branch: str='main', run_tests: bool=True, push: bool=False, remove: bool=True, owner: str | None=None, wait_timeout: float=600.0, leases_dir: Path | None=None, workers: int | None=None, post_merge_fn=None, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False) -> dict:
	wt_path = Path(worktree).resolve()
	if not is_linked_worktree(wt_path):
		raise ValueError(f'Not a linked git worktree: {wt_path}')
	main_repo = GitRepoGate(wt_path).main_repo()
	branch = _current_branch(wt_path)
	if None is leases_dir:
		ensure_worktree_dir_ignored(project_paths(main_repo).data_dir / 'repo-leases')
	lease = acquire_lease(main_repo, owner=owner, wait=True, timeout=wait_timeout, leases_dir=leases_dir)
	if not lease['acquired']:
		r = _fail_land(main_repo, wt_path, branch, 'lease_timeout', 'Timed out waiting for FIFO landing lease')
	else:
		try:
			r = _land_under_lease(main_repo, wt_path, branch, target_branch=target_branch, run_tests=run_tests, push=push, remove=remove, workers=workers, post_merge_fn=post_merge_fn, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store, tag=tag)
		finally:
			release_lease(main_repo, owner=lease['owner'], leases_dir=leases_dir)
	return r
def worktree_status(repo: Path | str) -> dict:
	main_repo = GitRepoGate(Path(repo).resolve()).main_repo()
	base_ref = _current_branch(main_repo) or 'HEAD'
	raw = GitRepoGate(main_repo).run_read(['worktree', 'list', '--porcelain']).stdout.decode('utf-8', errors='replace')
	entries = _parse_worktree_porcelain(raw)
	main_posix = main_repo.resolve().as_posix()
	for entry in entries:
		_enrich_worktree_entry(main_repo, main_posix, base_ref, entry)
	stale = [e['path'] for e in entries if e.get('stale')]
	behind = [e['path'] for e in entries if 0 < int(e.get('behind') or 0)]
	return {'valid': True, 'main_repo': main_repo.as_posix(), 'base_ref': base_ref, 'worktrees': entries, 'stale_worktrees': stale, 'behind_worktrees': behind}
