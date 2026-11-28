# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urlsplit
from Df.Core.lib.array.first import df_first
# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
import json
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.outcomes`
class OutcomeParser:
	BG_HEADER_SPLIT_RE = re.compile(r'(?m)^(?:Command output|Output|Log output):\s*$')
	BG_TASK_FINISHED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+finished\s+with\s+result:\s*([\s\S]*)', re.IGNORECASE)
	BG_TASK_ID_RE = re.compile(r'task\s+id:\s*([A-Za-z0-9_./:-]+)', re.IGNORECASE)
	BG_TASK_LOG_RE = re.compile(r'(?:Task\s+logs\s+are\s+available\s+at|Log):\s*(file:///[^\s\'"<>]+)', re.IGNORECASE)
	EXIT_CODE_RE = re.compile(r'(?im)^(?:(?:Command|Process)\s+exited\s+with\s+code\s+(-?\d+)\.?|Exit\s+code:\s*(-?\d+))\s*$')
	INVOCATION_ERROR_RE = re.compile(
		r'(?i)(?:is not recognized as an internal or external command'
		r'|is not recognized as the name of a cmdlet'
		r'|:\s*command not found\b'
		r'|error:\s*unrecognized arguments:'
		r'|no such option:'
		r'|no module named\s+(?:pytest|unittest|nose|tox)\b'
		r'|cannot find module\b[^.\n]*(?:jest|vitest|mocha))'
	)
	OUTPUT_BODY_SPLIT_RE = re.compile(r'(?m)^(?:Command output|Output):\s*$')
	ZERO_TESTS_RE = re.compile(
		r'(?i)(?:\bRan\s+0\s+tests?\s+in\b'
		r'|\bcollected\s+0\s+items\b'
		r'|\bno\s+tests\s+ran\b'
		r'|\b0\s+tests?\s+passed,\s*0\s+failed\b'
		r'|[\u2139i]\s+tests\s+0\b)'
	)
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	__COL0_BRACE_RE = re.compile(r'(?m)^\{')
	__FAIL_LOG_RE = re.compile(r'(?m:^FAILED(?:\s*\(|\s+\S)|^FAIL\b)|(?i:\btest result:\s*FAILED\b|\bFAILURES!\b|\bERRORS!\b|\bFailed!\s*-\s*Failed:\s*[1-9]|=+\s+[^=\n]*\b[1-9]\d*\s+(?:failed|errors?)\b[^=\n]*=+)')
	__NODE_FAIL_LOG_RE = re.compile(r'[\u2139i]\s+fail\s+[1-9]\d*\b')
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	__REBASE_CONFLICT_RE = re.compile(r'(?im)^(?:CONFLICT\s*\(|error:\s*could not apply\b|Merge conflict in\b)|(?i:Resolve all conflicts manually|fix conflicts and then run "git rebase --continue")')
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	__TRUNC_LAND_FAIL_RE = re.compile(r'(?i)(?:"valid"\s*:\s*false\b[\s\S]*"(?:landed|stage)"|"(?:landed|stage)"[\s\S]*"valid"\s*:\s*false\b)')
	# @used-by :func:`agent_tools.tdd.outcomes.parse_command_outcome()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.__record_bg_task_completion()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_command_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_outcome_parser_worktree_land_json_truncation_and_log_fallback()`
	def __init__(self, outputs: list[str] | tuple[str, ...] | str, *, task_log_paths: list[Path] | None=None, first_fn=None) -> None:
		self.__outputs = outputs
		self.__task_log_paths = task_log_paths
		self.__first_fn = first_fn
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :func:`agent_tools.tdd.outcomes.parse_command_outcome()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.__record_bg_task_completion()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_command_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_outcome_parser_worktree_land_json_truncation_and_log_fallback()`
	def parse(self) -> dict:
		parts = [self.__outputs] if isinstance(self.__outputs, str) else [str(o) for o in (self.__outputs or ()) if o]
		combined = '\n'.join(parts)
		bg_task_id, bg_log_path = OutcomeParser.__extract_bg_meta(combined, self.__first_fn)
		exit_code = OutcomeParser.__header_exit_code(parts)
		log_cands = OutcomeParser.__collect_log_candidates(bg_log_path, self.__task_log_paths)
		extra_log_text = ''
		if None is exit_code:
			exit_code, extra_log_text = OutcomeParser.__infer_from_log_files(log_cands)
		if None is exit_code:
			exit_code = OutcomeParser.infer_exit_code_from_log_text(combined)
		full_text = combined + extra_log_text
		is_inv_err = bool(OutcomeParser.INVOCATION_ERROR_RE.search(full_text))
		has_fail_log = bool(OutcomeParser.__FAIL_LOG_RE.search(full_text) or OutcomeParser.__NODE_FAIL_LOG_RE.search(full_text))
		ran_zero = bool(OutcomeParser.ZERO_TESTS_RE.search(full_text)) and (not has_fail_log)
		is_fail = (None is not exit_code) and (0 != exit_code) and (not is_inv_err) and (not ran_zero)
		is_pass = (0 == exit_code) and (not ran_zero) and (not is_inv_err)
		wl_green, wl_repo, wl_fail = OutcomeParser.__classify_worktree_land_json(full_text, exit_code, ran_zero, log_cands)
		return {'background_log_path': bg_log_path, 'background_task_id': bg_task_id, 'exit_code': exit_code, 'has_fail_log': has_fail_log, 'has_rebase_conflict': OutcomeParser.__has_rebase_conflict(full_text, exit_code), 'is_failure': is_fail, 'is_invocation_error': is_inv_err, 'is_pass': is_pass, 'ran_zero_tests': ran_zero, 'worktree_land_failed': wl_fail, 'worktree_land_full_green': wl_green, 'worktree_land_main_repo': wl_repo}
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`OutcomeParser.parse()`
	@staticmethod
	def __classify_worktree_land_json(full_text: str, exit_code: int | None, ran_zero: bool, log_candidates: list[Path]) -> tuple[bool, str | None, bool]:
		wl_green, wl_repo, wl_fail = (False, None, False)
		if 0 == exit_code and (not ran_zero):
			objs = OutcomeParser.__iter_top_level_json_dicts(full_text) if '"test_result"' in full_text else []
			wl_green, wl_repo = OutcomeParser.__find_land_pass_repo(objs)
			if (not wl_green) and log_candidates:
				log_txt = OutcomeParser.__read_worktree_land_logs(log_candidates)
				if '"test_result"' in log_txt:
					wl_green, wl_repo = OutcomeParser.__find_land_pass_repo(OutcomeParser.__iter_top_level_json_dicts(log_txt))
		elif None is not exit_code and 0 != exit_code and any((tok in full_text for tok in ('"test_result"', '"landed"', '"stage"'))):
			objs = OutcomeParser.__iter_top_level_json_dicts(full_text)
			wl_fail = any((False is obj.get('valid') and ('landed' in obj or 'stage' in obj) for obj in objs)) or bool(OutcomeParser.__TRUNC_LAND_FAIL_RE.search(full_text))
		return (wl_green, wl_repo, wl_fail)
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`OutcomeParser.__classify_worktree_land_json()`
	@staticmethod
	def __find_land_pass_repo(objs: list[dict]) -> tuple[bool, str | None]:
		r: tuple[bool, str | None] = (False, None)
		for obj in objs:
			if OutcomeParser.__is_valid_land_pass_obj(obj):
				raw_repo = obj.get('main_repo')
				r = (True, str(raw_repo) if isinstance(raw_repo, str) and raw_repo.strip() else None)
				break
		return r
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`OutcomeParser.__find_land_pass_repo()`
	@staticmethod
	def __is_valid_land_pass_obj(obj: dict) -> bool:
		runs = obj.get('test_runs')
		tr = obj.get('test_result')
		total = tr.get('total_tests') if isinstance(tr, dict) else None
		return True is obj.get('valid') and int is type(runs) and 0 < runs and isinstance(tr, dict) and True is tr.get('ok') and (None is total or (int is type(total) and 0 < total))
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`OutcomeParser.__classify_worktree_land_json()`
	@staticmethod
	def __iter_top_level_json_dicts(text: str) -> list[dict]:
		parts = OutcomeParser.BG_HEADER_SPLIT_RE.split(text or '', maxsplit=1)
		body = parts[1] if 2 == len(parts) else (text or '')
		dec, pos, r = (json.JSONDecoder(), 0, [])
		for m in OutcomeParser.__COL0_BRACE_RE.finditer(body):
			idx = m.start()
			if idx < pos:
				continue
			try:
				obj, pos = dec.raw_decode(body, idx)
			except ValueError:
				pos = idx + 1
			else:
				if isinstance(obj, dict):
					r.append(obj)
		return r
	# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
	# @used-by :meth:`OutcomeParser.__classify_worktree_land_json()`
	@staticmethod
	def __read_worktree_land_logs(log_candidates: list[Path]) -> str:
		chunks: list[str] = []
		for lp in log_candidates:
			try:
				if lp.is_file():
					chunks.append(lp.read_text(encoding='utf-8', errors='replace')[-65536:])
			except OSError:
				continue
		return '\n'.join(chunks)
	# @used-by :meth:`OutcomeParser.parse()`
	@staticmethod
	def __collect_log_candidates(bg_log_path: str | None, task_log_paths: list[Path] | None) -> list[Path]:
		r: list[Path] = [Path(bg_log_path)] if bg_log_path else []
		for lp in task_log_paths or ():
			p_obj = Path(lp)
			if p_obj not in r:
				r.append(p_obj)
		return r
	# @used-by :meth:`OutcomeParser.parse()`
	@staticmethod
	def __extract_bg_meta(combined: str, first_fn=None) -> tuple[str | None, str | None]:
		tids = OutcomeParser.extract_bg_task_ids(combined)
		bg_tid = (first_fn if None is not first_fn else df_first)(tids)
		m_log = OutcomeParser.BG_TASK_LOG_RE.search(combined)
		lp = OutcomeParser.uri_to_local_path(m_log.group(1)) if m_log else None
		return (bg_tid, str(lp) if None is not lp else None)
	# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
	# @used-by :meth:`OutcomeParser.parse()`
	@staticmethod
	def __has_rebase_conflict(full_text: str, exit_code: int | None) -> bool:
		return None is not exit_code and 0 != exit_code and bool(OutcomeParser.__REBASE_CONFLICT_RE.search(full_text))
	# @used-by :meth:`OutcomeParser.parse()`
	@staticmethod
	def __header_exit_code(parts: list[str]) -> int | None:
		r = None
		for part in parts:
			header = OutcomeParser.OUTPUT_BODY_SPLIT_RE.split(part, maxsplit=1)[0]
			m_hdr = OutcomeParser.EXIT_CODE_RE.search(header)
			if m_hdr:
				r = int(m_hdr.group(1) or m_hdr.group(2))
		return r
	# @used-by :meth:`OutcomeParser.parse()`
	@staticmethod
	def __infer_from_log_files(log_candidates: list[Path]) -> tuple[int | None, str]:
		exit_code = None
		extra = ''
		for lp in log_candidates:
			try:
				if lp.is_file():
					tail = lp.read_text(encoding='utf-8', errors='replace')[-16000:]
					extra += '\n' + tail
					inferred = OutcomeParser.infer_exit_code_from_log_text(tail)
					if None is not inferred:
						exit_code = inferred
						break
			except OSError:
				continue
		return (exit_code, extra)
	# @used-by :meth:`OutcomeParser.infer_exit_code_from_log_text()`
	@staticmethod
	def __is_pass_log_text(text: str) -> bool:
		return bool(
			(re.search(r'(?m)^Ran\s+\d+\s+tests?\s+in\s+\d', text) and re.search(r'(?m)^OK(?:\s|\(|$)', text))
			or re.search(r'(?i)\btest result:\s*ok\.\s*[1-9]\d*\s+passed;\s*0\s+failed\b|\bPassed!\s*-\s*Failed:\s*0,\s*Passed:\s*[1-9]|\bOK\s*\(\d+\s+tests?', text)
			or (re.search(r'(?m)^(?:=+\s+[^=\n]*\b)?[1-9]\d*\s+passed\b', text) and (not re.search(r'(?i)\b[1-9]\d*\s+(?:failed|errors?)\b', text)))
			or (re.search(r'[\u2139i]\s+fail\s+0\b', text) and re.search(r'[\u2139i]\s+tests\s+[1-9]\d*\b', text))
		)
	# @used-by :func:`agent_tools.tdd.outcomes.extract_bg_task_ids()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.__track_bg_command_outputs()`
	# @used-by :meth:`OutcomeParser.__extract_bg_meta()`
	@staticmethod
	def extract_bg_task_ids(text: str) -> list[str]:
		r: list[str] = []
		header = OutcomeParser.BG_HEADER_SPLIT_RE.split(text or '', maxsplit=1)[0]
		if not OutcomeParser.EXIT_CODE_RE.search(header):
			for m_tid in OutcomeParser.BG_TASK_ID_RE.finditer(header):
				tid = m_tid.group(1).strip().rstrip('.,')
				if tid and tid not in r:
					r.append(tid)
		return r
	# @used-by :func:`agent_tools.tdd.outcomes._infer_exit_code_from_log_text()`
	# @used-by :meth:`OutcomeParser.__infer_from_log_files()`
	# @used-by :meth:`OutcomeParser.parse()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	@staticmethod
	def infer_exit_code_from_log_text(text: str) -> int | None:
		r = None
		if text:
			m_ec = OutcomeParser.EXIT_CODE_RE.search(text)
			if m_ec:
				r = int(m_ec.group(1) or m_ec.group(2))
			elif OutcomeParser.__FAIL_LOG_RE.search(text):
				r = 1
			elif OutcomeParser.__is_pass_log_text(text):
				r = 0
			elif OutcomeParser.__NODE_FAIL_LOG_RE.search(text):
				r = 1
		return r
	# @used-by :func:`agent_tools.tdd.outcomes._uri_to_local_path()`
	# @used-by :meth:`OutcomeParser.__extract_bg_meta()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	@staticmethod
	def uri_to_local_path(uri: str) -> Path | None:
		raw = (uri or '').strip()
		if not raw:
			r = None
		elif not raw.lower().startswith('file:'):
			r = Path(raw)
		else:
			parsed = urlsplit(raw)
			p_str = unquote(parsed.path)
			if parsed.netloc and re.fullmatch(r'[A-Za-z]:', parsed.netloc):
				p_str = parsed.netloc + p_str
			elif re.match(r'^/[A-Za-z]:/', p_str):
				p_str = p_str[1:]
			r = Path(p_str)
		return r
