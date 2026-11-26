# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import ast
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class StructureVisitor(ast.NodeVisitor):
	__CROSS_FROM_PREFIXES = ('Df.', 'agent_tools', 'app.', 'src.')
	__CROSS_IMPORT_PREFIXES = ('Df.', 'agent_tools.', 'app.', 'src.')
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_structure_visitor_and_trigger_classifier_detect_df_cross_imports()`
	def __init__(self) -> None:
		self.classes: set[str] = set()
		self.interfaces: set[str] = set()
		self.functions: set[str] = set()
		self.imports: set[str] = set()
		self.cross_imports: set[str] = set()
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
		self.functions.add(node.name)
		self.generic_visit(node)
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	def visit_ClassDef(self, node: ast.ClassDef) -> None:
		self.classes.add(node.name)
		for base in node.bases:
			bname = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else '')
			if bname in ('ABC', 'Protocol'):
				self.interfaces.add(node.name)
		self.generic_visit(node)
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
		self.functions.add(node.name)
		self.generic_visit(node)
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	def visit_Import(self, node: ast.Import) -> None:
		for alias in node.names:
			self.imports.add(alias.name)
			if 'Df' == alias.name or alias.name.startswith(StructureVisitor.__CROSS_IMPORT_PREFIXES):
				self.cross_imports.add(alias.name)
	# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__extract_python_symbols()`
	def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
		mod = node.module or ''
		label = ('.' * int(node.level or 0)) + mod
		if label:
			self.imports.add(label)
		if 0 < int(node.level or 0) or 'Df' == mod or mod.startswith(StructureVisitor.__CROSS_FROM_PREFIXES):
			self.cross_imports.add(label or '.')
