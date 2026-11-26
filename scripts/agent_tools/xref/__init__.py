# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from .python_sync import check_python_file_local, check_python_repo, sync_python_repo
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
# @used-by :func:`agent_tools.cli_registry._format_xref()`
# @used-by :mod:`agent_tools.xref`
def format_xref_text(res: dict) -> str:
	lines = [f"xref ({res.get('lang', 'all')}): valid={res.get('valid')} files={res.get('file_count', 0)} issues={res.get('issue_count', 0)}"]
	for issue in (res.get('issues') or ())[:50]:
		lines.append(f'  - {issue}')
	for changed in (res.get('changed_files') or ())[:50]:
		lines.append(f'  * {changed}')
	return '\n'.join(lines) + '\n'
# @used-by :func:`agent_tools.cli_registry._exec_xref_check()`
# @used-by :mod:`agent_tools.xref`
def run_xref_check(repo: Path, *, lang: str='all', files: list[str] | None=None) -> dict:
	if lang in ('all', 'python'):
		r = check_python_repo(repo, files=files)
	else:
		r = {'file_count': 0, 'issue_count': 0, 'issues': [], 'lang': lang, 'repo': Path(repo).resolve().as_posix(), 'valid': True}
	return r
# @used-by :func:`agent_tools.cli_registry._exec_xref_sync()`
# @used-by :mod:`agent_tools.xref`
def run_xref_sync(repo: Path, *, lang: str='all', apply: bool=True, files: list[str] | None=None) -> dict:
	if lang in ('all', 'python'):
		r = sync_python_repo(repo, apply=apply, files=files)
	else:
		r = {'applied': apply, 'changed_count': 0, 'changed_files': [], 'file_count': 0, 'lang': lang, 'repo': Path(repo).resolve().as_posix(), 'valid': True}
	return r
__all__ = ['check_python_file_local', 'check_python_repo', 'format_xref_text', 'run_xref_check', 'run_xref_sync', 'sync_python_repo']
