# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Js.Graph import Graph
# @used-by :mod:`agent_tools.xref.js_graph`
def build_js_call_graph(repo_index: dict) -> dict[str, set[str]]:
	return Graph(repo_index).build()
# @used-by :mod:`agent_tools.xref.js_graph`
def find_js_overridden_method(finfo: dict, dinfo: dict, repo_index: dict) -> str | None:
	return Graph.find_overridden_method(finfo, dinfo, repo_index)
__all__ = ['build_js_call_graph', 'find_js_overridden_method']
