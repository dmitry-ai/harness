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
_BUILTIN_CACHE: list[dict] | None = None
def _extract_pre_tool_entry(mod) -> dict | None:
	name = getattr(mod, 'NAME', None)
	priority = getattr(mod, 'PRIORITY', None)
	check = getattr(mod, 'check', None)
	return {'name': str(name), 'priority': int(priority), 'check': check, 'module': getattr(mod, '__name__', '')} if isinstance(name, str) and isinstance(priority, int) and callable(check) else None
def _load_extra_dir(directory: Path) -> list[dict]:
	out: list[dict] = []
	for pyf in sorted(Path(directory).glob('*.py')):
		if pyf.name.startswith('_'):
			continue
		spec = importlib.util.spec_from_file_location(f'_harness_gate_ext_{pyf.stem}', pyf)
		if None is not spec and None is not spec.loader:
			mod = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(mod)
			entry = _extract_pre_tool_entry(mod)
			if None is not entry:
				out.append(entry)
	return out
def _load_builtin_pre_tool_gates() -> list[dict]:
	global _BUILTIN_CACHE
	if None is _BUILTIN_CACHE:
		found: list[dict] = []
		pkg_dir = Path(__file__).resolve().parent
		for info in pkgutil.iter_modules([str(pkg_dir)]):
			if info.name.startswith('_'):
				continue
			mod = importlib.import_module(f'{__name__}.{info.name}')
			entry = _extract_pre_tool_entry(mod)
			if None is not entry:
				found.append(entry)
		found.sort(key=lambda item: (item['priority'], item['name']))
		_BUILTIN_CACHE = found
	return list(_BUILTIN_CACHE)
def discover_pre_tool_gates(*, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> list[dict]:
	gates = _load_builtin_pre_tool_gates()
	if extra_dirs:
		for d in extra_dirs:
			gates.extend(_load_extra_dir(Path(d)))
		gates.sort(key=lambda item: (item['priority'], item['name']))
	return gates
def run_pre_tool_gates(name: str, args: dict, payload: dict, *, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> dict:
	r = {'decision': 'allow'}
	for gate in discover_pre_tool_gates(extra_dirs=extra_dirs):
		err = gate['check'](name, args, payload)
		if err:
			r = {'decision': 'deny', 'reason': f"REJECTED ({gate['name']}): {err}"}
			break
	return r
__all__ = ['discover_pre_tool_gates', 'run_answer_gates', 'run_pre_tool_gates', 'run_stop_gates']
