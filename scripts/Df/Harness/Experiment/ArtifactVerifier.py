# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Experiment.ArtifactIngestor import ArtifactIngestor
from Df.Harness.Experiment.NativeGeoExtractor import NativeGeoExtractor
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ArtifactVerifier:
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def __init__(self, root, run: dict, contents: dict, events: dict) -> None:
		self.__root = Path(root).resolve()
		self.__run = run
		self.__contents = contents
		self.__events = events
	# @used-by :meth:`ArtifactVerifier.verify()`
	def __verify_artifact(self, kb_dir: Path, run_dir: Path, artifact: dict) -> None:
		if artifact.get('observation_kind') and (not artifact.get('source_observation')):
			raise ValueError('Observation capability label lacks its actual collector source')
		source = inside(kb_dir, artifact['path'])
		if not source.is_relative_to(run_dir):
			raise ValueError('Experimental artifact escapes immutable run')
		raw = source.read_bytes()
		self.__contents[artifact['id']] = raw
		if len(raw) != artifact.get('bytes') or df_sha256(raw) != artifact.get('sha256'):
			raise ValueError('Primary experimental artifact differs from its saved hash/size')
		if artifact.get('source_observation'):
			expected, body = ArtifactIngestor.collector_artifact(self.__root, {'id': artifact['id'], 'role': artifact.get('role'), 'observation': artifact['source_observation']})
			if any((artifact.get(key) != value for key, value in expected.items())) or body != raw:
				raise ValueError('Experimental artifact provenance differs from its actual collector source')
		self.__verify_geo(artifact)
	# @used-by :meth:`ArtifactVerifier.__verify_artifact()`
	def __verify_geo(self, artifact: dict) -> None:
		if artifact.get('geolocation_verified'):
			if not artifact.get('native_event_id'):
				if not artifact.get('source_observation'):
					raise ValueError('Geolocation capability lacks a measured source')
			else:
				event = self.__events.get(artifact['native_event_id'], {})
				if NativeGeoExtractor(event).extract_country() != artifact.get('country') or 'native-browser' != artifact.get('transport'):
					raise ValueError('Geolocation country differs from native measurement')
	# @used-by :meth:`ArtifactVerifier.verify()`
	def __verify_trace(self) -> None:
		if self.__run.get('native_trace'):
			from agent_tools.metrics import native_tool_trace
			trace = self.__run['native_trace']
			request = {key: trace[key] for key in ('surface', 'conversation_id', 'call_ids', 'step_indices', 'native_profile_home') if key in trace}
			current = native_tool_trace(self.__root, request)
			if current['events'] != trace.get('events'):
				raise ValueError('Experimental native actions/output differ from the actual selected native events')
			for artifact in self.__run['artifacts']:
				if artifact.get('native_event_id'):
					event = self.__events.get(artifact['native_event_id'])
					if not event or ArtifactIngestor.result_bytes(event['result']) != self.__contents[artifact['id']]:
						raise ValueError('Saved native primary output differs from native authored tool result')
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def verify(self, path: Path) -> None:
		from agent_tools.path_registry import project_paths
		kb_dir = project_paths(self.__root, exact_root=True).kb_dir
		for artifact in self.__run.get('artifacts', []):
			self.__verify_artifact(kb_dir, path.parent, artifact)
		self.__verify_trace()
