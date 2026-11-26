# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class GitWriteGate:
	NAME = 'EXEC-5-GIT-GATE'
	PRIORITY = 30
	TOOLS = frozenset({'run_command'})
	# @used-by :func:`agent_tools.gates.git_write.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if 'run_command' == name:
			from agent_tools.git_gate import prohibited_git_write_commands
			from agent_tools.worktree_guard import prohibited_worktree_remove_commands
			cmd = args.get('CommandLine', '')
			violations = [*prohibited_git_write_commands(cmd), *prohibited_worktree_remove_commands(cmd)]
			r = '; '.join(violations) if violations else None
		return r
