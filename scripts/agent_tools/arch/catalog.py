# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
from pathlib import Path
import json
import re
_CATALOG_CACHE: dict[str, dict] = {}
_PAREN_RE = re.compile(r'\(([^()]+)\)')
_STRIP_MD_RE = re.compile(r'[*_`"\'\u00ab\u00bb]+')
# @used-by :func:`load_pattern_catalog()`
# @used-by :func:`lookup_pattern()`
def _build_lookup_index(patterns: list[dict]) -> dict[str, dict]:
	index: dict[str, dict] = {}
	for entry in patterns:
		name = str(entry.get('name') or '').strip()
		if not name:
			continue
		index[_clean_pattern_token(name)] = entry
		for alias in entry.get('aliases') or ():
			tok = _clean_pattern_token(str(alias))
			if tok and tok not in index:
				index[tok] = entry
	return index
# @used-by :func:`_build_lookup_index()`
# @used-by :func:`_candidate_pattern_keys()`
def _clean_pattern_token(raw: str) -> str:
	cleaned = _STRIP_MD_RE.sub('', str(raw or ''))
	cleaned = re.sub(r'\s+', ' ', cleaned).strip().rstrip('.,;:').strip()
	return cleaned.casefold()
# @used-by :func:`lookup_pattern()`
def _candidate_pattern_keys(raw: str) -> list[str]:
	keys: list[str] = []
	base = str(raw or '').strip()
	without_paren = _PAREN_RE.sub('', base).strip()
	candidates = [base, without_paren, *_PAREN_RE.findall(base)]
	for item in list(candidates):
		for sep in ('/', '\u2014', '\u2013', ','):
			if sep in item:
				candidates.extend(item.split(sep))
	for cand in candidates:
		tok = _clean_pattern_token(cand)
		if tok and tok not in keys:
			keys.append(tok)
	return keys
# @used-by :func:`load_pattern_catalog()`
def _resolve_catalog_path(primary: str | Path | None) -> Path:
	if None is not primary:
		r = Path(primary).resolve() / 'references/architecture/patterns-catalog.json'
	else:
		local = Path(__file__).resolve().parents[3] / 'references/architecture/patterns-catalog.json'
		if local.is_file():
			r = local
		else:
			from ..runtime import PRIMARY
			r = Path(PRIMARY).resolve() / 'references/architecture/patterns-catalog.json'
	return r
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_catalog_loads_canonical_patterns_and_resolves_aliases()`
# @used-by :mod:`agent_tools.arch.catalog`
# @used-by :mod:`agent_tools.arch`
def catalog_pattern_names(*, catalog: dict | None=None) -> set[str]:
	cat = load_pattern_catalog() if None is catalog else catalog
	return {str(entry['name']) for entry in cat.get('patterns') or () if entry.get('name')}
# @used-by :func:`agent_tools.arch.spec.validate_arch_spec_markdown()`
# @used-by :func:`catalog_pattern_names()`
# @used-by :func:`lookup_pattern()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_catalog_loads_canonical_patterns_and_resolves_aliases()`
# @used-by :mod:`agent_tools.arch.catalog`
# @used-by :mod:`agent_tools.arch`
def load_pattern_catalog(primary: str | Path | None=None) -> dict:
	path = _resolve_catalog_path(primary)
	key = str(path)
	cached = _CATALOG_CACHE.get(key)
	if None is not cached:
		r = cached
	else:
		data = json.loads(path.read_text(encoding='utf-8'))
		data['_lookup'] = _build_lookup_index(list(data.get('patterns') or ()))
		_CATALOG_CACHE[key] = data
		r = data
	return r
# @used-by :func:`agent_tools.arch.spec._validate_idiom_spec()`
# @used-by :func:`agent_tools.arch.spec._validate_pattern_spec()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_catalog_loads_canonical_patterns_and_resolves_aliases()`
# @used-by :mod:`agent_tools.arch.catalog`
# @used-by :mod:`agent_tools.arch`
def lookup_pattern(name: str, *, catalog: dict | None=None) -> dict | None:
	cat = load_pattern_catalog() if None is catalog else catalog
	index = cat.get('_lookup') or _build_lookup_index(list(cat.get('patterns') or ()))
	r: dict | None = None
	for key in _candidate_pattern_keys(name):
		hit = index.get(key)
		if None is not hit:
			r = hit
			break
	return r
__all__ = ['catalog_pattern_names', 'load_pattern_catalog', 'lookup_pattern']