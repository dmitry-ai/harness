# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import importlib
import importlib.util
import pkgutil
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class PreToolRegistry:
	BUILTIN_TOOLS_MANIFEST = {
		'arch_audit': frozenset({'write_file', 'edit_file'}),
		'ask_question_gate': frozenset({'ask_question'}),
		'batch_synthesis': frozenset({'run_command', 'write_file', 'edit_file'}),
		'browser_mcp': frozenset({'mcp_*', 'invoke_subagent', 'write_file', 'edit_file'}),
		'bulk_source_read': frozenset({'read_file'}),
		'cdp_bypass': frozenset({'run_command', 'read_file', 'write_file', 'edit_file'}),
		'code_size': frozenset({'write_file', 'edit_file'}),
		'code_style': frozenset({'write_file', 'edit_file'}),
		'external_write': frozenset({'run_command'}),
		'git_write': frozenset({'run_command'}),
		'issue_comment': frozenset({'write_file', 'edit_file'}),
		'issue_first': frozenset({'run_command', 'write_file', 'edit_file'}),
		'journal_write': frozenset({'run_command', 'write_file', 'edit_file'}),
		'rules_budget': frozenset({'write_file', 'edit_file'}),
		'schedule_gate': frozenset({'schedule'}),
		'send_message_gate': frozenset({'send_message'}),
		'server_hygiene': frozenset({'run_command', 'write_file', 'edit_file'}),
		'subprocess_hygiene': frozenset({'write_file', 'edit_file'}),
		'tdd': frozenset({'run_command', 'write_file', 'edit_file'}),
		'worktree_isolation': frozenset({'write_file', 'edit_file', 'run_command'}),
		'xref': frozenset({'write_file', 'edit_file'}),
	}
	__MODULE_ENTRY_CACHE: dict[str, dict | None] = {}
	__NON_PRE_TOOL_MODULES = frozenset({'answer_checks', 'stop_checks'})
	# @used-by :func:`agent_tools.gates.run_pre_tool_gates()`
	# @used-by :meth:`PreToolRegistry.discover()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def __init__(self, pkg_name: str='agent_tools.gates', pkg_dir: Path | None=None) -> None:
		self.__pkg_name = pkg_name
		self.__pkg_dir = Path(pkg_dir) if None is not pkg_dir else Path(__file__).resolve().parents[3] / 'agent_tools/gates'
	# @used-by :meth:`PreToolRegistry.__load_builtin_entry()`
	# @used-by :meth:`PreToolRegistry.__load_extra_dir()`
	@staticmethod
	def __extract_entry(mod) -> dict | None:
		name = getattr(mod, 'NAME', None)
		priority = getattr(mod, 'PRIORITY', None)
		check = getattr(mod, 'check', None)
		raw_tools = getattr(mod, 'TOOLS', None)
		tools = frozenset((str(t) for t in raw_tools)) if isinstance(raw_tools, (set, frozenset, list, tuple)) else None
		return {'name': str(name), 'priority': int(priority), 'check': check, 'module': getattr(mod, '__name__', ''), 'tools': tools} if isinstance(name, str) and isinstance(priority, int) and callable(check) else None
	# @used-by :meth:`PreToolRegistry.__load_builtins()`
	# @uses :func:`agent_tools.gates.arch_audit.check()`
	# @uses :func:`agent_tools.gates.ask_question_gate.check()`
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
	def __load_builtin_entry(self, mod_name: str) -> dict | None:
		key = f'{self.__pkg_name}.{mod_name}'
		if key not in PreToolRegistry.__MODULE_ENTRY_CACHE:
			mod = importlib.import_module(key)
			PreToolRegistry.__MODULE_ENTRY_CACHE[key] = PreToolRegistry.__extract_entry(mod)
		return PreToolRegistry.__MODULE_ENTRY_CACHE[key]
	# @used-by :meth:`PreToolRegistry.discover()`
	def __load_builtins(self, *, tool_name: str | None=None) -> list[dict]:
		found: list[dict] = []
		for info in pkgutil.iter_modules([str(self.__pkg_dir)]):
			if info.name.startswith('_') or info.name in PreToolRegistry.__NON_PRE_TOOL_MODULES:
				continue
			known_tools = PreToolRegistry.BUILTIN_TOOLS_MANIFEST.get(info.name)
			if None is not tool_name and None is not known_tools and (not PreToolRegistry.__tool_matches(tool_name, known_tools)):
				continue
			entry = self.__load_builtin_entry(info.name)
			if None is not entry and PreToolRegistry.__tool_matches(tool_name, entry['tools']):
				found.append(entry)
		found.sort(key=lambda item: (item['priority'], item['name']))
		return found
	# @used-by :meth:`PreToolRegistry.discover()`
	@staticmethod
	def __load_extra_dir(directory: Path, *, tool_name: str | None=None) -> list[dict]:
		out: list[dict] = []
		for pyf in sorted(Path(directory).glob('*.py')):
			if pyf.name.startswith('_'):
				continue
			spec = importlib.util.spec_from_file_location(f'_harness_gate_ext_{pyf.stem}', pyf)
			if None is not spec and None is not spec.loader:
				mod = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(mod)
				entry = PreToolRegistry.__extract_entry(mod)
				if None is not entry and PreToolRegistry.__tool_matches(tool_name, entry['tools']):
					out.append(entry)
		return out
	# @used-by :meth:`PreToolRegistry.__load_builtins()`
	# @used-by :meth:`PreToolRegistry.__load_extra_dir()`
	@staticmethod
	def __tool_matches(tool_name: str | None, tools: frozenset[str] | None) -> bool:
		if None is tool_name or None is tools:
			r = True
		else:
			r = any((tool_name.startswith(pat[:-1]) if pat.endswith('*') else tool_name == pat for pat in tools))
		return r
	# @used-by :func:`agent_tools.gates.discover_pre_tool_gates()`
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.run()`
	# @used-by :meth:`PreToolRegistry.run()`
	@staticmethod
	def discover(*, tool_name: str | None=None, extra_dirs: list[Path] | tuple[Path, ...] | None=None, pkg_name: str='agent_tools.gates', pkg_dir: Path | None=None) -> list[dict]:
		reg = PreToolRegistry(pkg_name=pkg_name, pkg_dir=pkg_dir)
		gates = reg.__load_builtins(tool_name=tool_name)
		if extra_dirs:
			for d in extra_dirs:
				gates.extend(PreToolRegistry.__load_extra_dir(Path(d), tool_name=tool_name))
			gates.sort(key=lambda item: (item['priority'], item['name']))
		return gates
	# @used-by :func:`agent_tools.gates.run_pre_tool_gates()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def run(self, name: str, args: dict, payload: dict, *, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> dict:
		r = {'decision': 'allow'}
		for gate in PreToolRegistry.discover(tool_name=name, extra_dirs=extra_dirs, pkg_name=self.__pkg_name, pkg_dir=self.__pkg_dir):
			err = gate['check'](name, args, payload)
			if err:
				r = {'decision': 'deny', 'reason': f"REJECTED ({gate['name']}): {err}"}
				break
		return r
