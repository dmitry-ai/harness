# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
import re
from .catalog import load_pattern_catalog, lookup_pattern
_BACKTICK_RE = re.compile(r'`([^`\r\n]+)`')
_FENCE_RE = re.compile(r'```[\s\S]*?```')
_FIELD_LINE_RE = re.compile(r'^\s*(?:[-*+]|\d+[.)])?\s*(?:\*\*|__)?([A-Za-z_ \u0400-\u04ff]+?)(?:\*\*|__)?\s*[:\u2014]\s*(?:\*\*|__)?\s*(.+?)\s*$')
_INLINE_CAT_RE = re.compile(r'\(\s*`?(Creational|Structural|Behavioral|Concurrency|Architectural)`?\s*\)', re.I)
_IDENT_RE = re.compile(r'\b[A-Za-z_][A-Za-z0-9_./-]*\b')
_MIN_RATIONALE_CHARS = 20
_KEY_MAP = {
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
_REQUIRED_PATTERN_FIELDS = ('pattern', 'category', 'intent', 'participants', 'collaboration', 'consequences')
# @used-by :func:`extract_arch_specs()`
def _parse_field_line(line: str) -> tuple[str | None, str]:
	m = _FIELD_LINE_RE.match(line)
	if None is m:
		r = (None, '')
	else:
		raw_key = ' '.join(m.group(1).strip().casefold().split())
		r = (_KEY_MAP.get(raw_key), m.group(2).strip())
	return r
# @used-by :func:`extract_arch_specs()`
def _start_spec_block(key: str, val: str) -> dict:
	kind = 'idiom_exception' if 'idiom_exception' == key else 'pattern'
	spec: dict = {'kind': kind, 'pattern': val}
	if 'pattern' == kind:
		m_cat = _INLINE_CAT_RE.search(val)
		if None is not m_cat:
			spec['category'] = m_cat.group(1).capitalize()
	return spec
# @used-by :func:`validate_arch_spec_markdown()`
def _validate_idiom_spec(spec: dict, cat: dict, issues: list[dict]) -> dict | None:
	raw_pat = str(spec.get('pattern') or '').strip()
	hit = lookup_pattern(raw_pat, catalog=cat)
	native_c = str(spec.get('native_construct') or '').strip()
	rationale = str(spec.get('rationale') or '').strip()
	parts = str(spec.get('participants') or '').strip()
	missing = [k for k, v in (('Native Construct', native_c), ('Rationale', rationale), ('Participants', parts)) if not v]
	if None is hit:
		issues.append({'code': 'INVALID_IDIOM_EXCEPTION', 'message': f'idiom_exception must reference a canonical displaced pattern from patterns-catalog.json, got {raw_pat!r}'})
		r = None
	elif missing or _MIN_RATIONALE_CHARS > len(rationale):
		joined = ', '.join(missing)
		detail = f'missing {joined}' if missing else f'Rationale must be >= {_MIN_RATIONALE_CHARS} characters'
		pname = hit['name']
		issues.append({'code': 'INVALID_IDIOM_EXCEPTION', 'message': f'Invalid idiom_exception for {pname}: {detail}'})
		r = None
	else:
		r = {'pattern': hit['name'], 'native_construct': native_c, 'rationale': rationale, 'participants': parts}
	return r
# @used-by :func:`validate_arch_spec_markdown()`
def _validate_pattern_spec(spec: dict, cat: dict, *, require_full_fields: bool, issues: list[dict]) -> str | None:
	raw_pat = str(spec.get('pattern') or '').strip()
	hit = lookup_pattern(raw_pat, catalog=cat)
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
			missing = [f for f in _REQUIRED_PATTERN_FIELDS if not str(spec.get(f) or '').strip()]
			if missing:
				joined = ', '.join(missing)
				issues.append({'code': 'INCOMPLETE_ARCH_SPEC_FIELDS', 'message': f'Pattern specification for {r} is missing required GoF field(s): {joined}'})
	return r
# @used-by :func:`validate_arch_spec_markdown()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_accepts_gof_ru_and_idiom_exception()`
# @used-by :mod:`agent_tools.arch.spec`
# @used-by :mod:`agent_tools.arch`
def extract_arch_specs(markdown_text: str) -> list[dict]:
	cleaned = _FENCE_RE.sub('', markdown_text or '')
	specs: list[dict] = []
	cur: dict | None = None
	for line in cleaned.splitlines():
		key, val = _parse_field_line(line)
		if key in ('pattern', 'idiom_exception'):
			if None is not cur:
				specs.append(cur)
			cur = _start_spec_block(key, val)
		elif None is not key and None is not cur:
			cur[key] = val
		elif line.strip().startswith('#') and None is not cur:
			specs.append(cur)
			cur = None
	if None is not cur:
		specs.append(cur)
	return specs
# @used-by :func:`validate_arch_spec_markdown()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_accepts_gof_ru_and_idiom_exception()`
# @used-by :mod:`agent_tools.arch.spec`
# @used-by :mod:`agent_tools.arch`
def extract_declared_participants(specs: list[dict]) -> list[str]:
	found: list[str] = []
	for spec in specs or ():
		raw = str(spec.get('participants') or '')
		tokens = _BACKTICK_RE.findall(raw) or _IDENT_RE.findall(raw)
		for tok in tokens:
			cand = tok.strip().strip('.,;:')
			if cand and cand not in found:
				found.append(cand)
	return found
# @used-by :func:`agent_tools.arch.evaluator.evaluate_response_architecture()`
# @used-by :func:`agent_tools.arch.review_store._build_package_payload()`
# @used-by :func:`agent_tools.arch.review_store.inspect_arch_status()`
# @used-by :func:`agent_tools.issues.linter._check_arch_policy()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_accepts_gof_ru_and_idiom_exception()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_spec_validator_rejects_unknown_mismatched_and_incomplete_specs()`
# @used-by :mod:`agent_tools.arch.spec`
# @used-by :mod:`agent_tools.arch`
def validate_arch_spec_markdown(text: str, *, require_full_fields: bool=True, catalog: dict | None=None) -> dict:
	cat = load_pattern_catalog() if None is catalog else catalog
	specs = extract_arch_specs(text)
	issues: list[dict] = []
	patterns: list[str] = []
	idioms: list[dict] = []
	for spec in specs:
		if 'idiom_exception' == spec['kind']:
			ok_id = _validate_idiom_spec(spec, cat, issues)
			if None is not ok_id:
				idioms.append(ok_id)
		else:
			pname = _validate_pattern_spec(spec, cat, require_full_fields=require_full_fields, issues=issues)
			if None is not pname and pname not in patterns:
				patterns.append(pname)
	if not specs:
		issues.append({'code': 'MISSING_ARCH_PATTERN_SPEC', 'message': 'Architectural proposal lacks Software design pattern specification (Pattern, Category, Intent, Participants, Collaboration, Consequences, or idiom_exception per ARCH-1)'})
	return {'valid': not issues and bool(patterns or idioms), 'specs': specs, 'patterns': patterns, 'participants': extract_declared_participants(specs), 'idiom_exceptions': idioms, 'issues': issues}
__all__ = ['extract_arch_specs', 'extract_declared_participants', 'validate_arch_spec_markdown']