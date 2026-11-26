# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.git import df_git_read_text
from Df.Harness.Gate.XrefChecker import XrefChecker
from agent_tools.xref import run_xref_check
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class XrefWorktreeGate:
	# @used-by :func:`agent_tools.xref_gate.verify_worktree_xref_changes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def __init__(self, wt_path: Path, target_branch: str, *, strict: bool=False) -> None:
		self.__wt = Path(wt_path).resolve()
		self.__target_branch = target_branch
		self.__strict = strict
	# @used-by :meth:`XrefWorktreeGate.verify()`
	def __git_changed_paths(self) -> list[str]:
		raw = df_git_read_text(self.__wt, 'diff', '--name-only', '--diff-filter=ACMRD', f'{self.__target_branch}..HEAD') or ''
		return sorted({ln.strip().replace('\\', '/') for ln in raw.splitlines() if ln.strip()})
	# @used-by :func:`agent_tools.xref_gate.verify_worktree_xref_changes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def verify(self) -> list[str]:
		changed = self.__git_changed_paths()
		langs = sorted({lg for rel in changed for lg in (XrefChecker.lang_for_rel(rel),) if None is not lg})
		errs: list[str] = []
		if langs and (self.__strict or XrefChecker.is_governed_repo(self.__wt, changed)):
			changed_set = set(changed)
			for lang in langs:
				if self.__strict or XrefChecker.is_repo_lang_synced(self.__wt, lang, changed_set):
					errs.extend((XrefChecker.format_error(e) for e in run_xref_check(self.__wt, lang=lang)['issues']))
				else:
					cur_texts = {rel: (self.__wt / rel).read_text(encoding='utf-8', errors='replace') for rel in changed if lang == XrefChecker.lang_for_rel(rel) and (self.__wt / rel).is_file()}
					errs.extend(XrefChecker.verify_legacy_changed_files(self.__wt, lang, list(cur_texts), cur_texts, lambda r, p: df_git_read_text(r, 'show', f'{self.__target_branch}:{p}')))
		return errs
