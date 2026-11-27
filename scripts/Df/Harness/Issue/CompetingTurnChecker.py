# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
_SKIP_TURN_SUFFIXES = ('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CompetingTurnChecker:
	# @used-by :func:`agent_tools.issues.turn_scope.has_competing_open_turns()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_repos_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def __init__(self, root: Path, current_cid: str) -> None:
		self.__root = Path(root).resolve()
		self.__cur_low = str(current_cid or '').strip().lower()
	# @used-by :meth:`CompetingTurnChecker.has_competing()`
	def __candidate_turns_dirs(self) -> list[Path]:
		from agent_tools.path_registry import project_paths
		cands: list[Path] = []
		try:
			cands.append(project_paths(self.__root, exact_root=True).turns_dir.resolve())
		except (OSError, ValueError):
			pass
		for sub in ('_/\ua616/data/turns', '\ua616/data/turns'):
			p = (self.__root / sub).resolve()
			if p not in cands:
				cands.append(p)
		return [d for d in cands if d.is_dir()]
	# @used-by :func:`agent_tools.issues.turn_scope.has_competing_open_turns()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_repos_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def has_competing(self) -> bool:
		open_cids: set[str] = set()
		open_total = 0
		for tdir in self.__candidate_turns_dirs():
			for tfile in tdir.glob('*.json'):
				if tfile.name.endswith(_SKIP_TURN_SUFFIXES):
					continue
				try:
					data: Any = json.loads(tfile.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				if isinstance(data, dict) and 'open' == data.get('status'):
					open_total += 1
					cid = str(data.get('conversation_id') or '').strip().lower()
					if cid:
						open_cids.add(cid)
		return bool(self.__cur_low and any((cid != self.__cur_low for cid in open_cids))) or 2 <= open_total
