# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_crash_ops import dfh_detect_hook_crashes, dfh_has_recorded_hook_issue, dfh_load_violation_receipt, dfh_text_documents_hook_crash
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class CrashAuditor:
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_hook_crash_status()`
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_check_runner_hook_crashes()`
	# @used-by :func:`agent_tools.hook_crash_audit.evaluate_hook_crash_check()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def __init__(self, root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> None:
		self.__root = root
		self.__native = native
		self.__turn = turn
		self.__value = value
		self.__response = response
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_hook_crash_status()`
	# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_check_runner_hook_crashes()`
	# @used-by :func:`agent_tools.hook_crash_audit.evaluate_hook_crash_check()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def run(self) -> dict[str, Any]:
		crashes = dfh_detect_hook_crashes(self.__native, self.__turn)
		if not crashes:
			r: dict[str, Any] = {'crashes': [], 'verified': True}
		else:
			key = str((self.__value or {}).get('key') or '')
			covered = set(dfh_load_violation_receipt(Path(self.__root), key).get('covered_hook_crash_steps') or ())
			if all((c.get('step') in covered for c in crashes)):
				r = {'crashes': crashes, 'recovered_via_receipt': True, 'resolution': 'recovered_via_receipt', 'verified': True}
			elif dfh_has_recorded_hook_issue(Path(self.__root), self.__turn or {}, self.__value, crashes):
				r = {'crashes': crashes, 'resolution': 'github_issue_recorded', 'verified': True}
			elif dfh_text_documents_hook_crash(self.__response, crashes):
				r = {'crashes': crashes, 'resolution': 'disclosed_in_response', 'verified': True}
			else:
				parts = [f"{c['hook']}@step {c['step']}" for c in crashes[:4]]
				summary = ', '.join(parts)
				r = {'crashes': crashes, 'detail': f'DOC-5 / EXEC-5 hook_crash_check: unhandled JSON hook failure(s) occurred during the active turn ({summary}). File a parent GitHub issue about the hook failure, explicitly analyze the hook failure in the response, or record recover-turn-violation before answer-prepare.', 'verified': False}
		return r