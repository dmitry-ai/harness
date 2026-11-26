# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
from Df.Harness.Gate.IssueCommentChecker import IssueCommentChecker
from Df.Harness.Gate.IssueCommentScanner import IssueCommentScanner
from agent_tools.tdd_gate import _git_head_text, _git_index_text
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class IssueCommentStagedGate:
	# @used-by :func:`agent_tools.issue_comment_gate.verify_staged_issue_comment_placement()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	def __init__(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> None:
		self.__repo = Path(repo_root).resolve()
		self.__staged_paths = list(staged_paths or ())
		self.__use_index = use_index
	# @used-by :func:`agent_tools.issue_comment_gate.verify_staged_issue_comment_placement()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	def verify(self) -> list[str]:
		violations: list[str] = []
		for rel in self.__staged_paths:
			if df_path_suffix(rel) not in IssueCommentScanner.SUPPORTED_SUFFIXES or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
				continue
			fpath = self.__repo / rel
			text = _git_index_text(self.__repo, rel) if self.__use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
			if None is not text:
				violations.extend(IssueCommentChecker(rel, text, baseline_source=_git_head_text(self.__repo, rel)).check())
		return violations
