# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.CallChainParser import CallChainParser
from agent_tools.research import request_context
import json
import re
CONTEXT_FIELDS = {'session', 'egress', 'url_country', 'language', 'selected_country', 'currency', 'session_id', 'state_fingerprint'}
MODE_PATTERNS = {'incognito': '"(?:incognito|isIncognito)"\\s*:\\s*true', 'normal': '"(?:incognito|isIncognito)"\\s*:\\s*false', 'isolated': '"isolated"\\s*:\\s*true'}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ConditionAuditor:
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def __init__(self, run: dict, artifacts: dict, native_texts_fn) -> None:
		self.__run = run
		self.__artifacts = artifacts
		self.__native_texts = native_texts_fn
	# @used-by :meth:`ConditionAuditor.issues()`
	def __check_egress(self, conditions: dict, issues: list[str]) -> None:
		egress = conditions.get('egress', {})
		if isinstance(egress, dict) and 'verified' == egress.get('verification'):
			ids = egress.get('evidence', [])
			issues += self.evidence_issues(ids, self.__artifacts, 'Verified IP country')
			candidates = [self.__artifacts.get(ident, {}) for ident in ids]
			if not any(('geolocation' == item.get('role') and True is item.get('geolocation_verified') and (item.get('country') == egress.get('country')) for item in candidates)):
				issues.append('IP country needs a saved same-transport geolocation measurement, not a regional URL or language')
			if self.__run['requirement']['method'] in ('browser_scenario', 'admin', 'serp') and any(('native-browser' != item.get('transport') for item in candidates)):
				issues.append('Browser IP geography must be measured in that native browser transport; a Python HTTP client can have different proxy/egress')
	# @used-by :meth:`ConditionAuditor.issues()`
	def __check_session(self, conditions: dict, issues: list[str]) -> None:
		session = conditions.get('session', {})
		if isinstance(session, dict) and 'verified' == session.get('verification'):
			ids = session.get('evidence', [])
			issues += self.evidence_issues(ids, self.__artifacts, 'Verified browser mode')
			events = [ev for ev in self.__native_texts(ids) if 'inspect' in CallChainParser.event_actions(ev)]
			texts = '\n'.join((json.dumps(ev.get('result'), ensure_ascii=False) for ev in events))
			pattern = MODE_PATTERNS.get(session.get('mode'))
			if not pattern or not re.search(pattern, texts.replace('\\"', '"')):
				issues.append('Browser mode needs native browser context inspection; no cookies does not prove Incognito')
	# @used-by :meth:`ConditionAuditor.__check_egress()`
	# @used-by :meth:`ConditionAuditor.__check_session()`
	# @used-by :meth:`Df.Harness.Experiment.BrowserStepAuditor.BrowserStepAuditor.__check_phase()`
	# @used-by :meth:`Df.Harness.Experiment.BrowserStepAuditor.BrowserStepAuditor.__check_step()`
	@staticmethod
	def evidence_issues(ids, artifacts: dict, label: str) -> list[str]:
		return [label + ': recorded primary artifact IDs required'] if not isinstance(ids, list) or not ids or any((not isinstance(x, str) or x not in artifacts for x in ids)) else []
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def issues(self) -> list[str]:
		conditions = self.__run.get('conditions', {})
		if not isinstance(conditions, dict):
			r = ['Experimental conditions must be an object']
		else:
			r = []
			try:
				request_context({key: value for key, value in conditions.items() if key in CONTEXT_FIELDS})
			except (ValueError, TypeError):
				r.append('Invalid session/egress conditions')
			self.__check_session(conditions, r)
			self.__check_egress(conditions, r)
		return r
