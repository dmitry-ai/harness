# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from functools import lru_cache
from Df.Harness.Xref.Python.Tags import Tags
import builtins
import importlib
import sys
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Overrides:
	__PROTOCOL_OBJECT_METHODS = frozenset({'__eq__', '__hash__', '__repr__', '__str__'})
	# @used-by :func:`agent_tools.xref.python_overrides.find_overridden_method()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__add_method_framework_edges()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__override_base_for_def()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def __init__(self, file_info: dict, cls_info: dict, repo_index: dict) -> None:
		self.__file_info = file_info
		self.__cls_info = cls_info
		self.__repo_index = repo_index
	# @used-by :func:`agent_tools.xref.python_overrides.find_overridden_method()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__add_method_framework_edges()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__override_base_for_def()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def find_overridden_method(self, method_name: str) -> str | None:
		r: str | None = None
		for b_raw in self.__cls_info.get('bases') or ():
			cand = Overrides.__resolve_base_target(self.__file_info, b_raw, self.__repo_index)
			if None is not cand:
				hit = Overrides.__check_repo_ancestors(cand, method_name, self.__repo_index, set()) if cand in self.__repo_index['classes'] else Overrides.__check_stdlib_override(cand, method_name)
				if None is not hit:
					r = hit
					break
		return r
	# @used-by :meth:`Overrides.find_overridden_method()`
	@staticmethod
	def __check_repo_ancestors(base_key: str, method_name: str, repo_index: dict, visited: set[str]) -> str | None:
		r: str | None = None
		if base_key not in visited and base_key in repo_index['classes']:
			visited.add(base_key)
			cinfo = repo_index['classes'][base_key]
			if method_name in cinfo['methods']:
				r = f'{base_key}.{method_name}'
			else:
				finfo = repo_index['by_module'][cinfo['module']]
				for b_raw in cinfo['bases']:
					cand = Overrides.__resolve_base_target(finfo, b_raw, repo_index)
					if None is not cand:
						hit = Overrides.__check_repo_ancestors(cand, method_name, repo_index, visited) if cand in repo_index['classes'] else Overrides.__check_stdlib_override(cand, method_name)
						if None is not hit:
							r = hit
							break
		return r
	# @used-by :meth:`Overrides.__check_repo_ancestors()`
	# @used-by :meth:`Overrides.find_overridden_method()`
	@staticmethod
	def __check_stdlib_override(base_dotted: str, method_name: str) -> str | None:
		cls_obj = Overrides.__load_stdlib_class(base_dotted)
		r: str | None = None
		if isinstance(cls_obj, type):
			for anc in cls_obj.__mro__:
				if object is anc and method_name not in Overrides.__PROTOCOL_OBJECT_METHODS:
					continue
				if method_name in anc.__dict__:
					r = f'{base_dotted}.{method_name}'
					break
		return r
	# @used-by :meth:`Overrides.__resolve_base_target()`
	@staticmethod
	def __expand_local_alias(file_info: dict, expr_name: str) -> str:
		imports, aliases, cur = (file_info['imports'], file_info['aliases'], expr_name)
		for _ in range(3):
			head = cur.split('.')[0]
			rest = cur[len(head):]
			if head in imports:
				cur = imports[head] + rest
			elif head in aliases:
				cur = aliases[head] + rest
			else:
				break
		return cur
	# @used-by :meth:`Overrides.__load_stdlib_module_class()`
	@staticmethod
	def __getattr_chain(obj: object, attrs: list[str]) -> object | None:
		cur: object | None = obj
		for attr in attrs:
			cur = getattr(cur, attr, None)
			if None is cur:
				break
		return cur
	# @used-by :meth:`Overrides.__check_stdlib_override()`
	@staticmethod
	@lru_cache(maxsize=256)
	def __load_stdlib_class(dotted: str) -> type | None:
		r: type | None = None
		parts = [p for p in dotted.split('.') if p]
		if 1 == len(parts) and hasattr(builtins, parts[0]):
			cand = getattr(builtins, parts[0])
			r = cand if isinstance(cand, type) else None
		elif parts and parts[0] in sys.stdlib_module_names:
			r = Overrides.__load_stdlib_module_class(parts)
		return r
	# @used-by :meth:`Overrides.__load_stdlib_class()`
	@staticmethod
	def __load_stdlib_module_class(parts: list[str]) -> type | None:
		r: type | None = None
		for split in range(len(parts) - 1, 0, -1):
			try:
				mod = importlib.import_module('.'.join(parts[:split]))
			except Exception:
				continue
			obj = Overrides.__getattr_chain(mod, parts[split:])
			if isinstance(obj, type):
				r = obj
				break
		return r
	# @used-by :meth:`Overrides.__check_repo_ancestors()`
	# @used-by :meth:`Overrides.find_overridden_method()`
	# @used-by :meth:`Overrides.is_unittest_testcase_subclass()`
	@staticmethod
	def __resolve_base_target(file_info: dict, base_raw: str, repo_index: dict) -> str | None:
		mod = file_info['module']
		expanded = Overrides.__expand_local_alias(file_info, base_raw)
		local_cls = f'{mod}.{expanded}' if mod else expanded
		if local_cls in repo_index['classes']:
			r: str | None = local_cls
		elif expanded in repo_index['classes']:
			r = expanded
		elif Tags.resolve_stdlib_symbol(expanded):
			r = expanded
		else:
			r = Overrides.__resolve_stdlib_base(expanded)
		return r
	# @used-by :meth:`Overrides.__resolve_base_target()`
	@staticmethod
	def __resolve_stdlib_base(expanded: str) -> str | None:
		r: str | None = None
		if hasattr(builtins, expanded) and isinstance(getattr(builtins, expanded), type):
			r = expanded
		elif Tags.resolve_stdlib_symbol(expanded):
			r = expanded
		return r
	# @used-by :func:`agent_tools.xref.python_overrides.is_unittest_testcase_subclass()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__add_method_framework_edges()`
	@staticmethod
	def is_unittest_testcase_subclass(file_info: dict, cls_info: dict, repo_index: dict) -> bool:
		r = False
		for b_raw in cls_info.get('bases') or ():
			cand = Overrides.__resolve_base_target(file_info, b_raw, repo_index)
			if None is not cand:
				if cand in ('unittest.TestCase', 'unittest.case.TestCase', 'unittest.IsolatedAsyncioTestCase'):
					r = True
					break
				if cand in repo_index['classes']:
					sub_cls = repo_index['classes'][cand]
					if Overrides.is_unittest_testcase_subclass(repo_index['by_module'][sub_cls['module']], sub_cls, repo_index):
						r = True
						break
		return r
