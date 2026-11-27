# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Experiment.NativeGeoExtractor import NativeGeoExtractor
from agent_tools.research import inside, json_data, load_observation, observation_capabilities
import json
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ArtifactIngestor:
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.record_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def __init__(self, root, run: dict, raw_artifacts, trace_request) -> None:
		self.__root = Path(root).resolve()
		self.__run = run
		self.__raw_artifacts = raw_artifacts
		self.__trace_request = trace_request
	# @used-by :meth:`ArtifactIngestor.__ingest_trace()`
	def __append_aliases(self, saved: list, contents: dict, native_aliases: list, events: dict) -> None:
		for item in native_aliases:
			if item['id'] in contents or item['native_event_id'] not in events:
				raise ValueError('Native logical artifact needs a unique id and actual selected native event')
			event = events[item['native_event_id']]
			raw = self.result_bytes(event['result'])
			saved.append({'id': item['id'], 'role': item.get('role', 'native-tool-output'), 'native_event_id': event['id'], 'sha256': df_sha256(raw), 'bytes': len(raw)})
			contents[item['id']] = raw
			if 'geolocation' == item.get('role') and (country := NativeGeoExtractor(event).extract_country()):
				saved[-1].update(country=country, geolocation_verified=True, transport='native-browser')
	# @used-by :meth:`ArtifactIngestor.__ingest_raw()`
	def __build_item(self, item: dict) -> tuple[dict, bytes]:
		if item.get('observation'):
			artifact, raw = self.collector_artifact(self.__root, item)
		else:
			source = inside(self.__root, item.get('path', ''))
			if not source.is_file():
				raise ValueError('Primary artifact file required')
			raw = source.read_bytes()
			artifact = {'id': item['id'], 'role': item.get('role', 'observation'), 'source_file': source.relative_to(self.__root).as_posix(), 'source_kind': 'imported-file'}
		artifact['sha256'] = df_sha256(raw)
		artifact['bytes'] = len(raw)
		return (artifact, raw)
	# @used-by :meth:`ArtifactIngestor.ingest()`
	def __ingest_raw(self) -> tuple[list, dict, list]:
		if not isinstance(self.__raw_artifacts, list):
			raise ValueError('Artifacts list required')
		saved, contents, native_aliases = ([], {}, [])
		for item in self.__raw_artifacts:
			if not isinstance(item, dict) or not re.fullmatch('[A-Za-z0-9_-]{1,100}', str(item.get('id', ''))):
				raise ValueError('Artifact needs a filename-safe stable id')
			if item['id'] in contents:
				raise ValueError('Duplicate artifact id')
			if item.get('native_event_id'):
				native_aliases.append(item)
			else:
				artifact, raw = self.__build_item(item)
				saved.append(artifact)
				contents[item['id']] = raw
		return (saved, contents, native_aliases)
	# @used-by :meth:`ArtifactIngestor.ingest()`
	def __ingest_trace(self, saved: list, contents: dict, native_aliases: list) -> None:
		if not self.__trace_request:
			if native_aliases:
				raise ValueError('Native artifact aliases require an actual selected native trace')
		else:
			from agent_tools.metrics import native_tool_trace
			trace = native_tool_trace(self.__root, self.__trace_request)
			self.__run['native_trace'] = trace
			for event in trace['events']:
				ident = 'tool-' + re.sub('[^A-Za-z0-9_-]', '_', event['id'])
				if ident in contents:
					raise ValueError('Artifact id collides with recorder-owned native event')
				raw = self.result_bytes(event['result'])
				saved.append({'id': ident, 'role': 'native-tool-output', 'native_event_id': event['id'], 'sha256': df_sha256(raw), 'bytes': len(raw)})
				contents[ident] = raw
			self.__append_aliases(saved, contents, native_aliases, {ev['id']: ev for ev in trace['events']})
	# @used-by :meth:`ArtifactIngestor.__build_item()`
	# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_artifact()`
	@staticmethod
	def collector_artifact(root, item: dict) -> tuple[dict, bytes]:
		meta = load_observation(root, item['observation'])
		source = inside(Path(root) / '\ua616/KB', item['observation'])
		raw = (source.parent / 'response.bin').read_bytes()
		artifact = {'id': item['id'], 'role': item.get('role', 'observation'), 'source_observation': item['observation'], 'source_observation_sha256': df_sha256(source.read_bytes()), 'observation_kind': meta.get('kind'), 'observation_capabilities': sorted(observation_capabilities(meta)), 'source_url': meta.get('url'), 'observed_at': meta.get('observed_at')}
		if 'geolocation' == artifact['role'] and NativeGeoExtractor.is_geo_url(meta.get('url', '')) and ('content' in artifact['observation_capabilities']):
			try:
				country = NativeGeoExtractor.extract_verified_country(json.loads(raw))
				if country:
					artifact.update(country=country, geolocation_verified=True, transport='http-client')
			except (ValueError, TypeError, AttributeError):
				pass
		return (artifact, raw)
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.record_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def ingest(self) -> tuple[list, dict]:
		saved, contents, native_aliases = self.__ingest_raw()
		self.__ingest_trace(saved, contents, native_aliases)
		self.__run['artifacts'] = saved
		return (saved, contents)
	# @used-by :meth:`ArtifactIngestor.__append_aliases()`
	# @used-by :meth:`ArtifactIngestor.__ingest_trace()`
	# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_trace()`
	@staticmethod
	def result_bytes(value) -> bytes:
		return value.encode('utf-8') if isinstance(value, str) else json_data(value)
