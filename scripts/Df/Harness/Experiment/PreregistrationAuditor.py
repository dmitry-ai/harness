# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Experiment.PlanLoader import PlanLoader
from agent_tools.research import inside
from agent_tools.storage import iter_embedded_json_objects
import json
import re
CLI_NAMES = ('harness.py', 'upwork_project.py')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PreregistrationAuditor:
	# @used-by :meth:`Df.Harness.Experiment.PlanStore.PlanStore.preregistration_issues()`
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def __init__(self, root, run: dict, events=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__run = run
		self.__events = events
	# @used-by :meth:`PreregistrationAuditor.__check_timing()`
	@staticmethod
	def __after_plan(value, prepared_at: str) -> bool:
		try:
			observed = datetime.fromisoformat(value.replace('Z', '+00:00'))
			prepared = datetime.fromisoformat(prepared_at)
			r = None is not observed.tzinfo and observed > prepared
		except (ValueError, TypeError, AttributeError):
			r = False
		return r
	# @used-by :meth:`PreregistrationAuditor.issues()`
	def __check_conditions(self, plan: dict, issues: list[str]) -> None:
		expected = plan['requirement']['conditions']
		actual = self.__run.get('conditions', {})
		for key in ('url_country', 'language', 'selected_country', 'currency', 'session_id'):
			if key in expected and actual.get(key) != expected[key]:
				issues.append('Actual experimental condition differs from preregistered ' + key)
		for key, field in (('session', 'mode'), ('egress', 'country')):
			val = expected.get(key, {}).get(field) if isinstance(expected.get(key), dict) else None
			if val not in (None, 'unknown') and actual.get(key, {}).get(field) != val:
				issues.append('Actual experimental condition differs from preregistered ' + key + '.' + field)
	# @used-by :meth:`PreregistrationAuditor.issues()`
	def __check_timing(self, plan: dict, issues: list[str]) -> None:
		observed = [item.get('observed_at') for item in self.__run.get('artifacts', []) if item.get('source_observation')]
		ev_list = list(self.__events) if None is not self.__events else self.__run.get('native_trace', {}).get('events', [])
		commits = [ev for ev in ev_list if self.__is_plan_commit(ev)]
		actions = [ev for ev in ev_list if ev not in commits]
		observed += [ev.get('created_at') for ev in actions]
		if not observed or any((not self.__after_plan(value, plan['prepared_at']) for value in observed)):
			issues.append('Verified/refuted run requires fresh timestamped observations/actions after this exact plan; saved data cannot masquerade as a newly performed test')
		if self.__run['requirement']['method'] in ('browser_scenario', 'admin', 'serp'):
			if not commits or not actions or (not any((c.get('output_step', -1) < min((e.get('step', -1) for e in actions)) for c in commits))):
				issues.append('Native plan commitment receipt must precede the actual native observations/actions; a backdated file alone is not preregistration')
	# @used-by :meth:`PreregistrationAuditor.__check_timing()`
	def __is_plan_commit(self, event: dict) -> bool:
		if True is not event.get('successful'):
			r = False
		else:
			args = json.dumps(event.get('arguments'), ensure_ascii=False)
			if not re.search('\\bprepare-experiment\\b', args) or not any((cli in args for cli in CLI_NAMES)):
				r = False
			else:
				from agent_tools.path_registry import same_project_root
				r = any((1 == rec.get('upwork_experiment_plan') and same_project_root(rec.get('project_root'), self.__pp.root) and (rec.get('plan') == self.__run.get('plan')) and (rec.get('plan_sha256') == self.__run.get('plan_sha256')) and (rec.get('requirement_sha256') == self.__run.get('requirement_sha256')) for rec in iter_embedded_json_objects(event.get('result'))))
		return r
	# @used-by :meth:`PreregistrationAuditor.issues()`
	def __load_plan(self) -> tuple[dict | None, list[str] | None]:
		plan, early = (None, None)
		try:
			plan = PlanLoader(self.__pp.root, self.__run['plan']).load_plan()
			path = inside(self.__pp.kb_dir, self.__run['plan'])
			if df_sha256(path.read_bytes()) != self.__run.get('plan_sha256'):
				early = ['Run does not bind the exact immutable plan hash']
			elif plan['requirement_sha256'] != self.__run.get('requirement_sha256'):
				early = ['Run changed the preregistered statement, test, expected or falsifying outcomes']
		except (OSError, KeyError, ValueError, TypeError):
			early = ['Run needs a valid immutable plan committed before observations']
		return (plan, early)
	# @used-by :meth:`Df.Harness.Experiment.PlanStore.PlanStore.preregistration_issues()`
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def issues(self) -> list[str]:
		plan, early = self.__load_plan()
		if None is not early:
			r = early
		elif self.__run.get('status') not in ('verified', 'refuted'):
			r = []
		else:
			r = []
			self.__check_timing(plan, r)
			self.__check_conditions(plan, r)
		return r
