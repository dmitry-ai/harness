# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Core.lib.text.source import df_match_delim
from ..tdd.comment_lexers_c import can_start_regex
from ..tdd.comment_scanners import scan_block_comment, scan_js_regex, scan_line_comment, scan_quoted
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
_OPEN_FOR_CLOSE = {')': '(', '>': '<', ']': '[', '}': '{'}
_WORD_RE = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
# @used-by :func:`_scan_template_expr_tokens()`
# @used-by :func:`_scan_template_tokens()`
# @used-by :func:`_tokenize_js_atom()`
# @used-by :func:`_tokenize_js_word_or_punct()`
def _push_tok(kind: str, text: str, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> None:
	toks.append((kind, text, line))
	prev_words.append(text)
# @used-by :func:`_scan_template_tokens()`
def _scan_template_expr_tokens(src: str, start: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
	i, n, depth = (start, len(src), 1)
	while i < n and 0 < depth:
		ch = src[i]
		if '}' == ch and 1 == depth:
			i += 1
			break
		if ch in ('{', '}'):
			depth += 1 if '{' == ch else -1
			_push_tok('punct', ch, line, toks, prev_words)
			i += 1
		else:
			i, line = _tokenize_js_step(src, i, line, toks, prev_words)
	return (i, line)
# @used-by :func:`_tokenize_js_step()`
def _scan_template_tokens(src: str, start: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
	i, n = (start + 1, len(src))
	while i < n:
		ch = src[i]
		if '\\' == ch:
			i += 2
		elif '\n' == ch:
			line += 1
			i += 1
		elif '`' == ch:
			_push_tok('str', '`...`', line, toks, prev_words)
			i += 1
			break
		elif src.startswith('${', i):
			i, line = _scan_template_expr_tokens(src, i + 2, line, toks, prev_words)
		else:
			i += 1
	return (i, line)
# @used-by :func:`_tokenize_js_step()`
def _tokenize_js_atom(src: str, i: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
	ch = src[i]
	if ch in ("'", '"'):
		end = max(i + 1, scan_quoted(src, i, ch, backslash=True, allow_nl=False))
		_push_tok('str', src[i:end], line, toks, prev_words)
		r = (end, line)
	elif '/' == ch and can_start_regex(prev_words):
		end = max(i + 1, scan_js_regex(src, i))
		_push_tok('regex', src[i:end], line, toks, prev_words)
		r = (end, line)
	elif src.startswith('=>', i):
		_push_tok('punct', '=>', line, toks, prev_words)
		r = (i + 2, line)
	else:
		r = _tokenize_js_word_or_punct(src, i, line, toks, prev_words)
	return r
# @used-by :func:`_scan_template_expr_tokens()`
# @used-by :func:`tokenize_js()`
def _tokenize_js_step(src: str, i: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
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
	elif '`' == ch:
		r = _scan_template_tokens(src, i, line, toks, prev_words)
	else:
		r = _tokenize_js_atom(src, i, line, toks, prev_words)
	return r
# @used-by :func:`_tokenize_js_atom()`
def _tokenize_js_word_or_punct(src: str, i: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
	m = _WORD_RE.match(src, i)
	if None is not m:
		_push_tok('word', m.group(0), line, toks, prev_words)
		r = (m.end(), line)
	else:
		_push_tok('punct', src[i], line, toks, prev_words)
		r = (i + 1, line)
	return r
# @used-by :func:`arrow_body_end()`
# @used-by :func:`skip_ts_type_until()`
def _update_depths(tok: str, depths: dict[str, int]) -> bool:
	r = False
	if tok in depths:
		depths[tok] += 1
	elif tok in _OPEN_FOR_CLOSE:
		op = _OPEN_FOR_CLOSE[tok]
		if op in depths:
			if 0 < depths[op]:
				depths[op] -= 1
			else:
				r = True
	return r
# @used-by :func:`agent_tools.xref.js_model._finish_class_member()`
# @used-by :func:`agent_tools.xref.js_model._parse_top_global_fn()`
# @used-by :func:`agent_tools.xref.js_model._parse_var_fn_rhs()`
def arrow_body_end(toks: list[tuple[str, str, int]], arrow_idx: int) -> int:
	n = len(toks)
	if arrow_idx + 1 < n and '{' == toks[arrow_idx + 1][1]:
		r = match_delim(toks, arrow_idx + 1, '{', '}')
	else:
		depths = {'(': 0, '[': 0, '{': 0}
		i = arrow_idx + 1
		while i < n:
			t = toks[i][1]
			if ';' == t and 0 == sum(depths.values()):
				break
			if _update_depths(t, depths) and '}' == t:
				break
			i += 1
		r = i
	return r
# @used-by :func:`agent_tools.xref.js_model._finish_class_member()`
# @used-by :func:`agent_tools.xref.js_model._parse_top_global_fn()`
# @used-by :func:`agent_tools.xref.js_model._parse_var_fn_rhs()`
def find_arrow_after_eq(toks: list[tuple[str, str, int]], eq_idx: int) -> int:
	n = len(toks)
	i = eq_idx + 2 if eq_idx + 1 < n and 'async' == toks[eq_idx + 1][1] else eq_idx + 1
	r = -1
	if i < n and 'word' == toks[i][0] and i + 1 < n and '=>' == toks[i + 1][1]:
		r = i + 1
	elif i < n and '(' == toks[i][1]:
		j = match_delim(toks, i, '(', ')') + 1
		if j < n and ':' == toks[j][1]:
			j = skip_ts_type_until(toks, j + 1, {'=>'})
		if j < n and '=>' == toks[j][1]:
			r = j
	return r
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`agent_tools.xref.js_imports.parse_destruct_require()`
# @used-by :func:`agent_tools.xref.js_imports.parse_esm_export_list()`
# @used-by :func:`agent_tools.xref.js_imports.parse_module_exports_rhs()`
# @used-by :func:`agent_tools.xref.js_imports.record_esm_specifiers()`
# @used-by :func:`agent_tools.xref.js_model._finish_class_member()`
# @used-by :func:`agent_tools.xref.js_model._parse_class_body()`
# @used-by :func:`agent_tools.xref.js_model._parse_fn_expr_body()`
# @used-by :func:`agent_tools.xref.js_model._parse_top_class()`
# @used-by :func:`agent_tools.xref.js_model._parse_top_fallback()`
# @used-by :func:`agent_tools.xref.js_model._parse_top_func()`
# @used-by :func:`arrow_body_end()`
# @used-by :func:`find_arrow_after_eq()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
	return df_match_delim(toks, start, open_ch, close_ch)
# @used-by :func:`agent_tools.xref.js_model._finish_class_member()`
# @used-by :func:`agent_tools.xref.js_model._parse_fn_expr_body()`
# @used-by :func:`agent_tools.xref.js_model._parse_named_var_decl()`
# @used-by :func:`agent_tools.xref.js_model._parse_top_func()`
# @used-by :func:`find_arrow_after_eq()`
def skip_ts_type_until(toks: list[tuple[str, str, int]], start: int, stop_set: set[str]) -> int:
	depths = {'(': 0, '<': 0, '[': 0}
	i, n = (start, len(toks))
	while i < n:
		t = toks[i][1]
		if 0 == sum(depths.values()) and t in stop_set:
			break
		_update_depths(t, depths)
		i += 1
	return i
# @used-by :func:`agent_tools.xref.js_model.index_js_file()`
def tokenize_js(source: str) -> list[tuple[str, str, int]]:
	toks: list[tuple[str, str, int]] = []
	prev_words: list[str] = []
	i, n, line = (0, len(source), 1)
	if source.startswith('#!'):
		nl = source.find('\n')
		i = n if -1 == nl else nl + 1
		line = 2
	while i < n:
		i, line = _tokenize_js_step(source, i, line, toks, prev_words)
	return toks
# @used-by :func:`agent_tools.xref.js_imports.parse_destruct_require()`
# @used-by :func:`agent_tools.xref.js_imports.parse_esm_import()`
# @used-by :func:`agent_tools.xref.js_model._parse_named_var_decl()`
def unquote(s: str) -> str:
	return s[1:-1] if 2 <= len(s) and s[0] == s[-1] and s[0] in ("'", '"') else s
