# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
from Df.Harness.Tdd.CommentScanners import CommentScanners
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.comment_lexers_script`
class ScriptCommentLexer:
	__BATCH_COMMENT_RE = re.compile(r'^[ \t]*(?:@?rem(?:\s|$)|::)', re.IGNORECASE)
	__PERL_POD_RE = re.compile(r'^=(?:pod|head\d|over|item|back|begin|end|for|encoding)\b')
	__VBS_REM_RE = re.compile(r'rem(?:\s|$)', re.IGNORECASE)
	# @used-by :meth:`ScriptCommentLexer.__hash_block_step()`
	# @used-by :meth:`ScriptCommentLexer.__hash_here_or_regex()`
	# @used-by :meth:`ScriptCommentLexer.__hash_quote_step()`
	# @used-by :meth:`ScriptCommentLexer.__hash_step()`
	# @used-by :meth:`ScriptCommentLexer.__sql_step()`
	# @used-by :meth:`ScriptCommentLexer.__vbs_step()`
	@staticmethod
	def __emit_if_ok(src: str, i: int, end: int, out: list[str]) -> int:
		if 0 <= end:
			out.append(src[i:end])
		return end
	# @used-by :meth:`ScriptCommentLexer.__hash_step()`
	@staticmethod
	def __hash_block_step(src: str, i: int, cfg: dict, comments: list[str]) -> int:
		at_bol = 0 == i or '\n' == src[i - 1]
		r = -2
		if cfg.get('ps_block') and src.startswith('<#', i):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_block_comment(src, i, '<#', '#>'), comments)
		elif at_bol and cfg.get('ruby_block') and src.startswith('=begin', i):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_line_block(src, i, '=end'), comments)
		elif at_bol and cfg.get('perl_pod') and ScriptCommentLexer.__PERL_POD_RE.match(src[i:]):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_line_block(src, i, '=cut'), comments)
		return r
	# @used-by :meth:`ScriptCommentLexer.__hash_step()`
	@staticmethod
	def __hash_comment_allowed(src: str, i: int, cfg: dict) -> bool:
		if cfg.get('sh_hash'):
			r = 0 == i or src[i - 1] in ' \t\r\n;|&()'
		elif cfg.get('perl_pod') and 0 < i and '$' == src[i - 1]:
			r = False
		else:
			r = True
		return r
	# @used-by :meth:`ScriptCommentLexer.__hash_quote_step()`
	@staticmethod
	def __hash_here_or_regex(src: str, i: int, cfg: dict, tokens: list[str]) -> int:
		end = -2
		if cfg.get('ps_here') and '@' == src[i] and i + 1 < len(src) and src[i + 1] in ('"', "'"):
			end = CommentScanners.scan_ps_herestring(src, i, src[i + 1])
		elif cfg.get('sh_heredoc') and src.startswith('<<', i) and (not src.startswith('<<<', i)):
			cand = CommentScanners.scan_heredoc(src, i, php=False)
			if 0 <= cand:
				end = cand
		elif cfg.get('regex_slash') and '/' == src[i] and CLikeCommentLexer.can_start_regex(tokens):
			end = CommentScanners.scan_js_regex(src, i)
		return ScriptCommentLexer.__emit_if_ok(src, i, end, tokens)
	# @used-by :meth:`ScriptCommentLexer.__hash_step()`
	@staticmethod
	def __hash_quote_step(src: str, i: int, cfg: dict, tokens: list[str]) -> int:
		ch = src[i]
		end = -2
		if "'" == ch and cfg.get('single_quote', True):
			end = CommentScanners.scan_quoted(src, i, "'", backslash=bool(cfg.get('sq_bs')), doubled=bool(cfg.get('ps_here')))
		elif cfg.get('triple_quote') and src.startswith('"""', i):
			end = CommentScanners.scan_triple_quote(src, i, '"')
		elif '"' == ch:
			end = CommentScanners.scan_quoted(src, i, '"', backslash=not cfg.get('ps_here'), backtick=bool(cfg.get('ps_here')))
		elif '`' == ch and cfg.get('backtick_str'):
			end = CommentScanners.scan_quoted(src, i, '`', backslash=True)
		return ScriptCommentLexer.__emit_if_ok(src, i, end, tokens) if -2 != end else ScriptCommentLexer.__hash_here_or_regex(src, i, cfg, tokens)
	# @used-by :meth:`ScriptCommentLexer.lex_hash_script()`
	@staticmethod
	def __hash_step(src: str, i: int, cfg: dict, tokens: list[str], comments: list[str]) -> int:
		nxt = ScriptCommentLexer.__hash_block_step(src, i, cfg, comments)
		if -2 != nxt:
			r = nxt
		elif '#' == src[i] and ScriptCommentLexer.__hash_comment_allowed(src, i, cfg):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif '\\' == src[i] and cfg.get('sh_hash') and i + 1 < len(src):
			tokens.append(src[i:i + 2])
			r = i + 2
		else:
			r = ScriptCommentLexer.__hash_quote_step(src, i, cfg, tokens)
		return r
	# @used-by :meth:`ScriptCommentLexer.lex_sql()`
	@staticmethod
	def __sql_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if src.startswith('--', i):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif src.startswith('/*', i):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_block_comment(src, i, '/*', '*/'), comments)
		elif ch in ("'", '"', '`'):
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_quoted(src, i, ch, backslash=False, doubled=True), tokens)
		elif '[' == ch:
			r = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_quoted(src, i, ']', backslash=False), tokens)
		else:
			r = -2
		return r
	# @used-by :meth:`ScriptCommentLexer.lex_vbscript()`
	@staticmethod
	def __vbs_step(src: str, i: int, stmt_start: bool, tokens: list[str], comments: list[str]) -> tuple[int, bool, bool]:
		ch = src[i]
		if "'" == ch or (stmt_start and ScriptCommentLexer.__VBS_REM_RE.match(src, i)):
			r = (ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_line_comment(src, i), comments), stmt_start, True)
		elif '"' == ch:
			end = ScriptCommentLexer.__emit_if_ok(src, i, CommentScanners.scan_quoted(src, i, '"', backslash=False, doubled=True, allow_nl=False), tokens)
			r = (end, False, 0 <= end)
		else:
			r = (CLikeCommentLexer.scan_word_or_char(src, i, tokens), ':' == ch, True)
		return r
	# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_batch()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_batch(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
		tokens: list[str] = []
		comments: list[str] = []
		for raw in (source or '').splitlines():
			if ScriptCommentLexer.__BATCH_COMMENT_RE.match(raw):
				comments.append(raw)
			elif raw.strip():
				tokens.extend((raw.rstrip(), '\n'))
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments))
	# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_hash_script()`
	# @used-by :meth:`Df.Harness.Tdd.CommentDiff.CommentDiff.lex_language()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	@staticmethod
	def lex_hash_script(source: str, cfg: dict) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		n, tokens, comments, ok = (len(source), [], [], True)
		i = CLikeCommentLexer.consume_shebang(source, tokens, True)
		while i < n and ok:
			ch = source[i]
			if ch in ' \t\r':
				i += 1
			elif '\n' == ch:
				tokens.append('\n')
				i += 1
			else:
				nxt = ScriptCommentLexer.__hash_step(source, i, cfg, tokens, comments)
				ok = -1 != nxt
				i = CLikeCommentLexer.scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments)) if ok else None
	# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_sql()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_sql(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		i, n, tokens, comments, ok = (0, len(source), [], [], True)
		while i < n and ok:
			if source[i] in ' \t\r\n':
				i += 1
			else:
				nxt = ScriptCommentLexer.__sql_step(source, i, tokens, comments)
				ok = -1 != nxt
				i = CLikeCommentLexer.scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
		return (tuple(tokens), tuple(comments)) if ok else None
	# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_vbscript()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
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
				i, stmt_start, ok = ScriptCommentLexer.__vbs_step(source, i, stmt_start, tokens, comments)
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments)) if ok else None
