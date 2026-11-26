# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .comment_lexers_c import can_start_regex, consume_shebang, scan_word_or_char
from .comment_scanners import finalize_line_tokens, scan_block_comment, scan_heredoc, scan_js_regex, scan_line_block, scan_line_comment, scan_ps_herestring, scan_quoted
import re
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
_BATCH_COMMENT_RE = re.compile(r'^[ \t]*(?:@?rem(?:\s|$)|::)', re.IGNORECASE)
_PERL_POD_RE = re.compile(r'^=(?:pod|head\d|over|item|back|begin|end|for|encoding)\b')
_VBS_REM_RE = re.compile(r'rem(?:\s|$)', re.IGNORECASE)
def _emit_if_ok(src: str, i: int, end: int, out: list[str]) -> int:
	if 0 <= end:
		out.append(src[i:end])
	return end
def _hash_block_step(src: str, i: int, cfg: dict, comments: list[str]) -> int:
	at_bol = 0 == i or '\n' == src[i - 1]
	r = -2
	if cfg.get('ps_block') and src.startswith('<#', i):
		r = _emit_if_ok(src, i, scan_block_comment(src, i, '<#', '#>'), comments)
	elif at_bol and cfg.get('ruby_block') and src.startswith('=begin', i):
		r = _emit_if_ok(src, i, scan_line_block(src, i, '=end'), comments)
	elif at_bol and cfg.get('perl_pod') and _PERL_POD_RE.match(src[i:]):
		r = _emit_if_ok(src, i, scan_line_block(src, i, '=cut'), comments)
	return r
def _hash_comment_allowed(src: str, i: int, cfg: dict) -> bool:
	if cfg.get('sh_hash'):
		r = 0 == i or src[i - 1] in ' \t\r\n;|&()'
	elif cfg.get('perl_pod') and 0 < i and '$' == src[i - 1]:
		r = False
	else:
		r = True
	return r
def _hash_here_or_regex(src: str, i: int, cfg: dict, tokens: list[str]) -> int:
	end = -2
	if cfg.get('ps_here') and '@' == src[i] and i + 1 < len(src) and src[i + 1] in ('"', "'"):
		end = scan_ps_herestring(src, i, src[i + 1])
	elif cfg.get('sh_heredoc') and src.startswith('<<', i) and (not src.startswith('<<<', i)):
		cand = scan_heredoc(src, i, php=False)
		if 0 <= cand:
			end = cand
	elif cfg.get('regex_slash') and '/' == src[i] and can_start_regex(tokens):
		end = scan_js_regex(src, i)
	return _emit_if_ok(src, i, end, tokens)
def _hash_quote_step(src: str, i: int, cfg: dict, tokens: list[str]) -> int:
	ch = src[i]
	end = -2
	if "'" == ch and cfg.get('single_quote', True):
		end = scan_quoted(src, i, "'", backslash=bool(cfg.get('sq_bs')), doubled=bool(cfg.get('ps_here')))
	elif '"' == ch:
		end = scan_quoted(src, i, '"', backslash=not cfg.get('ps_here'), backtick=bool(cfg.get('ps_here')))
	elif '`' == ch and cfg.get('backtick_str'):
		end = scan_quoted(src, i, '`', backslash=True)
	return _emit_if_ok(src, i, end, tokens) if -2 != end else _hash_here_or_regex(src, i, cfg, tokens)
def _hash_step(src: str, i: int, cfg: dict, tokens: list[str], comments: list[str]) -> int:
	nxt = _hash_block_step(src, i, cfg, comments)
	if -2 != nxt:
		r = nxt
	elif '#' == src[i] and _hash_comment_allowed(src, i, cfg):
		r = _emit_if_ok(src, i, scan_line_comment(src, i), comments)
	elif '\\' == src[i] and cfg.get('sh_hash') and i + 1 < len(src):
		tokens.append(src[i:i + 2])
		r = i + 2
	else:
		r = _hash_quote_step(src, i, cfg, tokens)
	return r
def _sql_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if src.startswith('--', i):
		r = _emit_if_ok(src, i, scan_line_comment(src, i), comments)
	elif src.startswith('/*', i):
		r = _emit_if_ok(src, i, scan_block_comment(src, i, '/*', '*/'), comments)
	elif ch in ("'", '"', '`'):
		r = _emit_if_ok(src, i, scan_quoted(src, i, ch, backslash=False, doubled=True), tokens)
	elif '[' == ch:
		r = _emit_if_ok(src, i, scan_quoted(src, i, ']', backslash=False), tokens)
	else:
		r = -2
	return r
def _vbs_step(src: str, i: int, stmt_start: bool, tokens: list[str], comments: list[str]) -> tuple[int, bool, bool]:
	ch = src[i]
	if "'" == ch or (stmt_start and _VBS_REM_RE.match(src, i)):
		r = (_emit_if_ok(src, i, scan_line_comment(src, i), comments), stmt_start, True)
	elif '"' == ch:
		end = _emit_if_ok(src, i, scan_quoted(src, i, '"', backslash=False, doubled=True, allow_nl=False), tokens)
		r = (end, False, 0 <= end)
	else:
		r = (scan_word_or_char(src, i, tokens), ':' == ch, True)
	return r
def lex_batch(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	tokens: list[str] = []
	comments: list[str] = []
	for raw in (source or '').splitlines():
		if _BATCH_COMMENT_RE.match(raw):
			comments.append(raw)
		elif raw.strip():
			tokens.extend((raw.rstrip(), '\n'))
	return (finalize_line_tokens(tokens), tuple(comments))
def lex_hash_script(source: str, cfg: dict) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	n, tokens, comments, ok = (len(source), [], [], True)
	i = consume_shebang(source, tokens, True)
	while i < n and ok:
		ch = source[i]
		if ch in ' \t\r':
			i += 1
		elif '\n' == ch:
			tokens.append('\n')
			i += 1
		else:
			nxt = _hash_step(source, i, cfg, tokens, comments)
			ok = -1 != nxt
			i = scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
def lex_sql(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	i, n, tokens, comments, ok = (0, len(source), [], [], True)
	while i < n and ok:
		if source[i] in ' \t\r\n':
			i += 1
		else:
			nxt = _sql_step(source, i, tokens, comments)
			ok = -1 != nxt
			i = scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
	return (tuple(tokens), tuple(comments)) if ok else None
def lex_vbscript(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	i, n, tokens, comments, ok, stmt_start = (0, len(source), [], [], True, True)
	while i < n and ok:
		ch = source[i]
		if ch in ' \t\r':
			i += 1
		elif '\n' == ch:
			tokens.append('\n')
			i, stmt_start = (i + 1, True)
		else:
			i, stmt_start, ok = _vbs_step(source, i, stmt_start, tokens, comments)
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
