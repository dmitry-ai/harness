# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Xref.Java.Syncer import Syncer as JavaSyncer
from Df.Harness.Xref.Js.Syncer import Syncer as JsSyncer
from Df.Harness.Xref.Python.Syncer import Syncer as PythonSyncer
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Engine:
	# @used-by :func:`agent_tools.xref.run_xref_check()`
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_tdd_and_xref_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def __init__(self, repo_root: Path | str) -> None:
		self.__repo_root = Path(repo_root).resolve()
	# @used-by :func:`agent_tools.xref.run_xref_check()`
	# @used-by :meth:`Df.Harness.Gate.XrefStagedGate.XrefStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.XrefWorktreeGate.XrefWorktreeGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_tdd_and_xref_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def check(self, *, lang: str='all', files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
		runners = {'java': JavaSyncer.check_repo, 'js': JsSyncer.check_repo, 'python': PythonSyncer.check_repo}
		file_count, issues = (0, [])
		for name in Engine.__selected_langs(lang):
			sub = runners[name](self.__repo_root, files=files, overrides_map=overrides_map)
			file_count += int(sub.get('file_count', 0))
			issues.extend(sub.get('issues') or ())
		return {'file_count': file_count, 'issue_count': len(issues), 'issues': issues, 'lang': lang, 'repo': self.__repo_root.as_posix(), 'valid': not issues}
	# @used-by :meth:`Engine.check()`
	# @used-by :meth:`Engine.sync_repo()`
	@staticmethod
	def __selected_langs(lang: str) -> tuple[str, ...]:
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
	# @used-by :func:`agent_tools.xref.format_xref_text()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	@staticmethod
	def format_text(res: dict) -> str:
		lines = [f"xref ({res.get('lang', 'all')}): valid={res.get('valid')} files={res.get('file_count', 0)} issues={res.get('issue_count', 0)}"]
		lines.extend((f'  - {issue}' for issue in (res.get('issues') or ())[:50]))
		lines.extend((f'  * {changed}' for changed in (res.get('changed_files') or ())[:50]))
		return '\n'.join(lines) + '\n'
	# @used-by :func:`agent_tools.xref.run_xref_sync()`
	@staticmethod
	def sync_repo(repo: Path, *, lang: str='all', apply: bool=True, files: list[str] | None=None) -> dict:
		runners = {'java': JavaSyncer, 'js': JsSyncer, 'python': PythonSyncer}
		root = Path(repo).resolve()
		file_count, changed = (0, [])
		for name in Engine.__selected_langs(lang):
			sub = runners[name](root).sync(apply=apply, files=files)
			file_count += int(sub.get('file_count', 0))
			changed.extend(sub.get('changed_files') or ())
		return {'applied': apply, 'changed_count': len(changed), 'changed_files': changed, 'file_count': file_count, 'lang': lang, 'repo': root.as_posix(), 'valid': True}
