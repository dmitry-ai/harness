# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Experiment.ArtifactVerifier import ArtifactVerifier
from Df.Harness.Experiment.AssertionEvaluator import AssertionEvaluator
from Df.Harness.Experiment.CapabilityResolver import CapabilityResolver
from Df.Harness.Experiment.PreregistrationAuditor import PreregistrationAuditor
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
from Df.Harness.Experiment.RunAuditor import RunAuditor
from agent_tools.research import inside
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RunLoader:
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.__resolve_experiment()`
	# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.__check_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.load()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def __init__(self, root, reference: str) -> None:
		self.__root = root
		self.__reference = reference
	# @used-by :meth:`RunLoader.load_run()`
	@staticmethod
	def __check_unsigned_digest(path: Path, run: dict) -> None:
		unsigned = json.loads(json.dumps(run))
		for artifact in unsigned.get('artifacts', []):
			artifact.pop('path', None)
		if path.parent.name != RequirementValidator.digest(unsigned):
			raise ValueError('Immutable experimental run metadata changed')
	# @used-by :meth:`RunLoader.load_run()`
	def __load_raw(self, pp) -> tuple[Path, dict]:
		path = inside(pp.kb_dir, self.__reference)
		run = json.loads(path.read_text(encoding='utf-8'))
		if not path.is_relative_to(pp.evidence_dir / 'Experiments'):
			raise ValueError('Experiment must be a recorder-owned immutable run')
		if run.get('requirement_sha256') != RequirementValidator.digest(run.get('requirement')):
			raise ValueError('Experimental requirement changed after measurement')
		return (path, run)
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.__resolve_experiment()`
	# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.__check_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.load()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def load_run(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		path, run = self.__load_raw(pp)
		contents: dict = {}
		artifacts = {item.get('id'): item for item in run.get('artifacts', []) if isinstance(item, dict)}
		event_list = list(run.get('native_trace', {}).get('events', []))
		events = {ev.get('id'): ev for ev in event_list if isinstance(ev, dict)}
		ArtifactVerifier(pp.root, run, contents, events).verify(path)
		self.__check_unsigned_digest(path, run)
		native_fn = lambda ids: [events[nid] for ident in ids if isinstance(ident, str) and (nid := artifacts.get(ident, {}).get('native_event_id')) in events]
		issues = RunAuditor(run, artifacts, events, native_fn).issues() + PreregistrationAuditor(pp.root, run, event_list).issues()
		if run.get('evaluation') != AssertionEvaluator(run, contents, events).evaluate():
			issues.append('Recorded interpretation differs from preregistered raw predicate results')
		if run.get('status') in ('verified', 'refuted') and run['status'] != run.get('evaluation', {}).get('status'):
			issues.append('Verified/refuted status contradicts the raw deterministic results')
		if issues or run.get('capabilities') != CapabilityResolver(run).capabilities():
			raise ValueError('; '.join(issues or ['Experimental capabilities differ from recorded measurements']))
		return run
