# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_DEFERRAL_BASIS_RE = re.compile(r'(?i)(?:\bA\d+\b|ask_question|clarification|user\s+(?:confirm\w*|approv\w*|consent\w*|instruct\w*|authoriz\w*|choice|decision|answer)|confirm(?:ed|ation)\s+A\d+|blocker|blocked-report|blocked\s+by|\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\w*|\u0441\u043e\u0433\u043b\u0430\u0441\w*|\u0443\u0442\u043e\u0447\u043d\u0435\u043d\w*|\u0432\u044b\u0431\u043e\u0440\w*\s+\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\w*|\u0440\u0435\u0448\u0435\u043d\w*\s+\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\w*|\u043e\u0442\u0432\u0435\u0442\w*\s+\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\w*|\u0431\u043b\u043e\u043a\u0435\u0440\w*|\u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\w*)')
_DEFERRAL_REASON_RE = re.compile(r'(?i)(?:defer(?:red|ral|ring)|postpon(?:ed|ing)|left\s+open\s+(?:because|due\s+to|per|as|since|after)|stopped\s+(?:after|because|due\s+to|per)|reason|rationale|because|due\s+to|blocked\s+(?:by|on)|\u043f\u0435\u0440\u0435\u043d\u0435\u0441\w*|\u043e\u0442\u043b\u043e\u0436\w+|\u043f\u0440\u0438\u0447\u0438\u043d\w*|\u043e\u0441\u043d\u043e\u0432\u0430\u043d\w*|\u043e\u0441\u0442\u0430\u043d\u043e\u0432\w*|\u0438\u0437-\u0437\u0430|\u043f\u043e\u0441\u043a\u043e\u043b\u044c\u043a\u0443|\u0432\u0432\u0438\u0434\u0443|\u0432\s+\u0441\u0432\u044f\u0437\u0438\s+\u0441|\u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\w*)')
_EXPLICIT_STOP_CONSENT_RE = re.compile(r'(?i)(?:stop\s+(?:the|this)\s+turn|end\s+(?:the|this)\s+turn|pause\s+(?:the|this)\s+turn|return\s+control\s+(?:after|before|without)|do\s+not\s+(?:start|execute|implement)\s+[^\n]*in\s+this\s+turn|\u043e\u0441\u0442\u0430\u043d\u043e\u0432(?:\u0438|\u0438\u0442\u044c|\u043b\u044e|\u0438\u043c|\u043a\u0430)\s+(?:\u0442\u0435\u043a\u0443\u0449\w*\s+)?\u0445\u043e\u0434|\u0437\u0430\u0432\u0435\u0440\u0448(?:\u0438|\u0438\u0442\u044c|\u0443|\u0438\u043c)\s+(?:\u0442\u0435\u043a\u0443\u0449\w*\s+)?\u0445\u043e\u0434|\u0432\u0435\u0440\u043d(?:\u0438|\u0443\u0442\u044c|\u0443)\s+\u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438|\u043d\u0435\s+\u0432\u044b\u043f\u043e\u043b\u043d\u044f(?:\u0439|\u0442\u044c|\u044f)\s+[^\n]*\u0432\s+(?:\u044d\u0442\u043e\u043c|\u0442\u0435\u043a\u0443\u0449\u0435\u043c)\s+\u0445\u043e\u0434)')
class ScopeDeferralEvaluator:
	# @used-by :func:`agent_tools.scope_deferral.evaluate_scope_deferral()`
	# @used-by :meth:`ScopeDeferralEvaluator.check_runner()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	def __init__(self, turn: dict[str, Any] | None, turn_state: dict[str, Any] | None, lifecycle_chk: dict[str, Any] | None, response: str | None=None, *, blocked_report: bool=False) -> None:
		self.__turn = turn
		self.__turn_state = turn_state
		self.__lifecycle_chk = lifecycle_chk
		self.__response = response
		self.__blocked_report = blocked_report
	# @used-by :meth:`ScopeDeferralEvaluator.evaluate()`
	# @used-by :meth:`ScopeDeferralEvaluator.find_explicit_stop_consent()`
	@staticmethod
	def __collect_clarifications(turn: dict[str, Any] | None, turn_state: dict[str, Any] | None) -> list[dict[str, Any]]:
		raw = (turn or {}).get('clarifications') or (turn_state or {}).get('clarifications') or ()
		return [item for item in raw if isinstance(item, dict)]
	# @used-by :meth:`ScopeDeferralEvaluator.evaluate()`
	@classmethod
	def __consent_violation_message(cls, urls_str: str, clars: list[dict[str, Any]]) -> str:
		if not clars:
			r = f'SCOPE-2 clarification consent violation: active turn left open deferred child issue(s) ({urls_str}) without --blocked-report or explicit user stop authorization in clarifications'
		else:
			summary = cls.__format_summary(clars)
			r = f'SCOPE-2 clarification consent violation: active turn left open deferred child issue(s) ({urls_str}) while clarifications ({summary}) lack explicit user authorization to stop the turn before completing remaining subtasks'
		return r
	# @used-by :meth:`ScopeDeferralEvaluator.evaluate()`
	@staticmethod
	def __deferred_child_urls(deferred_children: list[dict[str, Any]]) -> list[str]:
		return [str(url) for entry in deferred_children for url in (entry.get('children') or ()) if url]
	# @used-by :meth:`ScopeDeferralEvaluator.__consent_violation_message()`
	@staticmethod
	def __format_summary(clars: list[dict[str, Any]]) -> str:
		parts: list[str] = []
		for item in clars:
			ans_ids = [str(a.get('id') or '').strip() for a in (item.get('answers') or ()) if isinstance(a, dict) and str(a.get('id') or '').strip()]
			step = item.get('answer_step') if None is not item.get('answer_step') else item.get('ask_step')
			label = ', '.join(ans_ids) if ans_ids else 'raw_output'
			parts.append(f'step {step}: {label}' if None is not step else label)
		return '; '.join(parts)
	# @used-by :meth:`ScopeDeferralEvaluator.evaluate()`
	@staticmethod
	def __has_disclosure(response: str | None) -> bool:
		text = str(response or '')
		return bool(text and _DEFERRAL_REASON_RE.search(text) and _DEFERRAL_BASIS_RE.search(text))
	# @used-by :meth:`ScopeDeferralEvaluator.find_explicit_stop_consent()`
	@staticmethod
	def __iter_answers(clars: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str, str]]:
		rows: list[tuple[dict[str, Any], str, str]] = []
		for item in clars:
			answers = [a for a in (item.get('answers') or ()) if isinstance(a, dict)]
			if answers:
				for ans in answers:
					rows.append((item, str(ans.get('id') or 'A1').strip() or 'A1', str(ans.get('text') or '')))
			elif str(item.get('raw_output') or '').strip():
				rows.append((item, 'A1', str(item.get('raw_output') or '')))
		return rows
	# @used-by :func:`agent_tools.scope_deferral.check_runner_scope_deferral()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	@classmethod
	def check_runner(cls, runner, lifecycle_chk: dict[str, Any]) -> None:
		chk = cls(runner.turn, runner.value, lifecycle_chk, runner.response, blocked_report=bool(runner.blocked_report)).evaluate()
		runner.value['scope_deferral_check'] = chk
		if not chk['verified']:
			runner._fail_gate('scope_deferral', '; '.join(chk['violations']))
	# @used-by :func:`agent_tools.scope_deferral.evaluate_scope_deferral()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	def evaluate(self) -> dict[str, Any]:
		deferred = [d for d in ((self.__lifecycle_chk or {}).get('deferred_children') or ()) if isinstance(d, dict)]
		violations: list[str] = []
		consent = self.find_explicit_stop_consent(self.__turn, self.__turn_state) if deferred else None
		if deferred:
			urls_str = ', '.join(self.__deferred_child_urls(deferred))
			if (not self.__blocked_report) and None is consent:
				violations.append(self.__consent_violation_message(urls_str, self.__collect_clarifications(self.__turn, self.__turn_state)))
			if None is not self.__response and (not self.__has_disclosure(self.__response)):
				violations.append(f'SCOPE-2 deferral disclosure violation: response leaves open deferred child issue(s) ({urls_str}) without explicitly stating the deferral rationale and citing user confirmation or blocker')
		return {'verified': not violations, 'deferred_children': deferred, 'stop_consent': consent, 'violations': violations}
	# @used-by :func:`agent_tools.scope_deferral.find_explicit_stop_consent()`
	# @used-by :meth:`Df.Harness.Issue.ScopeCompletenessChecker.ScopeCompletenessChecker.check()`
	# @used-by :meth:`ScopeDeferralEvaluator.evaluate()`
	@classmethod
	def find_explicit_stop_consent(cls, turn: dict[str, Any] | None, turn_state: dict[str, Any] | None=None) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		for item, ans_id, ans_text in cls.__iter_answers(cls.__collect_clarifications(turn, turn_state)):
			if _EXPLICIT_STOP_CONSENT_RE.search(ans_text):
				r = {'authorized': True, 'answer_id': ans_id, 'ask_step': item.get('ask_step'), 'answer_step': item.get('answer_step'), 'text': ans_text.strip()}
				break
		return r
