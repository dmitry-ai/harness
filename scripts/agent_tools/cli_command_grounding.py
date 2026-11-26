# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce verified CLI execution grounding in answer checks and restore EXEC-2 rule":
# https://github.com/dmitry-ai/harness/issues/290
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from .hook_crash_audit import _load_turn_rows
from .platforms.trace_common import parse_tool_args
from .statements import analysis_gate_issues
from .tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
_CLI_CMD_RE = re.compile(r'''(?:harness|upwork_project|df_github_issue)\.py["']?\s+([a-z][a-z0-9-]+)([^\r\n`\u00bb]*)''', re.IGNORECASE)
_CONCRETE_TARGET_RE = re.compile(r'(?:[A-Za-z]:[/\\]|--domain\s+[A-Za-z0-9.-]+\.[A-Za-z]{2,}|--issue\s+\d+)')
_DIAGNOSTIC_LINE_RE = re.compile(r'(?i)(?:exit=[1-9]|exited\s+with\s+code\s+[1-9]|traceback|valueerror|\bfailed\b|\u0443\u043f\u0430\u043b|\u043e\u0442\u043a\u0430\u0437\u0430\u043b)')
_DISCLAIMER_RE = re.compile(r'(?i)(?:\u043d\u0435\s+\u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043e|\u043d\u0435\s+\u0442\u0435\u0441\u0442\u0438\u0440\u043e\u0432\u0430\u043b|\u0431\u0435\u0437\s+\u043f\u0440\u043e\u0433\u043e\u043d\u0430|\u043d\u0435\s+\u0437\u0430\u043f\u0443\u0441\u043a\u0430\u043b|\u043d\u0435\s+\u043f\u0440\u043e\u0432\u0435\u0440\u044f\u043b|\bnot\s+tested\b|\buntested\b|\bnot\s+verified\s+on\s+a\s+live\b|\bwithout\s+running\b)')
_DOMAIN_ARG_RE = re.compile(r'--domain\s+["\']?([A-Za-z0-9.-]+\.[A-Za-z]{2,})', re.IGNORECASE)
_GUILLEMET_RE = re.compile(r'\u00ab[^\u00bb]*\u00bb')
_MUTATING_SUBCMDS = frozenset({'build-native', 'close', 'configure', 'create', 'edit', 'init', 'install-global', 'journal-sync', 'reconcile-unprepared-delivery', 'register', 'rename-project', 'render-analysis', 'repo-tag', 'repo-tag-retro', 'save-analysis', 'worktree-cleanup', 'worktree-land'})
_PLACEHOLDER_RE = re.compile(r'<[^>\r\n]{1,40}>|\{[a-z_][a-z0-9_-]*\}', re.IGNORECASE)
_TOP_NUM_HEAD_RE = re.compile(r'^#\s+(\d+)\b')
# @used-by :func:`_record_call_outcome()`
def _cmd_from_tool_call(call: dict[str, Any]) -> str:
	name = str(call.get('name') or '')
	r = ''
	if 'exec' == name or name.endswith(('run_command', 'exec_command')):
		args = parse_tool_args(call.get('args', call.get('arguments', {})))
		r = str(args.get('CommandLine') or args.get('cmd') or args.get('command') or '')
	return r
# @used-by :func:`_collect_passing_trace_commands()`
def _collect_row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	outs: list[str] = []
	for cand in rows[pos + 1:]:
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type') and cand.get('content'):
			outs.append(str(cand.get('content')))
	return outs
# @used-by :func:`_record_call_outcome()`
# @used-by :func:`_resolve_bg_completions()`
def _is_passing_output(text: str) -> bool:
	out = parse_command_outcome(text)
	low = (text or '').lower()
	has_invalid = '"valid": false' in low or '"valid":false' in low
	return (0 == out.get('exit_code') or ('pass' == out.get('status') and None is out.get('exit_code'))) and (not has_invalid)
# @used-by :func:`_collect_passing_trace_commands()`
def _record_call_outcome(call: dict[str, Any], matched: str, bg_cmds: dict[str, str], passing: list[str]) -> None:
	cmd = _cmd_from_tool_call(call)
	if cmd:
		out_info = parse_command_outcome(matched)
		if out_info.get('background_task_id'):
			bg_cmds[str(out_info['background_task_id'])] = cmd
		elif _is_passing_output(matched):
			passing.append(cmd.lower())
# @used-by :func:`_collect_passing_trace_commands()`
def _resolve_bg_completions(rows: list[dict[str, Any]], bg_cmds: dict[str, str], passing: list[str]) -> None:
	for row in rows:
		if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
			m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
			if None is not m_fin and m_fin.group(1).strip() in bg_cmds and _is_passing_output(m_fin.group(2)):
				passing.append(bg_cmds[m_fin.group(1).strip()].lower())
# @used-by :func:`unverified_cli_command_issues()`
def _collect_passing_trace_commands(turn: dict[str, Any] | None, native: dict[str, Any] | None) -> list[str]:
	rows = _load_turn_rows(native, turn)
	passing: list[str] = []
	bg_cmds: dict[str, str] = {}
	for pos, row in enumerate(rows):
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		outs = _collect_row_outputs(rows, pos) if calls else []
		joined_outs = '\n'.join(outs)
		for c_idx, call in enumerate(calls):
			_record_call_outcome(call, outs[c_idx] if c_idx < len(outs) else joined_outs, bg_cmds, passing)
	_resolve_bg_completions(rows, bg_cmds, passing)
	return passing
# @used-by :func:`unverified_cli_command_issues()`
def _command_verified_in_trace(subcmd: str, domain: str | None, passing_cmds: list[str]) -> bool:
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
# @used-by :func:`unverified_cli_command_issues()`
def _extract_recommended_commands(response: str) -> list[tuple[str, str, str | None]]:
	found: list[tuple[str, str, str | None]] = []
	in_section_one = False
	for raw in (response or '').splitlines():
		stripped = raw.strip()
		m_head = _TOP_NUM_HEAD_RE.match(stripped)
		if None is not m_head:
			in_section_one = '1' == m_head.group(1)
			continue
		if in_section_one or stripped.startswith('>') or _DIAGNOSTIC_LINE_RE.search(stripped):
			continue
		clean = _GUILLEMET_RE.sub('', raw)
		for m in _CLI_CMD_RE.finditer(clean):
			subcmd, rest = (m.group(1).lower(), m.group(2) or '')
			snippet = f'{subcmd} {rest.strip()}'.strip()
			if subcmd in _MUTATING_SUBCMDS and _CONCRETE_TARGET_RE.search(rest) and (not _PLACEHOLDER_RE.search(snippet)):
				m_dom = _DOMAIN_ARG_RE.search(rest)
				found.append((subcmd, snippet[:120], m_dom.group(1).lower() if None is not m_dom else None))
	return found
# 2026-11-26 "Trigger DOC-5 four-track validation from active-turn bug-report signals": https://github.com/dmitry-ai/harness/issues/294
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor.validate()`
# @used-by :mod:`agent_tools.cli_command_grounding`
def response_turn_gate_issues(root: Path, response: str, *, requests: list | tuple=(), turn: dict[str, Any] | None=None, native: dict[str, Any] | None=None) -> list[str]:
	turn_ctx = {'root': root, 'turn': turn, 'native': native}
	return [*analysis_gate_issues(response, requests=requests, turn_context=turn_ctx), *unverified_cli_command_issues(response, turn=turn, native=native)]
# @used-by :func:`response_turn_gate_issues()`
# @used-by :mod:`agent_tools.cli_command_grounding`
def unverified_cli_command_issues(response: str, *, turn: dict[str, Any] | None=None, native: dict[str, Any] | None=None) -> list[str]:
	errs: list[str] = []
	if None is not turn and 'standalone' != turn.get('turn_id') and (not _DISCLAIMER_RE.search(response or '')):
		cmds = _extract_recommended_commands(response)
		if cmds:
			passing = _collect_passing_trace_commands(turn, native)
			for subcmd, snippet, domain in cmds:
				if not _command_verified_in_trace(subcmd, domain, passing):
					errs.append(f'EXEC-2 / VERIFY-4: Concrete mutating CLI command `{snippet}` is recommended without a passing live or shadow-replay run in the active turn (verify via shadow-replay or add an explicit untested warning)')
	return errs
__all__ = ['response_turn_gate_issues', 'unverified_cli_command_issues']