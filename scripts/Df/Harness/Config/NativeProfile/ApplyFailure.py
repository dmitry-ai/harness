# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ApplyFailure(ValueError):
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	# @see :meth:`ValueError.__init__()`
	@override
	def __init__(self, error, rollback, backups, recovery=None) -> None:
		status = rollback['status']
		super().__init__(f'{error}; rollback {status}' + (f'; recovery receipt: {recovery}' if recovery else ''))
		self.rollback, self.backups, self.recovery = (rollback, backups, recovery)
