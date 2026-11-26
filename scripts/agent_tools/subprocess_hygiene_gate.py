# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
import ast
import importlib
import re
from .code_size_gate import _resolve_python_target
from .tdd_gate import _compute_edited_content, _git_head_text, _git_index_text, is_test_file
_BLOCKING_FUNCS = frozenset({'call', 'check_call', 'check_output', 'run'})
_CHECKED_FUNCS = _BLOCKING_FUNCS | frozenset({'Popen'})
_LAUNCHER_NAME_RE = re.compile(r'(?i)(?:launcher|runner|watchdog|git_shim|hook_runner)')
# @used-by :func:`_scan_source_findings()`
def _call_violations(call: ast.Call, fn_name: str, rel_label: str) -> list[tuple[tuple[str, str, str], str]]:
	out: list[tuple[tuple[str, str, str], str]] = []
	sig = ast.unparse(call)
	lineno = getattr(call, 'lineno', 0)
	if not _kw_has_non_none(call, ('stdin', 'input')):
		out.append(((fn_name, 'stdin', sig), f'SUBPROCESS-HYGIENE: {rel_label}:{lineno} calls subprocess.{fn_name}() without stdin=subprocess.DEVNULL (or input=...); inherited open stdin pipes can deadlock background runs.'))
	if fn_name in _BLOCKING_FUNCS and (not _kw_has_non_none(call, ('timeout',))):
		out.append(((fn_name, 'timeout', sig), f'SUBPROCESS-HYGIENE: {rel_label}:{lineno} calls subprocess.{fn_name}() without timeout=...; unbounded subprocess calls can hang tests or launchers indefinitely.'))
	return out
# @used-by :func:`_scan_source_findings()`
def _collect_subprocess_bindings(tree: ast.AST) -> tuple[set[str], dict[str, str]]:
	mods: set[str] = set()
	funcs: dict[str, str] = {}
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				if 'subprocess' == alias.name:
					mods.add(alias.asname or alias.name)
		elif isinstance(node, ast.ImportFrom) and 'subprocess' == node.module:
			for alias in node.names:
				if alias.name in _CHECKED_FUNCS:
					funcs[alias.asname or alias.name] = alias.name
	return (mods, funcs)
# @used-by :func:`_kw_has_non_none()`
def _expr_has_dict_key(node: ast.AST, names: tuple[str, ...]) -> bool:
	r = False
	for sub in ast.walk(node):
		if isinstance(sub, ast.Dict) and any((isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value in names for k in sub.keys)):
			r = True
			break
	return r
# @used-by :func:`_call_violations()`
def _kw_has_non_none(call: ast.Call, names: tuple[str, ...]) -> bool:
	r = False
	for kw in call.keywords:
		if None is kw.arg:
			if _expr_has_dict_key(kw.value, names):
				r = True
				break
		elif kw.arg in names and (not (isinstance(kw.value, ast.Constant) and None is kw.value.value)):
			r = True
			break
	return r
# @used-by :func:`_scan_source_findings()`
def _resolve_call_name(call: ast.Call, mod_aliases: set[str], direct_funcs: dict[str, str]) -> str | None:
	fn = call.func
	if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id in mod_aliases and fn.attr in _CHECKED_FUNCS:
		r = fn.attr
	elif isinstance(fn, ast.Name) and fn.id in direct_funcs:
		r = direct_funcs[fn.id]
	else:
		r = None
	return r
# @used-by :func:`check_subprocess_hygiene_violations()`
def _scan_source_findings(rel_label: str, source: str) -> list[tuple[tuple[str, str, str], str]] | None:
	try:
		tree = ast.parse(source or '')
	except SyntaxError:
		r = None
	else:
		mods, funcs = _collect_subprocess_bindings(tree)
		found: list[tuple[tuple[str, str, str], str]] = []
		if mods or funcs:
			for node in ast.walk(tree):
				if isinstance(node, ast.Call):
					fn_name = _resolve_call_name(node, mods, funcs)
					if None is not fn_name:
						found.extend(_call_violations(node, fn_name, rel_label))
		r = found
	return r
# 2026-11-24
# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
# https://github.com/dmitry-ai/harness/issues/206
# @used-by :func:`evaluate_pre_tool_use_subprocess_hygiene()`
# @used-by :func:`verify_staged_subprocess_hygiene()`
# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_ast_hygiene_flags_unguarded_subprocess_in_tests_and_launchers_with_ratchet()`
def check_subprocess_hygiene_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	r: list[str] = []
	if is_subprocess_hygiene_target(path):
		rel_label = Path(path).as_posix()
		cur = _scan_source_findings(rel_label, source)
		if cur:
			base = _scan_source_findings(rel_label, baseline_source) if None is not baseline_source else None
			base_counts = Counter((sig for sig, _ in (base or ())))
			for sig, msg in cur:
				if 0 < base_counts[sig]:
					base_counts[sig] -= 1
				else:
					r.append(msg)
	return r
# @used-by :func:`agent_tools.gates.subprocess_hygiene.check()`
# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
def evaluate_pre_tool_use_subprocess_hygiene(name: str, args: dict, payload: dict) -> str | None:
	r = None
	if name in ('write_file', 'edit_file'):
		resolved = _resolve_python_target(args, payload)
		if None is not resolved:
			repo_root, target, rel = resolved
			if is_subprocess_hygiene_target(rel):
				_, new_text, _, _ = _compute_edited_content(name, args, target)
				if None is not new_text:
					errs = check_subprocess_hygiene_violations(rel, new_text, baseline_source=_git_head_text(repo_root, rel))
					r = '; '.join(errs[:3]) if errs else None
	return r
# @used-by :func:`check_subprocess_hygiene_violations()`
# @used-by :func:`evaluate_pre_tool_use_subprocess_hygiene()`
# @used-by :func:`verify_staged_subprocess_hygiene()`
def is_subprocess_hygiene_target(path: str | Path) -> bool:
	rel = Path(str(path)).as_posix()
	low = rel.casefold()
	return low.endswith('.py') and (not low.startswith(('\ua616/', '\ua66e/', '.git/'))) and (is_test_file(rel) or bool(_LAUNCHER_NAME_RE.search(Path(rel).name)))
# @used-by :meth:`agent_tools.git_gate.GitRepoGate._verify_agent_staged()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_code_size_ratchet()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_subprocess_hygiene()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_tdd_commit()`
def run_staged_gate(mod_name: str, func_name: str, *args, **kwargs) -> None:
	mod = importlib.import_module(f'.{mod_name}', __package__)
	violations = getattr(mod, func_name)(*args, **kwargs)
	if violations:
		raise ValueError('; '.join(violations))
# @used-by :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_subprocess_hygiene()`
def verify_staged_subprocess_hygiene(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	repo = Path(repo_root).resolve()
	violations: list[str] = []
	for rel in staged_paths or ():
		if not is_subprocess_hygiene_target(rel):
			continue
		fpath = repo / rel
		text = _git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
		if None is not text:
			violations.extend(check_subprocess_hygiene_violations(rel, text, baseline_source=_git_head_text(repo, rel)))
	return violations
