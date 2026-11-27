# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.text.source import df_line_indent
from Df.Harness.Xref.Java.Lexer import Lexer
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Model:
	SKIP_PARTS = frozenset({'.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'out', 'target', 'venv', '\ua616', '\ua66e'})
	__JAVA_MODS = frozenset({'abstract', 'default', 'final', 'native', 'non-sealed', 'private', 'protected', 'public', 'sealed', 'static', 'strictfp', 'synchronized', 'transient', 'volatile'})
	__TYPE_KW = frozenset({'class', 'enum', 'interface', 'record'})
	# @used-by :func:`agent_tools.xref.java_model.build_java_repo_index()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.check_repo()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.sync()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_java_xref_classes_tokenize_index_graph_and_sync()`
	def __init__(self, repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> None:
		self.__repo_root = Path(repo_root).resolve()
		self.__overrides_map = overrides_map
	# @used-by :func:`agent_tools.xref.java_model.build_java_repo_index()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.check_repo()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.sync()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_java_xref_classes_tokenize_index_graph_and_sync()`
	def build_repo_index(self) -> dict:
		files, symbols, types, methods_by_name = ({}, {}, {}, {})
		for rel, src in Model.discover_files(self.__repo_root, overrides_map=self.__overrides_map):
			finfo = Model.index_file(rel, src)
			files[rel] = finfo
			for tfqn, tinfo in finfo['types'].items():
				types[tfqn] = {**tinfo, 'package': finfo['package'], 'rel_path': rel}
			for dinfo in finfo['defs']:
				skey = dinfo['symbol_key']
				symbols[skey] = {**dinfo, 'package': finfo['package'], 'rel_path': rel}
				methods_by_name.setdefault(dinfo['name'], []).append(skey)
		return {'files': files, 'methods_by_name': methods_by_name, 'repo_root': self.__repo_root, 'symbols': symbols, 'types': types}
	# @used-by :meth:`Model.__parse_type_body_item()`
	@staticmethod
	def __consume_modifiers(toks: list[tuple[str, str, int]], start: int, end: int) -> tuple[int, int, set[str], bool]:
		i, anchor_ln, mods, has_ov = (start, toks[start][2], set(), False)
		while i < end:
			t = toks[i][1]
			if '@' == t:
				if i + 1 < end and 'Override' == toks[i + 1][1]:
					has_ov = True
				i = Lexer.skip_annotation(toks, i, end)
			elif t in Model.__JAVA_MODS:
				mods.add(t)
				i += 1
			else:
				break
		return (i, anchor_ln, mods, has_ov)
	# @used-by :meth:`Model.__parse_member()`
	@staticmethod
	def __find_decl_end(toks: list[tuple[str, str, int]], start: int, end: int) -> int:
		i, r = (start, end)
		while i < end:
			t = toks[i][1]
			if ';' == t:
				r = i + 1
				break
			if '{' == t:
				r = Lexer.match_delim(toks, i, '{', '}') + 1
				break
			i += 1
		return r
	# @used-by :meth:`Model.__parse_member()`
	@staticmethod
	def __find_method_paren(toks: list[tuple[str, str, int]], start: int, end: int) -> int:
		i, r = (start, -1)
		while i < end:
			t = toks[i][1]
			if t in (';', '=', '{'):
				break
			if '<' == t:
				i = Lexer.match_delim(toks, i, '<', '>') + 1
				continue
			if '@' == t:
				i = Lexer.skip_annotation(toks, i, end)
				continue
			if '(' == t and i > start and 'word' == toks[i - 1][0]:
				r = i
				break
			i += 1
		return r
	# @used-by :meth:`Model.__parse_type_body()`
	@staticmethod
	def __is_enum_const_region(toks: list[tuple[str, str, int]], i: int, end: int) -> bool:
		return 'word' == toks[i][0] and i + 1 < end and toks[i + 1][1] in (',', ';', '}')
	# @used-by :meth:`Model.__parse_type_body_item()`
	@staticmethod
	def __parse_member(toks: list[tuple[str, str, int]], i: int, end: int, anchor_ln: int, mods: set[str], has_ov: bool, ctx: dict) -> int:
		p_open = Model.__find_method_paren(toks, i, end)
		if -1 == p_open:
			r = Model.__find_decl_end(toks, i, end)
		else:
			mname = toks[p_open - 1][1]
			p_close = Lexer.match_delim(toks, p_open, '(', ')')
			body_i = Model.__skip_throws(toks, p_close + 1, end)
			if body_i < end and toks[body_i][1] in ('{', ';'):
				r = Model.__record_method_def(toks, mname, p_open, p_close, body_i, anchor_ln, mods, has_ov, ctx)
			else:
				r = Model.__find_decl_end(toks, i, end)
		return r
	# @used-by :meth:`Model.index_file()`
	@staticmethod
	def __parse_pkg_and_imports(toks: list[tuple[str, str, int]]) -> tuple[str, dict[str, str], list[str], int]:
		pkg, imports, static_imps, i, n = ('', {}, [], 0, len(toks))
		while i < n:
			t = toks[i][1]
			if 'package' == t:
				pkg, i = Model.__read_dotted_until_semi(toks, i + 1)
			elif 'import' == t:
				is_st = i + 1 < n and 'static' == toks[i + 1][1]
				dotted, i = Model.__read_dotted_until_semi(toks, i + 2 if is_st else i + 1)
				if is_st:
					static_imps.append(dotted)
				elif dotted and (not dotted.endswith('.*')):
					imports[dotted.rsplit('.', 1)[-1]] = dotted
			else:
				break
		return (pkg, imports, static_imps, i)
	# @used-by :meth:`Model.__parse_type_decl()`
	# @used-by :meth:`Model.__record_anon_class()`
	# @used-by :meth:`Model.index_file()`
	@staticmethod
	def __parse_type_body(toks: list[tuple[str, str, int]], start: int, end: int, ctx: dict) -> None:
		i = start
		while i < end:
			if ';' == toks[i][1]:
				i += 1
			elif 'enum' == ctx['kind'] and Model.__is_enum_const_region(toks, i, end):
				i = Model.__skip_enum_constants(toks, i, end)
			else:
				i = Model.__parse_type_body_item(toks, i, end, ctx)
	# @used-by :meth:`Model.__parse_type_body()`
	@staticmethod
	def __parse_type_body_item(toks: list[tuple[str, str, int]], i: int, end: int, ctx: dict) -> int:
		mi, anchor_ln, mods, has_ov = Model.__consume_modifiers(toks, i, end)
		if mi < end and toks[mi][1] in Model.__TYPE_KW:
			r = Model.__parse_type_decl(toks, mi, end, ctx['state'], ctx['type_qual'], ctx['enclosing_res'])
		elif mi < end and '{' == toks[mi][1]:
			b_end = Lexer.match_delim(toks, mi, '{', '}')
			Model.__scan_anon_classes(toks, mi + 1, b_end, ctx['state'], ctx['type_qual'], ctx['type_fqn'])
			r = b_end + 1
		else:
			before_defs = len(ctx['state']['defs'])
			nxt = Model.__parse_member(toks, mi, end, anchor_ln, mods, has_ov, ctx)
			if len(ctx['state']['defs']) == before_defs and mi < nxt:
				Model.__scan_anon_classes(toks, mi, min(nxt, end), ctx['state'], ctx['type_qual'], ctx['type_fqn'])
			r = max(i + 1, nxt)
		return r
	# @used-by :meth:`Model.__parse_type_body_item()`
	@staticmethod
	def __parse_type_decl(toks: list[tuple[str, str, int]], kw_i: int, end: int, state: dict, parent_qual: str, enclosing_res: str | None) -> int:
		kind, name_i = (toks[kw_i][1], kw_i + 1)
		if name_i >= end or 'word' != toks[name_i][0]:
			r = kw_i + 1
		else:
			tname = toks[name_i][1]
			tqual = f'{parent_qual}.{tname}' if parent_qual else tname
			pkg = state['package']
			tfqn = f'{pkg}.{tqual}' if pkg else tqual
			bases, body_open = Model.__scan_type_header(toks, name_i + 1, end)
			if body_open < end and '{' == toks[body_open][1]:
				body_end = Lexer.match_delim(toks, body_open, '{', '}')
				state['types'][tfqn] = {'anon_super': None, 'bases': bases, 'fqn': tfqn, 'is_anon': False, 'kind': kind, 'lineno': toks[kw_i][2], 'name': tname, 'qualname': tqual}
				ctx = {'anon_super': None, 'enclosing_res': enclosing_res or tfqn, 'is_anon': False, 'kind': kind, 'state': state, 'type_fqn': tfqn, 'type_name': tname, 'type_qual': tqual}
				Model.__parse_type_body(toks, body_open + 1, body_end, ctx)
				r = body_end + 1
			else:
				r = name_i + 1
		return r
	# @used-by :meth:`Model.__parse_pkg_and_imports()`
	@staticmethod
	def __read_dotted_until_semi(toks: list[tuple[str, str, int]], start: int) -> tuple[str, int]:
		parts: list[str] = []
		i, n = (start, len(toks))
		while i < n and ';' != toks[i][1]:
			parts.append(toks[i][1])
			i += 1
		return (''.join(parts), i + 1 if i < n else n)
	# @used-by :meth:`Model.__scan_anon_classes()`
	# @used-by :meth:`Model.__scan_type_header()`
	@staticmethod
	def __read_new_type(toks: list[tuple[str, str, int]], start: int, end: int) -> tuple[str, int]:
		parts, i = ([toks[start][1]], start + 1)
		while i + 1 < end and '.' == toks[i][1] and 'word' == toks[i + 1][0]:
			parts.append(toks[i + 1][1])
			i += 2
		if i < end and '<' == toks[i][1]:
			i = Lexer.match_delim(toks, i, '<', '>') + 1
		return ('.'.join(parts), i)
	# @used-by :meth:`Model.__scan_anon_classes()`
	@staticmethod
	def __record_anon_class(toks: list[tuple[str, str, int]], i: int, sup: str, p_close: int, state: dict, parent_qual: str, enclosing_res: str) -> int:
		b_end = Lexer.match_delim(toks, p_close + 1, '{', '}')
		state['anon_seq'] += 1
		aqual = f"{parent_qual}.<anon#{state['anon_seq']}>"
		pkg = state['package']
		afqn = f'{pkg}.{aqual}' if pkg else aqual
		state['types'][afqn] = {'anon_super': sup, 'bases': [sup], 'fqn': afqn, 'is_anon': True, 'kind': 'anon', 'lineno': toks[i][2], 'name': aqual, 'qualname': aqual}
		ctx = {'anon_super': sup, 'enclosing_res': enclosing_res, 'is_anon': True, 'kind': 'anon', 'state': state, 'type_fqn': afqn, 'type_name': aqual, 'type_qual': aqual}
		Model.__parse_type_body(toks, p_close + 2, b_end, ctx)
		return b_end + 1
	# @used-by :meth:`Model.__parse_member()`
	@staticmethod
	def __record_method_def(toks: list[tuple[str, str, int]], mname: str, p_open: int, p_close: int, body_i: int, anchor_ln: int, mods: set[str], has_ov: bool, ctx: dict) -> int:
		params, is_va = Lexer.extract_param_types(toks, p_open, p_close)
		sig = f"{mname}({', '.join(params)})"
		is_ctor = mname == ctx['type_name']
		has_body = '{' == toks[body_i][1]
		b_end = Lexer.match_delim(toks, body_i, '{', '}') if has_body else body_i
		is_empty_priv = is_ctor and 'private' in mods and 0 == len(params) and has_body and body_i + 1 == b_end
		skey = f"{ctx['type_fqn']}#{sig}"
		dinfo = {'anon_super': ctx['anon_super'], 'body_end': b_end, 'body_start': body_i, 'doc_anchor_line': anchor_ln, 'enclosing_res': ctx['enclosing_res'], 'has_override': has_ov, 'indent': Model.line_indent(ctx['state']['lines'], anchor_ln), 'is_abstract': (not has_body) or 'abstract' in mods or 'interface' == ctx['kind'], 'is_anon': ctx['is_anon'], 'is_ctor': is_ctor, 'is_empty_private_ctor': is_empty_priv, 'is_varargs': is_va, 'lineno': toks[p_open - 1][2], 'name': mname, 'param_count': len(params), 'params': params, 'sig': sig, 'symbol_key': skey, 'type_fqn': ctx['type_fqn'], 'type_name': ctx['type_name'], 'type_qual': ctx['type_qual']}
		ctx['state']['defs'].append(dinfo)
		if has_body:
			Model.__scan_anon_classes(toks, body_i + 1, b_end, ctx['state'], ctx['type_qual'], ctx['enclosing_res'] if ctx['is_anon'] else skey)
		return b_end + 1
	# @used-by :meth:`Model.__parse_type_body_item()`
	# @used-by :meth:`Model.__record_method_def()`
	@staticmethod
	def __scan_anon_classes(toks: list[tuple[str, str, int]], start: int, end: int, state: dict, parent_qual: str, enclosing_res: str) -> None:
		i = start
		while i < end:
			if 'new' == toks[i][1] and i + 1 < end and 'word' == toks[i + 1][0]:
				sup, nxt = Model.__read_new_type(toks, i + 1, end)
				if nxt < end and '(' == toks[nxt][1]:
					p_close = Lexer.match_delim(toks, nxt, '(', ')')
					if p_close + 1 < end and '{' == toks[p_close + 1][1]:
						i = Model.__record_anon_class(toks, i, sup, p_close, state, parent_qual, enclosing_res)
						continue
			i += 1
	# @used-by :meth:`Model.__parse_type_decl()`
	@staticmethod
	def __scan_type_header(toks: list[tuple[str, str, int]], start: int, end: int) -> tuple[list[str], int]:
		bases, i, in_clause = ([], start, False)
		while i < end and '{' != toks[i][1]:
			t = toks[i][1]
			if '(' == t:
				i = Lexer.match_delim(toks, i, '(', ')') + 1
			elif '<' == t:
				i = Lexer.match_delim(toks, i, '<', '>') + 1
			elif t in ('extends', 'implements'):
				in_clause, i = (True, i + 1)
			elif 'permits' == t:
				in_clause, i = (False, i + 1)
			elif in_clause and 'word' == toks[i][0]:
				bname, i = Model.__read_new_type(toks, i, end)
				bases.append(bname)
			else:
				i += 1
		return (bases, i)
	# @used-by :meth:`Model.__parse_type_body()`
	@staticmethod
	def __skip_enum_constants(toks: list[tuple[str, str, int]], start: int, end: int) -> int:
		i, r = (start, end)
		while i < end:
			if ';' == toks[i][1]:
				r = i + 1
				break
			i = Lexer.match_delim(toks, i, '{', '}') + 1 if '{' == toks[i][1] else i + 1
		return r
	# @used-by :meth:`Model.__parse_member()`
	@staticmethod
	def __skip_throws(toks: list[tuple[str, str, int]], start: int, end: int) -> int:
		i = start
		while i < end and toks[i][1] not in ('{', ';'):
			i += 1
		return i
	# @used-by :func:`agent_tools.xref.java_model.discover_java_files()`
	# @used-by :meth:`Model.build_repo_index()`
	@staticmethod
	def discover_files(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> list[tuple[str, str]]:
		root = Path(repo_root).resolve()
		ov = {Path(k).as_posix(): v for k, v in (overrides_map or {}).items()}
		rels = {k for k in ov if k.lower().endswith('.java')}
		for fpath in root.rglob('*.java'):
			parts = fpath.relative_to(root).parts
			if not any((p in Model.SKIP_PARTS for p in parts)):
				rels.add(Path(*parts).as_posix())
		out: list[tuple[str, str]] = []
		for rel in sorted(rels):
			src = ov[rel] if rel in ov else ((root / rel).read_text(encoding='utf-8', errors='replace') if (root / rel).is_file() else None)
			if None is not src:
				out.append((rel, src))
		return out
	# @used-by :func:`agent_tools.xref.java_model.index_java_file()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.check_file_local()`
	# @used-by :meth:`Model.build_repo_index()`
	@staticmethod
	def index_file(rel_posix: str, source: str) -> dict:
		lines = (source or '').splitlines()
		toks = Lexer(source or '').tokenize()
		pkg, imports, static_imps, start_i = Model.__parse_pkg_and_imports(toks)
		state = {'anon_seq': 0, 'defs': [], 'lines': lines, 'package': pkg, 'types': {}}
		ctx = {'anon_super': None, 'enclosing_res': None, 'is_anon': False, 'kind': 'file', 'state': state, 'type_fqn': pkg, 'type_name': '', 'type_qual': ''}
		Model.__parse_type_body(toks, start_i, len(toks), ctx)
		return {'defs': state['defs'], 'imports': imports, 'lines': lines, 'package': pkg, 'rel_path': rel_posix, 'source': source or '', 'static_imports': static_imps, 'tokens': toks, 'types': state['types']}
	# @used-by :func:`agent_tools.xref.java_model._line_indent()`
	# @used-by :meth:`Model.__record_method_def()`
	@staticmethod
	def line_indent(lines: list[str], lineno: int) -> str:
		return df_line_indent(lines[lineno - 1] if 1 <= lineno <= len(lines) else '')
