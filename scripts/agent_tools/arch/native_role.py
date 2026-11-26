# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add arch-auditor subagent role and content-addressed review CLI":
# https://github.com/dmitry-ai/harness/issues/361
from __future__ import annotations
from pathlib import Path
# @used-by :func:`populate_antigravity_roles()`
def _antigravity_model_line(ag_cfg: dict, role_cfg: dict) -> str:
	ag_parent = 'parent' == (ag_cfg.get('subagents') or {}).get('selection') or role_cfg.get('selection') in ('parent', 'inherit')
	tier = role_cfg.get('tier')
	return '' if ag_parent or not tier else f'model: {tier}\n'
# @used-by :func:`agent_tools.native_profiles.shared_native_outputs()`
# @used-by :mod:`agent_tools.arch.native_role`
def codex_role_protocol_path(canon: Path, role: str) -> str:
	rel = 'agents/arch-protocol.md' if 'ARCH' == role else 'agents/worker.md'
	return (canon / rel).as_posix()
# @used-by :func:`agent_tools.native_profiles.shared_native_outputs()`
# @used-by :mod:`agent_tools.arch.native_role`
def populate_antigravity_roles(outputs: dict, primary: Path, canon: Path, ag_cfg: dict) -> None:
	ag_roles = ag_cfg.get('roles') or {}
	if 'AF' in ag_roles:
		model_line = _antigravity_model_line(ag_cfg, ag_roles['AF'])
		worker_p = (canon / 'agents/worker.md').as_posix()
		outputs[primary / 'agents/af-worker.md'] = f'---\nname: af-worker\ndescription: "Extracts and verifies Upwork evidence for an assigned question."\n{model_line}subagent: true\nmainAgent: false\n---\nRead the shared worker protocol: {worker_p}  \nEnvironment: Antigravity.  \nFollow the platform protocol and runtime.json; the parent agent selects the model per task complexity, and the requested selection does not prove the actual runtime model.  \nUse `harness.py extract` and `harness.py evidence-query` on saved captures instead of reading raw HTML/JSON bodies into context, write structured findings to the assigned output path (default `\ua616/KB/Evidence/<question>-extract.json`), and return only that file path plus a compact summary of verified facts, quotes, and gaps.  \n<!-- https://github.com/dmitry-ai/harness/issues/217 -->  \n'
	if 'ARCH' in ag_roles:
		model_line = _antigravity_model_line(ag_cfg, ag_roles['ARCH'])
		proto_p = (canon / 'agents/arch-protocol.md').as_posix()
		outputs[primary / 'agents/arch-auditor.md'] = f'---\nname: arch-auditor\ndescription: "Audits software design patterns and architecture specifications as an independent read-only falsifier."\n{model_line}subagent: true\nmainAgent: false\n---\nRead the shared architecture auditor protocol: {proto_p}  \nEnvironment: Antigravity.  \nFollow the platform protocol and runtime.json; the parent agent selects the model per task complexity, and the requested selection does not prove the actual runtime model.  \nLoad the frozen package exclusively via `harness.py arch-review-input`, check for missing patterns, pattern-washing, and overengineering without modifying files, and return one compact JSON verdict directly in your final response without calling `send_message`.  \n<!-- https://github.com/dmitry-ai/harness/issues/361 -->  \n'
__all__ = ['codex_role_protocol_path', 'populate_antigravity_roles']
