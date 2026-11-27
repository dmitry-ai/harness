# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_verif_ops import dfh_closed_issues_after, dfh_detect_shadow_replay_runs, dfh_latest_unresolved_failure, dfh_response_discloses_shadow_failure
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class VerificationObserver:
	# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_check_runner_verification_observability()`
	# @used-by :func:`agent_tools.verification_observability.evaluate_verification_observability()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def __init__(self, root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> None:
		self.__root = root
		self.__native = native
		self.__turn = turn
		self.__value = value
		self.__response = response
	# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_check_runner_verification_observability()`
	# @used-by :func:`agent_tools.verification_observability.evaluate_verification_observability()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def run(self) -> dict[str, Any]:
		unresolved = dfh_latest_unresolved_failure(dfh_detect_shadow_replay_runs(self.__native, self.__turn))
		if None is unresolved:
			r: dict[str, Any] = {'unresolved_failure': None, 'verified': True}
		else:
			fail_step = int(unresolved['step'])
			exit_code = unresolved.get('exit_code')
			closed_after = dfh_closed_issues_after(self.__turn, fail_step)
			if closed_after:
				joined = ', '.join(closed_after[:5])
				r = {'closed_after_failure': closed_after, 'detail': f'EXEC-2 / VERIFY-4 verification_observability_check: unresolved shadow-replay failure at step {fail_step} (exit={exit_code}) was followed by closing issue(s) {joined} without a subsequent passing shadow-replay rerun.', 'unresolved_failure': unresolved, 'verified': False}
			elif dfh_response_discloses_shadow_failure(self.__response):
				r = {'resolution': 'disclosed_in_response', 'unresolved_failure': unresolved, 'verified': True}
			else:
				r = {'detail': f'EXEC-2 / VERIFY-4 verification_observability_check: shadow-replay failed at step {fail_step} (exit={exit_code}) with no later passing rerun and without explicit failure disclosure in the response.', 'unresolved_failure': unresolved, 'verified': False}
		return r