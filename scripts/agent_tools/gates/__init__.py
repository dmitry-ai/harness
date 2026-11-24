# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce single falsifier review default and block duplicate send_message reports":
# https://github.com/dmitry-ai/harness/issues/226
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
import importlib
import importlib.util
from pathlib import Path
import pkgutil
from .answer_checks import run_answer_gates
from .stop_checks import run_stop_gates
_BUILTIN_TOOLS_MANIFEST = {
	'batch_synthesis': frozenset({'run_command', 'write_file', 'edit_file'}),
	'browser_mcp': frozenset({'mcp_*', 'invoke_subagent', 'write_file', 'edit_file'}),
	'bulk_source_read': frozenset({'read_file'}),
	'cdp_bypass': frozenset({'run_command', 'read_file', 'write_file', 'edit_file'}),
	'code_size': frozenset({'write_file', 'edit_file'}),
	'external_write': frozenset({'run_command'}),
	'git_write': frozenset({'run_command'}),
	'issue_first': frozenset({'run_command', 'write_file', 'edit_file'}),
	'journal_write': frozenset({'run_command', 'write_file', 'edit_file'}),
	'rules_budget': frozenset({'write_file', 'edit_file'}),
	'schedule_gate': frozenset({'schedule'}),
	'send_message_gate': frozenset({'send_message'}),
	'server_hygiene': frozenset({'run_command', 'write_file', 'edit_file'}),
	'subprocess_hygiene': frozenset({'write_file', 'edit_file'}),
	'tdd': frozenset({'run_command', 'write_file', 'edit_file'}),
	'worktree_isolation': frozenset({'write_file', 'edit_file'}),
}
_MODULE_ENTRY_CACHE: dict[str, dict | None] = {}
_NON_PRE_TOOL_MODULES = frozenset({'answer_checks', 'stop_checks'})
def _extract_pre_tool_entry(mod) -> dict | None:
	name = getattr(mod, 'NAME', None)
	priority = getattr(mod, 'PRIORITY', None)
	check = getattr(mod, 'check', None)
	raw_tools = getattr(mod, 'TOOLS', None)
	tools = frozenset((str(t) for t in raw_tools)) if isinstance(raw_tools, (set, frozenset, list, tuple)) else None
	return {'name': str(name), 'priority': int(priority), 'check': check, 'module': getattr(mod, '__name__', ''), 'tools': tools} if isinstance(name, str) and isinstance(priority, int) and callable(check) else None
def _load_builtin_entry(mod_name: str) -> dict | None:
	if mod_name not in _MODULE_ENTRY_CACHE:
		mod = importlib.import_module(f'{__name__}.{mod_name}')
		_MODULE_ENTRY_CACHE[mod_name] = _extract_pre_tool_entry(mod)
	return _MODULE_ENTRY_CACHE[mod_name]
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
def _tool_matches(tool_name: str | None, tools: frozenset[str] | None) -> bool:
	if None is tool_name or None is tools:
		r = True
	else:
		r = any((tool_name.startswith(pat[:-1]) if pat.endswith('*') else tool_name == pat for pat in tools))
	return r
def discover_pre_tool_gates(*, tool_name: str | None=None, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> list[dict]:
	gates = _load_builtin_pre_tool_gates(tool_name=tool_name)
	if extra_dirs:
		for d in extra_dirs:
			gates.extend(_load_extra_dir(Path(d), tool_name=tool_name))
		gates.sort(key=lambda item: (item['priority'], item['name']))
	return gates
def run_pre_tool_gates(name: str, args: dict, payload: dict, *, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> dict:
	r = {'decision': 'allow'}
	for gate in discover_pre_tool_gates(tool_name=name, extra_dirs=extra_dirs):
		err = gate['check'](name, args, payload)
		if err:
			r = {'decision': 'deny', 'reason': f"REJECTED ({gate['name']}): {err}"}
			break
	return r
__all__ = ['_BUILTIN_TOOLS_MANIFEST', 'discover_pre_tool_gates', 'run_answer_gates', 'run_pre_tool_gates', 'run_stop_gates']
