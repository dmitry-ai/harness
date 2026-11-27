# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_addon_ops import dfh_evaluate_worktree_removal_audit, dfh_inspect_companion_runtime_health, dfh_touches_antigravity_addons
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class AddonObserver:
	# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_check_runner_addon_observability()`
	# @used-by :func:`agent_tools.addon_observability.evaluate_addon_observability()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def __init__(self, root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> None:
		self.__root = root
		self.__native = native
		self.__turn = turn
		self.__value = value
		self.__response = response
	# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_check_runner_addon_observability()`
	# @used-by :func:`agent_tools.addon_observability.evaluate_addon_observability()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_hook_subsystem_classes()`
	def run(self) -> dict[str, Any]:
		wt_chk = dfh_evaluate_worktree_removal_audit(self.__root, self.__native, self.__turn, self.__value, self.__response)
		issues: list[str] = [] if wt_chk['verified'] else [wt_chk['detail']]
		comp_health: dict[str, Any] | None = None
		explicit_rt = bool(str(os.environ.get('HARNESS_COMPANION_RUNTIME_JSON') or '').strip())
		if dfh_touches_antigravity_addons(self.__turn) or explicit_rt:
			comp_health = dfh_inspect_companion_runtime_health()
			if not comp_health['healthy']:
				detail = '; '.join(comp_health['issues'])
				comp_path = comp_health['path']
				issues.append(f'EXEC-5 / DOC-5 companion runtime fault ({comp_path}): {detail}')
		return {'companion_health': comp_health, 'detail': '; '.join(issues), 'verified': not issues, 'worktree_errors': wt_chk['errors']}