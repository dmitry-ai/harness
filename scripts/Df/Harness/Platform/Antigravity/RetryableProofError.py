# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class RetryableProofError(ValueError):
	# @used-by :func:`Df.Harness.lib.ag_review_wait.dfh_wait_for_reviewer_final_step()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
	# @see :meth:`ValueError.__init__()`
	@override
	def __init__(self, message: str) -> None:
		super().__init__(message)
		self.retryable = True
