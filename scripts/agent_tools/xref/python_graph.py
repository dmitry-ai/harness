# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Python.Graph import Graph
# @used-by :mod:`agent_tools.xref.python_graph`
def build_python_call_graph(repo_index: dict) -> dict[str, set[tuple[str, str]]]:
	return Graph(repo_index).build()
__all__ = ['build_python_call_graph']
