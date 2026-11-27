# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Js.Model import Model
JS_EXTS = Model.JS_EXTS
SKIP_PARTS = Model.SKIP_PARTS
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.xref.js_model`
def _line_indent(lines: list[str], lineno: int) -> str:
	return Model.line_indent(lines, lineno)
# @used-by :mod:`agent_tools.xref.js_model`
def build_js_repo_index(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> dict:
	return Model(repo_root, overrides_map=overrides_map).build_repo_index()
# @used-by :mod:`agent_tools.xref.js_model`
def discover_js_files(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> list[tuple[str, str]]:
	return Model.discover_files(repo_root, overrides_map=overrides_map)
# @used-by :mod:`agent_tools.xref.js_model`
def index_js_file(rel_posix: str, source: str) -> dict:
	return Model.index_file(rel_posix, source)
__all__ = ['JS_EXTS', 'SKIP_PARTS', '_line_indent', 'build_js_repo_index', 'discover_js_files', 'index_js_file']
