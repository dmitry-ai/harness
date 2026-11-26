# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import unquote
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class JsonPointer:
	# @used-by :func:`agent_tools.evidence.resolve_pointer()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_text_or_structured()`
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__select_raw()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, value, fragment: str, *, decode_uri: bool=True) -> None:
		self.__value = value
		self.__fragment = unquote(fragment) if decode_uri else fragment
	# @used-by :meth:`JsonPointer.resolve()`
	def __step(self, current, raw: str):
		if re.search('~(?![01])', raw):
			raise ValueError('Invalid JSON pointer escape')
		key = raw.replace('~1', '/').replace('~0', '~')
		if isinstance(current, dict):
			r = current[key]
		elif not isinstance(current, list):
			raise ValueError('Pointer traverses a scalar')
		else:
			if not re.fullmatch('0|[1-9][0-9]*', key):
				raise ValueError('Array pointer must be a nonnegative canonical index')
			r = current[int(key)]
		return r
	# @used-by :func:`agent_tools.evidence.pointer()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	@staticmethod
	def render_pointer(*parts) -> str:
		return '/' + '/'.join((str(x).replace('~', '~0').replace('/', '~1') for x in parts)) if parts else ''
	# @used-by :func:`agent_tools.evidence.resolve_pointer()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_text_or_structured()`
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__select_raw()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def resolve(self):
		if not self.__fragment:
			r = self.__value
		else:
			if not self.__fragment.startswith('/'):
				raise ValueError('JSON fragment must be an RFC 6901 pointer')
			cur = self.__value
			for raw in self.__fragment[1:].split('/'):
				cur = self.__step(cur, raw)
			r = cur
		return r