# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.XrefChecker import XrefChecker
from Df.Harness.Tdd.Enforcement import Enforcement
from Df.Harness.Xref.Engine import Engine
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class XrefStagedGate:
	# @used-by :func:`agent_tools.xref_gate.verify_staged_xref()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def __init__(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True, strict: bool=False) -> None:
		self.__repo = Path(repo_root).resolve()
		self.__staged_paths = list(staged_paths or ())
		self.__use_index = use_index
		self.__strict = strict
	# @used-by :meth:`XrefStagedGate.verify()`
	def __staged_overrides(self) -> tuple[dict[str, str | None], list[str]]:
		overrides: dict[str, str | None] = {}
		langs: set[str] = set()
		for raw in self.__staged_paths:
			rel = Path(raw).as_posix()
			lang = XrefChecker.lang_for_rel(rel)
			if None is lang:
				continue
			langs.add(lang)
			fpath = self.__repo / rel
			overrides[rel] = Enforcement.git_index_text(self.__repo, rel) if self.__use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
		return (overrides, sorted(langs))
	# @used-by :func:`agent_tools.xref_gate.verify_staged_xref()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def verify(self) -> list[str]:
		overrides, langs = self.__staged_overrides()
		errs: list[str] = []
		if langs and (self.__strict or XrefChecker.is_governed_repo(self.__repo, self.__staged_paths, overrides_map=overrides)):
			changed_rels = set(overrides)
			for lang in langs:
				lang_ov = {k: v for k, v in overrides.items() if lang == XrefChecker.lang_for_rel(k)}
				if self.__strict or XrefChecker.is_repo_lang_synced(self.__repo, lang, changed_rels):
					errs.extend((XrefChecker.format_error(e) for e in Engine(self.__repo).check(lang=lang, overrides_map=lang_ov)['issues']))
				else:
					errs.extend(XrefChecker.verify_legacy_changed_files(self.__repo, lang, list(lang_ov), lang_ov, Enforcement.git_head_text))
		return errs
