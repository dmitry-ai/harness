# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .comment_scanners import finalize_line_tokens, scan_block_comment, scan_cpp_raw, scan_css_url, scan_heredoc, scan_js_regex, scan_line_comment, scan_quoted, scan_triple_quote
import io
import re
import tokenize
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
_CODING_RE = re.compile(r'coding[:=]\s*[-\w.]+')
_HTML_OPEN_RE = re.compile(r'<\?(?:php\b|=)?', re.IGNORECASE)
_REGEX_PREV_CHARS = frozenset('=([{,;:!?&|^~+-*/%<>')
_REGEX_PREV_WORDS = frozenset({'await', 'case', 'delete', 'do', 'else', 'in', 'instanceof', 'new', 'of', 'return', 'throw', 'typeof', 'void', 'yield'})
_WORD_RE = re.compile(r'[A-Za-z0-9_$]+')
# @used-by :func:`_c_like_special_step()`
def _c_like_comment_step(src: str, i: int, cfg: dict, comments: list[str]) -> int:
	r = -2
	if cfg.get('line_slash') and src.startswith('//', i):
		r = scan_line_comment(src, i)
		comments.append(src[i:r])
	elif src.startswith('/*', i):
		r = scan_block_comment(src, i, '/*', '*/', nested=bool(cfg.get('block_nested')))
		if 0 <= r:
			comments.append(src[i:r])
	return r
# @used-by :func:`lex_c_like()`
def _c_like_special_step(src: str, i: int, cfg: dict, tokens: list[str], comments: list[str]) -> int:
	c_end = _c_like_comment_step(src, i, cfg, comments)
	if -2 != c_end:
		r = c_end
	elif cfg.get('css_url') and 'url(' == src[i:i + 4].lower():
		r = _emit_slice(src, i, scan_css_url(src, i), tokens)
	elif cfg.get('regex_slash') and '/' == src[i] and can_start_regex(tokens):
		r = _emit_slice(src, i, scan_js_regex(src, i), tokens)
	else:
		r = _c_like_string_step(src, i, cfg, tokens)
	return r
# @used-by :func:`_c_like_special_step()`
def _c_like_string_step(src: str, i: int, cfg: dict, tokens: list[str]) -> int:
	ch = src[i]
	end = -2
	if cfg.get('raw_cpp') and src.startswith('R"', i):
		end = scan_cpp_raw(src, i)
	elif cfg.get('verbatim_at') and src.startswith('@"', i):
		end = scan_quoted(src, i + 1, '"', backslash=False, doubled=True)
	elif cfg.get('triple_quote') and src.startswith('"""', i):
		end = scan_triple_quote(src, i, '"')
	elif '"' == ch or ("'" == ch and cfg.get('single_quote', True)):
		end = scan_quoted(src, i, ch, backslash=True, allow_nl=bool(cfg.get('ml_quote')))
	elif '`' == ch and cfg.get('template_tick'):
		end = _scan_template_literal(src, i)
	return _emit_slice(src, i, end, tokens)
# @used-by :func:`_c_like_special_step()`
# @used-by :func:`_c_like_string_step()`
# @used-by :func:`_php_code_step()`
def _emit_slice(src: str, i: int, end: int, out: list[str]) -> int:
	if 0 <= end:
		out.append(src[i:end])
	return end
# @used-by :func:`lex_php()`
def _lex_php_body(src: str, start: int, tokens: list[str], comments: list[str]) -> tuple[int, bool]:
	i, n, ok = (start, len(src), True)
	while i < n and ok:
		if src.startswith('?>', i):
			tokens.append('?>')
			i += 2
			break
		if src[i] in ' \t\r\n':
			i += 1
		else:
			nxt = _php_code_step(src, i, tokens, comments)
			if -1 == nxt:
				ok = False
			else:
				i = scan_word_or_char(src, i, tokens) if -2 == nxt else nxt
	return (i, ok)
# @used-by :func:`_lex_php_body()`
def _php_code_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if src.startswith('//', i) or ('#' == ch and (not src.startswith('#[', i))):
		r = _emit_slice(src, i, scan_line_comment(src, i, stop_tag='?>'), comments)
	elif src.startswith('/*', i):
		r = _emit_slice(src, i, scan_block_comment(src, i, '/*', '*/'), comments)
	elif src.startswith('<<<', i):
		r = _emit_slice(src, i, scan_heredoc(src, i, php=True), tokens)
	elif ch in ("'", '"', '`'):
		r = _emit_slice(src, i, scan_quoted(src, i, ch, backslash=True), tokens)
	else:
		r = -2
	return r
# @used-by :func:`lex_php()`
def _php_html_segment(src: str, pos: int, end: int, tokens: list[str], comments: list[str]) -> bool:
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
# @used-by :func:`_scan_template_literal()`
def _scan_template_expr(src: str, pos: int) -> int:
	i, n, depth, r = (pos, len(src), 1, -1)
	while i < n:
		ch = src[i]
		if ch in ('"', "'", '`'):
			i = _scan_template_literal(src, i) if '`' == ch else scan_quoted(src, i, ch)
			if 0 > i:
				break
		elif '{' == ch:
			depth += 1
			i += 1
		elif '}' == ch:
			depth -= 1
			i += 1
			if 0 == depth:
				r = i
				break
		else:
			i += 1
	return r
# @used-by :func:`_c_like_string_step()`
# @used-by :func:`_scan_template_expr()`
def _scan_template_literal(src: str, pos: int) -> int:
	i, n, r = (pos + 1, len(src), -1)
	while i < n:
		ch = src[i]
		if '\\' == ch:
			i += 2
		elif '`' == ch:
			r = i + 1
			break
		elif src.startswith('${', i):
			i = _scan_template_expr(src, i + 2)
			if 0 > i:
				break
		else:
			i += 1
	return r
# @used-by :func:`_c_like_special_step()`
# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_here_or_regex()`
# @used-by :func:`agent_tools.xref.js_lex._tokenize_js_atom()`
def can_start_regex(tokens: list[str]) -> bool:
	prev = next((t for t in reversed(tokens) if '\n' != t), '')
	return (not prev) or prev in _REGEX_PREV_WORDS or prev[-1] in _REGEX_PREV_CHARS
# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_hash_script()`
# @used-by :func:`lex_c_like()`
def consume_shebang(source: str, tokens: list[str], enabled: bool) -> int:
	r = 0
	if enabled and source.startswith('#!'):
		nl = source.find('\n')
		r = len(source) if -1 == nl else nl
		tokens.extend((source[:r], '\n'))
	return r
# @used-by :func:`agent_tools.tdd.comment_diff.lex_language()`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_c_like(source: str, cfg: dict) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	n, tokens, comments, ok = (len(source), [], [], True)
	i = consume_shebang(source, tokens, bool(cfg.get('shebang_code')))
	while i < n and ok:
		ch = source[i]
		if ch in ' \t\r':
			i += 1
		elif '\n' == ch:
			tokens.append('\n')
			i += 1
		else:
			nxt = _c_like_special_step(source, i, cfg, tokens, comments)
			ok = -1 != nxt
			i = scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
# @used-by :func:`agent_tools.tdd.comment_diff.lex_language()`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_php(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	i, n, tokens, comments, ok = (0, len(source), [], [], True)
	while i < n and ok:
		m_open = _HTML_OPEN_RE.search(source, i)
		html_end = n if None is m_open else m_open.start()
		ok = _php_html_segment(source, i, html_end, tokens, comments)
		if (not ok) or None is m_open:
			break
		tokens.append(m_open.group(0).lower())
		i, ok = _lex_php_body(source, m_open.end(), tokens, comments)
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
# @used-by :func:`agent_tools.tdd.comment_diff.lex_language()`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_python(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	tokens: list[str] = []
	comments: list[str] = []
	try:
		for tok in tokenize.generate_tokens(io.StringIO(source).readline):
			if tok.type in (tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER):
				continue
			if tokenize.COMMENT == tok.type:
				is_ctrl = (1 == tok.start[0] and tok.string.startswith('#!')) or (2 >= tok.start[0] and bool(_CODING_RE.search(tok.string)))
				(tokens if is_ctrl else comments).append(tok.string)
			else:
				tokens.append(f'{tok.type}:{tok.string}')
		r: tuple[tuple[str, ...], tuple[str, ...]] | None = (tuple(tokens), tuple(comments))
	except (tokenize.TokenError, IndentationError):
		r = None
	return r
# @used-by :func:`_lex_php_body()`
# @used-by :func:`agent_tools.tdd.comment_lexers_script._vbs_step()`
# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_hash_script()`
# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_sql()`
# @used-by :func:`lex_c_like()`
def scan_word_or_char(src: str, i: int, tokens: list[str]) -> int:
	m = _WORD_RE.match(src, i)
	if None is not m:
		tokens.append(m.group(0))
		r = m.end()
	else:
		tokens.append(src[i])
		r = i + 1
	return r
