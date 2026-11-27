# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Js.Imports import Imports
# @used-by :mod:`agent_tools.xref.js_imports`
def parse_cjs_exports(toks: list[tuple[str, str, int]], idx: int, exports: dict[str, str], default_exp: list[str]) -> int:
	return Imports.parse_cjs_exports(toks, idx, exports, default_exp)
# @used-by :mod:`agent_tools.xref.js_imports`
def parse_destruct_require(toks: list[tuple[str, str, int]], open_i: int, imports: dict[str, tuple[str, str]]) -> int:
	return Imports.parse_destruct_require(toks, open_i, imports)
# @used-by :mod:`agent_tools.xref.js_imports`
def parse_esm_export_list(toks: list[tuple[str, str, int]], idx: int, exports: dict[str, str]) -> int:
	return Imports.parse_esm_export_list(toks, idx, exports)
# @used-by :mod:`agent_tools.xref.js_imports`
def parse_esm_import(toks: list[tuple[str, str, int]], idx: int, imports: dict[str, tuple[str, str]]) -> int:
	return Imports(toks).parse_esm_import(idx, imports)
# @used-by :mod:`agent_tools.xref.js_imports`
def parse_module_exports_rhs(toks: list[tuple[str, str, int]], rhs: int, exports: dict[str, str], default_exp: list[str]) -> int:
	return Imports.parse_module_exports_rhs(toks, rhs, exports, default_exp)
# @used-by :mod:`agent_tools.xref.js_imports`
def record_esm_specifiers(toks: list[tuple[str, str, int]], start: int, end: int, spec: str, imports: dict[str, tuple[str, str]]) -> None:
	Imports.record_esm_specifiers(toks, start, end, spec, imports)
__all__ = ['parse_cjs_exports', 'parse_destruct_require', 'parse_esm_export_list', 'parse_esm_import', 'parse_module_exports_rhs', 'record_esm_specifiers']
