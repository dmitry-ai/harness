# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Python.Syncer import Syncer
# @used-by :mod:`agent_tools.xref.python_sync`
# @used-by :mod:`agent_tools.xref`
def check_python_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
	return Syncer.check_file_local(rel_posix, source, baseline_source=baseline_source, strict_existing=strict_existing)
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_xref_python_model_and_check_support_dotpy_packages()`
# @used-by :meth:`test_python_xref.PythonXrefTests.test_override_requires_typing_override_and_see()`
# @used-by :meth:`test_python_xref.PythonXrefTests.test_reexport_through_package_init_and_all_resolves_callers()`
# @used-by :meth:`test_python_xref.PythonXrefTests.test_sync_and_check_python_call_graph_and_uses_propagation()`
# @used-by :meth:`test_python_xref.PythonXrefTests.test_validator_rejects_self_bare_tags_broken_and_stale_used_by()`
# @used-by :mod:`agent_tools.xref.python_sync`
# @used-by :mod:`agent_tools.xref`
def check_python_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	return Syncer.check_repo(repo_root, files=files, overrides_map=overrides_map)
# @used-by :meth:`test_python_xref.PythonXrefTests.test_override_requires_typing_override_and_see()`
# @used-by :meth:`test_python_xref.PythonXrefTests.test_reexport_through_package_init_and_all_resolves_callers()`
# @used-by :meth:`test_python_xref.PythonXrefTests.test_sync_and_check_python_call_graph_and_uses_propagation()`
# @used-by :mod:`agent_tools.xref.python_sync`
# @used-by :mod:`agent_tools.xref`
def sync_python_repo(repo_root: Path, *, apply: bool=True, files: list[str] | None=None) -> dict:
	return Syncer(repo_root).sync(apply=apply, files=files)
__all__ = ['check_python_file_local', 'check_python_repo', 'sync_python_repo']
