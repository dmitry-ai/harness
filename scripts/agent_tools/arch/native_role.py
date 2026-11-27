# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add arch-auditor subagent role and content-addressed review CLI":
# https://github.com/dmitry-ai/harness/issues/361
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.NativeRole import NativeRole
# @used-by :func:`Df.Harness.lib.native_ag_plan._populate_codex_shared_outputs()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_native_role_generates_antigravity_and_codex_paths()`
# @used-by :mod:`agent_tools.arch.native_role`
def codex_role_protocol_path(canon: Path, role: str) -> str:
	return NativeRole.codex_protocol_path(canon, role)
# @used-by :func:`Df.Harness.lib.native_ag_plan._populate_ag_shared_outputs()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_native_role_generates_antigravity_and_codex_paths()`
# @used-by :mod:`agent_tools.arch.native_role`
def populate_antigravity_roles(outputs: dict, primary: Path, canon: Path, ag_cfg: dict) -> None:
	NativeRole().populate_antigravity(outputs, primary, canon, ag_cfg)
__all__ = ['codex_role_protocol_path', 'populate_antigravity_roles']
