# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Core.lib.text.source import df_match_delim
from ..tdd.comment_scanners import scan_block_comment, scan_line_comment, scan_quoted, scan_triple_quote
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
_WORD_RE = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
# @used-by :func:`_parse_single_param()`
def _clean_param_type(parts: list[str]) -> str:
	type_parts = parts[:-1] if 2 <= len(parts) else parts
	raw = ''.join(type_parts)
	arr = ''
	while raw.endswith('[]'):
		arr += '[]'
		raw = raw[:-2]
	if raw.endswith('...'):
		arr = '...'
		raw = raw[:-3]
	simple = raw.rsplit('.', 1)[-1] if '.' in raw else raw
	return f'{simple}{arr}'
# @used-by :func:`extract_param_types()`
def _parse_single_param(toks: list[tuple[str, str, int]], start: int, end: int) -> tuple[str, bool]:
	i = start
	parts: list[str] = []
	is_varargs = False
	while i < end:
		t = toks[i][1]
		if '@' == t:
			i = skip_annotation(toks, i, end)
		elif '<' == t:
			i = match_delim(toks, i, '<', '>') + 1
		elif 'final' == t:
			i += 1
		elif '...' == t:
			is_varargs = True
			parts.append('...')
			i += 1
		else:
			parts.append(t)
			i += 1
	return (_clean_param_type(parts), is_varargs)
# @used-by :func:`_tokenize_java_step()`
def _tokenize_java_atom(src: str, i: int, line: int, toks: list[tuple[str, str, int]]) -> tuple[int, int]:
	ch = src[i]
	if src.startswith('"""', i):
		end = max(i + 3, scan_triple_quote(src, i, '"'))
		toks.append(('str', src[i:end], line))
		r = (end, line + src[i:end].count('\n'))
	elif ch in ('"', "'"):
		end = max(i + 1, scan_quoted(src, i, ch, backslash=True, allow_nl=False))
		toks.append(('str', src[i:end], line))
		r = (end, line)
	elif src.startswith('...', i):
		toks.append(('punct', '...', line))
		r = (i + 3, line)
	elif src.startswith('::', i):
		toks.append(('punct', '::', line))
		r = (i + 2, line)
	else:
		r = _tokenize_java_word_or_punct(src, i, line, toks)
	return r
# @used-by :func:`tokenize_java()`
def _tokenize_java_step(src: str, i: int, line: int, toks: list[tuple[str, str, int]]) -> tuple[int, int]:
	ch = src[i]
	if ch in ' \t\r':
		r = (i + 1, line)
	elif '\n' == ch:
		r = (i + 1, line + 1)
	elif src.startswith('//', i):
		r = (scan_line_comment(src, i), line)
	elif src.startswith('/*', i):
		end = scan_block_comment(src, i, '/*', '*/')
		end = len(src) if 0 > end else end
		r = (end, line + src[i:end].count('\n'))
	else:
		r = _tokenize_java_atom(src, i, line, toks)
	return r
# @used-by :func:`_tokenize_java_atom()`
def _tokenize_java_word_or_punct(src: str, i: int, line: int, toks: list[tuple[str, str, int]]) -> tuple[int, int]:
	m = _WORD_RE.match(src, i)
	if None is not m:
		toks.append(('word', m.group(0), line))
		r = (m.end(), line)
	else:
		toks.append(('punct', src[i], line))
		r = (i + 1, line)
	return r
# @used-by :func:`agent_tools.xref.java_graph._record_java_call()`
def count_top_args(toks: list[tuple[str, str, int]], open_p: int, close_p: int) -> int:
	if open_p + 1 >= close_p:
		r = 0
	else:
		count, depth, i = (1, 0, open_p + 1)
		while i < close_p:
			t = toks[i][1]
			if t in ('(', '[', '{'):
				depth += 1
			elif t in (')', ']', '}') and 0 < depth:
				depth -= 1
			elif ',' == t and 0 == depth:
				count += 1
			i += 1
		r = count
	return r
# @used-by :func:`agent_tools.xref.java_model._record_method_def()`
def extract_param_types(toks: list[tuple[str, str, int]], open_p: int, close_p: int) -> tuple[list[str], bool]:
	params: list[str] = []
	is_varargs = False
	seg_start, depth, i = (open_p + 1, 0, open_p + 1)
	while i <= close_p:
		t = toks[i][1] if i < close_p else ','
		if t in ('(', '<', '[', '{') and i < close_p:
			depth += 1
		elif t in (')', '>', ']', '}') and i < close_p and 0 < depth:
			depth -= 1
		elif ',' == t and 0 == depth:
			if seg_start < i:
				pt, va = _parse_single_param(toks, seg_start, i)
				if pt:
					params.append(pt)
				is_varargs = is_varargs or va
			seg_start = i + 1
		i += 1
	return (params, is_varargs)
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_parse_single_param()`
# @used-by :func:`agent_tools.xref.java_graph._record_java_call()`
# @used-by :func:`agent_tools.xref.java_model._find_decl_end()`
# @used-by :func:`agent_tools.xref.java_model._find_method_paren()`
# @used-by :func:`agent_tools.xref.java_model._parse_member()`
# @used-by :func:`agent_tools.xref.java_model._parse_type_body_item()`
# @used-by :func:`agent_tools.xref.java_model._parse_type_decl()`
# @used-by :func:`agent_tools.xref.java_model._read_new_type()`
# @used-by :func:`agent_tools.xref.java_model._record_method_def()`
# @used-by :func:`agent_tools.xref.java_model._scan_anon_classes()`
# @used-by :func:`agent_tools.xref.java_model._scan_type_header()`
# @used-by :func:`agent_tools.xref.java_model._skip_enum_constants()`
# @used-by :func:`skip_annotation()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
	return df_match_delim(toks, start, open_ch, close_ch)
# @used-by :func:`_parse_single_param()`
# @used-by :func:`agent_tools.xref.java_model._consume_modifiers()`
# @used-by :func:`agent_tools.xref.java_model._find_method_paren()`
def skip_annotation(toks: list[tuple[str, str, int]], at_i: int, end: int) -> int:
	i = at_i + 1
	if i < end and 'word' == toks[i][0]:
		i += 1
		while i + 1 < end and '.' == toks[i][1] and 'word' == toks[i + 1][0]:
			i += 2
	if i < end and '(' == toks[i][1]:
		i = match_delim(toks, i, '(', ')') + 1
	return i
# @used-by :func:`agent_tools.xref.java_model.index_java_file()`
def tokenize_java(source: str) -> list[tuple[str, str, int]]:
	toks: list[tuple[str, str, int]] = []
	i, n, line = (0, len(source), 1)
	while i < n:
		i, line = _tokenize_java_step(source, i, line, toks)
	return toks
