# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace, _SKIP_TURN_SUFFIXES
from Df.Harness.Issue.ParityAuditor import ParityAuditor
import json
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class PendingPeerFinder:
	# @used-by :func:`agent_tools.github_issue._pending_similar_peer_slugs()`
	# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__finalize_close()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def __init__(self, workspace: EvidenceWorkspace, code_repo: Path | None, *, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]]=()) -> None:
		self.__workspace = workspace
		self.__code_repo = code_repo
		self.__repo = repo
		self.__project_root = project_root
		self.__source_files = source_files
	# @used-by :meth:`PendingPeerFinder.__recorded_open_turn_repos()`
	@staticmethod
	def __collect_recorded_repos(tdata: dict[str, Any], recorded: set[str]) -> None:
		gh_raw = tdata.get('github_issues') or {}
		items = gh_raw.values() if isinstance(gh_raw, dict) else gh_raw if isinstance(gh_raw, list) else ()
		for item in items:
			if isinstance(item, dict):
				acts = {str(a) for a in (item.get('actions') or ()) if a}
				if item.get('last_action'):
					acts.add(str(item['last_action']))
				r_slug = str(item.get('repo') or '').strip().lower()
				if r_slug and (acts & {'create', 'edit', 'comment'}):
					recorded.add(r_slug)
	# @used-by :meth:`PendingPeerFinder.find()`
	@classmethod
	def __recorded_open_turn_repos(cls, turn_dirs: list[Path]) -> set[str]:
		recorded: set[str] = set()
		for tdir in turn_dirs:
			if not tdir.is_dir():
				continue
			for tfile in tdir.glob('*.json'):
				if tfile.name.endswith(_SKIP_TURN_SUFFIXES):
					continue
				try:
					tdata = json.loads(tfile.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				if isinstance(tdata, dict) and 'open' == tdata.get('status'):
					cls.__collect_recorded_repos(tdata, recorded)
		return recorded
	# @used-by :func:`agent_tools.github_issue._pending_similar_peer_slugs()`
	# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__finalize_close()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def find(self) -> list[str]:
		r: list[str] = []
		if None is not self.__code_repo:
			try:
				from agent_tools.path_registry import project_paths
				pp_repo = project_paths(self.__code_repo)
			except (OSError, ValueError):
				pp_repo = None
			if None is not pp_repo:
				peer_slugs = dfa_unique_fast([slug for peer in pp_repo.similar_projects for slug in ParityAuditor.similar_project_repo_slugs(peer)])
				if peer_slugs:
					turn_dirs = list(dict.fromkeys([*(tdir for _, tdir in self.__workspace.resolve_issue_targets(self.__source_files, self.__repo, project_root=self.__project_root)), pp_repo.turns_dir]))
					recorded = self.__recorded_open_turn_repos(turn_dirs)
					r = [s for s in peer_slugs if s.lower() not in recorded]
		return r
