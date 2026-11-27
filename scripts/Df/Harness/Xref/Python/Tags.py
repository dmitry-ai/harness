# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import builtins
import importlib
import re
import sys
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Tags:
	__BARE_PY_TARGET_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*(?:\(\))?$')
	__EXTERNAL_RUNNERS = frozenset({'CLI', 'cli', 'pre-commit', 'pytest', 'python', 'unittest', 'unused'})
	__SPHINX_RE = re.compile(r'^:(?:py:)?(attr|class|const|data|deco|exc|func|meth|mod|obj|type):`([^`\n]+)`(.*)$')
	__TAG_RE = re.compile(r'^#\s*@(used-by|uses|see)\s+(.+?)\s*$')
	# @used-by :func:`agent_tools.xref.python_tags.parse_header_block()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__check_def_xref()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__sync_def_edit()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.check_file_local()`
	# @used-by :meth:`Tags.collect_file_uses()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def __init__(self, lines: list[str], anchor_line: int, rel_path: str='') -> None:
		self.__lines = lines
		self.__anchor_line = anchor_line
		self.__rel_path = rel_path
	# @used-by :func:`agent_tools.xref.python_tags.parse_header_block()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__check_def_xref()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__sync_def_edit()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.check_file_local()`
	# @used-by :meth:`Tags.collect_file_uses()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def parse_header_block(self) -> dict:
		idx = self.__anchor_line - 2
		block_lines: list[tuple[int, str]] = []
		while 0 <= idx and self.__lines[idx].strip().startswith('#'):
			block_lines.append((idx + 1, self.__lines[idx]))
			idx -= 1
		block_lines.reverse()
		prefix, used_by, uses, see, errs = ([], [], [], [], [])
		for ln, raw in block_lines:
			parsed = Tags.parse_tag_line(raw, ln)
			if None is parsed:
				prefix.append(raw)
			else:
				Tags.__validate_tag_entry(parsed, self.__rel_path, errs)
				({'used-by': used_by, 'uses': uses, 'see': see}[parsed['tag']]).append(parsed)
		start_line = block_lines[0][0] if block_lines else self.__anchor_line
		return {'prefix': prefix, 'see': see, 'start_line': start_line, 'syntax_errors': errs, 'used_by': used_by, 'uses': uses}
	# @used-by :meth:`Tags.collect_file_uses()`
	@staticmethod
	def __enclosing_scope_for_line(file_info: dict, lineno: int) -> tuple[str, str]:
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
	# @used-by :meth:`Tags.__probe_stdlib_parts()`
	@staticmethod
	def __has_attr_chain(obj: object, attrs: list[str]) -> bool:
		r = True
		for attr in attrs:
			if hasattr(obj, attr):
				obj = getattr(obj, attr)
			else:
				r = False
				break
		return r
	# @used-by :meth:`Tags.resolve_stdlib_symbol()`
	@staticmethod
	def __probe_stdlib_parts(parts: list[str]) -> bool:
		r = False
		for split in range(len(parts), 0, -1):
			mod_name = '.'.join(parts[:split])
			if mod_name.split('.')[0] not in sys.stdlib_module_names and 'builtins' != mod_name:
				continue
			try:
				obj = importlib.import_module(mod_name)
			except Exception:
				continue
			if Tags.__has_attr_chain(obj, parts[split:]):
				r = True
				break
		return r
	# @used-by :meth:`Tags.resolve_sphinx_target()`
	@staticmethod
	def __resolve_in_repo(clean: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
		syms, classes, mods = (repo_index['symbols'], repo_index['classes'], repo_index['by_module'])
		local_key = f'{current_module}.{clean}' if current_module else clean
		if local_key in syms or local_key in classes:
			r: tuple[bool, str | None] = (True, local_key)
		elif clean in syms or clean in classes or clean in mods:
			r = (True, clean)
		else:
			r = Tags.__resolve_module_attr_in_repo(clean, current_module, repo_index)
		return r
	# @used-by :meth:`Tags.__resolve_in_repo()`
	@staticmethod
	def __resolve_module_attr_in_repo(clean: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
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
				mapped = f"{finfo['imports'][head]}.{rest}"
				if mapped in repo_index['symbols'] or mapped in repo_index['classes'] or Tags.resolve_stdlib_symbol(mapped):
					r = (True, mapped)
		return r
	# @used-by :meth:`Tags.parse_header_block()`
	@staticmethod
	def __validate_tag_entry(entry: dict, rel_path: str, errs: list[str]) -> None:
		tag, lineno = (entry['tag'], entry['lineno'])
		if entry['sphinx_target']:
			if entry['sphinx_target'].startswith('self.'):
				errs.append(f'XREF: {rel_path}:{lineno} @{tag} must not use self. in # comments above def (use ClassName.method())')
		else:
			body = entry['raw_value']
			if 'self.' in body:
				errs.append(f'XREF: {rel_path}:{lineno} @{tag} must not use self. in # comments above def (use ClassName.method())')
			if Tags.__BARE_PY_TARGET_RE.match(body) and body not in Tags.__EXTERNAL_RUNNERS:
				errs.append(f'XREF: {rel_path}:{lineno} @{tag} target {body!r} must use a Sphinx role (e.g. :func:`...` or :meth:`...`)')
	# @used-by :func:`agent_tools.xref.python_tags.collect_file_uses()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__add_uses_edges()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__validate_file_uses_tags()`
	@staticmethod
	def collect_file_uses(file_info: dict) -> list[dict]:
		header_owner: dict[int, tuple[str, str]] = {}
		mod = file_info['module']
		for dinfo in file_info['defs']:
			blk = Tags(file_info['lines'], dinfo['dec_lineno'], file_info['rel_path']).parse_header_block()
			owner_qn = dinfo['parent_resolvable'] if dinfo['is_nested'] else dinfo['qualname']
			owner_kind = 'meth' if (dinfo['is_method'] and not dinfo['is_nested']) else 'func'
			for ln in range(blk['start_line'], dinfo['dec_lineno']):
				header_owner[ln] = (f'{mod}.{owner_qn}', owner_kind)
		out: list[dict] = []
		for idx, raw in enumerate(file_info['lines'], 1):
			parsed = Tags.parse_tag_line(raw, idx)
			if None is not parsed and 'uses' == parsed['tag']:
				ckey, ckind = header_owner.get(idx) or Tags.__enclosing_scope_for_line(file_info, idx)
				out.append({**parsed, 'caller_key': ckey, 'caller_kind': ckind})
		return out
	# @used-by :func:`agent_tools.xref.python_tags.format_ref()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__expected_used_by_lines()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__format_override_see()`
	@staticmethod
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
	# @used-by :func:`agent_tools.xref.python_tags.is_valid_external_target()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__collect_actual_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__sync_def_edit()`
	@staticmethod
	def is_valid_external_target(raw_value: str, repo_root: Path) -> bool:
		token = raw_value.split()[0] if raw_value.strip() else ''
		if token in Tags.__EXTERNAL_RUNNERS or token.startswith(('http://', 'https://')):
			r = True
		elif '/' in token or token.endswith(('.cmd', '.html', '.ini', '.java', '.js', '.json', '.md', '.ps1', '.sh', '.toml', '.ts', '.xml', '.yaml', '.yml')):
			r = (repo_root / token).exists() or token.startswith(('platforms/', 'rules/', 'scripts/', 'skills/', 'tests/'))
		else:
			r = False
		return r
	# @used-by :func:`agent_tools.xref.python_tags.parse_tag_line()`
	# @used-by :meth:`Tags.collect_file_uses()`
	# @used-by :meth:`Tags.parse_header_block()`
	@staticmethod
	def parse_tag_line(raw_line: str, lineno: int) -> dict | None:
		m = Tags.__TAG_RE.match(raw_line.strip())
		if None is m:
			r = None
		else:
			tag, rest = (m.group(1), m.group(2).strip())
			sm = Tags.__SPHINX_RE.match(rest)
			if None is sm:
				r = {'lineno': lineno, 'note': '', 'raw': raw_line, 'raw_value': rest, 'role': None, 'sphinx_target': None, 'tag': tag}
			else:
				r = {'lineno': lineno, 'note': sm.group(3).strip(), 'raw': raw_line, 'raw_value': rest, 'role': sm.group(1), 'sphinx_target': sm.group(2).strip(), 'tag': tag}
		return r
	# @used-by :func:`agent_tools.xref.python_tags.resolve_sphinx_target()`
	# @used-by :meth:`Df.Harness.Xref.Python.Graph.Graph.__add_uses_edges()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__check_see_tags()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__collect_actual_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.__validate_file_uses_tags()`
	@staticmethod
	def resolve_sphinx_target(target_raw: str, current_module: str, repo_index: dict) -> tuple[bool, str | None]:
		clean = target_raw[:-2] if target_raw.endswith('()') else target_raw
		ok, key = Tags.__resolve_in_repo(clean, current_module, repo_index)
		if (not ok) and Tags.resolve_stdlib_symbol(clean):
			ok, key = (True, clean)
		return (ok, key)
	# @used-by :func:`agent_tools.xref.python_tags.resolve_stdlib_symbol()`
	# @used-by :meth:`Df.Harness.Xref.Python.Overrides.Overrides.__resolve_base_target()`
	# @used-by :meth:`Df.Harness.Xref.Python.Overrides.Overrides.__resolve_stdlib_base()`
	# @used-by :meth:`Tags.__resolve_module_attr_in_repo()`
	# @used-by :meth:`Tags.resolve_sphinx_target()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref_cov.DfHarnessS11Wave2bXrefCovTests.test_python_xref_covers_all_exports_with_overrides_and_stdlib_tags()`
	@staticmethod
	@lru_cache(maxsize=512)
	def resolve_stdlib_symbol(dotted: str) -> bool:
		parts = [p for p in dotted.split('.') if p]
		r = False
		if parts:
			if parts[0] in sys.stdlib_module_names or 'builtins' == parts[0]:
				r = Tags.__probe_stdlib_parts(parts)
			elif hasattr(builtins, parts[0]):
				r = Tags.__probe_stdlib_parts(['builtins', *parts])
		return r
