# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
_BARE_BLOCK_RE = re.compile(r'^\*?\s*@(used-by|uses)\b')
_EXT_RUNNERS = frozenset({'build.ps1', 'CLI', 'IntelliJ', 'JUnit', 'JVM', 'META-INF/plugin.xml', 'non-instantiable'})
_LINK_RE = re.compile(r'^\{@link\s+([^}]+)\}(.*)$')
_LIST_TAG_RE = re.compile(r'^\*?\s*-\s*@(used-by|uses)\s+(.+?)\s*$')
_SEE_TAG_RE = re.compile(r'^\*?\s*@see\s+(.+?)\s*$')
# @used-by :func:`parse_javadoc_block()`
def _parse_javadoc_lines(lines: list[str], start_idx: int, end_idx: int, rel_path: str) -> dict:
	desc, used_by, uses, see, errs = ([], [], [], [], [])
	for idx in range(start_idx, end_idx + 1):
		st = lines[idx].strip()
		if st in ('/**', '*/'):
			continue
		inner = st.removeprefix('/**').removesuffix('*/').strip()
		_classify_javadoc_line(inner, idx + 1, rel_path, desc, used_by, uses, see, errs)
	return {'desc_lines': desc, 'end_line': end_idx + 1, 'has_block': True, 'see': see, 'start_line': start_idx + 1, 'syntax_errors': errs, 'used_by': used_by, 'uses': uses}
# @used-by :func:`_parse_javadoc_lines()`
def _classify_javadoc_line(inner: str, lineno: int, rel_path: str, desc: list[str], used_by: list[dict], uses: list[dict], see: list[dict], errs: list[str]) -> None:
	bm = _BARE_BLOCK_RE.match(inner)
	lm = _LIST_TAG_RE.match(inner)
	sm = _SEE_TAG_RE.match(inner)
	if None is not bm:
		tag = bm.group(1)
		errs.append(f'XREF: {rel_path}:{lineno} Java Javadoc forbids bare @{tag} block tag (use "- @{tag} ...")')
	elif None is not lm:
		entry = _build_link_entry(lm.group(1), lm.group(2).strip(), lineno)
		(used_by if 'used-by' == lm.group(1) else uses).append(entry)
	elif None is not sm:
		see.append({'lineno': lineno, 'raw_value': sm.group(1).strip(), 'tag': 'see'})
	elif inner and '*' != inner:
		desc.append(inner.removeprefix('*').strip())
# @used-by :func:`_classify_javadoc_line()`
def _build_link_entry(tag: str, rest: str, lineno: int) -> dict:
	m = _LINK_RE.match(rest)
	if None is m:
		r = {'lineno': lineno, 'link_target': None, 'note': '', 'raw_value': rest, 'tag': tag}
	else:
		r = {'lineno': lineno, 'link_target': m.group(1).strip(), 'note': m.group(2).strip(), 'raw_value': rest, 'tag': tag}
	return r
# @used-by :func:`resolve_java_target()`
def _resolve_type_fqn(type_raw: str, current_finfo: dict, repo_index: dict) -> str | None:
	types = repo_index['types']
	pkg = current_finfo['package']
	cands = [type_raw]
	if pkg:
		cands.insert(0, f'{pkg}.{type_raw}')
	head = type_raw.split('.', 1)[0]
	if head in current_finfo['imports']:
		rest = type_raw[len(head):]
		cands.insert(0, current_finfo['imports'][head] + rest)
	r: str | None = None
	for c in cands:
		if c in types:
			r = c
			break
	if None is r:
		suffix = f'.{type_raw}'
		hits = [tfqn for tfqn in types if tfqn.endswith(suffix)]
		r = hits[0] if 1 == len(hits) else None
	return r
# @used-by :func:`agent_tools.xref.java_graph._add_java_uses_edges()`
# @used-by :func:`agent_tools.xref.java_sync._validate_java_file_uses()`
def collect_file_java_uses(finfo: dict) -> list[dict]:
	out: list[dict] = []
	for dinfo in finfo['defs']:
		hdr = parse_javadoc_block(finfo['lines'], dinfo['doc_anchor_line'], finfo['rel_path'])
		caller = dinfo['enclosing_res'] if dinfo['is_anon'] else dinfo['symbol_key']
		for entry in hdr['uses']:
			out.append({**entry, 'caller_key': caller})
	return out
# @used-by :func:`agent_tools.xref.java_sync._check_java_override()`
# @used-by :func:`agent_tools.xref.java_sync._expected_java_used_by()`
# @used-by :func:`agent_tools.xref.java_sync._sync_java_def_edit()`
def format_java_ref(target_key: str, current_finfo: dict, repo_index: dict, *, wrap_link: bool=True) -> str:
	if '#' not in target_key and target_key not in repo_index['types']:
		r = target_key
	else:
		t_fqn, sig = target_key.split('#', 1) if '#' in target_key else (target_key, '')
		disp = _shorten_java_type(t_fqn, current_finfo, repo_index)
		ref = f'{disp}#{sig}' if sig else disp
		r = f'{{@link {ref}}}' if wrap_link else ref
	return r
# @used-by :func:`format_java_ref()`
def _shorten_java_type(t_fqn: str, current_finfo: dict, repo_index: dict) -> str:
	tinfo = repo_index['types'].get(t_fqn)
	if None is not tinfo:
		tpkg, tqual = (tinfo['package'], tinfo['qualname'])
		top = tqual.split('.', 1)[0]
		if tpkg == current_finfo['package'] or current_finfo['imports'].get(top) == (f'{tpkg}.{top}' if tpkg else top):
			r = tqual
		else:
			r = t_fqn
	else:
		simple = t_fqn.rsplit('.', 1)[-1]
		if current_finfo['imports'].get(simple) == t_fqn or t_fqn.startswith('java.lang.'):
			r = simple
		else:
			r = t_fqn
	return r
# @used-by :func:`agent_tools.xref.java_sync._collect_actual_java_used_by()`
# @used-by :func:`agent_tools.xref.java_sync._sync_java_def_edit()`
def is_valid_java_external(raw_value: str, repo_root: Path) -> bool:
	token = raw_value.split()[0] if raw_value.strip() else ''
	if token in _EXT_RUNNERS or token.startswith(('http://', 'https://')):
		r = True
	elif '/' in token or token.endswith(('.gradle', '.java', '.json', '.kts', '.md', '.ps1', '.xml')):
		r = (repo_root / token).exists() or token.startswith(('META-INF/', 'src/'))
	else:
		r = False
	return r
# @used-by :func:`agent_tools.xref.java_sync._check_java_def()`
# @used-by :func:`agent_tools.xref.java_sync._sync_java_def_edit()`
# @used-by :func:`agent_tools.xref.java_sync.check_java_file_local()`
# @used-by :func:`collect_file_java_uses()`
def parse_javadoc_block(lines: list[str], anchor_line: int, rel_path: str='') -> dict:
	end_idx = anchor_line - 2
	r = {'desc_lines': [], 'end_line': anchor_line - 1, 'has_block': False, 'see': [], 'start_line': anchor_line, 'syntax_errors': [], 'used_by': [], 'uses': []}
	if 0 <= end_idx and lines[end_idx].strip().endswith('*/'):
		start_idx = end_idx
		while 0 <= start_idx and (not lines[start_idx].strip().startswith('/*')):
			start_idx -= 1
		if 0 <= start_idx and lines[start_idx].strip().startswith('/**'):
			r = _parse_javadoc_lines(lines, start_idx, end_idx, rel_path)
	return r
_JAVA_LANG_TYPES = frozenset({'AutoCloseable', 'Comparable', 'Iterable', 'Object', 'Runnable', 'Thread', 'Throwable'})
# @used-by :func:`agent_tools.xref.java_graph._add_java_uses_edges()`
# @used-by :func:`agent_tools.xref.java_sync._collect_actual_java_used_by()`
# @used-by :func:`agent_tools.xref.java_sync._validate_java_file_uses()`
def resolve_java_target(raw_target: str, current_finfo: dict, repo_index: dict) -> tuple[bool, str | None]:
	t_part, m_part = raw_target.split('#', 1) if '#' in raw_target else (raw_target, '')
	t_clean = t_part.strip()
	t_fqn = _resolve_type_fqn(t_clean, current_finfo, repo_index) if t_clean else None
	if None is not t_fqn:
		r = _resolve_repo_java_member(t_fqn, m_part, repo_index)
	else:
		r = _resolve_external_java_ref(t_clean, m_part, current_finfo)
	return r
# @used-by :func:`resolve_java_target()`
def _resolve_external_java_ref(t_clean: str, m_part: str, current_finfo: dict) -> tuple[bool, str | None]:
	head = t_clean.split('.', 1)[0] if t_clean else ''
	if head in current_finfo['imports']:
		fqn = current_finfo['imports'][head] + t_clean[len(head):]
		r: tuple[bool, str | None] = (True, f'{fqn}#{m_part.strip()}' if m_part else fqn)
	elif t_clean in _JAVA_LANG_TYPES or t_clean.startswith(('java.', 'javax.', 'com.intellij.', 'org.jetbrains.')):
		fqn = f'java.lang.{t_clean}' if t_clean in _JAVA_LANG_TYPES else t_clean
		r = (True, f'{fqn}#{m_part.strip()}' if m_part else fqn)
	else:
		r = (False, None)
	return r
# @used-by :func:`resolve_java_target()`
def _resolve_repo_java_member(t_fqn: str, m_part: str, repo_index: dict) -> tuple[bool, str | None]:
	if not m_part:
		r: tuple[bool, str | None] = (True, t_fqn)
	else:
		clean_m = re.sub(r'\s+', ' ', m_part.strip()).replace('( ', '(').replace(' )', ')')
		cand = f'{t_fqn}#{clean_m}'
		if cand in repo_index['symbols']:
			r = (True, cand)
		else:
			mname = clean_m.split('(', 1)[0]
			hits = [sk for sk in repo_index['symbols'] if sk.startswith(f'{t_fqn}#{mname}(')]
			r = (True, hits[0]) if 1 == len(hits) else (False, None)
	return r
