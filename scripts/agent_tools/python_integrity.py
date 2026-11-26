# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import ast
import builtins
import os
from pathlib import Path
import py_compile
import subprocess
import symtable
import tempfile
# 2026-11-24
# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
# https://github.com/dmitry-ai/harness/issues/186
_BUILTIN_NAMES = frozenset(dir(builtins)) | frozenset({'__all__', '__annotations__', '__builtins__', '__cached__', '__class__', '__doc__', '__file__', '__loader__', '__module__', '__name__', '__package__', '__path__', '__qualname__', '__spec__', '__warningregistry__'})
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_SKIP_PARTS = frozenset({'.git', '__pycache__', 'node_modules', '\ua616', '\ua66e'})
def _collect_defined_globals(tree: ast.AST, top_table: symtable.SymbolTable) -> set[str]:
	defined = set(_BUILTIN_NAMES)
	for sym in top_table.get_symbols():
		if sym.is_assigned() or sym.is_imported() or sym.is_namespace() or sym.is_parameter() or sym.is_annotated():
			defined.add(sym.get_name())
	for node in ast.walk(tree):
		if isinstance(node, ast.Global):
			defined.update(node.names)
	for node in _iter_module_level_imports(tree):
		for alias in node.names:
			if '*' != alias.name:
				defined.add(alias.asname or alias.name.split('.')[0])
	return defined
def _collect_undefined_globals(table: symtable.SymbolTable, defined: set[str], out: set[str]) -> None:
	for sym in table.get_symbols():
		if sym.is_referenced() and sym.is_global() and (not sym.is_local()) and (sym.get_name() not in defined):
			out.add(sym.get_name())
	for child in table.get_children():
		_collect_undefined_globals(child, defined, out)
def _git_read_text(repo: Path, *args: str) -> str | None:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=30, check=False, creationflags=_NO_WINDOW)
	return proc.stdout if 0 == proc.returncode else None
def _has_wildcard_import(tree: ast.AST) -> bool:
	return any((isinstance(node, ast.ImportFrom) and any(('*' == a.name for a in node.names)) for node in _iter_module_level_imports(tree)))
def _iter_module_level_imports(node: ast.AST) -> list[ast.Import | ast.ImportFrom]:
	out: list[ast.Import | ast.ImportFrom] = []
	for child in ast.iter_child_nodes(node):
		if isinstance(child, (ast.Import, ast.ImportFrom)):
			out.append(child)
		elif isinstance(child, (ast.If, ast.Try, ast.With, ast.AsyncWith)) or (hasattr(ast, 'TryStar') and isinstance(child, ast.TryStar)):
			out.extend(_iter_module_level_imports(child))
	return out
def _py_compile_error(path: Path, rel_label: str) -> str | None:
	r = None
	with tempfile.TemporaryDirectory() as td:
		cfile = Path(td) / 'probe.pyc'
		try:
			py_compile.compile(str(path), cfile=str(cfile), dfile=rel_label, doraise=True)
		except (py_compile.PyCompileError, SyntaxError, ValueError, OSError) as exc:
			r = f'CODE-4: Python py_compile error in {rel_label}: {exc}'
	return r
def check_python_integrity(path: str | Path, source: str) -> list[str]:
	rel_label = Path(path).as_posix()
	text = source or ''
	errs: list[str] = []
	try:
		tree = ast.parse(text, filename=rel_label)
		compile(tree, rel_label, 'exec')
		top_table = symtable.symtable(text, rel_label, 'exec')
	except (SyntaxError, ValueError) as exc:
		errs.append(f'CODE-4: Python syntax/compile error in {rel_label}: {exc}')
	else:
		if not _has_wildcard_import(tree):
			defined = _collect_defined_globals(tree, top_table)
			undef: set[str] = set()
			_collect_undefined_globals(top_table, defined, undef)
			if undef:
				errs.append(f'CODE-4: Undefined global symbol(s) in {rel_label}: {", ".join(sorted(undef)[:8])}')
	return errs
def verify_directory_python_integrity(root_dir: Path) -> list[str]:
	base = Path(root_dir).resolve()
	errs: list[str] = []
	for pyf in sorted(base.rglob('*.py')):
		rel_parts = pyf.relative_to(base).parts
		if any((p in _SKIP_PARTS for p in rel_parts)):
			continue
		rel = Path(*rel_parts).as_posix()
		errs.extend(check_python_integrity(rel, pyf.read_text(encoding='utf-8', errors='replace')))
	return errs
def verify_python_file_integrity(path: Path, *, rel_label: str | None=None) -> list[str]:
	fpath = Path(path).resolve()
	label = rel_label if None is not rel_label else fpath.as_posix()
	comp_err = _py_compile_error(fpath, label)
	if None is not comp_err:
		r = [comp_err]
	else:
		r = check_python_integrity(label, fpath.read_text(encoding='utf-8', errors='replace'))
	return r
def verify_touched_python_files(repo_root: Path, rel_paths: list[str] | set[str]) -> list[str]:
	from .code_size_gate import check_python_size_violations
	from .tdd_gate import _git_head_text
	repo = Path(repo_root).resolve()
	errs: list[str] = []
	for rel in sorted(rel_paths or ()):
		if not rel.lower().endswith('.py') or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
			continue
		fpath = repo / rel
		if fpath.is_file():
			errs.extend(verify_python_file_integrity(fpath, rel_label=rel))
			errs.extend(check_python_size_violations(rel, fpath.read_text(encoding='utf-8', errors='replace'), baseline_source=_git_head_text(repo, rel)))
	return errs
def verify_worktree_python_changes(wt_path: Path, target_branch: str) -> list[str]:
	from .code_size_gate import check_python_size_violations
	wt = Path(wt_path).resolve()
	raw = _git_read_text(wt, 'diff', '--name-only', '--diff-filter=ACMR', f'{target_branch}..HEAD') or ''
	errs: list[str] = []
	for rel in sorted({ln.strip() for ln in raw.splitlines() if ln.strip()}):
		if not rel.lower().endswith('.py') or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
			continue
		fpath = wt / rel
		if fpath.is_file():
			errs.extend(verify_python_file_integrity(fpath, rel_label=rel))
			base_text = _git_read_text(wt, 'show', f'{target_branch}:{rel}')
			errs.extend(check_python_size_violations(rel, fpath.read_text(encoding='utf-8', errors='replace'), baseline_source=base_text))
	return errs
__all__ = ['check_python_integrity', 'verify_directory_python_integrity', 'verify_python_file_integrity', 'verify_touched_python_files', 'verify_worktree_python_changes']
