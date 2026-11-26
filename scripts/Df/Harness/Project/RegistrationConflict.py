# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RegistrationConflict(ValueError):
	# @used-by :meth:`Df.Harness.Project.RegistrationValidator.RegistrationValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	# @see :meth:`ValueError.__init__()`
	@override
	def __init__(self, message, *, expected, actual, issues) -> None:
		super().__init__(message)
		self.expected, self.actual, self.issues = (expected, actual, list((x for x in issues)))