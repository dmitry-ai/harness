# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return the leading whitespace indentation prefix of a source line.
# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.line_indent()`
# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.line_indent()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_line_indent(line: str) -> str:
	return line[:len(line) - len(line.lstrip(' \t'))]
# Find the matching closing delimiter token index starting from `start` in a `(kind, text, line)` token stream.
# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.match_delim()`
# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.match_delim()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
	depth, i, n, r = (0, start, len(toks), len(toks) - 1)
	while i < n:
		if open_ch == toks[i][1]:
			depth += 1
		elif close_ch == toks[i][1]:
			depth -= 1
			if 0 == depth:
				r = i
				break
		i += 1
	return r
# Sequentially replace each `(old, new)` pair in `text` case-insensitively.
# @used-by :func:`Df.Harness.lib.project.dfh_rewrite_value()`
# @used-by :func:`agent_tools.project_rename_state._rewrite_text()`
# @used-by :func:`agent_tools.shadow_replay_clone._rewrite_path_text()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_text_rewrite_pairs(text: str, pairs: list[tuple[str, str]] | tuple[tuple[str, str], ...]) -> str:
	out = text
	for old_s, new_s in pairs:
		out = re.sub(re.escape(old_s), lambda _m, rep=new_s: rep, out, flags=re.IGNORECASE)
	return out