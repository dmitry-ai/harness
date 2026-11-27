# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.IssueActionExtractor import IssueActionExtractor
from Df.Harness.lib.issue import dfh_is_df_issue_command_text
from agent_tools.tdd.outcomes import _BG_TASK_FINISHED_RE, _BG_TASK_LOG_RE, _uri_to_local_path
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class BgTaskRecorder:
	# @used-by :func:`agent_tools.issue_first_bg.handle_antigravity_bg_task_message()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
	def __init__(self, c_str: str, step_idx, seg: dict, parse_command_outcome) -> None:
		self.__c_str = c_str
		self.__step_idx = step_idx
		self.__seg = seg
		self.__parse_outcome = parse_command_outcome
	# @used-by :meth:`BgTaskRecorder.__record_seg_issues()`
	@staticmethod
	def __bg_fin_outputs(fin_body: str, log_path: str | None) -> list[str]:
		r = [fin_body]
		m_log = _BG_TASK_LOG_RE.search(fin_body)
		cand = _uri_to_local_path(m_log.group(1)) if m_log else (Path(log_path) if log_path else None)
		if None is not cand and cand.is_file():
			try:
				r.append(cand.read_text(encoding='utf-8', errors='replace'))
			except OSError:
				pass
		return r
	# @used-by :meth:`BgTaskRecorder.record()`
	def __record_seg_issues(self, cev: dict, fin_body: str, prev_log: str | None) -> None:
		from Df.Harness.Issue.IssueFirstPreToolEvaluator import IssueFirstPreToolEvaluator
		cmd = str(cev.get('cmd') or '')
		if dfh_is_df_issue_command_text(cmd):
			eff_step = self.__step_idx if isinstance(self.__step_idx, int) else int(cev.get('step', 0))
			outs = self.__bg_fin_outputs(fin_body, prev_log)
			if 'issue_first_events' in self.__seg:
				self.__seg['issue_first_events'].extend(IssueFirstPreToolEvaluator.build_issue_action_events(eff_step, cmd, outs))
			if 'issue_actions' in self.__seg:
				for act in IssueActionExtractor(outs).extract():
					self.__seg['issue_actions'].append({**act, 'step': eff_step})
	# @used-by :func:`agent_tools.issue_first_bg.handle_antigravity_bg_task_message()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
	def record(self) -> None:
		m_fin = _BG_TASK_FINISHED_RE.search(self.__c_str)
		if m_fin:
			fin_tid, fin_body = (m_fin.group(1).strip(), m_fin.group(2))
			cev = (self.__seg.get('bg_tdd_index') or {}).get(fin_tid)
			if None is not cev:
				prev_log = (cev.get('outcome') or {}).get('background_log_path')
				cev['outcome'] = self.__parse_outcome(fin_body)
				self.__record_seg_issues(cev, fin_body, prev_log)
