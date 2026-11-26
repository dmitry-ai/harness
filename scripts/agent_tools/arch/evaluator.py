# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
from pathlib import Path
from typing import Any
from .spec import validate_arch_spec_markdown
from .triggers import classify_markdown_arch_trigger
# @used-by :func:`agent_tools.blocked_report._run_runner_audits()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_runner_architecture_check_records_state_and_fails_gate_on_missing_patterns()`
# @used-by :mod:`agent_tools.arch.evaluator`
# @used-by :mod:`agent_tools.arch`
def check_runner_architecture(runner) -> None:
	chk = evaluate_response_architecture(runner.root, runner.turn, runner.response, blocked_report=bool(getattr(runner, 'blocked_report', False)))
	runner.value['arch_audit_check'] = chk
	if not chk['verified']:
		runner._fail_gate('architecture', '; '.join(chk['violations']))
# @used-by :func:`agent_tools.gates.answer_checks._architecture_messages()`
# @used-by :func:`check_runner_architecture()`
# @used-by :mod:`agent_tools.arch.evaluator`
# @used-by :mod:`agent_tools.arch`
def evaluate_response_architecture(root: Path | None, turn: dict[str, Any] | None, response: str | None, *, blocked_report: bool=False) -> dict[str, Any]:
	trig = classify_markdown_arch_trigger(response or '', is_issue=False, is_parent_issue=False)
	if blocked_report or (not trig['triggered']):
		r: dict[str, Any] = {'verified': True, 'triggered': False, 'significant': False, 'reasons': [], 'patterns': [], 'violations': []}
	else:
		spec_res = validate_arch_spec_markdown(response or '', require_full_fields=False)
		violations = [f"ARCH-1 ({it['code']}): {it['message']}" for it in spec_res['issues']]
		r = {'verified': not violations, 'triggered': True, 'significant': bool(trig['significant']), 'reasons': list(trig['reasons']), 'patterns': list(spec_res['patterns']), 'violations': violations}
	return r
__all__ = ['check_runner_architecture', 'evaluate_response_architecture']