# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/238
from __future__ import annotations
import re
_CPP_RAW_RE = re.compile(r'R"([^\s()\\]{0,16})\(')
_HEREDOC_START_RE = re.compile(r'<<<[ \t]*(?:"([A-Za-z_]\w*)"|\'([A-Za-z_]\w*)\'|([A-Za-z_]\w*))')
_SH_HEREDOC_RE = re.compile(r'<<(-?)[ \t]*(?:"([A-Za-z_]\w*)"|\'([A-Za-z_]\w*)\'|([A-Za-z_]\w*))')
def finalize_line_tokens(raw_tokens: list[str]) -> tuple[str, ...]:
	out: list[str] = []
	for tok in raw_tokens:
		if '\n' == tok:
			if out and '\n' != out[-1]:
				out.append('\n')
		else:
			out.append(tok)
	if out and '\n' != out[-1]:
		out.append('\n')
	return tuple(out)
def scan_block_comment(src: str, pos: int, open_tok: str, close_tok: str, *, nested: bool=False) -> int:
	n = len(src)
	olen, clen = (len(open_tok), len(close_tok))
	i, depth, r = (pos + olen, 1, -1)
	while i < n:
		if nested and src.startswith(open_tok, i):
			depth += 1
			i += olen
		elif src.startswith(close_tok, i):
			depth -= 1
			i += clen
			if 0 == depth:
				r = i
				break
		else:
			i += 1
	return r
def scan_cpp_raw(src: str, pos: int) -> int:
	m = _CPP_RAW_RE.match(src, pos)
	if None is m:
		r = -1
	else:
		end_marker = f'){m.group(1)}"'
		idx = src.find(end_marker, m.end())
		r = -1 if -1 == idx else idx + len(end_marker)
	return r
def scan_css_url(src: str, pos: int) -> int:
	n = len(src)
	i = pos + 4
	while i < n and src[i] in ' \t\r\n':
		i += 1
	if i < n and src[i] in ('"', "'"):
		end_q = scan_quoted(src, i, src[i], backslash=True, allow_nl=False)
		r = -1 if 0 > end_q else _scan_until_paren(src, end_q)
	else:
		r = _scan_until_paren(src, i)
	return r
def scan_heredoc(src: str, pos: int, *, php: bool=False) -> int:
	pat = _HEREDOC_START_RE if php else _SH_HEREDOC_RE
	m = pat.match(src, pos)
	if None is m:
		r = -1
	else:
		tag = next((g for g in m.groups()[-3:] if g), '')
		nl = src.find('\n', m.end())
		r = -1 if -1 == nl else _find_heredoc_end(src, nl + 1, tag, php=php)
	return r
def scan_js_regex(src: str, pos: int) -> int:
	i, n, in_cls, r = (pos + 1, len(src), False, -1)
	while i < n and src[i] not in '\r\n':
		ch = src[i]
		if '\\' == ch:
			i += 2
		elif '/' == ch and (not in_cls):
			r = _scan_regex_flags(src, i + 1)
			break
		else:
			in_cls = True if '[' == ch else (False if ']' == ch and in_cls else in_cls)
			i += 1
	return r
def scan_line_block(src: str, pos: int, end_prefix: str) -> int:
	n = len(src)
	i, r = (pos, -1)
	while i < n:
		nl = src.find('\n', i)
		line_end = n if -1 == nl else nl + 1
		if src[i:line_end].startswith(end_prefix) and (len(end_prefix) == len(src[i:line_end].rstrip('\r\n')) or src[i + len(end_prefix)] in ' \t\r\n'):
			r = line_end
			break
		i = line_end
	return r
def scan_line_comment(src: str, pos: int, *, stop_tag: str='') -> int:
	n = len(src)
	nl = src.find('\n', pos)
	end = n if -1 == nl else nl
	if stop_tag:
		tag_idx = src.find(stop_tag, pos, end)
		if -1 != tag_idx:
			end = tag_idx
	return end
def scan_ps_herestring(src: str, pos: int, quote: str) -> int:
	nl = src.find('\n', pos + 2)
	if -1 == nl:
		r = -1
	else:
		end_marker = f'\n{quote}@'
		idx = src.find(end_marker, nl)
		r = -1 if -1 == idx else idx + len(end_marker)
	return r
def scan_quoted(src: str, pos: int, quote: str, *, backslash: bool=True, doubled: bool=False, allow_nl: bool=True, backtick: bool=False) -> int:
	n = len(src)
	i, r = (pos + 1, -1)
	while i < n:
		ch = src[i]
		if (not allow_nl) and ch in '\r\n':
			break
		if backslash and '\\' == ch:
			i += 2
		elif backtick and '`' == ch:
			i += 2
		elif doubled and ch == quote and i + 1 < n and src[i + 1] == quote:
			i += 2
		elif ch == quote:
			r = i + 1
			break
		else:
			i += 1
	return r
def scan_triple_quote(src: str, pos: int, quote: str) -> int:
	marker = quote * 3
	i, n, r = (pos + 3, len(src), -1)
	while i < n:
		if '\\' == src[i]:
			i += 2
		elif src.startswith(marker, i):
			r = i + 3
			break
		else:
			i += 1
	return r
def _find_heredoc_end(src: str, start: int, tag: str, *, php: bool) -> int:
	i, n, r = (start, len(src), -1)
	while i < n:
		nl = src.find('\n', i)
		line_end = n if -1 == nl else nl
		stripped = src[i:line_end].strip()
		matched = (stripped == tag or stripped.startswith(f'{tag};')) if php else (stripped == tag)
		if matched:
			r = line_end
			break
		i = n if -1 == nl else nl + 1
	return r
def _scan_regex_flags(src: str, pos: int) -> int:
	n = len(src)
	i = pos
	while i < n and src[i].isalpha():
		i += 1
	return i
def _scan_until_paren(src: str, pos: int) -> int:
	n = len(src)
	i, r = (pos, -1)
	while i < n:
		if '\\' == src[i]:
			i += 2
		elif ')' == src[i]:
			r = i + 1
			break
		else:
			i += 1
	return r
