# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
from __future__ import annotations
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import atexit
import io
import os
import shutil
import subprocess
import sys
import tempfile
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_BARE_TEMPLATES: dict[str, Path] = {}
_CACHE_DIRS: list[tempfile.TemporaryDirectory] = []
_WORK_TEMPLATES: dict[str, Path] = {}
# @used-by :func:`clone_template_git_repo()`
def _append_origin_remote(cfg: Path, remote_url: str, push_url: str | None) -> None:
	lines = ['[remote "origin"]', f'\turl = {remote_url}']
	if None is not push_url:
		lines.append(f'\tpushurl = {push_url}')
	lines.append('\tfetch = +refs/heads/*:refs/remotes/origin/*')
	cfg.write_text(cfg.read_text(encoding='utf-8') + '\n'.join(lines) + '\n', encoding='utf-8')
# @used-by :func:`_template_root()`
def _cleanup_templates() -> None:
	_BARE_TEMPLATES.clear()
	_WORK_TEMPLATES.clear()
	while _CACHE_DIRS:
		td = _CACHE_DIRS.pop()
		try:
			td.cleanup()
		except OSError:
			shutil.rmtree(td.name, ignore_errors=True)
# @used-by :func:`run_harness_inprocess()`
def _clear_harness_caches() -> None:
	from agent_tools import path_cache, path_registry
	path_registry.clear_registry_cache()
	path_cache.clear_path_cache()
# @used-by :func:`run_harness_inprocess()`
def _exit_code_from_system_exit(exc: SystemExit, err_buf: io.StringIO) -> int:
	code = exc.code
	if None is code:
		r = 0
	elif isinstance(code, int):
		r = int(code)
	else:
		err_buf.write(f'{code}\n')
		r = 1
	return r
# @used-by :func:`clone_template_bare_repo()`
# @used-by :func:`clone_template_git_repo()`
def _template_root() -> Path:
	if not _CACHE_DIRS:
		_CACHE_DIRS.append(tempfile.TemporaryDirectory(prefix='harness-git-tmpl-'))
		atexit.register(_cleanup_templates)
	return Path(_CACHE_DIRS[0].name).resolve()
# @used-by :func:`test_issue_first_completion._init_github_project()`
# @used-by :func:`test_tdd_completion._build_template_project()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_clone_template_bare_repo_caches_init_and_supports_push()`
def clone_template_bare_repo(dest: Path, *, initial_branch: str='main') -> Path:
	tmpl = _BARE_TEMPLATES.get(initial_branch)
	if None is tmpl or (not tmpl.is_dir()):
		tmpl = _template_root() / f'bare-{len(_BARE_TEMPLATES)}.git'
		subprocess.run(['git', 'init', '--bare', '-b', initial_branch, str(tmpl)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
		_BARE_TEMPLATES[initial_branch] = tmpl
	target = Path(dest)
	shutil.copytree(tmpl, target, dirs_exist_ok=True)
	assert (target / 'HEAD').is_file(), f'Template bare HEAD missing in {target}'
	return target
# @used-by :func:`test_issue_first_completion._init_github_project()`
# @used-by :func:`test_runtime_snapshot._seed_harness_git_repo()`
# @used-by :func:`test_tdd_completion._build_template_project()`
# @used-by :func:`test_tdd_git_gate._init_repo()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_read_git_and_git_shim_and_unflagged_detector()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_clone_template_bare_repo_caches_init_and_supports_push()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_clone_template_git_repo_caches_init_and_isolates_clones()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests._init_repo()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_isolated_temp_project_ignores_unrelated_host_worktree_cwd()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
def clone_template_git_repo(dest: Path, *, initial_branch: str='main', remote_url: str | None=None, push_url: str | None=None) -> Path:
	tmpl = _WORK_TEMPLATES.get(initial_branch)
	if None is tmpl or (not tmpl.is_dir()):
		tmpl = _template_root() / f'work-{len(_WORK_TEMPLATES)}'
		tmpl.mkdir(parents=True, exist_ok=True)
		subprocess.run(['git', 'init', '-b', initial_branch, str(tmpl)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
		cfg = tmpl / '.git/config'
		cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = test@example.com\n\tname = Test User\n', encoding='utf-8')
		_WORK_TEMPLATES[initial_branch] = tmpl
	target = Path(dest)
	shutil.copytree(tmpl, target, dirs_exist_ok=True)
	assert (target / '.git/config').is_file(), f'Template git config missing in {target}'
	if None is not remote_url:
		_append_origin_remote(target / '.git/config', remote_url, push_url)
	return target
# @used-by :func:`test_project_rename._run_harness()`
# @used-by :func:`test_upwork_init_e2e._run_cli()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_run_harness_inprocess_executes_cli_isolates_env_cwd_and_clears_caches()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_run_harness_inprocess_restores_env_and_cwd_on_system_exit_and_exception()`
def run_harness_inprocess(args: list[str] | tuple[str, ...], *, cwd: Path | None=None, env: dict[str, str] | None=None) -> subprocess.CompletedProcess:
	from agent_tools import upwork_project
	arg_list = [str(a) for a in args]
	old_env = dict(os.environ)
	old_cwd = os.getcwd()
	out_buf = io.StringIO()
	err_buf = io.StringIO()
	rc = 0
	try:
		if None is not env:
			os.environ.clear()
			os.environ.update({str(k): str(v) for k, v in env.items()})
		if None is not cwd:
			os.chdir(cwd)
		_clear_harness_caches()
		with redirect_stdout(out_buf), redirect_stderr(err_buf):
			try:
				raw_rc = upwork_project.main(arg_list)
				rc = 0 if None is raw_rc else int(raw_rc)
			except SystemExit as exc:
				rc = _exit_code_from_system_exit(exc, err_buf)
	finally:
		os.chdir(old_cwd)
		os.environ.clear()
		os.environ.update(old_env)
		_clear_harness_caches()
	return subprocess.CompletedProcess(['harness.py', *arg_list], rc, out_buf.getvalue(), err_buf.getvalue())
