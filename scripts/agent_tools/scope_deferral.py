# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Verify explicit user stop consent in clarifications during answer checks":
# https://github.com/dmitry-ai/harness/issues/375
from __future__ import annotations
from typing import Any
import re
_EXPLICIT_STOP_CONSENT_RE = re.compile(r'(?i)(?:stop\s+(?:the|this)\s+turn|end\s+(?:the|this)\s+turn|pause\s+(?:the|this)\s+turn|return\s+control\s+(?:after|before|without)|do\s+not\s+(?:start|execute|implement)\s+[^\n]*in\s+this\s+turn|\u043e\u0441\u0442\u0430\u043d\u043e\u0432(?:\u0438|\u0438\u0442\u044c|\u043b\u044e|\u0438\u043c|\u043a\u0430)\s+(?:\u0442\u0435\u043a\u0443\u0449\w*\s+)?\u0445\u043e\u0434|\u0437\u0430\u0432\u0435\u0440\u0448(?:\u0438|\u0438\u0442\u044c|\u0443|\u0438\u043c)\s+(?:\u0442\u0435\u043a\u0443\u0449\w*\s+)?\u0445\u043e\u0434|\u0432\u0435\u0440\u043d(?:\u0438|\u0443\u0442\u044c|\u0443)\s+\u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438|\u043d\u0435\s+\u0432\u044b\u043f\u043e\u043b\u043d\u044f(?:\u0439|\u0442\u044c|\u044f)\s+[^\n]*\u0432\s+(?:\u044d\u0442\u043e\u043c|\u0442\u0435\u043a\u0443\u0449\u0435\u043c)\s+\u0445\u043e\u0434)')
# @used-by :func:`evaluate_scope_deferral()`
# @used-by :func:`find_explicit_stop_consent()`
def _collect_clarifications(turn: dict[str, Any] | None, turn_state: dict[str, Any] | None) -> list[dict[str, Any]]:
	raw = (turn or {}).get('clarifications') or (turn_state or {}).get('clarifications') or ()
	return [item for item in raw if isinstance(item, dict)]
# @used-by :func:`evaluate_scope_deferral()`
def _deferred_child_urls(deferred_children: list[dict[str, Any]]) -> list[str]:
	return [str(url) for entry in deferred_children for url in (entry.get('children') or ()) if url]
# @used-by :func:`evaluate_scope_deferral()`
def _format_clarification_summary(clars: list[dict[str, Any]]) -> str:
	parts: list[str] = []
	for item in clars:
		ans_ids = [str(a.get('id') or '').strip() for a in (item.get('answers') or ()) if isinstance(a, dict) and str(a.get('id') or '').strip()]
		step = item.get('answer_step') if None is not item.get('answer_step') else item.get('ask_step')
		label = ', '.join(ans_ids) if ans_ids else 'raw_output'
		parts.append(f'step {step}: {label}' if None is not step else label)
	return '; '.join(parts)
# @used-by :func:`find_explicit_stop_consent()`
def _iter_clarification_answers(clars: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str, str]]:
	rows: list[tuple[dict[str, Any], str, str]] = []
	for item in clars:
		answers = [a for a in (item.get('answers') or ()) if isinstance(a, dict)]
		if answers:
			for ans in answers:
				rows.append((item, str(ans.get('id') or 'A1').strip() or 'A1', str(ans.get('text') or '')))
		elif str(item.get('raw_output') or '').strip():
			rows.append((item, 'A1', str(item.get('raw_output') or '')))
	return rows
# @used-by :func:`agent_tools.blocked_report.evaluate_runner_code_hygiene()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_runner_scope_deferral_and_raw_output_fallback()`
def check_runner_scope_deferral(runner, lifecycle_chk: dict[str, Any]) -> None:
	chk = evaluate_scope_deferral(runner.turn, runner.value, lifecycle_chk, runner.response, blocked_report=bool(runner.blocked_report))
	runner.value['scope_deferral_check'] = chk
	if not chk['verified']:
		runner._fail_gate('scope_deferral', '; '.join(chk['violations']))
# @used-by :func:`agent_tools.gates.answer_checks._scope_deferral_messages()`
# @used-by :func:`check_runner_scope_deferral()`
def evaluate_scope_deferral(turn: dict[str, Any] | None, turn_state: dict[str, Any] | None, lifecycle_chk: dict[str, Any] | None, response: str | None=None, *, blocked_report: bool=False) -> dict[str, Any]:
	deferred = [d for d in ((lifecycle_chk or {}).get('deferred_children') or ()) if isinstance(d, dict)]
	violations: list[str] = []
	consent = find_explicit_stop_consent(turn, turn_state) if deferred else None
	if deferred and (not blocked_report) and None is consent:
		urls_str = ', '.join(_deferred_child_urls(deferred))
		clars = _collect_clarifications(turn, turn_state)
		if clars:
			summary = _format_clarification_summary(clars)
			violations.append(f'SCOPE-2 clarification consent violation: active turn left open deferred child issue(s) ({urls_str}) while clarifications ({summary}) lack explicit user authorization to stop the turn before completing remaining subtasks')
		else:
			violations.append(f'SCOPE-2 clarification consent violation: active turn left open deferred child issue(s) ({urls_str}) without --blocked-report or explicit user stop authorization in clarifications')
	return {'verified': not violations, 'deferred_children': deferred, 'stop_consent': consent, 'violations': violations}
# @used-by :func:`agent_tools.issues.scope_completeness.flag_parent_and_deferred_children()`
# @used-by :func:`evaluate_scope_deferral()`
def find_explicit_stop_consent(turn: dict[str, Any] | None, turn_state: dict[str, Any] | None=None) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	for item, ans_id, ans_text in _iter_clarification_answers(_collect_clarifications(turn, turn_state)):
		if _EXPLICIT_STOP_CONSENT_RE.search(ans_text):
			r = {'authorized': True, 'answer_id': ans_id, 'ask_step': item.get('ask_step'), 'answer_step': item.get('answer_step'), 'text': ans_text.strip()}
			break
	return r
