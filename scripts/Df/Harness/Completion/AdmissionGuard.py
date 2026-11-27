# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.lib.admission_ops import dfh_capture_admission, dfh_require_current_admission, dfh_verify_admission
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class AdmissionGuard:
	# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
	def __init__(self, mode: str='verify', *, paths=None, requests=None, response: str='', identity: dict | None=None, reference: Any=None, capability: Any=None) -> None:
		self.__mode = mode
		self.__paths = paths
		self.__requests = requests
		self.__response = response
		self.__identity = identity or {}
		self.__reference = reference
		self.__capability = capability
	# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
	def run(self) -> Any:
		if 'capture' == self.__mode:
			r: Any = dfh_capture_admission(self.__paths, self.__requests, self.__response, self.__identity)
		elif 'require_current' == self.__mode:
			r = dfh_require_current_admission(self.__capability, self.__identity)
		else:
			r = dfh_verify_admission(self.__reference, self.__identity)
		return r
