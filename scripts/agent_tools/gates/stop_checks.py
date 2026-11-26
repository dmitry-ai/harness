# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# @used-by :mod:`agent_tools.gates.stop_checks`
def _check_code_lifecycle(state: dict) -> dict | None:
	clc = state.get('code_lifecycle_check') if isinstance(state.get('code_lifecycle_check'), dict) else {}
	if False is not clc.get('verified'):
		r = None
	else:
		detail = '; '.join((str(v) for v in (clc.get('violations') or ()))) or 'code/issue or similar_projects parity lifecycle incomplete'
		r = {'decision': 'continue', 'reason': f'EXEC-5 Stop Gate: {detail}. Resolve pending code/issue or similar_projects parity checks and re-run harness.py answer-prepare.'}
	return r
# @used-by :mod:`agent_tools.gates.stop_checks`
def _check_issue_first(state: dict) -> dict | None:
	ifc = state.get('issue_first_check') if isinstance(state.get('issue_first_check'), dict) else {}
	if False is not ifc.get('verified'):
		r = None
	else:
		detail = '; '.join((str(v) for v in (ifc.get('violations') or ()))) or 'Issue-First verification failed (parent GitHub issue required before tests and code)'
		r = {'decision': 'continue', 'reason': f'EXEC-5 Stop Gate (ISSUE-FIRST): {detail}. Establish a parent GitHub issue via df_github_issue.py before tests/code and re-run harness.py answer-prepare.'}
	return r
# @used-by :mod:`agent_tools.gates.stop_checks`
def _check_prepared(state: dict) -> dict | None:
	prep = state.get('prepared')
	if state.get('status') in ('prepared', 'delivered') and isinstance(prep, dict) and state.get('readiness_check', {}).get('verified'):
		r = None
	else:
		detail = (state.get('readiness_check') or {}).get('detail') or 'answer-prepare has not succeeded for the current turn'
		r = {'decision': 'continue', 'reason': f'FILE-3 / EXEC-5 Stop Gate: Turn is not prepared ({detail}). Run harness.py answer-prepare and output the exact prepared response.'}
	return r
# @used-by :mod:`agent_tools.gates.stop_checks`
def _check_tdd(state: dict) -> dict | None:
	tddc = state.get('tdd_check') if isinstance(state.get('tdd_check'), dict) else {}
	if False is not tddc.get('verified'):
		r = None
	else:
		detail = '; '.join((str(v) for v in (tddc.get('violations') or ()))) or 'TDD Red-First / Full-Suite-Green verification failed'
		r = {'decision': 'continue', 'reason': f'EXEC-2 Stop Gate: {detail}. Resolve TDD violations, run the full test suite to GREEN, and re-run harness.py answer-prepare.'}
	return r
STOP_GATES = (
	(10, 'prepared', _check_prepared),
	(20, 'issue_first', _check_issue_first),
	(30, 'code_lifecycle', _check_code_lifecycle),
	(40, 'tdd', _check_tdd),
)
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
# @used-by :func:`check_stop_gate.evaluate_stop_payload()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_stop_gates_evaluate_in_priority_order()`
# @used-by :mod:`agent_tools.gates`
def run_stop_gates(state: dict) -> dict | None:
	r = None
	for _, _, fn in sorted(STOP_GATES, key=lambda item: item[0]):
		hit = fn(state)
		if None is not hit:
			r = hit
			break
	return r
