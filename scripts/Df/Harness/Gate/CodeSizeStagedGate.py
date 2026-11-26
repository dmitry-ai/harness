# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.CodeSizeChecker import CodeSizeChecker
from Df.Harness.Gate.PythonIntegrity import PythonIntegrity
from agent_tools.tdd_gate import _git_head_text, _git_index_text
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeSizeStagedGate:
	# @used-by :func:`agent_tools.code_size_gate.verify_staged_code_size_ratchet()`
	def __init__(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> None:
		self.__repo = Path(repo_root).resolve()
		self.__staged_paths = list(staged_paths or ())
		self.__use_index = use_index
	# @used-by :func:`agent_tools.code_size_gate.verify_staged_code_size_ratchet()`
	def verify(self) -> list[str]:
		violations: list[str] = []
		for rel in self.__staged_paths:
			if not rel.lower().endswith('.py') or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
				continue
			fpath = self.__repo / rel
			text = _git_index_text(self.__repo, rel) if self.__use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
			if None is not text:
				size_errs = CodeSizeChecker(rel, text, baseline_source=_git_head_text(self.__repo, rel)).check()
				violations.extend(size_errs)
				if not any(('syntax' in e.lower() for e in size_errs)):
					violations.extend(PythonIntegrity.check(rel, text))
		return violations
