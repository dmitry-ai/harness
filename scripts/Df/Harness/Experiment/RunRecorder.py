# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Experiment.ArtifactIngestor import ArtifactIngestor
from Df.Harness.Experiment.AssertionEvaluator import AssertionEvaluator
from Df.Harness.Experiment.CapabilityResolver import CapabilityResolver
from Df.Harness.Experiment.PlanLoader import PlanLoader
from Df.Harness.Experiment.PreregistrationAuditor import PreregistrationAuditor
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
from Df.Harness.Experiment.RunAuditor import RunAuditor
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import json_data
from agent_tools.storage import create_bytes
import json
_OWNED_KEYS = ('capabilities', 'recorded_at', 'requirement_sha256', 'evaluation')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RunRecorder:
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.record()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def __init__(self, root, specification, *, tool_trace=None) -> None:
		self.__root = root
		self.__spec = specification
		self.__tool_trace = tool_trace
	# @used-by :meth:`RunRecorder.record_run()`
	@staticmethod
	def __audit_run(pp, run: dict, contents: dict) -> list[str]:
		artifacts = {item.get('id'): item for item in run.get('artifacts', []) if isinstance(item, dict)}
		event_list = list(run.get('native_trace', {}).get('events', []))
		events = {ev.get('id'): ev for ev in event_list if isinstance(ev, dict)}
		run['evaluation'] = AssertionEvaluator(run, contents, events).evaluate()
		native_fn = lambda ids: [events[nid] for ident in ids if isinstance(ident, str) and (nid := artifacts.get(ident, {}).get('native_event_id')) in events]
		issues = RunAuditor(run, artifacts, events, native_fn).issues() + PreregistrationAuditor(pp.root, run, event_list).issues()
		if run.get('status') in ('verified', 'refuted') and run['status'] != run['evaluation']['status']:
			issues.append('Submitted verdict contradicts preregistered raw predicates or lacks a decisive deterministic measurement')
		if issues:
			raise ValueError('; '.join(issues))
		capabilities = CapabilityResolver(run).capabilities()
		if run.get('status') in ('verified', 'refuted') and run['requirement']['property'] not in capabilities:
			raise ValueError('Recorded method/evidence does not establish the requested property')
		return capabilities
	# @used-by :meth:`RunRecorder.record_run()`
	def __init_run(self, resolved) -> dict:
		if not isinstance(self.__spec, dict):
			raise ValueError('Experimental run object required')
		run = json.loads(json.dumps(self.__spec, ensure_ascii=False, allow_nan=False))
		if any((key in run for key in _OWNED_KEYS)):
			raise ValueError('Capabilities, timestamps and requirement hash are recorder-owned')
		if not df_is_sne(run.get('plan')) or not df_is_sne(run.get('plan_sha256')):
			raise ValueError('Run requires the exact preregistered plan reference and hash')
		plan = PlanLoader(resolved, run['plan']).load_plan()
		if 'requirement' not in run:
			run['requirement'] = plan['requirement']
		run.update(schema_version=1, kind='experiment', recorded_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'))
		issues = RequirementValidator([run.get('requirement')]).issues()
		if issues:
			raise ValueError('; '.join(issues))
		run['requirement_sha256'] = RequirementValidator.digest(run['requirement'])
		return run
	# @used-by :meth:`RunRecorder.record_run()`
	@staticmethod
	def __write_run(pp, run: dict, saved: list, contents: dict, capabilities: list[str]) -> dict:
		run['capabilities'] = capabilities
		directory = pp.evidence_dir / 'Experiments' / RequirementValidator.digest(run)
		directory.mkdir(parents=True, exist_ok=False)
		for artifact in saved:
			path = directory / (artifact['id'] + '.bin')
			create_bytes(path, contents[artifact['id']])
			artifact['path'] = path.relative_to(pp.kb_dir).as_posix()
		target = directory / 'experiment.json'
		create_bytes(target, json_data(run))
		return {'experiment': target.relative_to(pp.kb_dir).as_posix(), 'experiment_sha256': df_sha256(target.read_bytes()), 'requirement_id': run['requirement']['id'], 'status': run['status'], 'capabilities': capabilities, 'limitation': run.get('limitation')}
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.record()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def record_run(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		run = self.__init_run(pp.root)
		raw_artifacts = run.pop('artifacts', [])
		trace_req = self.__tool_trace if None is not self.__tool_trace else run.pop('native_trace', None)
		run.pop('native_trace', None)
		saved, contents = ArtifactIngestor(pp.root, run, raw_artifacts, trace_req).ingest()
		capabilities = self.__audit_run(pp, run, contents)
		return self.__write_run(pp, run, saved, contents, capabilities)
