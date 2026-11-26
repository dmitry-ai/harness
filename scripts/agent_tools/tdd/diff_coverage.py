# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce diff-coverage check for newly added functions in tdd-check and worktree-land":
# https://github.com/dmitry-ai/harness/issues/292
from __future__ import annotations
from pathlib import Path
from typing import Any
import ast
import json
import os
import subprocess
import sys
import tempfile
from ..git_gate import _NO_WINDOW
from ..path_registry import project_paths
_SITE_HOOK_CODE = """import atexit, json, os, sys, threading, uuid
_raw_t = os.environ.get('HARNESS_DIFF_COV_TARGETS') or ''
_out_d = os.environ.get('HARNESS_DIFF_COV_DIR') or ''
if _raw_t and _out_d:
\t_targets = set(json.loads(_raw_t))
\t_cache = {}
\t_hits = set()
\tdef _norm(p):
\t\tv = _cache.get(p)
\t\tif None is v:
\t\t\tv = os.path.normcase(os.path.realpath(p))
\t\t\t_cache[p] = v
\t\treturn v
\tdef _line_tr(frame, event, _arg):
\t\tif 'line' == event:
\t\t\t_hits.add((_norm(frame.f_code.co_filename), frame.f_lineno))
\t\treturn _line_tr
\tdef _call_tr(frame, event, _arg):
\t\tr = None
\t\tif 'call' == event and '<module>' != frame.f_code.co_name:
\t\t\tfn = frame.f_code.co_filename
\t\t\tif fn and _norm(fn) in _targets:
\t\t\t\tnp = _norm(fn)
\t\t\t\t_hits.add((np, frame.f_code.co_firstlineno))
\t\t\t\t_hits.add((np, frame.f_lineno))
\t\t\t\tr = _line_tr
\t\treturn r
\tdef _flush():
\t\tif _hits:
\t\t\tdest = os.path.join(_out_d, f'{os.getpid()}-{uuid.uuid4().hex[:8]}.json')
\t\t\twith open(dest, 'w', encoding='utf-8') as fh:
\t\t\t\tjson.dump(sorted(_hits), fh)
\tatexit.register(_flush)
\tsys.settrace(_call_tr)
\tthreading.settrace(_call_tr)
"""
# @used-by :func:`_changed_py_files()`, :func:`_git_show_text()`
def _git_read(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '--no-optional-locks', '-C', str(repo_root), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, creationflags=_NO_WINDOW, check=False)
# @used-by :func:`_parse_module_functions()`
def _collect_ast_defs(body: list[ast.stmt], prefix: str, out: dict[str, dict[str, Any]]) -> None:
	for node in body:
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			qname = f'{prefix}{node.name}'
			out[qname] = {'name': qname, 'start_line': int(node.lineno), 'end_line': int(getattr(node, 'end_lineno', node.lineno) or node.lineno)}
		elif isinstance(node, ast.ClassDef):
			_collect_ast_defs(node.body, f'{prefix}{node.name}.', out)
# @used-by :func:`find_added_production_functions()`, :func:`select_targeted_test_modules()`
def _changed_py_files(repo_root: Path, *, base_ref: str, include_working_tree: bool) -> list[str]:
	found: set[str] = set()
	if include_working_tree:
		for args in (('diff', '--name-only', base_ref), ('ls-files', '--others', '--exclude-standard')):
			found.update((ln.strip().replace('\\', '/') for ln in _git_read(repo_root, *args).stdout.splitlines() if ln.strip()))
	else:
		found.update((ln.strip().replace('\\', '/') for ln in _git_read(repo_root, 'diff', '--name-only', f'{base_ref}..HEAD').stdout.splitlines() if ln.strip()))
	return sorted((rel for rel in found if rel.endswith('.py')))
# @used-by :func:`find_added_production_functions()`
def _git_show_text(repo_root: Path, ref: str, rel: str) -> str:
	proc = _git_read(repo_root, 'show', f'{ref}:{rel}')
	return proc.stdout if 0 == proc.returncode else ''
# @used-by :func:`find_added_production_functions()`, :func:`select_targeted_test_modules()`
def _is_test_py(rel: str) -> bool:
	low = rel.replace('\\', '/').lower()
	name = Path(low).name
	return low.startswith('tests/') or '/tests/' in low or name.startswith('test_') or 'conftest.py' == name
# @used-by :func:`find_added_production_functions()`
def _parse_module_functions(source: str) -> dict[str, dict[str, Any]]:
	out: dict[str, dict[str, Any]] = {}
	if source.strip():
		try:
			tree = ast.parse(source)
			_collect_ast_defs(tree.body, '', out)
		except SyntaxError:
			out = {}
	return out
# @used-by :func:`run_trace_diff_coverage()`
def _collect_hit_lines(cov_dir: Path) -> set[tuple[str, int]]:
	hits: set[tuple[str, int]] = set()
	for jf in sorted(cov_dir.glob('*.json')):
		try:
			for pair in json.loads(jf.read_text(encoding='utf-8')):
				if isinstance(pair, list) and 2 == len(pair):
					hits.add((str(pair[0]), int(pair[1])))
		except (OSError, ValueError):
			continue
	return hits
# @used-by :func:`run_trace_diff_coverage()`
def _find_uncovered(repo_root: Path, added_funcs: dict[str, list[dict[str, Any]]], hits: set[tuple[str, int]]) -> tuple[list[str], int]:
	uncovered: list[str] = []
	checked = 0
	for rel, funcs in sorted(added_funcs.items()):
		norm_f = os.path.normcase(os.path.realpath(str(repo_root / rel)))
		for fn in funcs:
			checked += 1
			if not any(((norm_f, ln) in hits for ln in range(fn['start_line'], fn['end_line'] + 1))):
				uncovered.append(f"{rel}:{fn['name']} (L{fn['start_line']})")
	return (uncovered, checked)
# @used-by :func:`enrich_tdd_check_report()`
def _touched_git_repos(root_p: Path, turn_obj: dict[str, Any]) -> list[Path]:
	from ..worktree_flow import resolve_touched_repo_file
	from ..git_gate import is_issue_tracked_code_repo
	repos: list[Path] = []
	seen: set[str] = set()
	cands = [Path(str(tf)) for tf in (turn_obj.get('touched_files') or ()) if tf]
	cands.append(root_p)
	for cand in cands:
		resolved = cand.resolve() if cand.is_absolute() else (root_p / cand).resolve()
		hit = resolve_touched_repo_file(resolved, is_issue_tracked_code_repo)
		repo = hit[0] if None is not hit else (resolved if (resolved / '.git').exists() else None)
		if None is not repo and repo.as_posix().lower() not in seen:
			seen.add(repo.as_posix().lower())
			repos.append(repo)
	return repos
# @used-by :func:`verify_worktree_diff_coverage()`, :func:`verify_repo_diff_coverage()`
def find_added_production_functions(repo_root: Path, *, base_ref: str='HEAD', include_working_tree: bool=False) -> dict[str, list[dict[str, Any]]]:
	added: dict[str, list[dict[str, Any]]] = {}
	for rel in _changed_py_files(repo_root, base_ref=base_ref, include_working_tree=include_working_tree):
		if _is_test_py(rel):
			continue
		fpath = repo_root / rel
		if not fpath.is_file():
			continue
		cur_fns = _parse_module_functions(fpath.read_text(encoding='utf-8', errors='replace'))
		base_fns = _parse_module_functions(_git_show_text(repo_root, base_ref, rel))
		new_list = [info for name, info in cur_fns.items() if name not in base_fns]
		if new_list:
			added[rel] = new_list
	return added
# @used-by :func:`verify_worktree_diff_coverage()`, :func:`verify_repo_diff_coverage()`
def select_targeted_test_modules(repo_root: Path, changed_prod_rels: list[str], *, base_ref: str='HEAD', include_working_tree: bool=False) -> list[Path]:
	tests_dir = repo_root / 'tests'
	if not tests_dir.is_dir():
		r: list[Path] = []
	else:
		all_tests = sorted(tests_dir.glob('test_*.py'))
		if 5 >= len(all_tests):
			r = all_tests
		else:
			changed_tests = {(repo_root / rel).resolve() for rel in _changed_py_files(repo_root, base_ref=base_ref, include_working_tree=include_working_tree) if _is_test_py(rel)}
			direct = [tf for tf in all_tests if tf.resolve() in changed_tests]
			if direct:
				r = direct
			else:
				stems = {Path(rel).stem for rel in changed_prod_rels}
				r = [tf for tf in all_tests if any((st in tf.read_text(encoding='utf-8', errors='replace') for st in stems))]
	return r
# @used-by :func:`run_trace_diff_coverage()`
def _pytest_argv(test_modules: list[Path]) -> list[str]:
	import importlib.util
	extra = ['-n', 'auto', '--dist', 'worksteal'] if 1 < len(test_modules) and None is not importlib.util.find_spec('xdist') else []
	return [sys.executable, '-m', 'pytest', '-q', '--no-header', '-o', 'addopts=', '-p', 'no:cacheprovider', *extra, *(str(m) for m in test_modules)]
# @used-by :func:`verify_worktree_diff_coverage()`, :func:`verify_repo_diff_coverage()`
def run_trace_diff_coverage(repo_root: Path, added_funcs: dict[str, list[dict[str, Any]]], test_modules: list[Path], *, timeout: float=240.0) -> dict[str, Any]:
	targets = [os.path.normcase(os.path.realpath(str(repo_root / rel))) for rel in sorted(added_funcs)]
	with tempfile.TemporaryDirectory() as td:
		site_dir, cov_dir = (Path(td) / 'site', Path(td) / 'cov')
		site_dir.mkdir()
		cov_dir.mkdir()
		(site_dir / 'sitecustomize.py').write_text(_SITE_HOOK_CODE, encoding='utf-8')
		prev_pp = os.environ.get('PYTHONPATH') or ''
		env = {**os.environ, 'PYTHONPATH': f'{site_dir}{os.pathsep}{prev_pp}' if prev_pp else str(site_dir), 'HARNESS_DIFF_COV_TARGETS': json.dumps(targets), 'HARNESS_DIFF_COV_DIR': str(cov_dir), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
		proc = subprocess.run(_pytest_argv(test_modules), cwd=str(repo_root), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=_NO_WINDOW, check=False)
		hits = _collect_hit_lines(cov_dir)
	uncovered, checked = _find_uncovered(repo_root, added_funcs, hits)
	return {'valid': 0 == proc.returncode and (not uncovered), 'exit_code': proc.returncode, 'checked_functions': checked, 'uncovered': uncovered, 'targeted_modules': [m.name for m in test_modules]}
# @used-by :func:`agent_tools.completion.tdd_check_turn()`
def enrich_tdd_check_report(root_p: Path, role: str, turn_key: str, turn_obj: dict[str, Any], tdd_chk: dict[str, Any]) -> dict[str, Any]:
	repos = _touched_git_repos(root_p, turn_obj)
	uncovered: list[str] = []
	checked = 0
	for repo in repos:
		cov = verify_repo_diff_coverage(repo)
		checked += int(cov.get('checked_functions') or 0)
		uncovered.extend(cov.get('uncovered') or ())
	cov_summary = {'valid': not uncovered, 'checked_functions': checked, 'uncovered': uncovered}
	return {'valid': bool(tdd_chk.get('verified', True)) and cov_summary['valid'], 'read_only': True, 'role': role, 'turn_key': turn_key, 'tdd_check': tdd_chk, 'diff_coverage': cov_summary, 'event_count': len(turn_obj.get('tdd_events') or ())}
# @used-by :func:`enrich_tdd_check_report()`
def verify_repo_diff_coverage(repo_root: Path, *, base_ref: str='HEAD') -> dict[str, Any]:
	added = find_added_production_functions(repo_root, base_ref=base_ref, include_working_tree=True)
	if not added:
		r: dict[str, Any] = {'valid': True, 'checked_functions': 0, 'uncovered': [], 'targeted_modules': []}
	else:
		mods = select_targeted_test_modules(repo_root, list(added), base_ref=base_ref, include_working_tree=True)
		r = run_trace_diff_coverage(repo_root, added, mods) if mods else {'valid': False, 'checked_functions': sum((len(v) for v in added.values())), 'uncovered': [f"{rel}:{fn['name']} (L{fn['start_line']})" for rel, v in sorted(added.items()) for fn in v], 'targeted_modules': []}
	return r
# @used-by :func:`agent_tools.worktree_flow._run_land_checks()`
def verify_worktree_diff_coverage(wt_path: Path, target_branch: str) -> dict[str, Any]:
	added = find_added_production_functions(wt_path, base_ref=target_branch, include_working_tree=False)
	if not added:
		r: dict[str, Any] = {'valid': True, 'checked_functions': 0, 'uncovered': [], 'targeted_modules': []}
	else:
		mods = select_targeted_test_modules(wt_path, list(added), base_ref=target_branch, include_working_tree=False)
		r = run_trace_diff_coverage(wt_path, added, mods) if mods else {'valid': False, 'checked_functions': sum((len(v) for v in added.values())), 'uncovered': [f"{rel}:{fn['name']} (L{fn['start_line']})" for rel, v in sorted(added.items()) for fn in v], 'targeted_modules': []}
	return r
__all__ = ['enrich_tdd_check_report', 'find_added_production_functions', 'run_trace_diff_coverage', 'select_targeted_test_modules', 'verify_repo_diff_coverage', 'verify_worktree_diff_coverage']