# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Python.Model import Model
import ast
SKIP_PARTS = Model.SKIP_PARTS
# @used-by :mod:`agent_tools.xref.python_model`
def _add_import_node(node: ast.AST, module_name: str, is_pkg: bool, out: dict[str, str]) -> None:
	Model.add_import_node(node, module_name, is_pkg, out)
# @used-by :mod:`agent_tools.xref.python_model`
def _expr_dotted(expr: ast.AST) -> str:
	return Model.expr_dotted(expr)
# @used-by :mod:`agent_tools.xref.python_model`
def build_python_repo_index(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> dict:
	return Model(repo_root, overrides_map=overrides_map).build_repo_index()
# @used-by :mod:`agent_tools.xref.python_model`
def discover_python_files(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> list[tuple[str, str, str]]:
	return Model.discover_files(repo_root, overrides_map=overrides_map)
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_xref_python_model_and_check_support_dotpy_packages()`
# @used-by :mod:`agent_tools.xref.python_model`
def index_python_file(rel_posix: str, module_name: str, source: str) -> dict:
	return Model.index_file(rel_posix, module_name, source)
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_xref_python_model_and_check_support_dotpy_packages()`
# @used-by :mod:`agent_tools.xref.python_model`
def module_name_for_rel(rel_posix: str, source_roots: tuple[str, ...]) -> str:
	return Model.module_name_for_rel(rel_posix, source_roots)
__all__ = ['SKIP_PARTS', '_add_import_node', '_expr_dotted', 'build_python_repo_index', 'discover_python_files', 'index_python_file', 'module_name_for_rel']
