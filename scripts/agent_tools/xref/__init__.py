# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
from .java_sync import check_java_file_local, check_java_repo, sync_java_repo
from .js_sync import check_js_file_local, check_js_repo, sync_js_repo
from .python_sync import check_python_file_local, check_python_repo, sync_python_repo
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`run_xref_check()`
# @used-by :func:`run_xref_sync()`
def _selected_langs(lang: str) -> tuple[str, ...]:
	norm = str(lang or 'all').strip().lower()
	if 'all' == norm:
		r: tuple[str, ...] = ('python', 'js', 'java')
	elif norm in ('javascript', 'js', 'ts', 'typescript'):
		r = ('js',)
	elif norm in ('java', 'python'):
		r = (norm,)
	else:
		r = ()
	return r
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
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`agent_tools.cli_registry._exec_xref_check()`
# @used-by :mod:`agent_tools.xref`
def run_xref_check(repo: Path, *, lang: str='all', files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	runners = {'java': check_java_repo, 'js': check_js_repo, 'python': check_python_repo}
	file_count, issues = (0, [])
	for name in _selected_langs(lang):
		sub = runners[name](repo, files=files, overrides_map=overrides_map)
		file_count += int(sub.get('file_count', 0))
		issues.extend(sub.get('issues') or ())
	return {'file_count': file_count, 'issue_count': len(issues), 'issues': issues, 'lang': lang, 'repo': Path(repo).resolve().as_posix(), 'valid': not issues}
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`agent_tools.cli_registry._exec_xref_sync()`
# @used-by :mod:`agent_tools.xref`
def run_xref_sync(repo: Path, *, lang: str='all', apply: bool=True, files: list[str] | None=None) -> dict:
	runners = {'java': sync_java_repo, 'js': sync_js_repo, 'python': sync_python_repo}
	file_count, changed = (0, [])
	for name in _selected_langs(lang):
		sub = runners[name](repo, apply=apply, files=files)
		file_count += int(sub.get('file_count', 0))
		changed.extend(sub.get('changed_files') or ())
	return {'applied': apply, 'changed_count': len(changed), 'changed_files': changed, 'file_count': file_count, 'lang': lang, 'repo': Path(repo).resolve().as_posix(), 'valid': True}
__all__ = ['check_java_file_local', 'check_java_repo', 'check_js_file_local', 'check_js_repo', 'check_python_file_local', 'check_python_repo', 'format_xref_text', 'run_xref_check', 'run_xref_sync', 'sync_java_repo', 'sync_js_repo', 'sync_python_repo']
