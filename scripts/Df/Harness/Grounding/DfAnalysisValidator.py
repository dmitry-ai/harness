# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.Doc5ContextDetector import Doc5ContextDetector
from Df.Harness.Grounding.ProblemTrackAuditor import ProblemTrackAuditor
from Df.Harness.Grounding.ScatterBannerAuditor import ScatterBannerAuditor
from Df.Harness.lib.grounding_md import dfh_markdown_table_issues, dfh_mask_fenced_lines, dfh_parse_explicit_items, dfh_parse_section_items
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_AGAINST_RE = re.compile(r'(?i)(?:\u0434\u043e\u0432\u043e\u0434\u044b\s+\u043f\u0440\u043e\u0442\u0438\u0432|\u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442\u044b\s+\u043f\u0440\u043e\u0442\u0438\u0432|(?:^|[\s(*_-])\u043f\u0440\u043e\u0442\u0438\u0432\s*[:\u2014\u2013-]|arguments?\s+against|counterevidence|cons\s*[:\u2014\u2013-])')
_CMD_RE = re.compile(r'(?i)(?:^|[\s(\[])(?:/df-analysis|\$df-analysis|\[df-analysis\]\(slashCommand;df-analysis\))(?=$|[\s.,;:!?)\]])')
_FOR_RE = re.compile(r'(?i)(?:\u0434\u043e\u0432\u043e\u0434\u044b\s+\u0437\u0430|\u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442\u044b\s+\u0437\u0430|(?:^|[\s(*_-])\u0437\u0430\s*[:\u2014\u2013-]|arguments?\s+for|evidence\s+for|pros\s*[:\u2014\u2013-])')
_GH_ISSUE_URL_RE = re.compile(r'^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+$')
_JSON_FENCE_RE = re.compile(r'```json[ \t]*\r?\n([\s\S]*?)\r?\n```')
_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)|https?://\S+|file://\S+')
_PCT_RE = re.compile(r'\b\d+(?:[.,]\d+)?\s*%')
_PROB_HEAD_RE = re.compile(r'(?i)(?:\u043f\u0440\u043e\u0431\u043b\u0435\u043c|problem|defect|\u0441\u0431\u043e|\u043e\u0448\u0438\u0431\u043a|bug|failure|\u043c\u0435\u0442\u0430-?\u0434\u0430\u043d\u043d|metadata)')
_TOP_HEAD_RE = re.compile(r'^#\s+(\d+)\.?(?:\s+(.*))?$')
_VERBATIM_RE = re.compile(r'```|^\s*>\s*\S|\u00ab[^\u00bb]{4,}\u00bb|"[^"\n]{4,}"|`[^`\n]{3,}`', re.M)
class DfAnalysisValidator:
	# @used-by :func:`agent_tools.statements.validate_df_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.response_turn_gate_issues()`
	# @used-by :meth:`DfAnalysisValidator.analysis_gate_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def __init__(self, response: str, *, requests: list | tuple=(), mode: str='auto', turn_context: dict | None=None) -> None:
		self.__response = response
		self.__requests = requests
		self.__mode = mode
		self.__turn_context = turn_context
	# @used-by :meth:`DfAnalysisValidator.__check_item_group()`
	@staticmethod
	def __check_item_fields(label: str, body: str, *, require_link: bool, kind: str) -> list[str]:
		errs: list[str] = []
		rule = 'DOC-2' if 'hypothesis' == kind else 'DOC-3'
		if require_link and (not _LINK_RE.search(body)):
			errs.append(f'{rule} / df-analysis: {kind} "{label}" must include a primary source link')
		if not _FOR_RE.search(body):
			errs.append(f'{rule} / df-analysis: {kind} "{label}" must state arguments for')
		if not _AGAINST_RE.search(body):
			errs.append(f'{rule} / df-analysis: {kind} "{label}" must state arguments against')
		if not _PCT_RE.search(body):
			errs.append(f'{rule} / df-analysis: {kind} "{label}" must state an analyst score in %')
		return errs
	# @used-by :meth:`DfAnalysisValidator.__check_problem_sections()`
	# @used-by :meth:`DfAnalysisValidator.__validate_general()`
	@classmethod
	def __check_item_group(cls, items: list[tuple[str, str]], *, require_link: bool, kind: str, context: str) -> list[str]:
		rule = 'DOC-2' if 'hypothesis' == kind else 'DOC-3'
		errs: list[str] = []
		if 2 > len(items):
			errs.append(f'{rule} / df-analysis: {context} must evaluate at least 2 competing {kind} items (found {len(items)})')
		for label, body in items:
			errs.extend(cls.__check_item_fields(label, body, require_link=require_link, kind=kind))
		return errs
	# @used-by :meth:`DfAnalysisValidator.validate()`
	@classmethod
	def __check_problem_blocks(cls, blocks: list[dict]) -> list[str]:
		errs: list[str] = []
		multi = 1 < len(blocks)
		for idx, blk in enumerate(blocks, 1):
			prefix = f'[Analysis #{idx}] ' if multi else ''
			errs.extend((f'{prefix}{err}' for err in cls.__check_problem_sections(blk['sections'])))
		errs.extend(ProblemTrackAuditor(blocks).audit())
		return errs
	# @used-by :meth:`DfAnalysisValidator.__check_problem_sections()`
	@classmethod
	def __check_problem_metadata(cls, body: str) -> list[str]:
		m = _JSON_FENCE_RE.search(body or '')
		if None is m:
			r = ['DOC-5 / df-analysis: Section # 0 (Problem Metadata) must contain a fenced ```json metadata block']
		else:
			try:
				obj = json.loads(m.group(1))
			except ValueError as exc:
				r = [f'DOC-5 / df-analysis: Section # 0 JSON metadata block is invalid: {exc}']
			else:
				r = cls.__validate_metadata_obj(obj)
		return r
	# @used-by :meth:`DfAnalysisValidator.__check_problem_blocks()`
	@classmethod
	def __check_problem_sections(cls, sections: dict[int, tuple[str, str]]) -> list[str]:
		errs = [f'DOC-5 / df-analysis: Problem analysis is missing required top-level section # {num}' for num in range(5) if num not in sections]
		if 0 in sections:
			errs.extend(cls.__check_problem_metadata(sections[0][1]))
		if 1 in sections and (15 > len(sections[1][1].strip()) or (not _VERBATIM_RE.search(sections[1][1].strip()))):
			errs.append('DOC-5 / df-analysis: Section # 1 (Problem Description) must include verbatim diagnostic messages or quoted output')
		if 2 in sections:
			errs.extend(cls.__check_item_group(dfh_parse_section_items(sections[2][1]), require_link=True, kind='hypothesis', context='Section # 2 (Root Cause Analysis)'))
		if 3 in sections and 10 > len(sections[3][1].strip()):
			errs.append('DOC-5 / df-analysis: Section # 3 (Source Project Attribution) must identify the owning source project')
		if 4 in sections:
			errs.extend(cls.__check_item_group(dfh_parse_section_items(sections[4][1]), require_link=False, kind='solution method', context='Section # 4 (Systemic Solutions)'))
		return errs
	# @used-by :meth:`DfAnalysisValidator.validate()`
	@staticmethod
	def __requests_invoke_df_analysis(requests: list | tuple) -> bool:
		r = False
		for req in requests or ():
			raw = str(req.get('text') or req.get('content') or '') if isinstance(req, dict) else str(req or '')
			plain = '\n'.join((line for _, line, fenced in dfh_mask_fenced_lines(raw) if not fenced))
			if _CMD_RE.search(plain):
				r = True
				break
		return r
	# @used-by :meth:`DfAnalysisValidator.validate()`
	@classmethod
	def __validate_general(cls, text: str, explicit_cmd: bool) -> list[str]:
		hyps, mets = dfh_parse_explicit_items(text)
		errs: list[str] = []
		if explicit_cmd and (not hyps) and (not mets):
			errs.append('DOC-2 / DOC-3 / df-analysis: /df-analysis response must present evaluated hypotheses (H-*) and/or solution methods (M-*)')
		if hyps:
			errs.extend(cls.__check_item_group(hyps, require_link=True, kind='hypothesis', context='Hypothesis analysis'))
		if mets:
			errs.extend(cls.__check_item_group(mets, require_link=False, kind='solution method', context='Solution method analysis'))
		return errs
	# @used-by :meth:`DfAnalysisValidator.__check_problem_metadata()`
	@staticmethod
	def __validate_metadata_obj(obj: object) -> list[str]:
		errs: list[str] = []
		if not isinstance(obj, dict):
			errs.append('DOC-5 / df-analysis: Section # 0 JSON metadata must be a JSON object')
		else:
			if 'Issue' not in obj:
				errs.append('DOC-5 / df-analysis: Section # 0 metadata is missing mandatory "Issue" key')
			elif None is not obj['Issue'] and (not (isinstance(obj['Issue'], str) and _GH_ISSUE_URL_RE.fullmatch(obj['Issue'].strip().rstrip('/')))):
				errs.append('DOC-5 / df-analysis: Section # 0 "Issue" must be a valid GitHub issue URL or null (non-GitHub workspace)')
			for req_key in ('Time', 'Project'):
				if req_key not in obj:
					errs.append(f'DOC-5 / df-analysis: Section # 0 metadata is missing required "{req_key}" key')
		return errs
	# @used-by :func:`agent_tools.statements.analysis_gate_issues()`
	@classmethod
	def analysis_gate_issues(cls, response: str, *, requests: list | tuple=(), turn_context: dict | None=None) -> list[str]:
		return [*dfh_markdown_table_issues(response), *cls(response, requests=requests, mode='auto', turn_context=turn_context).validate()]
	# @used-by :func:`agent_tools.statements.validate_df_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.response_turn_gate_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def validate(self) -> list[str]:
		from agent_tools.metadata import strip_leading_metadata_header
		body = strip_leading_metadata_header(self.__response or '')
		blocks = ProblemTrackAuditor.extract_blocks(body, dfh_mask_fenced_lines, _TOP_HEAD_RE)
		eff_mode = Doc5ContextDetector(body, blocks, self.__requests, self.__mode, turn_context=self.__turn_context, prob_head_re=_PROB_HEAD_RE, req_cmd_fn=self.__requests_invoke_df_analysis, explicit_fn=dfh_parse_explicit_items).detect()
		if 'problem' == eff_mode:
			r = self.__check_problem_blocks(blocks)
		elif 'general' == eff_mode:
			r = self.__validate_general(body, self.__requests_invoke_df_analysis(self.__requests) or 'general' == self.__mode)
		else:
			r = []
		r.extend(ScatterBannerAuditor(body, blocks=blocks, mode=eff_mode).audit())
		return r