# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import os
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Execute a read-only Git command with `--no-optional-locks` and return stdout on success, or None.
# @used-by :func:`agent_tools.python_integrity._git_read_text()`
# @used-by :func:`agent_tools.tdd.comment_diff._git_read_text()`
# @used-by :func:`agent_tools.tdd.enforcement._git_show_text()`
# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.verify_worktree()`
# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.__git_changed_paths()`
# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_git_read_text(repo: str | Path, *args: str, timeout: int=30) -> str | None:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(Path(repo)), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=timeout, check=False, creationflags=_NO_WINDOW)
	return proc.stdout if 0 == proc.returncode else None
# Locate the nearest enclosing Git repository root containing `.git`, or None.
# @used-by :func:`agent_tools.code_size_gate._find_git_root()`
# @used-by :func:`agent_tools.repo_tags._find_git_root()`
# @used-by :func:`agent_tools.tdd.classifier._find_git_ancestor()`
# @used-by :meth:`Df.Harness.Gate.CodeSizeAnalyzer.CodeSizeAnalyzer.resolve_python_target()`
# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.resolve_target()`
# @used-by :meth:`Df.Harness.Gate.WorktreeIsolationGate.WorktreeIsolationGate.__governed_repo_for_path()`
# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.resolve_target()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_git_root(path: str | Path) -> Path | None:
	p = Path(path)
	start = p if p.is_dir() else p.parent
	r: Path | None = None
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r