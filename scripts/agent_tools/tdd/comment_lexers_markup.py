# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement diff executability classifier and automatic test skip":
# https://github.com/dmitry-ai/harness/issues/358
from __future__ import annotations
from .comment_lexers_c import lex_c_like, scan_word_or_char
from .comment_scanners import finalize_line_tokens, scan_line_comment, scan_quoted
import re
_DOCKER_DIR_RE = re.compile(r'^#[ \t]*(?:syntax|escape|check)[ \t]*=', re.IGNORECASE)
_SFC_BLOCK_RE = re.compile(r'(<(script|style)\b[^>]*>)([\s\S]*?)(</\2\s*>)', re.IGNORECASE)
_SFC_CSS_CFG = {'css_url': True, 'line_slash': False, 'single_quote': True}
_SFC_TS_CFG = {'line_slash': True, 'regex_slash': True, 'shebang_code': True, 'single_quote': True, 'template_tick': True}
# @used-by :func:`lex_sfc()`
def _consume_astro_frontmatter(source: str, tokens: list[str], comments: list[str]) -> tuple[int, bool]:
	pos, ok = (0, True)
	if source.startswith(('---\n', '---\r\n')):
		first_nl = source.find('\n') + 1
		m_end = re.search(r'^---[ \t]*\r?$', source[first_nl:], re.M)
		if None is m_end:
			ok = False
		else:
			fm_lex = lex_c_like(source[first_nl:first_nl + m_end.start()], _SFC_TS_CFG)
			if None is fm_lex:
				ok = False
			else:
				tokens.extend(('---', *fm_lex[0], '---'))
				comments.extend(fm_lex[1])
				pos = first_nl + m_end.end()
	return (pos, ok)
# @used-by :func:`lex_sfc()`
def _sfc_html_segment(src: str, pos: int, end: int, tokens: list[str], comments: list[str]) -> bool:
	i, ok = (pos, True)
	while i < end:
		c_idx = src.find('<!--', i, end)
		if -1 == c_idx:
			if src[i:end].strip():
				tokens.append(src[i:end].strip())
			break
		if src[i:c_idx].strip():
			tokens.append(src[i:c_idx].strip())
		c_end = src.find('-->', c_idx + 4, end)
		if -1 == c_end:
			ok = False
			break
		comments.append(src[c_idx:c_end + 3])
		i = c_end + 3
	return ok
# @used-by :func:`lex_tcl()`
def _tcl_step(source: str, i: int, cmd_start: bool, tokens: list[str], comments: list[str]) -> tuple[int, bool, bool]:
	ch = source[i]
	if '#' == ch and cmd_start:
		end = scan_line_comment(source, i)
		comments.append(source[i:end])
		r = (end, cmd_start, True)
	elif '"' == ch:
		end = scan_quoted(source, i, '"', backslash=True)
		if 0 <= end:
			tokens.append(source[i:end])
		r = (end, False, 0 <= end)
	else:
		r = (scan_word_or_char(source, i, tokens), ch in ';{', True)
	return r
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_dockerfile(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	tokens, comments, in_header = ([], [], True)
	for raw in (source or '').splitlines():
		s = raw.strip()
		if not s:
			continue
		if in_header and _DOCKER_DIR_RE.match(s):
			tokens.extend((s, '\n'))
		elif s.startswith('#'):
			comments.append(raw)
		else:
			in_header = False
			tokens.extend((s, '\n'))
	return (finalize_line_tokens(tokens), tuple(comments))
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_indent_hash(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	tokens, comments = ([], [])
	for raw in (source or '').splitlines():
		stripped = raw.lstrip(' \t')
		if not stripped:
			continue
		if stripped.startswith('#'):
			comments.append(raw)
		else:
			lead = raw[:len(raw) - len(stripped)]
			tokens.extend((f'INDENT:{lead}', stripped.rstrip(), '\n'))
	return (finalize_line_tokens(tokens), tuple(comments))
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sed(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	tokens, comments = ([], [])
	for idx, raw in enumerate((source or '').splitlines(), 1):
		s = raw.strip()
		if not s:
			continue
		if 1 == idx and s.startswith('#n'):
			tokens.extend((s, '\n'))
		elif s.startswith('#'):
			comments.append(raw)
		else:
			tokens.extend((s, '\n'))
	return (finalize_line_tokens(tokens), tuple(comments))
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sfc(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	tokens, comments = ([], [])
	pos, ok = _consume_astro_frontmatter(source or '', tokens, comments)
	for m in _SFC_BLOCK_RE.finditer(source or '', pos):
		if not ok:
			break
		ok = _sfc_html_segment(source, pos, m.start(), tokens, comments)
		if ok:
			cfg = _SFC_TS_CFG if 'script' == m.group(2).lower() else _SFC_CSS_CFG
			sub = lex_c_like(m.group(3), cfg)
			if None is sub:
				ok = False
			else:
				tokens.extend((m.group(1).strip(), *sub[0], m.group(4).strip()))
				comments.extend(sub[1])
				pos = m.end()
	if ok:
		ok = _sfc_html_segment(source or '', pos, len(source or ''), tokens, comments)
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_tcl(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	i, n, tokens, comments, ok, cmd_start = (0, len(source), [], [], True, True)
	while i < n and ok:
		ch = source[i]
		if ch in ' \t\r':
			i += 1
		elif '\n' == ch:
			tokens.append('\n')
			i, cmd_start = (i + 1, True)
		else:
			i, cmd_start, ok = _tcl_step(source, i, cmd_start, tokens, comments)
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
