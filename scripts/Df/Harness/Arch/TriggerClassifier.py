# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
import re
from Df.Harness.Arch.StructureVisitor import StructureVisitor
from agent_tools.tdd.classifier import classify_code_path
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class TriggerClassifier:
	REGISTRY_PATH_HINTS = (
		'gates/__init__.py',
		'gates/answer_checks.py',
		'gates/stop_checks.py',
		'staged_gates.py',
		'cli_registry.py',
		'cli_domains.py',
		'platforms/antigravity/hooks.json',
	)
	__ARCH_HEADING_RE = re.compile(r'(?im)^#{1,4}\s+[^\n]*(?:\barchitecture\b|\btarget\s+architecture\b|\bsystem\s+design\b|\b\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440|\b\u0446\u0435\u043b\u0435\u0432\u0430\u044f\s+\u0441\u0445\u0435\u043c\u0430)')
	__DESIGN_VERB_RE = re.compile(r'(?i)\b(?:create|implement|introduce|refactor|redesign|decompose|build|architect|\u0441\u043e\u0437\u0434\u0430\u0442\u044c|\u0440\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c|\u0432\u043d\u0435\u0434\u0440\u0438\u0442\u044c|\u043f\u0435\u0440\u0435\u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c)\b')
	__FENCE_RE = re.compile(r'```[\s\S]*?```')
	__GENERIC_CLASS_RE = re.compile(r'\b(?:class|interface|protocol|trait|struct)\s+([A-Za-z_][A-Za-z0-9_]*)')
	__GENERIC_FUNC_RE = re.compile(r'\b(?:function|def|func)\s+([A-Za-z_][A-Za-z0-9_]*)')
	__M_HEADING_RE = re.compile(r'(?im)^(?:#{1,4}\s+|(?:\*\*|__)?)(?:M-(?:[A-Za-z]+-)*\d+)\b')
	__MIN_NEW_MODULE_SLOC = 10
	__MIN_SLOC_DELTA = 30
	__STRUCT_TOKEN_PATS = (
		('code_file', re.compile(r'(?:scripts/|src/|app/|lib/)[A-Za-z0-9_./-]+\.(?:py|js|ts|java|php|go|rs)\b')),
		('class_decl', re.compile(r'\b(?:class|Protocol|ABC|interface)\s+`?[A-Z][A-Za-z0-9_]*`?')),
		('hook_registry', re.compile(r'\b(?:PreToolUse|ANSWER_GATES|STOP_GATES|cli_registry|staged_gates|gates/__init__|hooks\.json)\b')),
		('subagent_role', re.compile(r'\b(?:subagent|arch-auditor|invoke_subagent|spawn_agent|\u0441\u0443\u0431\u0430\u0433\u0435\u043d\u0442)\b', re.I)),
		('subsystem_noun', re.compile(r'\b(?:subsystem|plugin\s+registry|pipeline|middleware|dispatcher|router|layer(?:ed)?|\u043f\u043e\u0434\u0441\u0438\u0441\u0442\u0435\u043c|\u0440\u0435\u0435\u0441\u0442\u0440|\u043c\u043e\u0434\u0443\u043b|\u0433\u0435\u0439\u0442|\u0445\u0443\u043a)\b', re.I)),
	)
	# @used-by :meth:`TriggerClassifier.__collect_code_trigger_reasons()`
	@staticmethod
	def __append_scale_reasons(reasons: list[str], added_sloc: int, changed_prod_files: list[str] | tuple[str, ...]) -> None:
		prod_set = {Path(p).as_posix() for p in changed_prod_files if p and 'production' == classify_code_path(Path(p))}
		if 2 <= len(prod_set):
			reasons.append(f'multi_file_production_change:{len(prod_set)}')
		if TriggerClassifier.__MIN_SLOC_DELTA <= added_sloc:
			reasons.append(f'large_sloc_delta:{added_sloc}')
	# @used-by :meth:`TriggerClassifier.classify_code_change()`
	@staticmethod
	def __collect_code_trigger_reasons(rel_posix: str, old_text: str | None, new_text: str | None, old_sym: dict, new_sym: dict, changed_prod_files: list[str] | tuple[str, ...]) -> tuple[list[str], list[str], list[str], int]:
		reasons: list[str] = []
		added_classes = sorted(new_sym['classes'] - old_sym['classes'])
		added_cross = sorted(new_sym['cross_imports'] - old_sym['cross_imports'])
		added_sloc = max(0, int(new_sym['sloc']) - int(old_sym['sloc']))
		if TriggerClassifier.__is_registry_path(rel_posix, old_text, new_text):
			reasons.append(f'registry_or_hook_modified:{rel_posix}')
		if TriggerClassifier.__is_new_structural_module(old_text, new_sym):
			reasons.append(f'new_production_module:{rel_posix}')
		if added_classes:
			reasons.append(f"new_classes:{','.join(added_classes[:5])}")
		if added_cross:
			reasons.append(f"new_cross_module_imports:{','.join(added_cross[:5])}")
		TriggerClassifier.__append_scale_reasons(reasons, added_sloc, changed_prod_files)
		return (reasons, added_classes, added_cross, added_sloc)
	# @used-by :meth:`TriggerClassifier.__extract_python_symbols()`
	# @used-by :meth:`TriggerClassifier.extract_symbols()`
	@staticmethod
	def __count_sloc(source: str) -> int:
		return sum((1 for ln in (source or '').splitlines() if ln.strip() and (not ln.strip().startswith(('#', '//', '/*', '*')))))
	# @used-by :meth:`TriggerClassifier.extract_symbols()`
	# @uses :meth:`Df.Harness.Arch.StructureVisitor.StructureVisitor.visit_AsyncFunctionDef()`
	# @uses :meth:`Df.Harness.Arch.StructureVisitor.StructureVisitor.visit_ClassDef()`
	# @uses :meth:`Df.Harness.Arch.StructureVisitor.StructureVisitor.visit_FunctionDef()`
	# @uses :meth:`Df.Harness.Arch.StructureVisitor.StructureVisitor.visit_Import()`
	# @uses :meth:`Df.Harness.Arch.StructureVisitor.StructureVisitor.visit_ImportFrom()`
	@staticmethod
	def __extract_python_symbols(source: str) -> dict:
		sloc = TriggerClassifier.__count_sloc(source)
		try:
			tree = ast.parse(source or '')
		except SyntaxError:
			r = {'classes': set(), 'interfaces': set(), 'functions': set(), 'imports': set(), 'cross_imports': set(), 'sloc': sloc}
		else:
			vis = StructureVisitor()
			vis.visit(tree)
			r = {'classes': vis.classes, 'interfaces': vis.interfaces, 'functions': vis.functions, 'imports': vis.imports, 'cross_imports': vis.cross_imports, 'sloc': sloc}
		return r
	# @used-by :meth:`TriggerClassifier.__collect_code_trigger_reasons()`
	@staticmethod
	def __is_new_structural_module(old_text: str | None, new_sym: dict) -> bool:
		pub_funcs = [f for f in new_sym['functions'] if not f.startswith('_')]
		return None is old_text and (TriggerClassifier.__MIN_NEW_MODULE_SLOC <= new_sym['sloc'] or bool(new_sym['classes']) or 2 <= len(pub_funcs))
	# @used-by :meth:`TriggerClassifier.__collect_code_trigger_reasons()`
	# @used-by :meth:`TriggerClassifier.classify_code_change()`
	@staticmethod
	def __is_registry_path(rel_posix: str, old_text: str | None, new_text: str | None) -> bool:
		norm = rel_posix.replace('\\', '/').lower()
		if any((norm.endswith(hint) for hint in TriggerClassifier.REGISTRY_PATH_HINTS)):
			r = True
		elif norm.endswith('runtime.json'):
			r = '"roles"' in (new_text or '') and (old_text or '') != (new_text or '')
		else:
			r = False
		return r
	# @used-by :func:`agent_tools.arch.triggers.classify_code_change_trigger()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__staged_code_entries()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.evaluate_pre_tool_use()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__collect_modules()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
	def classify_code_change(self, rel_path: str, old_text: str | None, new_text: str | None, *, changed_prod_files: list[str] | tuple[str, ...]=()) -> dict:
		norm = Path(rel_path).as_posix()
		is_reg = TriggerClassifier.__is_registry_path(norm, old_text, new_text)
		cls = classify_code_path(Path(norm), content=new_text)
		if 'production' != cls and (not is_reg):
			r = {'triggered': False, 'reasons': [], 'added_classes': [], 'added_cross_imports': [], 'added_sloc': 0, 'symbols': []}
		else:
			old_sym = TriggerClassifier.extract_symbols(old_text or '', rel_path=norm)
			new_sym = TriggerClassifier.extract_symbols(new_text or '', rel_path=norm)
			reasons, added_classes, added_cross, added_sloc = TriggerClassifier.__collect_code_trigger_reasons(norm, old_text, new_text, old_sym, new_sym, changed_prod_files)
			r = {'triggered': bool(reasons), 'reasons': reasons, 'added_classes': added_classes, 'added_cross_imports': added_cross, 'added_sloc': added_sloc, 'symbols': sorted(new_sym['classes'] | new_sym['functions'])}
		return r
	# @used-by :func:`agent_tools.arch.triggers.classify_markdown_arch_trigger()`
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.evaluate_response()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
	@staticmethod
	def classify_markdown(text: str, *, is_issue: bool=False, is_parent_issue: bool=False) -> dict:
		prose = TriggerClassifier.__FENCE_RE.sub('', text or '')
		has_flag = '"architecture_change"' in (text or '')
		has_heading = bool(TriggerClassifier.__ARCH_HEADING_RE.search(prose))
		has_m = bool(TriggerClassifier.__M_HEADING_RE.search(prose))
		hits = [label for label, pat in TriggerClassifier.__STRUCT_TOKEN_PATS if pat.search(prose)]
		reasons: list[str] = []
		if has_flag:
			reasons.append('explicit_architecture_change_flag')
		if has_heading and 1 <= len(hits):
			reasons.append('architecture_section_with_components')
		if has_m and 2 <= len(hits):
			reasons.append('method_proposal_with_software_components')
		if is_parent_issue and (not reasons) and bool(TriggerClassifier.__DESIGN_VERB_RE.search(prose)) and 3 <= len(hits):
			reasons.append('structural_parent_issue_proposal')
		significant = has_flag or (has_heading and 2 <= len(hits)) or (has_m and 3 <= len(hits)) or (is_issue and bool(reasons))
		return {'triggered': bool(reasons), 'significant': bool(reasons and significant), 'reasons': reasons, 'signals': hits}
	# @used-by :func:`agent_tools.arch.triggers.extract_code_symbols()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__staged_code_entries()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__collect_modules()`
	# @used-by :meth:`TriggerClassifier.classify_code_change()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
	@staticmethod
	def extract_symbols(source: str, *, rel_path: str='') -> dict:
		low = rel_path.replace('\\', '/').lower()
		if low.endswith('.py') or '.py' == Path(low).name:
			r = TriggerClassifier.__extract_python_symbols(source or '')
		else:
			txt = source or ''
			r = {'classes': set(TriggerClassifier.__GENERIC_CLASS_RE.findall(txt)), 'interfaces': set(), 'functions': set(TriggerClassifier.__GENERIC_FUNC_RE.findall(txt)), 'imports': set(), 'cross_imports': set(), 'sloc': TriggerClassifier.__count_sloc(txt)}
		return r
