# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Js.Syncer import Syncer
# @used-by :mod:`agent_tools.xref.js_sync`
# @used-by :mod:`agent_tools.xref`
def check_js_file_local(rel_posix: str, source: str, *, baseline_source: str | None=None, strict_existing: bool=False) -> list[str]:
	return Syncer.check_file_local(rel_posix, source, baseline_source=baseline_source, strict_existing=strict_existing)
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_global_assignment_and_top_level_listener_edges()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_override_and_ts_override_require_see_and_modifier()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_sync_and_check_commonjs_esm_classes_and_uses()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_validator_rejects_broken_and_missing_used_by()`
# @used-by :mod:`agent_tools.xref.js_sync`
# @used-by :mod:`agent_tools.xref`
def check_js_repo(repo_root: Path, *, files: list[str] | None=None, overrides_map: dict[str, str] | None=None) -> dict:
	return Syncer.check_repo(repo_root, files=files, overrides_map=overrides_map)
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_global_assignment_and_top_level_listener_edges()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_override_and_ts_override_require_see_and_modifier()`
# @used-by :meth:`test_js_xref.JsXrefTests.test_js_sync_and_check_commonjs_esm_classes_and_uses()`
# @used-by :mod:`agent_tools.xref.js_sync`
# @used-by :mod:`agent_tools.xref`
def sync_js_repo(repo_root: Path, *, apply: bool=True, files: list[str] | None=None) -> dict:
	return Syncer(repo_root).sync(apply=apply, files=files)
__all__ = ['check_js_file_local', 'check_js_repo', 'sync_js_repo']
