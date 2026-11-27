# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urlsplit
from Df.Core.lib.array.first import df_first
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
	__FAIL_LOG_RE = re.compile(r'(?m:^FAILED(?:\s*\(|\s+\S)|^FAIL\b)|(?i:\btest result:\s*FAILED\b|\bFAILURES!\b|\bERRORS!\b|\bFailed!\s*-\s*Failed:\s*[1-9]|=+\s+[^=\n]*\b[1-9]\d*\s+(?:failed|errors?)\b[^=\n]*=+)')
	__NODE_FAIL_LOG_RE = re.compile(r'[\u2139i]\s+fail\s+[1-9]\d*\b')
	# @used-by :func:`agent_tools.tdd.outcomes.parse_command_outcome()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.__record_bg_task_completion()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_command_event()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	def __init__(self, outputs: list[str] | tuple[str, ...] | str, *, task_log_paths: list[Path] | None=None, first_fn=None) -> None:
		self.__outputs = outputs
		self.__task_log_paths = task_log_paths
		self.__first_fn = first_fn
	# @used-by :func:`agent_tools.article.check_link_style()`
	# @used-by :func:`agent_tools.claims.evaluate_safe_arithmetic()`
	# @used-by :func:`agent_tools.contract_invariants.audit_readable_link_call_sites()`
	# @used-by :func:`agent_tools.env_isolation_contracts._extract_worktree_land_gates()`
	# @used-by :func:`agent_tools.env_isolation_contracts._verify_contract_test_ref()`
	# @used-by :func:`agent_tools.env_isolation_contracts.audit_metadata_test_env_isolation()`
	# @used-by :func:`agent_tools.links.readable_link_issues()`
	# @used-by :func:`agent_tools.links.references()`
	# @used-by :func:`agent_tools.markdown_links.numeric_text()`
	# @used-by :func:`agent_tools.source_grounding.extract_authored_prose()`
	# @used-by :func:`agent_tools.tdd.outcomes.parse_command_outcome()`
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeAnalyzer.CodeSizeAnalyzer.analyze()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleAnalyzer.CodeStyleAnalyzer.analyze()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.build_py_spans()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneChecker.SubprocessHygieneChecker.__scan_source_findings()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.lex_python()`
	# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.parse_module_functions()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.__record_bg_task_completion()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_command_event()`
	# @used-by :meth:`Df.Harness.Tdd.SubstantiveTestChecker.SubstantiveTestChecker.__py_has_ast_assertion()`
	# @used-by :meth:`Df.Harness.Tdd.SubstantiveTestChecker.SubstantiveTestChecker.__py_source_text_issues()`
	# @used-by :meth:`Df.Harness.Xref.Python.Model.Model.index_file()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._extract_markdown_refs()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_s11_arch_invariants_and_zero_class_facades()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
	# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def parse(self) -> dict:
		parts = [self.__outputs] if isinstance(self.__outputs, str) else [str(o) for o in (self.__outputs or ()) if o]
		combined = '\n'.join(parts)
		bg_task_id, bg_log_path = OutcomeParser.__extract_bg_meta(combined, self.__first_fn)
		exit_code = OutcomeParser.__header_exit_code(parts)
		extra_log_text = ''
		if None is exit_code:
			exit_code, extra_log_text = OutcomeParser.__infer_from_log_files(OutcomeParser.__collect_log_candidates(bg_log_path, self.__task_log_paths))
		if None is exit_code:
			exit_code = OutcomeParser.infer_exit_code_from_log_text(combined)
		full_text = combined + extra_log_text
		is_inv_err = bool(OutcomeParser.INVOCATION_ERROR_RE.search(full_text))
		has_fail_log = bool(OutcomeParser.__FAIL_LOG_RE.search(full_text) or OutcomeParser.__NODE_FAIL_LOG_RE.search(full_text))
		ran_zero = bool(OutcomeParser.ZERO_TESTS_RE.search(full_text)) and (not has_fail_log)
		is_fail = (None is not exit_code) and (0 != exit_code) and (not is_inv_err) and (not ran_zero)
		is_pass = (0 == exit_code) and (not ran_zero) and (not is_inv_err)
		return {'background_log_path': bg_log_path, 'background_task_id': bg_task_id, 'exit_code': exit_code, 'is_failure': is_fail, 'is_invocation_error': is_inv_err, 'is_pass': is_pass, 'ran_zero_tests': ran_zero}
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
