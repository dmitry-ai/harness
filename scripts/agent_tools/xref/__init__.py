# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Engine import Engine
from .java_sync import check_java_file_local, check_java_repo, sync_java_repo
from .js_sync import check_js_file_local, check_js_repo, sync_js_repo
from .python_sync import check_python_file_local, check_python_repo, sync_python_repo
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_xref()`
# @used-by :mod:`agent_tools.xref`
def format_xref_text(res: dict) -> str:
	return Engine.format_text(res)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_xref_check()`
# @used-by :meth:`test_harness_xref_compliance.HarnessXrefComplianceTests.test_harness_python_and_js_pass_xref_check_with_zero_issues()`
# @used-by :mod:`agent_tools.xref`
def run_xref_check(repo: Path, *, lang: str='all', files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	return Engine(repo).check(lang=lang, files=files, overrides_map=overrides_map)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_xref_sync()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_xref_handles_cross_cutting_multi_file_commit()`
# @used-by :mod:`agent_tools.xref`
def run_xref_sync(repo: Path, *, lang: str='all', apply: bool=True, files: list[str] | None=None) -> dict:
	return Engine.sync_repo(repo, lang=lang, apply=apply, files=files)
__all__ = ['check_java_file_local', 'check_java_repo', 'check_js_file_local', 'check_js_repo', 'check_python_file_local', 'check_python_repo', 'format_xref_text', 'run_xref_check', 'run_xref_sync', 'sync_java_repo', 'sync_js_repo', 'sync_python_repo']
