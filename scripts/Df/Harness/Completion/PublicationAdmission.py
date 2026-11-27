# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
SEAL = object()
class PublicationAdmission:
	# @used-by :func:`Df.Harness.lib.admission_ops.dfh_capture_admission()`
	def __init__(self, reference, identity, *, seal=None) -> None:
		if seal is not SEAL:
			raise ValueError('Publication admission requires the current strict gate')
		self.reference = deepcopy(reference)
		self.identity = deepcopy(identity)
		self._seal = seal
