# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove landed worktrees by default and flag stale worktrees in worktree-status":
# https://github.com/dmitry-ai/harness/issues/203
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Auto-exclude worktrees_dir in enclosing repo info/exclude on worktree creation":
# https://github.com/dmitry-ai/harness/issues/201
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
from __future__ import annotations
from pathlib import Path
import re
import shutil
import subprocess
from .git_gate import GitRepoGate, _NO_WINDOW
from .git_ignore import ensure_worktree_dir_ignored, prepare_worktrees_base_dir
from .landing_lease import acquire_lease, release_lease
from .path_registry import project_paths
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
def _maybe_promote_snapshot(main_repo: Path, *, promote_snapshot: bool | None, snapshot_store: Path | None) -> dict | None:
	from .runtime_snapshot import is_harness_code_repo, promote_runtime_snapshot
	should = promote_snapshot if None is not promote_snapshot else is_harness_code_repo(main_repo)
	return promote_runtime_snapshot(main_repo, store_dir=snapshot_store) if should else None
def _merge_and_finalize(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, push: bool, remove: bool, test_runs: int, test_res: dict | None, post_merge_fn, promote_snapshot: bool | None=None, snapshot_store: Path | None=None) -> dict:
	ff = _git_exec(main_repo, 'merge', '--ff-only', branch)
	if 0 != ff.returncode:
		r = _fail_land(main_repo, wt_path, branch, 'ff_merge', ff.stderr.strip() or ff.stdout.strip(), test_runs=test_runs, test_result=test_res)
	else:
		if post_merge_fn:
			post_merge_fn(main_repo)
		snap = _maybe_promote_snapshot(main_repo, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store)
		if None is not snap and (not snap.get('valid')):
			r = _fail_land(main_repo, wt_path, branch, 'snapshot_promote', str(snap.get('error') or 'Runtime snapshot promotion failed'), test_runs=test_runs, test_result=test_res)
		else:
			r = _push_and_finish_land(main_repo, wt_path, branch, target_branch, push=push, remove=remove, test_runs=test_runs, test_res=test_res, snap=snap)
	return r
def _push_and_finish_land(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, push: bool, remove: bool, test_runs: int, test_res: dict | None, snap: dict | None) -> dict:
	p_err = ''
	if push:
		p_proc = _git_exec(main_repo, 'push')
		p_err = '' if 0 == p_proc.returncode else (p_proc.stderr.strip() or p_proc.stdout.strip())
	if p_err:
		r = _fail_land(main_repo, wt_path, branch, 'push', p_err, test_runs=test_runs, test_result=test_res)
	else:
		removed = bool(worktree_cleanup(main_repo, wt_path, force=True)['valid']) if remove else False
		head = GitRepoGate(main_repo).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
		r = {'valid': True, 'landed': True, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': branch, 'target_branch': target_branch, 'head': head, 'test_runs': test_runs, 'test_result': test_res, 'pushed': push, 'removed': removed, 'runtime_snapshot': snap}
	return r
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
	reb = _git_exec(wt_path, 'rebase', target_branch)
	if 0 != reb.returncode:
		_git_exec(wt_path, 'rebase', '--abort')
		r = (_fail_land(main_repo, wt_path, branch, 'rebase', reb.stderr.strip() or reb.stdout.strip()), 0, None)
	else:
		ok_tests, test_runs, test_res = _run_land_tests(wt_path, run_tests=run_tests, workers=workers)
		err = None if ok_tests else _fail_land(main_repo, wt_path, branch, 'tests', 'Full test suite failed on rebased worktree', test_runs=test_runs, test_result=test_res)
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
def _run_land_tests(wt_path: Path, *, run_tests: bool, workers: int | None) -> tuple[bool, int, dict | None]:
	tests_dir = wt_path / 'tests'
	if not run_tests or (not tests_dir.is_dir()):
		r = (True, 0, None)
	else:
		from .parallel_runner import run_parallel_tests
		res = run_parallel_tests(tests_dir, workers=workers, failfast=True)
		r = (bool(res.get('ok')), 1, res)
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
	base_dir, ignore_info = prepare_worktrees_base_dir(main_repo, worktrees_dir=worktrees_dir)
	wt_path = (base_dir / safe_id).resolve()
	if not (wt_path / '.git').exists():
		proc = _git_exec(main_repo, 'worktree', 'add', '-b', branch, str(wt_path), base_ref)
		if 0 != proc.returncode:
			raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f'git worktree add failed for {wt_path}')
	head = GitRepoGate(wt_path).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
	return {'valid': True, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': _current_branch(wt_path) or branch, 'base_ref': base_ref, 'head': head, 'enclosing_ignore': ignore_info}
def worktree_cleanup(repo: Path | str, target: Path | str, *, force: bool=False) -> dict:
	main_repo = GitRepoGate(Path(repo).resolve()).main_repo()
	wt_path = Path(target).resolve()
	branch = _current_branch(wt_path) if (wt_path / '.git').exists() else ''
	proc = _git_exec(main_repo, 'worktree', 'remove', *(['--force'] if force else []), str(wt_path))
	if 0 != proc.returncode and force and wt_path.exists():
		shutil.rmtree(wt_path, ignore_errors=True)
	_git_exec(main_repo, 'worktree', 'prune')
	branch_deleted = False
	if branch and branch.startswith('task/'):
		branch_deleted = 0 == _git_exec(main_repo, 'branch', '-D' if force else '-d', branch).returncode
	return {'valid': not wt_path.exists(), 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': branch, 'branch_deleted': branch_deleted}
def _land_under_lease(main_repo: Path, wt_path: Path, branch: str, *, target_branch: str, run_tests: bool, push: bool, remove: bool, workers: int | None, post_merge_fn, promote_snapshot: bool | None=None, snapshot_store: Path | None=None) -> dict:
	if GitRepoGate(wt_path).git('status', '--porcelain').strip():
		r = _fail_land(main_repo, wt_path, branch, 'dirty_worktree', 'Worktree has uncommitted changes')
	elif GitRepoGate(main_repo).git('status', '--porcelain').strip():
		r = _fail_land(main_repo, wt_path, branch, 'dirty_main', 'Main checkout has uncommitted changes')
	else:
		err, test_runs, test_res = _rebase_and_test(main_repo, wt_path, branch, target_branch, run_tests=run_tests, workers=workers)
		r = err if None is not err else _merge_and_finalize(main_repo, wt_path, branch, target_branch, push=push, remove=remove, test_runs=test_runs, test_res=test_res, post_merge_fn=post_merge_fn, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store)
	return r
def worktree_land(worktree: Path | str, *, target_branch: str='main', run_tests: bool=True, push: bool=False, remove: bool=True, owner: str | None=None, wait_timeout: float=600.0, leases_dir: Path | None=None, workers: int | None=None, post_merge_fn=None, promote_snapshot: bool | None=None, snapshot_store: Path | None=None) -> dict:
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
			r = _land_under_lease(main_repo, wt_path, branch, target_branch=target_branch, run_tests=run_tests, push=push, remove=remove, workers=workers, post_merge_fn=post_merge_fn, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store)
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
