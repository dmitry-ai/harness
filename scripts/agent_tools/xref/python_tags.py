# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import importlib
import re
import sys
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
_BARE_PY_TARGET_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*(?:\(\))?$')
_EXTERNAL_RUNNERS = frozenset({'CLI', 'cli', 'pre-commit', 'pytest', 'python', 'unittest'})
_SPHINX_RE = re.compile(r'^:(?:py:)?(attr|class|const|data|deco|exc|func|meth|mod|obj|type):`([^`\n]+)`(.*)$')
_TAG_RE = re.compile(r'^#\s*@(used-by|uses|see)\s+(.+?)\s*$')
# @used-by :func:`collect_file_uses()`
def _enclosing_scope_for_line(file_info: dict, lineno: int) -> tuple[str, str]:
	mod = file_info['module']
	best: dict | None = None
	for dinfo in file_info['defs']:
		if dinfo['dec_lineno'] <= lineno <= dinfo['end_lineno'] and (not dinfo['is_nested']):
			if None is best or dinfo['dec_lineno'] >= best['dec_lineno']:
				best = dinfo
	if None is best:
		r = (mod, 'mod')
	else:
		bqn = best['qualname']
		r = (f'{mod}.{bqn}', best['kind'])
	return r
# @used-by :func:`_probe_stdlib_parts()`
def _has_attr_chain(obj: object, attrs: list[str]) -> bool:
	r = True
	for attr in attrs:
		if hasattr(obj, attr):
			obj = getattr(obj, attr)
		else:
			r = False
			break
	return r
# @used-by :func:`resolve_stdlib_symbol()`
def _probe_stdlib_parts(parts: list[str]) -> bool:
	r = False
	for split in range(len(parts), 0, -1):
		mod_name = '.'.join(parts[:split])
		if mod_name.split('.')[0] not in sys.stdlib_module_names and 'builtins' != mod_name:
			continue
		try:
			obj = importlib.import_module(mod_name)
		except Exception:
			continue
		if _has_attr_chain(obj, parts[split:]):
			r = True
			break
	return r
# @used-by :func:`resolve_sphinx_target()`
def _resolve_in_repo(clean: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
	syms, classes, mods = (repo_index['symbols'], repo_index['classes'], repo_index['by_module'])
	local_key = f'{current_module}.{clean}' if current_module else clean
	if local_key in syms or local_key in classes:
		r: tuple[bool, str | None] = (True, local_key)
	elif clean in syms or clean in classes or clean in mods:
		r = (True, clean)
	else:
		r = _resolve_module_attr_in_repo(clean, current_module, repo_index)
	return r
# @used-by :func:`_resolve_in_repo()`
def _resolve_module_attr_in_repo(clean: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
	mods = repo_index['by_module']
	finfo = mods.get(current_module)
	r: tuple[bool, str | None] = (False, None)
	if None is not finfo and clean in finfo['top_names']:
		r = (True, f'{current_module}.{clean}')
	elif '.' in clean:
		mod_part, attr_part = clean.rsplit('.', 1)
		mf = mods.get(mod_part)
		if None is not mf and (attr_part in mf['top_names'] or attr_part in mf['classes']):
			r = (True, clean)
		elif None is not finfo and clean.split('.')[0] in finfo['imports']:
			head, rest = clean.split('.', 1)
			imp_base = finfo['imports'][head]
			mapped = f'{imp_base}.{rest}'
			if mapped in repo_index['symbols'] or mapped in repo_index['classes'] or resolve_stdlib_symbol(mapped):
				r = (True, mapped)
	return r
# @used-by :func:`parse_header_block()`
def _validate_tag_entry(entry: dict, rel_path: str, errs: list[str]) -> None:
	tag, lineno = (entry['tag'], entry['lineno'])
	if entry['sphinx_target']:
		if entry['sphinx_target'].startswith('self.'):
			errs.append(f'XREF: {rel_path}:{lineno} @{tag} must not use self. in # comments above def (use ClassName.method())')
	else:
		body = entry['raw_value']
		if 'self.' in body:
			errs.append(f'XREF: {rel_path}:{lineno} @{tag} must not use self. in # comments above def (use ClassName.method())')
		if _BARE_PY_TARGET_RE.match(body) and body not in _EXTERNAL_RUNNERS:
			errs.append(f'XREF: {rel_path}:{lineno} @{tag} target {body!r} must use a Sphinx role (e.g. :func:`...` or :meth:`...`)')
# @used-by :func:`agent_tools.xref.python_graph._add_uses_edges()`
# @used-by :func:`agent_tools.xref.python_sync._validate_file_uses_tags()`
def collect_file_uses(file_info: dict) -> list[dict]:
	header_owner: dict[int, tuple[str, str]] = {}
	mod = file_info['module']
	for dinfo in file_info['defs']:
		blk = parse_header_block(file_info['lines'], dinfo['dec_lineno'], file_info['rel_path'])
		owner_qn = dinfo['parent_resolvable'] if dinfo['is_nested'] else dinfo['qualname']
		owner_kind = 'meth' if (dinfo['is_method'] and not dinfo['is_nested']) else 'func'
		for ln in range(blk['start_line'], dinfo['dec_lineno']):
			header_owner[ln] = (f'{mod}.{owner_qn}', owner_kind)
	out: list[dict] = []
	for idx, raw in enumerate(file_info['lines'], 1):
		parsed = parse_tag_line(raw, idx)
		if None is not parsed and 'uses' == parsed['tag']:
			ckey, ckind = header_owner.get(idx) or _enclosing_scope_for_line(file_info, idx)
			out.append({**parsed, 'caller_key': ckey, 'caller_kind': ckind})
	return out
# @used-by :func:`agent_tools.xref.python_sync._expected_used_by_lines()`
# @used-by :func:`agent_tools.xref.python_sync._format_override_see()`
def format_ref(target_key: str, target_kind: str, current_module: str) -> str:
	if 'external' == target_kind:
		r = target_key
	elif 'mod' == target_kind:
		r = f':mod:`{target_key}`'
	else:
		role = 'meth' if 'meth' == target_kind else 'func'
		pref = f'{current_module}.'
		short = target_key[len(pref):] if current_module and target_key.startswith(pref) else target_key
		r = f':{role}:`{short}()`'
	return r
# @used-by :func:`agent_tools.xref.python_sync._collect_actual_used_by()`
# @used-by :func:`agent_tools.xref.python_sync._sync_def_edit()`
def is_valid_external_target(raw_value: str, repo_root: Path) -> bool:
	token = raw_value.split()[0] if raw_value.strip() else ''
	if token in _EXTERNAL_RUNNERS or token.startswith(('http://', 'https://')):
		r = True
	elif '/' in token or token.endswith(('.cmd', '.html', '.ini', '.java', '.js', '.json', '.md', '.ps1', '.sh', '.toml', '.ts', '.xml', '.yaml', '.yml')):
		r = (repo_root / token).exists() or token.startswith(('platforms/', 'rules/', 'scripts/', 'skills/', 'tests/'))
	else:
		r = False
	return r
# @used-by :func:`agent_tools.xref.python_sync._check_def_xref()`
# @used-by :func:`agent_tools.xref.python_sync._sync_def_edit()`
# @used-by :func:`agent_tools.xref.python_sync.check_python_file_local()`
# @used-by :func:`collect_file_uses()`
def parse_header_block(lines: list[str], anchor_line: int, rel_path: str='') -> dict:
	idx = anchor_line - 2
	block_lines: list[tuple[int, str]] = []
	while 0 <= idx and lines[idx].strip().startswith('#'):
		block_lines.append((idx + 1, lines[idx]))
		idx -= 1
	block_lines.reverse()
	prefix, used_by, uses, see, errs = ([], [], [], [], [])
	for ln, raw in block_lines:
		parsed = parse_tag_line(raw, ln)
		if None is parsed:
			prefix.append(raw)
		else:
			_validate_tag_entry(parsed, rel_path, errs)
			({'used-by': used_by, 'uses': uses, 'see': see}[parsed['tag']]).append(parsed)
	start_line = block_lines[0][0] if block_lines else anchor_line
	return {'prefix': prefix, 'see': see, 'start_line': start_line, 'syntax_errors': errs, 'used_by': used_by, 'uses': uses}
# @used-by :func:`collect_file_uses()`
# @used-by :func:`parse_header_block()`
def parse_tag_line(raw_line: str, lineno: int) -> dict | None:
	m = _TAG_RE.match(raw_line.strip())
	if None is m:
		r = None
	else:
		tag, rest = (m.group(1), m.group(2).strip())
		sm = _SPHINX_RE.match(rest)
		if None is sm:
			r = {'lineno': lineno, 'note': '', 'raw': raw_line, 'raw_value': rest, 'role': None, 'sphinx_target': None, 'tag': tag}
		else:
			r = {'lineno': lineno, 'note': sm.group(3).strip(), 'raw': raw_line, 'raw_value': rest, 'role': sm.group(1), 'sphinx_target': sm.group(2).strip(), 'tag': tag}
	return r
# @used-by :func:`agent_tools.xref.python_graph._add_uses_edges()`
# @used-by :func:`agent_tools.xref.python_sync._check_see_tags()`
# @used-by :func:`agent_tools.xref.python_sync._collect_actual_used_by()`
# @used-by :func:`agent_tools.xref.python_sync._validate_file_uses_tags()`
def resolve_sphinx_target(target_raw: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
	clean = target_raw[:-2] if target_raw.endswith('()') else target_raw
	ok, key = _resolve_in_repo(clean, current_module, repo_index)
	if (not ok) and resolve_stdlib_symbol(clean):
		ok, key = (True, clean)
	return (ok, key)
# @used-by :func:`_resolve_module_attr_in_repo()`
# @used-by :func:`agent_tools.xref.python_overrides._resolve_base_target()`
# @used-by :func:`agent_tools.xref.python_overrides._resolve_stdlib_base()`
# @used-by :func:`resolve_sphinx_target()`
@lru_cache(maxsize=512)
def resolve_stdlib_symbol(dotted: str) -> bool:
	parts = [p for p in dotted.split('.') if p]
	r = False
	if parts:
		if parts[0] in sys.stdlib_module_names or 'builtins' == parts[0]:
			r = _probe_stdlib_parts(parts)
		elif hasattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__, parts[0]):
			r = _probe_stdlib_parts(['builtins', *parts])
	return r
