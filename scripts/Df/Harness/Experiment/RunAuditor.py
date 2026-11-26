# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.BrowserStepAuditor import BrowserStepAuditor
from Df.Harness.Experiment.CallChainParser import CallChainParser
from Df.Harness.Experiment.ConditionAuditor import ConditionAuditor
from Df.Harness.Experiment.RequirementValidator import RequirementValidator, STATUSES
from Df.Harness.Experiment.TraceContextAuditor import TraceContextAuditor
from Df.Qa.lib.validation.check_strict import df_is_sne
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RunAuditor:
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.run_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def __init__(self, run: dict, artifacts: dict, events: dict, native_texts_fn) -> None:
		self.__run = run
		self.__artifacts = artifacts
		self.__events = events
		self.__native_texts = native_texts_fn
	# @used-by :meth:`RunAuditor.__check_method()`
	def __check_admin(self) -> list[str]:
		r: list[str] = []
		conditions = self.__run.get('conditions', {})
		if not df_is_sne(conditions.get('admin_url')) or not df_is_sne(conditions.get('admin_object')):
			r.append('Admin observation needs exact authenticated setting URL and object scope')
		admin_url = conditions.get('admin_url', '')
		if not any((CallChainParser.event_actions(ev) & {'read', 'inspect'} and admin_url in json.dumps(ev.get('result'), ensure_ascii=False) for ev in self.__events.values())):
			r.append('Admin observation needs native browser inspection; public documentation is not store configuration')
		return r
	# @used-by :meth:`RunAuditor.issues()`
	def __check_header(self) -> list[str]:
		r = RequirementValidator([self.__run.get('requirement')]).issues()
		if 1 != self.__run.get('schema_version') or 'experiment' != self.__run.get('kind') or self.__run.get('status') not in STATUSES:
			r.append('Unknown experimental run schema/status')
		if not df_is_sne(self.__run.get('actual_result')):
			r.append('Actual result required; executable planned code is not a performed result')
		if self.__run.get('status') in ('unverified', 'unavailable') and (not df_is_sne(self.__run.get('limitation'))):
			r.append('Unverified/unavailable run needs an explicit limitation')
		if not isinstance(self.__run.get('actual_steps'), list):
			r.append('Actual performed steps must be a list')
		return r
	# @used-by :meth:`RunAuditor.issues()`
	def __check_method(self, method: str) -> list[str]:
		if method in ('http', 'dom'):
			r = [] if any((item.get('observation_kind') == method for item in self.__artifacts.values())) else ['HTTP/DOM run requires a hash-checked collector observation of that actual kind']
		elif 'geolocation' == method:
			r = ['Geolocation run needs a verified IP-country measurement'] if 'verified' != self.__run.get('conditions', {}).get('egress', {}).get('verification') else []
		elif 'admin' == method:
			r = self.__check_admin()
		elif 'serp' == method:
			r = self.__check_serp()
		elif 'browser_scenario' == method:
			r = BrowserStepAuditor(self.__run, self.__artifacts, self.__events, self.__native_texts).issues()
		else:
			r = []
		return r
	# @used-by :meth:`RunAuditor.__check_method()`
	def __check_serp(self) -> list[str]:
		r: list[str] = []
		search = self.__run.get('conditions', {}).get('search', {})
		if not isinstance(search, dict) or not all((df_is_sne(search.get(k)) for k in ('query', 'language', 'country'))):
			r.append('SERP run needs exact query, search language and country conditions')
		if not any((CallChainParser.event_actions(ev) & {'read', 'inspect'} or (ev.get('name', '').casefold().split('.')[-1].split('__')[-1] in ('search_web', 'search_query', 'run') and ('search_query' in ev.get('arguments', {}) or 'query' in ev.get('arguments', {}))) for ev in self.__events.values() if True is ev.get('successful'))):
			r.append('SERP run needs a recorded successful native search/browser result')
		return r
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.run_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def issues(self) -> list[str]:
		r = self.__check_header()
		if not r:
			r += ConditionAuditor(self.__run, self.__artifacts, self.__native_texts).issues()
			if len(self.__artifacts) != len(self.__run.get('artifacts', [])):
				r.append('Primary artifact IDs must be unique')
			if self.__run['status'] not in ('unverified', 'unavailable'):
				r += TraceContextAuditor(self.__run, self.__events, self.__native_texts).issues()
				if not self.__artifacts:
					r.append('A verified/refuted result needs recorded primary evidence')
				r += self.__check_method(self.__run['requirement']['method'])
		return r
