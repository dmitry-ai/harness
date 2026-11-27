# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Arch.Catalog import Catalog
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class SpecValidator:
	__BACKTICK_RE = re.compile(r'`([^`\r\n]+)`')
	__FENCE_RE = re.compile(r'```[\s\S]*?```')
	__FIELD_LINE_RE = re.compile(r'^\s*(?:[-*+]|\d+[.)])?\s*(?:\*\*|__)?([A-Za-z_ \u0400-\u04ff]+?)(?:\*\*|__)?\s*[:\u2014]\s*(?:\*\*|__)?\s*(.+?)\s*$')
	__IDENT_RE = re.compile(r'\b[A-Za-z_][A-Za-z0-9_./-]*\b')
	__INLINE_CAT_RE = re.compile(r'\(\s*`?(Creational|Structural|Behavioral|Concurrency|Architectural)`?\s*\)', re.I)
	__KEY_MAP = {
		'category': 'category',
		'collaboration': 'collaboration',
		'consequences': 'consequences',
		'design pattern': 'pattern',
		'idiom exception': 'idiom_exception',
		'idiom_exception': 'idiom_exception',
		'intent': 'intent',
		'native construct': 'native_construct',
		'participants': 'participants',
		'pattern': 'pattern',
		'rationale': 'rationale',
		'\u0432\u0437\u0430\u0438\u043c\u043e\u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435': 'collaboration',
		'\u0438\u0441\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u0438\u0434\u0438\u043e\u043c\u044b': 'idiom_exception',
		'\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f': 'category',
		'\u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435': 'intent',
		'\u043d\u0430\u0442\u0438\u0432\u043d\u044b\u0439 \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c': 'native_construct',
		'\u043e\u0431\u043e\u0441\u043d\u043e\u0432\u0430\u043d\u0438\u0435': 'rationale',
		'\u043f\u0430\u0442\u0442\u0435\u0440\u043d': 'pattern',
		'\u043f\u0430\u0442\u0442\u0435\u0440\u043d \u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f': 'pattern',
		'\u043f\u043e\u0441\u043b\u0435\u0434\u0441\u0442\u0432\u0438\u044f': 'consequences',
		'\u0441\u0443\u0442\u044c': 'intent',
		'\u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0438': 'participants',
		'\u044f\u0437\u044b\u043a\u043e\u0432\u043e\u0439 \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c': 'native_construct',
	}
	__MIN_RATIONALE_CHARS = 20
	__REQUIRED_PATTERN_FIELDS = ('pattern', 'category', 'intent', 'participants', 'collaboration', 'consequences')
	# @used-by :func:`agent_tools.arch.spec.validate_arch_spec_markdown()`
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.evaluate_response()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__build_package_payload()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.inspect_status()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.check_arch_policy()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	def __init__(self, *, catalog: dict | None=None) -> None:
		self.__catalog = catalog
	# @used-by :meth:`SpecValidator.extract_specs()`
	@staticmethod
	def __parse_field_line(line: str) -> tuple[str | None, str]:
		m = SpecValidator.__FIELD_LINE_RE.match(line)
		if None is m:
			r = (None, '')
		else:
			raw_key = ' '.join(m.group(1).strip().casefold().split())
			r = (SpecValidator.__KEY_MAP.get(raw_key), m.group(2).strip())
		return r
	# @used-by :meth:`SpecValidator.extract_specs()`
	@staticmethod
	def __start_spec_block(key: str, val: str) -> dict:
		kind = 'idiom_exception' if 'idiom_exception' == key else 'pattern'
		spec: dict = {'kind': kind, 'pattern': val}
		if 'pattern' == kind:
			m_cat = SpecValidator.__INLINE_CAT_RE.search(val)
			if None is not m_cat:
				spec['category'] = m_cat.group(1).capitalize()
		return spec
	# @used-by :meth:`SpecValidator.validate()`
	@staticmethod
	def __validate_idiom_spec(spec: dict, cat: dict, issues: list[dict]) -> dict | None:
		raw_pat = str(spec.get('pattern') or '').strip()
		hit = Catalog(catalog=cat).lookup(raw_pat)
		native_c = str(spec.get('native_construct') or '').strip()
		rationale = str(spec.get('rationale') or '').strip()
		parts = str(spec.get('participants') or '').strip()
		missing = [k for k, v in (('Native Construct', native_c), ('Rationale', rationale), ('Participants', parts)) if not v]
		if None is hit:
			issues.append({'code': 'INVALID_IDIOM_EXCEPTION', 'message': f'idiom_exception must reference a canonical displaced pattern from patterns-catalog.json, got {raw_pat!r}'})
			r = None
		elif missing or SpecValidator.__MIN_RATIONALE_CHARS > len(rationale):
			joined = ', '.join(missing)
			detail = f'missing {joined}' if missing else f'Rationale must be >= {SpecValidator.__MIN_RATIONALE_CHARS} characters'
			pname = hit['name']
			issues.append({'code': 'INVALID_IDIOM_EXCEPTION', 'message': f'Invalid idiom_exception for {pname}: {detail}'})
			r = None
		else:
			r = {'pattern': hit['name'], 'native_construct': native_c, 'rationale': rationale, 'participants': parts}
		return r
	# @used-by :meth:`SpecValidator.validate()`
	@staticmethod
	def __validate_pattern_spec(spec: dict, cat: dict, *, require_full_fields: bool, issues: list[dict]) -> str | None:
		raw_pat = str(spec.get('pattern') or '').strip()
		hit = Catalog(catalog=cat).lookup(raw_pat)
		r: str | None = None
		if None is hit:
			issues.append({'code': 'UNRECOGNIZED_ARCH_PATTERN', 'message': f'Unrecognized Software design pattern {raw_pat!r}; use a canonical name or alias from references/architecture/patterns-catalog.json'})
		else:
			r = str(hit['name'])
			raw_cat = str(spec.get('category') or '').strip().strip('`*').rstrip('.')
			hit_cat = str(hit['category'])
			if raw_cat and raw_cat.casefold() != hit_cat.casefold():
				issues.append({'code': 'MISMATCHED_ARCH_CATEGORY', 'message': f'Pattern {r} belongs to category {hit_cat}, not {raw_cat}'})
			if require_full_fields:
				missing = [f for f in SpecValidator.__REQUIRED_PATTERN_FIELDS if not str(spec.get(f) or '').strip()]
				if missing:
					joined = ', '.join(missing)
					issues.append({'code': 'INCOMPLETE_ARCH_SPEC_FIELDS', 'message': f'Pattern specification for {r} is missing required GoF field(s): {joined}'})
		return r
	# @used-by :func:`agent_tools.arch.spec.extract_declared_participants()`
	# @used-by :meth:`SpecValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	@staticmethod
	def extract_declared_participants(specs: list[dict]) -> list[str]:
		found: list[str] = []
		for spec in specs or ():
			raw = str(spec.get('participants') or '')
			tokens = SpecValidator.__BACKTICK_RE.findall(raw) or SpecValidator.__IDENT_RE.findall(raw)
			for tok in tokens:
				cand = tok.strip().strip('.,;:')
				if cand and cand not in found:
					found.append(cand)
		return found
	# @used-by :func:`agent_tools.arch.spec.extract_arch_specs()`
	# @used-by :meth:`SpecValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	@staticmethod
	def extract_specs(markdown_text: str) -> list[dict]:
		cleaned = SpecValidator.__FENCE_RE.sub('', markdown_text or '')
		specs: list[dict] = []
		cur: dict | None = None
		for line in cleaned.splitlines():
			key, val = SpecValidator.__parse_field_line(line)
			if key in ('pattern', 'idiom_exception'):
				if None is not cur:
					specs.append(cur)
				cur = SpecValidator.__start_spec_block(key, val)
			elif None is not key and None is not cur:
				cur[key] = val
			elif line.strip().startswith('#') and None is not cur:
				specs.append(cur)
				cur = None
		if None is not cur:
			specs.append(cur)
		return specs
	# @used-by :func:`agent_tools.arch.spec.validate_arch_spec_markdown()`
	# @used-by :meth:`Df.Harness.Arch.Evaluator.Evaluator.evaluate_response()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__build_package_payload()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.inspect_status()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.check_arch_policy()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions()`
	def validate(self, text: str, *, require_full_fields: bool=True) -> dict:
		cat = Catalog.load() if None is self.__catalog else self.__catalog
		specs = SpecValidator.extract_specs(text)
		issues: list[dict] = []
		patterns: list[str] = []
		idioms: list[dict] = []
		for spec in specs:
			if 'idiom_exception' == spec['kind']:
				ok_id = SpecValidator.__validate_idiom_spec(spec, cat, issues)
				if None is not ok_id:
					idioms.append(ok_id)
			else:
				pname = SpecValidator.__validate_pattern_spec(spec, cat, require_full_fields=require_full_fields, issues=issues)
				if None is not pname and pname not in patterns:
					patterns.append(pname)
		if not specs:
			issues.append({'code': 'MISSING_ARCH_PATTERN_SPEC', 'message': 'Architectural proposal lacks Software design pattern specification (Pattern, Category, Intent, Participants, Collaboration, Consequences, or idiom_exception per ARCH-1)'})
		return {'valid': not issues and bool(patterns or idioms), 'specs': specs, 'patterns': patterns, 'participants': SpecValidator.extract_declared_participants(specs), 'idiom_exceptions': idioms, 'issues': issues}
