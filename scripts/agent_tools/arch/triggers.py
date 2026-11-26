# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
from pathlib import Path
import ast
import re
from ..tdd.classifier import classify_code_path
REGISTRY_PATH_HINTS = (
	'gates/__init__.py',
	'gates/answer_checks.py',
	'gates/stop_checks.py',
	'staged_gates.py',
	'cli_registry.py',
	'cli_domains.py',
	'platforms/antigravity/hooks.json',
)
_ARCH_HEADING_RE = re.compile(r'(?im)^#{1,4}\s+[^\n]*(?:\barchitecture\b|\btarget\s+architecture\b|\bsystem\s+design\b|\b\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440|\b\u0446\u0435\u043b\u0435\u0432\u0430\u044f\s+\u0441\u0445\u0435\u043c\u0430)')
_DESIGN_VERB_RE = re.compile(r'(?i)\b(?:create|implement|introduce|refactor|redesign|decompose|build|architect|\u0441\u043e\u0437\u0434\u0430\u0442\u044c|\u0440\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c|\u0432\u043d\u0435\u0434\u0440\u0438\u0442\u044c|\u043f\u0435\u0440\u0435\u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c)\b')
_FENCE_RE = re.compile(r'```[\s\S]*?```')
_GENERIC_CLASS_RE = re.compile(r'\b(?:class|interface|protocol|trait|struct)\s+([A-Za-z_][A-Za-z0-9_]*)')
_GENERIC_FUNC_RE = re.compile(r'\b(?:function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)')
_M_HEADING_RE = re.compile(r'(?im)^(?:#{1,4}\s+|(?:\*\*|__)?)(?:M-(?:[A-Za-z]+-)*\d+)\b')
_MIN_NEW_MODULE_SLOC = 10
_MIN_SLOC_DELTA = 30
_STRUCT_TOKEN_PATS = (
	('code_file', re.compile(r'(?:scripts/|src/|app/|lib/)[A-Za-z0-9_./-]+\.(?:py|js|ts|java|php|go|rs)\b')),
	('class_decl', re.compile(r'\b(?:class|Protocol|ABC|interface)\s+`?[A-Z][A-Za-z0-9_]*`?')),
	('hook_registry', re.compile(r'\b(?:PreToolUse|ANSWER_GATES|STOP_GATES|cli_registry|staged_gates|gates/__init__|hooks\.json)\b')),
	('subagent_role', re.compile(r'\b(?:subagent|arch-auditor|invoke_subagent|spawn_agent|\u0441\u0443\u0431\u0430\u0433\u0435\u043d\u0442)\b', re.I)),
	('subsystem_noun', re.compile(r'\b(?:subsystem|plugin\s+registry|pipeline|middleware|dispatcher|router|layer(?:ed)?|\u043f\u043e\u0434\u0441\u0438\u0441\u0442\u0435\u043c|\u0440\u0435\u0435\u0441\u0442\u0440|\u043c\u043e\u0434\u0443\u043b|\u0433\u0435\u0439\u0442|\u0445\u0443\u043a)\b', re.I)),
)
class _PythonStructureVisitor(ast.NodeVisitor):
	# @used-by :func:`_extract_python_symbols()`
	def __init__(self) -> None:
		self.classes: set[str] = set()
		self.interfaces: set[str] = set()
		self.functions: set[str] = set()
		self.imports: set[str] = set()
		self.cross_imports: set[str] = set()
	# @used-by :func:`_extract_python_symbols()`
	def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
		self.functions.add(node.name)
		self.generic_visit(node)
	# @used-by :func:`_extract_python_symbols()`
	def visit_ClassDef(self, node: ast.ClassDef) -> None:
		self.classes.add(node.name)
		for base in node.bases:
			bname = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else '')
			if bname in ('ABC', 'Protocol'):
				self.interfaces.add(node.name)
		self.generic_visit(node)
	# @used-by :func:`_extract_python_symbols()`
	def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
		self.functions.add(node.name)
		self.generic_visit(node)
	# @used-by :func:`_extract_python_symbols()`
	def visit_Import(self, node: ast.Import) -> None:
		for alias in node.names:
			self.imports.add(alias.name)
			if alias.name.startswith(('agent_tools.', 'src.', 'app.')):
				self.cross_imports.add(alias.name)
	# @used-by :func:`_extract_python_symbols()`
	def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
		mod = node.module or ''
		label = ('.' * int(node.level or 0)) + mod
		if label:
			self.imports.add(label)
		if 0 < int(node.level or 0) or mod.startswith(('agent_tools', 'src.', 'app.')):
			self.cross_imports.add(label or '.')
# @used-by :func:`_collect_code_trigger_reasons()`
def _append_scale_reasons(reasons: list[str], added_sloc: int, changed_prod_files: list[str] | tuple[str, ...]) -> None:
	prod_set = {Path(p).as_posix() for p in changed_prod_files if p and 'production' == classify_code_path(Path(p))}
	if 2 <= len(prod_set):
		reasons.append(f'multi_file_production_change:{len(prod_set)}')
	if _MIN_SLOC_DELTA <= added_sloc:
		reasons.append(f'large_sloc_delta:{added_sloc}')
# @used-by :func:`classify_code_change_trigger()`
def _collect_code_trigger_reasons(rel_posix: str, old_text: str | None, new_text: str | None, old_sym: dict, new_sym: dict, changed_prod_files: list[str] | tuple[str, ...]) -> tuple[list[str], list[str], list[str], int]:
	reasons: list[str] = []
	added_classes = sorted(new_sym['classes'] - old_sym['classes'])
	added_cross = sorted(new_sym['cross_imports'] - old_sym['cross_imports'])
	added_sloc = max(0, int(new_sym['sloc']) - int(old_sym['sloc']))
	if _is_registry_path(rel_posix, old_text, new_text):
		reasons.append(f'registry_or_hook_modified:{rel_posix}')
	if _is_new_structural_module(old_text, new_sym):
		reasons.append(f'new_production_module:{rel_posix}')
	if added_classes:
		reasons.append(f"new_classes:{','.join(added_classes[:5])}")
	if added_cross:
		reasons.append(f"new_cross_module_imports:{','.join(added_cross[:5])}")
	_append_scale_reasons(reasons, added_sloc, changed_prod_files)
	return (reasons, added_classes, added_cross, added_sloc)
# @used-by :func:`_extract_python_symbols()`
# @used-by :func:`extract_code_symbols()`
def _count_sloc(source: str) -> int:
	return sum((1 for ln in (source or '').splitlines() if ln.strip() and (not ln.strip().startswith(('#', '//', '/*', '*')))))
# @used-by :func:`extract_code_symbols()`
# @uses :meth:`_PythonStructureVisitor.visit_AsyncFunctionDef()`
# @uses :meth:`_PythonStructureVisitor.visit_ClassDef()`
# @uses :meth:`_PythonStructureVisitor.visit_FunctionDef()`
# @uses :meth:`_PythonStructureVisitor.visit_Import()`
# @uses :meth:`_PythonStructureVisitor.visit_ImportFrom()`
def _extract_python_symbols(source: str) -> dict:
	sloc = _count_sloc(source)
	try:
		tree = ast.parse(source or '')
	except SyntaxError:
		r = {'classes': set(), 'interfaces': set(), 'functions': set(), 'imports': set(), 'cross_imports': set(), 'sloc': sloc}
	else:
		vis = _PythonStructureVisitor()
		vis.visit(tree)
		r = {'classes': vis.classes, 'interfaces': vis.interfaces, 'functions': vis.functions, 'imports': vis.imports, 'cross_imports': vis.cross_imports, 'sloc': sloc}
	return r
# @used-by :func:`_collect_code_trigger_reasons()`
def _is_new_structural_module(old_text: str | None, new_sym: dict) -> bool:
	pub_funcs = [f for f in new_sym['functions'] if not f.startswith('_')]
	return None is old_text and (_MIN_NEW_MODULE_SLOC <= new_sym['sloc'] or bool(new_sym['classes']) or 2 <= len(pub_funcs))
# @used-by :func:`_collect_code_trigger_reasons()`
# @used-by :func:`classify_code_change_trigger()`
def _is_registry_path(rel_posix: str, old_text: str | None, new_text: str | None) -> bool:
	norm = rel_posix.replace('\\', '/').lower()
	if any((norm.endswith(hint) for hint in REGISTRY_PATH_HINTS)):
		r = True
	elif norm.endswith('runtime.json'):
		r = '"roles"' in (new_text or '') and (old_text or '') != (new_text or '')
	else:
		r = False
	return r
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_code_change_trigger_detects_structural_changes_and_ignores_trivial_fixes()`
# @used-by :mod:`agent_tools.arch.triggers`
# @used-by :mod:`agent_tools.arch`
def classify_code_change_trigger(rel_path: str, old_text: str | None, new_text: str | None, *, changed_prod_files: list[str] | tuple[str, ...]=()) -> dict:
	norm = Path(rel_path).as_posix()
	is_reg = _is_registry_path(norm, old_text, new_text)
	cls = classify_code_path(Path(norm), content=new_text)
	if 'production' != cls and (not is_reg):
		r = {'triggered': False, 'reasons': [], 'added_classes': [], 'added_cross_imports': [], 'added_sloc': 0, 'symbols': []}
	else:
		old_sym = extract_code_symbols(old_text or '', rel_path=norm)
		new_sym = extract_code_symbols(new_text or '', rel_path=norm)
		reasons, added_classes, added_cross, added_sloc = _collect_code_trigger_reasons(norm, old_text, new_text, old_sym, new_sym, changed_prod_files)
		r = {'triggered': bool(reasons), 'reasons': reasons, 'added_classes': added_classes, 'added_cross_imports': added_cross, 'added_sloc': added_sloc, 'symbols': sorted(new_sym['classes'] | new_sym['functions'])}
	return r
# @used-by :func:`agent_tools.arch.evaluator.evaluate_response_architecture()`
# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter._check_arch_policy()`
# @used-by :mod:`agent_tools.arch.triggers`
# @used-by :mod:`agent_tools.arch`
def classify_markdown_arch_trigger(text: str, *, is_issue: bool=False, is_parent_issue: bool=False) -> dict:
	prose = _FENCE_RE.sub('', text or '')
	has_flag = '"architecture_change"' in (text or '')
	has_heading = bool(_ARCH_HEADING_RE.search(prose))
	has_m = bool(_M_HEADING_RE.search(prose))
	hits = [label for label, pat in _STRUCT_TOKEN_PATS if pat.search(prose)]
	reasons: list[str] = []
	if has_flag:
		reasons.append('explicit_architecture_change_flag')
	if has_heading and 1 <= len(hits):
		reasons.append('architecture_section_with_components')
	if has_m and 2 <= len(hits):
		reasons.append('method_proposal_with_software_components')
	if is_parent_issue and (not reasons) and bool(_DESIGN_VERB_RE.search(prose)) and 3 <= len(hits):
		reasons.append('structural_parent_issue_proposal')
	significant = has_flag or (has_heading and 2 <= len(hits)) or (has_m and 3 <= len(hits)) or (is_issue and bool(reasons))
	return {'triggered': bool(reasons), 'significant': bool(reasons and significant), 'reasons': reasons, 'signals': hits}
# @used-by :func:`classify_code_change_trigger()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_code_change_trigger_detects_structural_changes_and_ignores_trivial_fixes()`
# @used-by :mod:`agent_tools.arch.triggers`
# @used-by :mod:`agent_tools.arch`
def extract_code_symbols(source: str, *, rel_path: str='') -> dict:
	low = rel_path.replace('\\', '/').lower()
	if low.endswith('.py') or '.py' == Path(low).name:
		r = _extract_python_symbols(source or '')
	else:
		txt = source or ''
		r = {'classes': set(_GENERIC_CLASS_RE.findall(txt)), 'interfaces': set(), 'functions': set(_GENERIC_FUNC_RE.findall(txt)), 'imports': set(), 'cross_imports': set(), 'sloc': _count_sloc(txt)}
	return r
__all__ = ['REGISTRY_PATH_HINTS', 'classify_code_change_trigger', 'classify_markdown_arch_trigger', 'extract_code_symbols']