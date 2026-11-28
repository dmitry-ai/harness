# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Grounding.DfAnalysisValidator import DfAnalysisValidator
from Df.Harness.Grounding.HeadingTreeParser import HeadingTreeParser
from Df.Harness.Grounding.MixedTurnProblemSchema import MixedTurnProblemSchema
from Df.Harness.Grounding.StandaloneProblemSchema import StandaloneProblemSchema
# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
# @used-by :func:`Df.Harness.lib.blocked_report_ops._run_runner_audits()`
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__problem_report_messages()`
class ProblemReportEvaluator:
	# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
	# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__problem_report_messages()`
	# @used-by :meth:`ProblemReportEvaluator.check_runner()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_report_evaluator_answer_gates_preparer_and_stop_gate_pipeline()`
	def __init__(self, root: Path | None, turn: dict[str, Any] | None, turn_state: dict[str, Any] | None, response: str | None, *, requests: list | tuple=(), native: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__turn = turn
		self.__turn_state = turn_state
		self.__response = response or ''
		self.__requests = requests
		self.__native = native
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._run_runner_audits()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_report_evaluator_answer_gates_preparer_and_stop_gate_pipeline()`
	@staticmethod
	def check_runner(runner: Any) -> None:
		reqs = (runner.turn or {}).get('requests') or () if isinstance(getattr(runner, 'turn', None), dict) else ()
		chk = ProblemReportEvaluator(runner.root, runner.turn, runner.value, runner.response, requests=reqs, native=getattr(runner, 'native', None)).evaluate()
		runner.value['problem_report_check'] = chk
		if not chk['verified']:
			runner._fail_gate('problem_report', '; '.join(chk['violations']))
	# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
	# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__problem_report_messages()`
	# @used-by :meth:`ProblemReportEvaluator.check_runner()`
	# @used-by :meth:`test_problem_report_governance.ProblemReportGovernanceTests.test_problem_report_evaluator_answer_gates_preparer_and_stop_gate_pipeline()`
	def evaluate(self) -> dict[str, Any]:
		turn_ctx = {'root': self.__root, 'turn': self.__turn, 'turn_state': self.__turn_state, 'native': self.__native}
		violations = DfAnalysisValidator(self.__response, requests=self.__requests, mode='auto', turn_context=turn_ctx).validate()
		return {'verified': not violations, 'violations': violations}
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_response_documents_hook_crash_structured()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__is_diag_audit()`
	@staticmethod
	def has_problem_sections(text: str) -> bool:
		roots = HeadingTreeParser(text or '').parse()
		return MixedTurnProblemSchema.has_mixed_sections(roots) or StandaloneProblemSchema.has_any_problem_block(roots)
