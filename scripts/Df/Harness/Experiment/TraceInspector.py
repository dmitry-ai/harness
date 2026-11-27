# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.BrowserIdentityExtractor import BrowserIdentityExtractor, IDENTITY_ALIASES
from Df.Harness.Experiment.CallChainParser import CallChainParser, DIRECT_ACTIONS, LOCATORS, NUMBER_RE, TERMINALS, TOKEN_RE
from Df.Harness.Experiment.NativeGeoExtractor import GEO_HOSTS, NativeGeoExtractor
from Df.Harness.Experiment.TraceContextAuditor import TraceContextAuditor
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class TraceInspector:
	DIRECT_ACTIONS = DIRECT_ACTIONS
	GEO_HOSTS = GEO_HOSTS
	IDENTITY_ALIASES = IDENTITY_ALIASES
	LOCATORS = LOCATORS
	NUMBER_RE = NUMBER_RE
	TERMINALS = TERMINALS
	TOKEN_RE = TOKEN_RE
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def context_issues(cls, run: dict, events: dict, native_texts_fn) -> list[str]:
		return TraceContextAuditor(run, events, native_texts_fn).issues()
	# @used-by :func:`agent_tools.experiments._event_actions()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def event_actions(cls, event: dict) -> set[str]:
		return CallChainParser.event_actions(event)
	# @used-by :func:`agent_tools.experiments._event_browser_identity()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	@classmethod
	def event_browser_identity(cls, event: dict) -> dict | None:
		return BrowserIdentityExtractor(event).extract_identity()
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def extract_verified_country(cls, data) -> str | None:
		return NativeGeoExtractor.extract_verified_country(data)
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def is_geo_url(cls, target) -> bool:
		return NativeGeoExtractor.is_geo_url(target)
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def native_geolocation(cls, event: dict) -> str | None:
		return NativeGeoExtractor(event).extract_country()
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def native_tool_name(cls, event: dict) -> str:
		return CallChainParser.native_tool_name(event)
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	@classmethod
	def unconditional_calls(cls, code: str) -> list[tuple[str, str]]:
		return CallChainParser(code).parse_calls()
