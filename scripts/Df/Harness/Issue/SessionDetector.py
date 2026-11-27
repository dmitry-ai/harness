# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import os
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SessionDetector:
	# @used-by :func:`agent_tools.issues.turn_scope.detect_active_session()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.record_issue_in_open_turns()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def __init__(self, conversation_id: str | None=None, env: dict[str, str] | None=None) -> None:
		self.__conversation_id = conversation_id
		self.__environ = dict(os.environ) if None is env else dict(env)
	# @used-by :meth:`SessionDetector.detect()`
	@staticmethod
	def __fallback_env_session(environ: dict[str, str]) -> tuple[str, str]:
		from agent_tools.meta.transcripts import _parse_antigravity_source_metadata
		meta_cid, _ = _parse_antigravity_source_metadata(environ)
		ag_raw = str(environ.get('ANTIGRAVITY_CONVERSATION_ID') or '').strip() or str(meta_cid or '').strip()
		cx_raw = str(environ.get('CODEX_THREAD_ID') or '').strip()
		if ag_raw:
			r = ('antigravity', ag_raw.lower())
		elif cx_raw:
			r = ('codex', cx_raw.lower())
		else:
			r = ('', '')
		return r
	# @used-by :func:`agent_tools.issues.turn_scope.detect_active_session()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.record_issue_in_open_turns()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_turn_lib_session_scope_and_pending_peers()`
	def detect(self) -> tuple[str, str]:
		from agent_tools.meta.builders import _detect_env_platform
		plat, env_cid, _ = _detect_env_platform(self.__environ)
		if not env_cid:
			fb_plat, fb_cid = self.__fallback_env_session(self.__environ)
			plat, env_cid = (plat or fb_plat, fb_cid)
		explicit = str(self.__conversation_id or '').strip().lower()
		eff_cid = explicit if explicit else str(env_cid or '').strip().lower()
		eff_plat = str(plat or '').strip().lower()
		return (eff_plat, eff_cid)
