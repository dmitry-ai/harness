# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import importlib
import importlib.util
from pathlib import Path
import pkgutil
from .answer_checks import run_answer_gates
from .stop_checks import run_stop_gates
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
_BUILTIN_TOOLS_MANIFEST = {
	'batch_synthesis': frozenset({'run_command', 'write_file', 'edit_file'}),
	'browser_mcp': frozenset({'mcp_*', 'invoke_subagent', 'write_file', 'edit_file'}),
	'bulk_source_read': frozenset({'read_file'}),
	'cdp_bypass': frozenset({'run_command', 'read_file', 'write_file', 'edit_file'}),
	'code_size': frozenset({'write_file', 'edit_file'}),
	# 2026-11-25
	# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
	# https://github.com/dmitry-ai/harness/issues/243
	'code_style': frozenset({'write_file', 'edit_file'}),
	'external_write': frozenset({'run_command'}),
	'git_write': frozenset({'run_command'}),
	# 2026-11-26
	# "Add PreToolUse and pre-commit gate for issue-comment placement":
	# https://github.com/dmitry-ai/harness/issues/273
	'issue_comment': frozenset({'write_file', 'edit_file'}),
	'issue_first': frozenset({'run_command', 'write_file', 'edit_file'}),
	'journal_write': frozenset({'run_command', 'write_file', 'edit_file'}),
	'rules_budget': frozenset({'write_file', 'edit_file'}),
	'schedule_gate': frozenset({'schedule'}),
	# 2026-11-24
	# "Enforce single falsifier review default and block duplicate send_message reports":
	# https://github.com/dmitry-ai/harness/issues/226
	'send_message_gate': frozenset({'send_message'}),
	'server_hygiene': frozenset({'run_command', 'write_file', 'edit_file'}),
	'subprocess_hygiene': frozenset({'write_file', 'edit_file'}),
	'tdd': frozenset({'run_command', 'write_file', 'edit_file'}),
	# 2026-11-26 "Block raw worktree removal and fail closed on locked cleanup": https://github.com/dmitry-ai/harness/issues/303
	'worktree_isolation': frozenset({'write_file', 'edit_file', 'run_command'}),
	# 2026-11-26
	# "Enforce cross-reference compliance in PreToolUse and Git gates":
	# https://github.com/dmitry-ai/harness/issues/306
	'xref': frozenset({'write_file', 'edit_file'}),
}
_MODULE_ENTRY_CACHE: dict[str, dict | None] = {}
_NON_PRE_TOOL_MODULES = frozenset({'answer_checks', 'stop_checks'})
# @used-by :func:`_load_builtin_entry()`
# @used-by :func:`_load_extra_dir()`
def _extract_pre_tool_entry(mod) -> dict | None:
	name = getattr(mod, 'NAME', None)
	priority = getattr(mod, 'PRIORITY', None)
	check = getattr(mod, 'check', None)
	raw_tools = getattr(mod, 'TOOLS', None)
	tools = frozenset((str(t) for t in raw_tools)) if isinstance(raw_tools, (set, frozenset, list, tuple)) else None
	return {'name': str(name), 'priority': int(priority), 'check': check, 'module': getattr(mod, '__name__', ''), 'tools': tools} if isinstance(name, str) and isinstance(priority, int) and callable(check) else None
# @used-by :func:`_load_builtin_pre_tool_gates()`
# @uses :func:`agent_tools.gates.batch_synthesis.check()`
# @uses :func:`agent_tools.gates.browser_mcp.check()`
# @uses :func:`agent_tools.gates.bulk_source_read.check()`
# @uses :func:`agent_tools.gates.cdp_bypass.check()`
# @uses :func:`agent_tools.gates.code_size.check()`
# @uses :func:`agent_tools.gates.code_style.check()`
# @uses :func:`agent_tools.gates.external_write.check()`
# @uses :func:`agent_tools.gates.git_write.check()`
# @uses :func:`agent_tools.gates.issue_comment.check()`
# @uses :func:`agent_tools.gates.issue_first.check()`
# @uses :func:`agent_tools.gates.journal_write.check()`
# @uses :func:`agent_tools.gates.rules_budget.check()`
# @uses :func:`agent_tools.gates.schedule_gate.check()`
# @uses :func:`agent_tools.gates.send_message_gate.check()`
# @uses :func:`agent_tools.gates.server_hygiene.check()`
# @uses :func:`agent_tools.gates.subprocess_hygiene.check()`
# @uses :func:`agent_tools.gates.tdd.check()`
# @uses :func:`agent_tools.gates.worktree_isolation.check()`
# @uses :func:`agent_tools.gates.xref.check()`
def _load_builtin_entry(mod_name: str) -> dict | None:
	if mod_name not in _MODULE_ENTRY_CACHE:
		mod = importlib.import_module(f'{__name__}.{mod_name}')
		_MODULE_ENTRY_CACHE[mod_name] = _extract_pre_tool_entry(mod)
	return _MODULE_ENTRY_CACHE[mod_name]
# @used-by :func:`discover_pre_tool_gates()`
def _load_builtin_pre_tool_gates(*, tool_name: str | None=None) -> list[dict]:
	found: list[dict] = []
	pkg_dir = Path(__file__).resolve().parent
	for info in pkgutil.iter_modules([str(pkg_dir)]):
		if info.name.startswith('_') or info.name in _NON_PRE_TOOL_MODULES:
			continue
		known_tools = _BUILTIN_TOOLS_MANIFEST.get(info.name)
		if None is not tool_name and None is not known_tools and (not _tool_matches(tool_name, known_tools)):
			continue
		entry = _load_builtin_entry(info.name)
		if None is not entry and _tool_matches(tool_name, entry['tools']):
			found.append(entry)
	found.sort(key=lambda item: (item['priority'], item['name']))
	return found
# @used-by :func:`discover_pre_tool_gates()`
def _load_extra_dir(directory: Path, *, tool_name: str | None=None) -> list[dict]:
	out: list[dict] = []
	for pyf in sorted(Path(directory).glob('*.py')):
		if pyf.name.startswith('_'):
			continue
		spec = importlib.util.spec_from_file_location(f'_harness_gate_ext_{pyf.stem}', pyf)
		if None is not spec and None is not spec.loader:
			mod = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(mod)
			entry = _extract_pre_tool_entry(mod)
			if None is not entry and _tool_matches(tool_name, entry['tools']):
				out.append(entry)
	return out
# @used-by :func:`_load_builtin_pre_tool_gates()`
# @used-by :func:`_load_extra_dir()`
def _tool_matches(tool_name: str | None, tools: frozenset[str] | None) -> bool:
	if None is tool_name or None is tools:
		r = True
	else:
		r = any((tool_name.startswith(pat[:-1]) if pat.endswith('*') else tool_name == pat for pat in tools))
	return r
# @used-by :func:`run_pre_tool_gates()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_builtin_pre_tool_gates_discovered_in_strict_priority_order()`
# @used-by :meth:`test_hook_lazy_imports.HookLazyImportsTests.test_discover_pre_tool_gates_tool_filtering_and_manifest_parity()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :mod:`agent_tools.gates`
def discover_pre_tool_gates(*, tool_name: str | None=None, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> list[dict]:
	gates = _load_builtin_pre_tool_gates(tool_name=tool_name)
	if extra_dirs:
		for d in extra_dirs:
			gates.extend(_load_extra_dir(Path(d), tool_name=tool_name))
		gates.sort(key=lambda item: (item['priority'], item['name']))
	return gates
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
# @used-by :func:`check_rules_and_server_gate._evaluate_payload()`
# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_pre_tool_use_gate_and_pre_commit_enforce_code_style()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_send_message_gate_blocks_duplicate_json_verdicts_and_allows_prompts()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_dynamic_plugin_discovery_runs_without_touching_dispatcher()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_pre_tool_use_blocks_raw_git_worktree_remove()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_pre_tool_use_blocks_silent_shell_deletion_of_managed_worktrees()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns()`
# @used-by :meth:`test_xref_gate.XrefGateTests._assert_pre_tool_allows_valid_and_legacy_ratchet()`
# @used-by :meth:`test_xref_gate.XrefGateTests._assert_pre_tool_denies_bad_samples()`
# @used-by :mod:`agent_tools.gates`
def run_pre_tool_gates(name: str, args: dict, payload: dict, *, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> dict:
	r = {'decision': 'allow'}
	for gate in discover_pre_tool_gates(tool_name=name, extra_dirs=extra_dirs):
		err = gate['check'](name, args, payload)
		if err:
			r = {'decision': 'deny', 'reason': f"REJECTED ({gate['name']}): {err}"}
			break
	return r
__all__ = ['_BUILTIN_TOOLS_MANIFEST', 'discover_pre_tool_gates', 'run_answer_gates', 'run_pre_tool_gates', 'run_stop_gates']
