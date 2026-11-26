# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return True iff resolved `child` lies inside or equals resolved `parent`.
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_path_inside(child: str | Path, parent: str | Path) -> bool:
	try:
		r = Path(child).resolve().is_relative_to(Path(parent).resolve())
	except (OSError, ValueError):
		r = False
	return r
# Normalize a path string or Path to forward-slash POSIX form.
# @used-by :func:`agent_tools.addon_observability._norm_posix()`
# @used-by :func:`agent_tools.tdd.classifier._norm_posix()`
# @used-by :func:`agent_tools.worktree_guard._norm_posix()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_path_posix(path: str | Path) -> str:
	return path.as_posix() if isinstance(path, Path) else str(path).replace('\\', '/')
# Return effective lowercase file suffix, treating dotfiles such as `.py` as their own suffix.
# @used-by :func:`agent_tools.issues.git_read_cache._effective_suffix()`
# @used-by :func:`agent_tools.tdd.comment_diff.detect_comment_language()`
# @used-by :func:`agent_tools.xref_gate._path_suffix()`
# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.check()`
# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.resolve_target()`
# @used-by :meth:`Df.Harness.Gate.IssueCommentStagedGate.IssueCommentStagedGate.verify()`
# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.__iter_repo_source_files()`
# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.lang_for_rel()`
# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.resolve_target()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_path_suffix(path: str | Path) -> str:
	p = Path(path)
	return p.suffix.lower() or (p.name.lower() if p.name.startswith('.') else '')
# Return `(st_mtime_ns, st_size)` for an existing path, or None if unavailable.
# @used-by :func:`agent_tools.evidence_loader._obs_stat()`
# @used-by :func:`agent_tools.path_cache._stat_mtime_size()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_stat_sig(path: str | Path) -> tuple[int, int] | None:
	try:
		st = Path(path).stat()
		r: tuple[int, int] | None = (st.st_mtime_ns, st.st_size)
	except OSError:
		r = None
	return r
# Decode a `file://` URI into a readable host path string.
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_fs_and_git_helpers()`
def df_uri_file_decode(uri: str) -> str:
	parsed = urlsplit(uri)
	path = unquote(parsed.path)
	if parsed.netloc and 'localhost' != parsed.netloc:
		path = '//' + parsed.netloc + path
	elif re.match('^/[A-Za-z]:/', path):
		path = path[1:]
	return path