# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Java.Syncer import Syncer
# @used-by :mod:`agent_tools.xref.java_sync`
# @used-by :mod:`agent_tools.xref`
def check_java_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
	return Syncer.check_file_local(rel_posix, source, baseline_source=baseline_source, strict_existing=strict_existing)
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_anonymous_class_overloads_and_plugin_xml()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_rejects_bare_used_by_and_uses_block_tags()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_see_override_edges_unused_and_lf_sync()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_sync_and_check_overrides_records_and_uses()`
# @used-by :mod:`agent_tools.xref.java_sync`
# @used-by :mod:`agent_tools.xref`
def check_java_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	return Syncer.check_repo(repo_root, files=files, overrides_map=overrides_map)
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_anonymous_class_overloads_and_plugin_xml()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_see_override_edges_unused_and_lf_sync()`
# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_sync_and_check_overrides_records_and_uses()`
# @used-by :mod:`agent_tools.xref.java_sync`
# @used-by :mod:`agent_tools.xref`
def sync_java_repo(repo_root: Path, *, apply: bool=True, files: list[str] | None=None) -> dict:
	return Syncer(repo_root).sync(apply=apply, files=files)
__all__ = ['check_java_file_local', 'check_java_repo', 'sync_java_repo']
