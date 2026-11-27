# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import os
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class TurnScopeResolver:
	# @used-by :func:`agent_tools.issues.turn_scope.select_target_open_turns()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.record_issue_in_open_turns()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def __init__(self, open_files: list[tuple[Path, str, str]], active_plat: str, active_cid: str, *, env: dict[str, str] | None=None) -> None:
		self.__open_files = open_files
		self.__active_plat = active_plat
		self.__active_cid = active_cid
		self.__environ = dict(os.environ) if None is env else dict(env)
	# @used-by :meth:`TurnScopeResolver.select()`
	def __match_open_by_cid(self, cid_low: str) -> list[Path]:
		return [tfile for tfile, _, t_cid in self.__open_files if t_cid and cid_low == t_cid.lower()]
	# @used-by :meth:`TurnScopeResolver.select()`
	def __resolve_antigravity_parent_cid(self) -> str:
		r = ''
		try:
			from agent_tools.meta.builders import _collect_ag_issue_ctx
			ctx = _collect_ag_issue_ctx(self.__environ, self.__active_cid)
			parent = str(ctx.get('primary_cid') or '').strip().lower()
			r = parent if parent and parent != self.__active_cid.lower() else ''
		except Exception:
			r = ''
		return r
	# @used-by :meth:`TurnScopeResolver.select()`
	def __sole_untagged_open_turn(self) -> list[Path]:
		r: list[Path] = []
		if 1 == len(self.__open_files):
			tfile, t_plat, t_cid = self.__open_files[0]
			if (not t_cid) and ((not self.__active_plat) or (not t_plat) or self.__active_plat == t_plat):
				r = [tfile]
		return r
	# @used-by :func:`agent_tools.issues.turn_scope.select_target_open_turns()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.record_issue_in_open_turns()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def select(self) -> tuple[list[Path], str, str]:
		if not self.__active_cid:
			r = ([self.__open_files[0][0]], '', self.__active_plat or self.__open_files[0][1]) if 1 == len(self.__open_files) else ([], '', self.__active_plat)
		else:
			targets = self.__match_open_by_cid(self.__active_cid)
			rec_cid = self.__active_cid
			if (not targets) and 'antigravity' == self.__active_plat:
				parent_cid = self.__resolve_antigravity_parent_cid()
				if parent_cid:
					targets = self.__match_open_by_cid(parent_cid)
					if targets:
						rec_cid = parent_cid
			if not targets:
				targets = self.__sole_untagged_open_turn()
			r = (targets, rec_cid, self.__active_plat)
		return r
