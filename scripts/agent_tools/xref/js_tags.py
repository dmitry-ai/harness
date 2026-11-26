# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import posixpath
from pathlib import Path
import re
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
_BARE_JS_RE = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$.#]*(?:\(\))?$')
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
_EXT_RUNNERS = frozenset({'browser', 'CDP', 'chrome', 'CLI', 'cli', 'DOM', 'electron', 'Electron', 'IPC', 'node', 'node:test', 'npm', 'playwright', 'PowerShell', 'unused', 'VBS', 'Windows'})
_IMPORT_LINK_RE = re.compile(r"^import\(['\"]([^'\"]+)['\"]\)(?:\.([A-Za-z0-9_$.#]+))?$")
_LINK_RE = re.compile(r'^\{@link\s+([^}\s]+)(?:\s+([^}]+))?\}(.*)$')
_NOTE_LOCAL_RE = re.compile(r'^\(([A-Za-z0-9_$.#]+)\)$')
_TAG_LINE_RE = re.compile(r'^\*?\s*@(used-by|uses|see|override)(?:\s+(.*?))?\s*$')
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
# @used-by :func:`collect_file_js_uses()`
def _enclosing_or_next_def(finfo: dict, end_line: int) -> str:
	toks = finfo['tokens']
	r = '*module*'
	for dinfo in finfo['defs']:
		end_ln = toks[dinfo['body_end']][2] if dinfo['body_end'] < len(toks) else dinfo['lineno']
		if dinfo['lineno'] == end_line + 1:
			r = dinfo['qualname']
			break
		if dinfo['lineno'] <= end_line <= end_ln:
			r = dinfo['qualname']
	return r
# @used-by :func:`resolve_js_link()`
def _resolve_import_link(target_raw: str, note: str, current_rel: str, repo_index: dict) -> tuple[bool, str | None]:
	m = _IMPORT_LINK_RE.match(target_raw)
	if None is m:
		r: tuple[bool, str | None] = (False, None)
	else:
		spec, member = (m.group(1), m.group(2))
		target_rel = resolve_js_module_path(current_rel, spec, repo_index['files'])
		if None is target_rel:
			r = (False, None)
		elif member:
			r = _resolve_member_in_file(target_rel, member, repo_index)
		else:
			nm = _NOTE_LOCAL_RE.match(note.strip())
			r = _resolve_member_in_file(target_rel, nm.group(1), repo_index) if nm else (True, f'{target_rel}::*module*')
	return r
# @used-by :func:`_resolve_import_link()`
# @used-by :func:`resolve_js_link()`
def _resolve_member_in_file(rel: str, member: str, repo_index: dict) -> tuple[bool, str | None]:
	finfo = repo_index['files'].get(rel)
	syms = repo_index['symbols']
	if None is finfo:
		r: tuple[bool, str | None] = (False, None)
	elif f'{rel}::{member}' in syms:
		r = (True, f'{rel}::{member}')
	elif member in finfo['exports'] and f"{rel}::{finfo['exports'][member]}" in syms:
		mapped = finfo['exports'][member]
		r = (True, f'{rel}::{mapped}')
	elif member in finfo['classes']:
		r = (True, f'{rel}::{member}')
	elif member.endswith('()') and f'{rel}::{member[:-2]}' in syms:
		r = (True, f'{rel}::{member[:-2]}')
	else:
		r = (False, None)
	return r
# @used-by :func:`_parse_jsdoc_lines()`
def _validate_jsdoc_entry(entry: dict, rel_path: str, errs: list[str]) -> None:
	tag, ln = (entry['tag'], entry['lineno'])
	if None is entry['link_target']:
		body = entry['raw_value']
		if _BARE_JS_RE.match(body) and body not in _EXT_RUNNERS:
			errs.append(f'XREF: {rel_path}:{ln} @{tag} target {body!r} must use {{@link ...}}')
# @used-by :func:`agent_tools.xref.js_graph._add_js_uses_edges()`
# @used-by :func:`agent_tools.xref.js_sync._validate_js_file_uses()`
def collect_file_js_uses(finfo: dict) -> list[dict]:
	lines = finfo['lines']
	out: list[dict] = []
	i, n = (0, len(lines))
	while i < n:
		if lines[i].strip().startswith('/**'):
			j = i
			while j < n and '*/' not in lines[j]:
				j += 1
			owner = _enclosing_or_next_def(finfo, j + 1)
			for k in range(i, min(j + 1, n)):
				parsed = parse_jsdoc_tag_line(lines[k], k + 1)
				if None is not parsed and 'uses' == parsed['tag']:
					out.append({**parsed, 'caller_key': f"{finfo['rel_path']}::{owner}"})
			i = j + 1
		else:
			i += 1
	return out
# @used-by :func:`agent_tools.xref.js_sync._check_js_override()`
# @used-by :func:`agent_tools.xref.js_sync._expected_js_used_by()`
# @used-by :func:`agent_tools.xref.js_sync._sync_js_def_edit()`
def format_js_ref(caller_key: str, current_rel: str, repo_index: dict) -> str:
	if '::' not in caller_key:
		r = caller_key
	else:
		t_rel, qn = caller_key.split('::', 1)
		if t_rel == current_rel:
			r = f"{{@link import('./{posixpath.basename(t_rel)}')}}" if '*module*' == qn else f'{{@link {qn}}}'
		else:
			rel_spec = relative_js_spec(current_rel, t_rel)
			if '*module*' == qn:
				r = f"{{@link import('{rel_spec}')}}"
			else:
				r = _format_cross_file_symbol(t_rel, qn, rel_spec, repo_index)
	return r
# @used-by :func:`format_js_ref()`
def _format_cross_file_symbol(t_rel: str, qn: str, rel_spec: str, repo_index: dict) -> str:
	finfo = repo_index['files'].get(t_rel)
	root_sym = qn.split('#', 1)[0]
	exp_name = None
	if None is not finfo:
		for ek, local in finfo['exports'].items():
			if local == root_sym and 'default' != ek:
				exp_name = ek
				break
	if None is not exp_name:
		suffix = qn[len(root_sym):]
		r = f"{{@link import('{rel_spec}').{exp_name}{suffix}}}"
	else:
		r = f"{{@link import('{rel_spec}')}} ({qn})"
	return r
# @used-by :func:`agent_tools.xref.js_sync._collect_actual_js_used_by()`
# @used-by :func:`agent_tools.xref.js_sync._sync_js_def_edit()`
def is_valid_js_external(raw_value: str, repo_root: Path) -> bool:
	token = raw_value.split()[0] if raw_value.strip() else ''
	if token in _EXT_RUNNERS or token.startswith(('http://', 'https://')):
		r = True
	elif '/' in token or token.endswith(('.cjs', '.cmd', '.css', '.html', '.js', '.json', '.md', '.mjs', '.ps1', '.py', '.sh', '.ts', '.vbs', '.xml')):
		r = (repo_root / token).exists() or token.startswith(('browser_extension/', 'CSS/', 'Folders/', 'Multi-Account/', 'Titlebar-Badges/', 'Upgrade/'))
	else:
		r = False
	return r
# @used-by :func:`agent_tools.xref.js_sync._check_js_def()`
# @used-by :func:`agent_tools.xref.js_sync._sync_js_def_edit()`
# @used-by :func:`agent_tools.xref.js_sync.check_js_file_local()`
def parse_jsdoc_block(lines: list[str], anchor_line: int, rel_path: str='') -> dict:
	end_idx = anchor_line - 2
	r = {'desc_lines': [], 'end_line': anchor_line - 1, 'has_block': False, 'has_jsdoc_override': False, 'see': [], 'start_line': anchor_line, 'syntax_errors': [], 'used_by': [], 'uses': []}
	if 0 <= end_idx and lines[end_idx].strip().endswith('*/'):
		start_idx = end_idx
		while 0 <= start_idx and (not lines[start_idx].strip().startswith('/*')):
			start_idx -= 1
		if 0 <= start_idx and lines[start_idx].strip().startswith('/**'):
			r = _parse_jsdoc_lines(lines, start_idx, end_idx, rel_path)
	return r
# @used-by :func:`parse_jsdoc_block()`
def _parse_jsdoc_lines(lines: list[str], start_idx: int, end_idx: int, rel_path: str) -> dict:
	desc, used_by, uses, see, errs = ([], [], [], [], [])
	has_ov = False
	for idx in range(start_idx, end_idx + 1):
		raw = lines[idx]
		st = raw.strip()
		if st in ('/**', '*/'):
			continue
		inner = st.removeprefix('/**').removesuffix('*/').strip()
		parsed = parse_jsdoc_tag_line(inner, idx + 1)
		if None is parsed:
			if inner and '*' != inner:
				desc.append(inner.removeprefix('*').strip())
		elif 'override' == parsed['tag']:
			has_ov = True
		else:
			_validate_jsdoc_entry(parsed, rel_path, errs)
			({'used-by': used_by, 'uses': uses, 'see': see}[parsed['tag']]).append(parsed)
	return {'desc_lines': desc, 'end_line': end_idx + 1, 'has_block': True, 'has_jsdoc_override': has_ov, 'see': see, 'start_line': start_idx + 1, 'syntax_errors': errs, 'used_by': used_by, 'uses': uses}
# @used-by :func:`_parse_jsdoc_lines()`
# @used-by :func:`collect_file_js_uses()`
def parse_jsdoc_tag_line(raw_line: str, lineno: int) -> dict | None:
	m = _TAG_LINE_RE.match(raw_line.strip())
	if None is m:
		r = None
	else:
		tag, rest = (m.group(1), (m.group(2) or '').strip())
		lm = _LINK_RE.match(rest)
		if None is lm:
			r = {'lineno': lineno, 'link_target': None, 'note': '', 'raw': raw_line, 'raw_value': rest, 'tag': tag}
		else:
			note = ((lm.group(2) or '') + ' ' + (lm.group(3) or '')).strip()
			r = {'lineno': lineno, 'link_target': lm.group(1).strip(), 'note': note, 'raw': raw_line, 'raw_value': rest, 'tag': tag}
	return r
# @used-by :func:`format_js_ref()`
def relative_js_spec(from_rel: str, to_rel: str) -> str:
	rel = posixpath.relpath(to_rel, posixpath.dirname(from_rel) or '.')
	return rel if rel.startswith('.') else f'./{rel}'
# @used-by :func:`agent_tools.xref.js_graph._add_js_uses_edges()`
# @used-by :func:`agent_tools.xref.js_sync._check_js_see_tags()`
# @used-by :func:`agent_tools.xref.js_sync._collect_actual_js_used_by()`
# @used-by :func:`agent_tools.xref.js_sync._validate_js_file_uses()`
def resolve_js_link(target_raw: str, note: str, current_rel: str, repo_index: dict) -> tuple[bool, str | None]:
	if target_raw.startswith('import('):
		r = _resolve_import_link(target_raw, note, current_rel, repo_index)
	else:
		r = _resolve_member_in_file(current_rel, target_raw, repo_index)
	return r
# @used-by :func:`_resolve_import_link()`
# @used-by :func:`agent_tools.xref.js_graph._record_js_word_ref()`
# @used-by :func:`agent_tools.xref.js_graph._record_obj_member_call()`
# @used-by :func:`agent_tools.xref.js_graph._resolve_js_class()`
# @used-by :func:`agent_tools.xref.js_graph._resolve_js_ns_class()`
# @used-by :func:`agent_tools.xref.js_graph._scan_js_inline_require()`
def resolve_js_module_path(from_rel: str, spec: str, files: dict[str, dict]) -> str | None:
	r: str | None = None
	if spec.startswith('.'):
		base_dir = posixpath.dirname(from_rel)
		joined = posixpath.normpath(posixpath.join(base_dir, spec))
		cands = [joined]
		if not joined.endswith(('.js', '.mjs', '.cjs', '.ts', '.tsx')):
			cands.extend((f'{joined}.js', f'{joined}.ts', f'{joined}.mjs', f'{joined}.cjs', f'{joined}/index.js', f'{joined}/index.ts'))
		for c in cands:
			if c in files:
				r = c
				break
	return r
