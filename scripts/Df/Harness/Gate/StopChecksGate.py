# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class StopChecksGate:
	# @used-by :meth:`StopChecksGate.run()`
	@staticmethod
	def __check_arch_audit(state: dict) -> dict | None:
		aac = state.get('arch_audit_check') if isinstance(state.get('arch_audit_check'), dict) else {}
		if False is not aac.get('verified'):
			r = None
		else:
			detail = '; '.join((str(v) for v in (aac.get('violations') or ()))) or 'ARCH-1 / ARCH-2 architecture pattern specification or arch-auditor verification failed'
			r = {'decision': 'continue', 'reason': f'ARCH-AUDIT Stop Gate: {detail}. Resolve architecture specification or arch-auditor findings and re-run harness.py answer-prepare.'}
		return r
	# @used-by :meth:`StopChecksGate.run()`
	@staticmethod
	def __check_code_lifecycle(state: dict) -> dict | None:
		clc = state.get('code_lifecycle_check') if isinstance(state.get('code_lifecycle_check'), dict) else {}
		if False is not clc.get('verified'):
			r = None
		else:
			detail = '; '.join((str(v) for v in (clc.get('violations') or ()))) or 'code/issue or similar_projects parity lifecycle incomplete'
			r = {'decision': 'continue', 'reason': f'EXEC-5 Stop Gate: {detail}. Resolve pending code/issue or similar_projects parity checks and re-run harness.py answer-prepare.'}
		return r
	# @used-by :meth:`StopChecksGate.run()`
	@staticmethod
	def __check_issue_first(state: dict) -> dict | None:
		ifc = state.get('issue_first_check') if isinstance(state.get('issue_first_check'), dict) else {}
		if False is not ifc.get('verified'):
			r = None
		else:
			detail = '; '.join((str(v) for v in (ifc.get('violations') or ()))) or 'Issue-First verification failed (parent GitHub issue required before tests and code)'
			r = {'decision': 'continue', 'reason': f'EXEC-5 Stop Gate (ISSUE-FIRST): {detail}. Establish a parent GitHub issue via df_github_issue.py before tests/code and re-run harness.py answer-prepare.'}
		return r
	# @used-by :meth:`StopChecksGate.run()`
	@staticmethod
	def __check_prepared(state: dict) -> dict | None:
		prep = state.get('prepared')
		if state.get('status') in ('prepared', 'delivered') and isinstance(prep, dict) and state.get('readiness_check', {}).get('verified'):
			r = None
		else:
			detail = (state.get('readiness_check') or {}).get('detail') or 'answer-prepare has not succeeded for the current turn'
			r = {'decision': 'continue', 'reason': f'FILE-3 / EXEC-5 Stop Gate: Turn is not prepared ({detail}). Run harness.py answer-prepare and output the exact prepared response.'}
		return r
	# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
	# @used-by :meth:`StopChecksGate.run()`
	@staticmethod
	def __check_problem_report(state: dict) -> dict | None:
		prc = state.get('problem_report_check') if isinstance(state.get('problem_report_check'), dict) else {}
		if False is not prc.get('verified'):
			r = None
		else:
			detail = '; '.join((str(v) for v in (prc.get('violations') or ()))) or 'DOC-5 problem report hierarchy or GitHub issue validity check failed'
			r = {'decision': 'continue', 'reason': f'PROBLEM-REPORT Stop Gate: {detail}. Resolve DOC-5 structure or open parent GitHub issue errors and re-run harness.py answer-prepare.'}
		return r
	# @used-by :meth:`StopChecksGate.run()`
	@staticmethod
	def __check_tdd(state: dict) -> dict | None:
		tddc = state.get('tdd_check') if isinstance(state.get('tdd_check'), dict) else {}
		if False is not tddc.get('verified'):
			r = None
		else:
			detail = '; '.join((str(v) for v in (tddc.get('violations') or ()))) or 'TDD Red-First / Full-Suite-Green verification failed'
			r = {'decision': 'continue', 'reason': f'EXEC-2 Stop Gate: {detail}. Resolve TDD violations, run the full test suite to GREEN, and re-run harness.py answer-prepare.'}
		return r
	STOP_GATES = (
		(10, 'prepared', __check_prepared),
		(20, 'issue_first', __check_issue_first),
		(30, 'code_lifecycle', __check_code_lifecycle),
		(35, 'arch_audit', __check_arch_audit),
		(37, 'problem_report', __check_problem_report),
		(40, 'tdd', __check_tdd),
	)
	# @used-by :func:`agent_tools.gates.stop_checks.run_stop_gates()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_v4_arch_audit_and_pipeline_parity()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_report_evaluator_answer_gates_preparer_and_stop_gate_pipeline()`
	# @uses :meth:`Df.Harness.Gate.StopChecksGate.StopChecksGate.__check_arch_audit()`
	# @uses :meth:`Df.Harness.Gate.StopChecksGate.StopChecksGate.__check_code_lifecycle()`
	# @uses :meth:`Df.Harness.Gate.StopChecksGate.StopChecksGate.__check_issue_first()`
	# @uses :meth:`Df.Harness.Gate.StopChecksGate.StopChecksGate.__check_prepared()`
	# @uses :meth:`Df.Harness.Gate.StopChecksGate.StopChecksGate.__check_problem_report()`
	# @uses :meth:`Df.Harness.Gate.StopChecksGate.StopChecksGate.__check_tdd()`
	def run(self, state: dict) -> dict | None:
		r = None
		for _, _, fn in sorted(StopChecksGate.STOP_GATES, key=lambda item: item[0]):
			hit = fn(state)
			if None is not hit:
				r = hit
				break
		return r
