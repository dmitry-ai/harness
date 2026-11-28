# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Grounding.HeadingNode import HeadingNode
from Df.Harness.Grounding.HeadingTreeParser import HeadingTreeParser
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_CLI_CMD_RE = re.compile(r'''(?:harness|upwork_project|df_github_issue)\.py["']?\s+([a-z][a-z0-9-]+)([^\r\n`\u00bb]*)''', re.IGNORECASE)
_CONCRETE_TARGET_RE = re.compile(r'(?:[A-Za-z]:[/\\]|--domain\s+[A-Za-z0-9.-]+\.[A-Za-z]{2,}|--issue\s+\d+)')
_DESC_SUB_RE = re.compile(r'(?i)^(?:\d+\.2\.?(?:\s|$)|1\.?(?:\s|$))')
_DIAGNOSTIC_LINE_RE = re.compile(r'(?i)(?:exit=[1-9]|exited\s+with\s+code\s+[1-9]|traceback|valueerror|\bfailed\b|\u0443\u043f\u0430\u043b|\u043e\u0442\u043a\u0430\u0437\u0430\u043b)')
_DISCLAIMER_RE = re.compile(r'(?i)(?:\u043d\u0435\s+\u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043e|\u043d\u0435\s+\u0442\u0435\u0441\u0442\u0438\u0440\u043e\u0432\u0430\u043b|\u0431\u0435\u0437\s+\u043f\u0440\u043e\u0433\u043e\u043d\u0430|\u043d\u0435\s+\u0437\u0430\u043f\u0443\u0441\u043a\u0430\u043b|\u043d\u0435\s+\u043f\u0440\u043e\u0432\u0435\u0440\u044f\u043b|\bnot\s+tested\b|\buntested\b|\bnot\s+verified\s+on\s+a\s+live\b|\bwithout\s+running\b)')
_DOMAIN_ARG_RE = re.compile(r'--domain\s+["\']?([A-Za-z0-9.-]+\.[A-Za-z]{2,})', re.IGNORECASE)
_GUILLEMET_RE = re.compile(r'\u00ab[^\u00bb]*\u00bb')
_MUTATING_SUBCMDS = frozenset({'build-native', 'close', 'configure', 'create', 'edit', 'init', 'install-global', 'journal-sync', 'reconcile-unprepared-delivery', 'register', 'rename-project', 'render-analysis', 'repo-tag', 'repo-tag-retro', 'save-analysis', 'worktree-cleanup', 'worktree-land'})
_PLACEHOLDER_RE = re.compile(r'<[^>\r\n]{1,40}>|\{[a-z_][a-z0-9_-]*\}', re.IGNORECASE)
class CliCommandAuditor:
	# @used-by :func:`agent_tools.cli_command_grounding.unverified_cli_command_issues()`
	# @used-by :meth:`CliCommandAuditor.response_turn_gate_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	def __init__(self, response: str, *, turn: dict[str, Any] | None=None, native: dict[str, Any] | None=None) -> None:
		self.__response = response
		self.__turn = turn
		self.__native = native
	# @used-by :meth:`CliCommandAuditor.audit()`
	def __collect_passing_commands(self) -> list[str]:
		from agent_tools.hook_crash_audit import _load_turn_rows
		rows = _load_turn_rows(self.__native, self.__turn)
		passing: list[str] = []
		bg_cmds: dict[str, str] = {}
		for pos, row in enumerate(rows):
			calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
			outs = dfh_row_outputs(rows, pos) if calls else []
			joined_outs = '\n'.join(outs)
			for c_idx, call in enumerate(calls):
				self.__record_call_outcome(call, outs[c_idx] if c_idx < len(outs) else joined_outs, bg_cmds, passing)
		self.__resolve_bg_completions(rows, bg_cmds, passing)
		return passing
	# @used-by :meth:`CliCommandAuditor.audit()`
	@staticmethod
	def __command_verified(subcmd: str, domain: str | None, passing_cmds: list[str]) -> bool:
		dom = (domain or '').lower()
		r = False
		for cmd in passing_cmds:
			has_dom = (not dom) or (dom in cmd)
			direct = subcmd in cmd and has_dom
			shadow_dom = 'rename-project' == subcmd and 'shadow-replay' in cmd and '--exec-rename-domain' in cmd and has_dom
			shadow_cmd = 'shadow-replay' in cmd and '--command' in cmd and subcmd in cmd and has_dom
			if direct or shadow_dom or shadow_cmd:
				r = True
				break
		return r
	# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
	# @used-by :meth:`CliCommandAuditor.__extract_recommended()`
	@classmethod
	def __desc_line_set(cls, response: str) -> set[int]:
		skip: set[int] = set()
		for node in HeadingTreeParser.iter_all(HeadingTreeParser(response).parse()):
			if 3 >= node.level and _DESC_SUB_RE.match(node.title):
				skip.update(range(node.line_no, node.line_no + cls.__subtree_span(node)))
		return skip
	# @used-by :meth:`CliCommandAuditor.audit()`
	@classmethod
	def __extract_recommended(cls, response: str) -> list[tuple[str, str, str | None]]:
		found: list[tuple[str, str, str | None]] = []
		skip_lines = cls.__desc_line_set(response)
		for line_no, raw in enumerate((response or '').splitlines(), 1):
			stripped = raw.strip()
			if line_no in skip_lines or stripped.startswith('>') or _DIAGNOSTIC_LINE_RE.search(stripped):
				continue
			for m in _CLI_CMD_RE.finditer(_GUILLEMET_RE.sub('', raw)):
				subcmd, rest = (m.group(1).lower(), m.group(2) or '')
				snippet = f'{subcmd} {rest.strip()}'.strip()
				if subcmd in _MUTATING_SUBCMDS and _CONCRETE_TARGET_RE.search(rest) and (not _PLACEHOLDER_RE.search(snippet)):
					m_dom = _DOMAIN_ARG_RE.search(rest)
					found.append((subcmd, snippet[:120], m_dom.group(1).lower() if None is not m_dom else None))
		return found
	# @used-by :meth:`CliCommandAuditor.__collect_passing_commands()`
	@classmethod
	def __record_call_outcome(cls, call: dict[str, Any], matched: str, bg_cmds: dict[str, str], passing: list[str]) -> None:
		from agent_tools.tdd_gate import parse_command_outcome
		cmd = dfh_cmd_from_call(call)
		if cmd:
			out_info = parse_command_outcome(matched)
			if out_info.get('background_task_id'):
				bg_cmds[str(out_info['background_task_id'])] = cmd
			elif cls.is_passing_output(matched):
				passing.append(cmd.lower())
	# @used-by :meth:`CliCommandAuditor.__collect_passing_commands()`
	@classmethod
	def __resolve_bg_completions(cls, rows: list[dict[str, Any]], bg_cmds: dict[str, str], passing: list[str]) -> None:
		from agent_tools.tdd_gate import _BG_TASK_FINISHED_RE
		for row in rows:
			if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
				m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
				if None is not m_fin and m_fin.group(1).strip() in bg_cmds and cls.is_passing_output(m_fin.group(2)):
					passing.append(bg_cmds[m_fin.group(1).strip()].lower())
	# @used-by :meth:`CliCommandAuditor.__desc_line_set()`
	@classmethod
	def __subtree_span(cls, node: HeadingNode) -> int:
		return 1 + len(node.body_lines) + sum((cls.__subtree_span(ch) for ch in node.children))
	# @used-by :func:`agent_tools.cli_command_grounding.unverified_cli_command_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	def audit(self) -> list[str]:
		errs: list[str] = []
		if None is not self.__turn and 'standalone' != self.__turn.get('turn_id') and (not _DISCLAIMER_RE.search(self.__response or '')):
			cmds = self.__extract_recommended(self.__response)
			if cmds:
				passing = self.__collect_passing_commands()
				for subcmd, snippet, domain in cmds:
					if not self.__command_verified(subcmd, domain, passing):
						errs.append(f'EXEC-2 / VERIFY-4: Concrete mutating CLI command `{snippet}` is recommended without a passing live or shadow-replay run in the active turn (verify via shadow-replay or add an explicit untested warning)')
		return errs
	# @used-by :func:`agent_tools.cli_command_grounding._is_passing_output()`
	# @used-by :meth:`CliCommandAuditor.__record_call_outcome()`
	# @used-by :meth:`CliCommandAuditor.__resolve_bg_completions()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	@staticmethod
	def is_passing_output(text: str) -> bool:
		from agent_tools.cli_output_json import top_level_json_has_failure
		from agent_tools.tdd_gate import parse_command_outcome
		out = parse_command_outcome(text)
		return (0 == out.get('exit_code') or ('pass' == out.get('status') and None is out.get('exit_code'))) and (not top_level_json_has_failure(text))
	# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
	# @used-by :func:`agent_tools.cli_command_grounding.response_turn_gate_issues()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.validate()`
	@classmethod
	def response_turn_gate_issues(cls, root: Path, response: str, *, requests: list | tuple=(), turn: dict[str, Any] | None=None, native: dict[str, Any] | None=None, turn_state: dict[str, Any] | None=None, skip_df_analysis: bool=False) -> list[str]:
		from Df.Harness.Grounding.DfAnalysisValidator import DfAnalysisValidator
		from Df.Harness.lib.grounding_md import dfh_markdown_table_issues
		turn_ctx = {'root': root, 'turn': turn, 'turn_state': turn_state, 'native': native}
		df_errs = [] if skip_df_analysis else DfAnalysisValidator(response, requests=requests, mode='auto', turn_context=turn_ctx).validate()
		return [*dfh_markdown_table_issues(response), *df_errs, *cls(response, turn=turn, native=native).audit()]