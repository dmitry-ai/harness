# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.CallChainParser import CallChainParser
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.storage import iter_embedded_json_objects
from urllib.parse import urlsplit
import re
GEO_HOSTS = ('ipapi.co', 'ipinfo.io', 'api.iplocation.net')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class NativeGeoExtractor:
	# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__append_aliases()`
	# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_geo()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.native_geolocation()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def __init__(self, event: dict) -> None:
		self.__event = event
	# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__append_aliases()`
	# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_geo()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.native_geolocation()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def extract_country(self) -> str | None:
		args = self.__event.get('arguments', {})
		if not (CallChainParser.event_actions(self.__event) & {'read', 'inspect', 'navigate'}) or not isinstance(args, dict):
			r = None
		else:
			targets = [value for key, value in args.items() if key.casefold() in ('url', 'target_url') and isinstance(value, str)]
			targets += re.findall('https?://[^\\s\\\'"<>]+', str(args.get('code', '')))
			if not any((self.is_geo_url(target) for target in targets)):
				r = None
			else:
				r = next((country for data in iter_embedded_json_objects(self.__event.get('result')) if (country := self.extract_verified_country(data))), None)
		return r
	# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.collector_artifact()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.extract_verified_country()`
	# @used-by :meth:`NativeGeoExtractor.extract_country()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@staticmethod
	def extract_verified_country(data) -> str | None:
		if not isinstance(data, dict):
			r = None
		else:
			country = data.get('country_code') or data.get('country')
			r = country if re.fullmatch('[A-Z]{2}', str(country)) and df_is_sne(data.get('ip')) else None
		return r
	# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.collector_artifact()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.is_geo_url()`
	# @used-by :meth:`NativeGeoExtractor.extract_country()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@staticmethod
	def is_geo_url(target) -> bool:
		return isinstance(target, str) and (urlsplit(target).hostname or '').casefold() in GEO_HOSTS
