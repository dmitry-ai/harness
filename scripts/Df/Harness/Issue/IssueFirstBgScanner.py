# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools.tdd.events import _normalize_args_dict
from agent_tools.tdd.outcomes import _BG_TASK_FINISHED_RE, _BG_TASK_LOG_RE, _uri_to_local_path, extract_bg_task_ids
from agent_tools.tdd_gate import shell_write_targets
_WRITE_TOOLS = frozenset({'edit_file', 'multi_replace_file_content', 'replace_file_content', 'write_file', 'write_to_file'})
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueFirstBgScanner:
	# @used-by :func:`agent_tools.issue_first_bg.extract_segment_issue_first_events()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.extract_antigravity_events()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
	def __init__(self, segment: list[dict], cwd: Path | None, build_write_fn, build_action_fn) -> None:
		self.__segment = segment
		self.__cwd = cwd
		self.__build_write = build_write_fn
		self.__build_action = build_action_fn
	# @used-by :meth:`IssueFirstBgScanner.__record_bg_completion()`
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
	# @used-by :meth:`IssueFirstBgScanner.__dispatch_row_calls()`
	def __collect_row_outputs(self, pos: int) -> list[str]:
		r: list[str] = []
		for nxt in self.__segment[pos + 1:]:
			if not isinstance(nxt, dict):
				continue
			if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == nxt.get('type') and nxt.get('content'):
				r.append(str(nxt.get('content')))
		return r
	# @used-by :meth:`IssueFirstBgScanner.__process_row()`
	def __dispatch_row_calls(self, pos: int, step_idx: int, raw_calls: list, events: list[dict], bg_cmds: dict[str, tuple[str, str | None]]) -> None:
		calls = [c for c in raw_calls if isinstance(c, dict)]
		if calls:
			outputs = self.__collect_row_outputs(pos)
			for c_pos, call in enumerate(calls):
				matched = [outputs[c_pos]] if c_pos < len(outputs) else outputs
				self.__dispatch_single_call(step_idx, c_pos, call, matched, events, bg_cmds)
	# @used-by :meth:`IssueFirstBgScanner.__dispatch_row_calls()`
	def __dispatch_single_call(self, step_idx: int, c_pos: int, call: dict, matched: list[str], events: list[dict], bg_cmds: dict[str, tuple[str, str | None]]) -> None:
		cname = str(call.get('name') or '')
		cargs = _normalize_args_dict(call.get('args', {}))
		if cname in _WRITE_TOOLS:
			self.__handle_write(step_idx, c_pos, cname, cargs, matched, events)
		elif 'run_command' == cname:
			self.__handle_run_command(step_idx, c_pos, cargs, matched, events, bg_cmds)
	# @used-by :meth:`IssueFirstBgScanner.__dispatch_single_call()`
	def __handle_run_command(self, step_idx: int, c_pos: int, cargs: dict, matched: list[str], events: list[dict], bg_cmds: dict[str, tuple[str, str | None]]) -> None:
		cmd = str(cargs.get('CommandLine') or '')
		for wt in shell_write_targets(cmd, cwd=self.__cwd):
			ev = self.__build_write(step_idx, wt, cwd=self.__cwd, sub_step=c_pos, cmd_outputs=matched)
			if None is not ev:
				events.append(ev)
		events.extend(self.__build_action(step_idx, cmd, matched, sub_step=c_pos))
		self.__register_bg_tasks(cmd, matched, bg_cmds)
	# @used-by :meth:`IssueFirstBgScanner.__dispatch_single_call()`
	def __handle_write(self, step_idx: int, c_pos: int, cname: str, cargs: dict, matched: list[str], events: list[dict]) -> None:
		raw_p = str(next((cargs[k] for k in ('Path', 'TargetFile', 'AbsolutePath', 'path') if cargs.get(k)), '')).strip()
		if raw_p:
			raw_c = cargs.get('Content') if 'write_file' == cname else None
			ev = self.__build_write(step_idx, raw_p, cwd=self.__cwd, content=raw_c if isinstance(raw_c, str) else None, sub_step=c_pos, cmd_outputs=matched)
			if None is not ev:
				events.append(ev)
	# @used-by :meth:`IssueFirstBgScanner.extract()`
	def __process_row(self, pos: int, row: dict, events: list[dict], bg_cmds: dict[str, tuple[str, str | None]]) -> None:
		step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
		if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
			self.__record_bg_completion(str(row.get('content')), step_idx, bg_cmds, events)
		if row.get('tool_calls'):
			self.__dispatch_row_calls(pos, step_idx, row['tool_calls'], events, bg_cmds)
	# @used-by :meth:`IssueFirstBgScanner.__process_row()`
	def __record_bg_completion(self, c_str: str, step_idx: int, bg_cmds: dict[str, tuple[str, str | None]], events: list[dict]) -> None:
		m_fin = _BG_TASK_FINISHED_RE.search(c_str)
		if m_fin:
			entry = bg_cmds.get(m_fin.group(1).strip())
			if None is not entry:
				cmd, log_path = entry
				events.extend(self.__build_action(step_idx, cmd, self.__bg_fin_outputs(m_fin.group(2), log_path)))
	# @used-by :meth:`IssueFirstBgScanner.__handle_run_command()`
	@staticmethod
	def __register_bg_tasks(cmd: str, matched: list[str], bg_cmds: dict[str, tuple[str, str | None]]) -> None:
		joined = '\n'.join(matched)
		m_log = _BG_TASK_LOG_RE.search(joined)
		lp = _uri_to_local_path(m_log.group(1)) if m_log else None
		lp_str = str(lp) if None is not lp else None
		for tid in extract_bg_task_ids(joined):
			bg_cmds[tid] = (cmd, lp_str)
	# @used-by :func:`agent_tools.issue_first_bg.extract_segment_issue_first_events()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.extract_antigravity_events()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_bg_scanner_recorder_and_issue_lib_helpers()`
	def extract(self) -> list[dict]:
		events: list[dict] = []
		bg_cmds: dict[str, tuple[str, str | None]] = {}
		for pos, row in enumerate(self.__segment):
			if isinstance(row, dict):
				self.__process_row(pos, row, events, bg_cmds)
		return events
