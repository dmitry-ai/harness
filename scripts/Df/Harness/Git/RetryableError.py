# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RetryableError(RuntimeError):
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__sleep_or_raise()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__wait_active_leases()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @see :meth:`RuntimeError.__init__()`
	@override
	def __init__(self, message: str) -> None:
		super().__init__(message)
		self.retryable = True
