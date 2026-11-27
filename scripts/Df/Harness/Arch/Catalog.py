# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import re
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class Catalog:
	__CACHE: dict[str, dict] = {}
	__PAREN_RE = re.compile(r'\(([^()]+)\)')
	__STRIP_MD_RE = re.compile(r'[*_`"\'\u00ab\u00bb]+')
	# @used-by :func:`agent_tools.arch.catalog.lookup_pattern()`
	# @used-by :meth:`Df.Harness.Arch.SpecValidator.SpecValidator.__validate_idiom_spec()`
	# @used-by :meth:`Df.Harness.Arch.SpecValidator.SpecValidator.__validate_pattern_spec()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	def __init__(self, primary: str | Path | None=None, *, catalog: dict | None=None) -> None:
		self.__data = Catalog.load(primary) if None is catalog else catalog
	# @used-by :meth:`Catalog.load()`
	# @used-by :meth:`Catalog.lookup()`
	@staticmethod
	def __build_lookup_index(patterns: list[dict]) -> dict[str, dict]:
		index: dict[str, dict] = {}
		for entry in patterns:
			name = str(entry.get('name') or '').strip()
			if not name:
				continue
			index[Catalog.__clean_pattern_token(name)] = entry
			for alias in entry.get('aliases') or ():
				tok = Catalog.__clean_pattern_token(str(alias))
				if tok and tok not in index:
					index[tok] = entry
		return index
	# @used-by :meth:`Catalog.lookup()`
	@staticmethod
	def __candidate_pattern_keys(raw: str) -> list[str]:
		keys: list[str] = []
		base = str(raw or '').strip()
		without_paren = Catalog.__PAREN_RE.sub('', base).strip()
		candidates = [base, without_paren, *Catalog.__PAREN_RE.findall(base)]
		for item in list(candidates):
			for sep in ('/', '\u2014', '\u2013', ','):
				if sep in item:
					candidates.extend(item.split(sep))
		for cand in candidates:
			tok = Catalog.__clean_pattern_token(cand)
			if tok and tok not in keys:
				keys.append(tok)
		return keys
	# @used-by :meth:`Catalog.__build_lookup_index()`
	# @used-by :meth:`Catalog.__candidate_pattern_keys()`
	@staticmethod
	def __clean_pattern_token(raw: str) -> str:
		cleaned = Catalog.__STRIP_MD_RE.sub('', str(raw or ''))
		cleaned = re.sub(r'\s+', ' ', cleaned).strip().rstrip('.,;:').strip()
		return cleaned.casefold()
	# @used-by :meth:`Catalog.load()`
	@staticmethod
	def __resolve_catalog_path(primary: str | Path | None) -> Path:
		if None is not primary:
			r = Path(primary).resolve() / 'references/architecture/patterns-catalog.json'
		else:
			local = Path(__file__).resolve().parents[4] / 'references/architecture/patterns-catalog.json'
			if local.is_file():
				r = local
			else:
				from agent_tools.runtime import PRIMARY
				r = Path(PRIMARY).resolve() / 'references/architecture/patterns-catalog.json'
		return r
	# @used-by :func:`agent_tools.arch.catalog.load_pattern_catalog()`
	# @used-by :meth:`Catalog.__init__()`
	# @used-by :meth:`Catalog.names()`
	# @used-by :meth:`Df.Harness.Arch.SpecValidator.SpecValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	@classmethod
	def load(cls, primary: str | Path | None=None) -> dict:
		path = cls.__resolve_catalog_path(primary)
		key = str(path)
		cached = cls.__CACHE.get(key)
		if None is not cached:
			r = cached
		else:
			data = json.loads(path.read_text(encoding='utf-8'))
			data['_lookup'] = cls.__build_lookup_index(list(data.get('patterns') or ()))
			cls.__CACHE[key] = data
			r = data
		return r
	# @used-by :func:`agent_tools.arch.catalog.lookup_pattern()`
	# @used-by :meth:`Df.Harness.Arch.SpecValidator.SpecValidator.__validate_idiom_spec()`
	# @used-by :meth:`Df.Harness.Arch.SpecValidator.SpecValidator.__validate_pattern_spec()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	def lookup(self, name: str) -> dict | None:
		index = self.__data.get('_lookup') or Catalog.__build_lookup_index(list(self.__data.get('patterns') or ()))
		r: dict | None = None
		for key in Catalog.__candidate_pattern_keys(name):
			hit = index.get(key)
			if None is not hit:
				r = hit
				break
		return r
	# @used-by :func:`agent_tools.arch.catalog.catalog_pattern_names()`
	# @used-by :func:`test_df_harness_s11_wave2e_arch._arch_backward_imports()`
	# @used-by :meth:`Df.Harness.Arch.StructureVisitor.StructureVisitor.visit_Import()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeAnalyzer.CodeSizeAnalyzer.__is_override_import()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.__collect_defined_globals()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.__has_wildcard_import()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneChecker.SubprocessHygieneChecker.__collect_subprocess_bindings()`
	# @used-by :meth:`Df.Harness.Xref.Python.Model.Model.add_import_node()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	@classmethod
	def names(cls, *, catalog: dict | None=None) -> set[str]:
		cat = cls.load() if None is catalog else catalog
		return {str(entry['name']) for entry in cat.get('patterns') or () if entry.get('name')}
