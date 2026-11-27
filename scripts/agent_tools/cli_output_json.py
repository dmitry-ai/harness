# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py":
# https://github.com/dmitry-ai/harness/issues/368
from __future__ import annotations
from typing import Any
import json
import re
from .tdd.outcomes import _BG_HEADER_SPLIT_RE
_COL0_BRACE_RE = re.compile(r'(?m)^\{')
_INLINE_FAIL_RE = re.compile(r'"(?:valid|ok)"\s*:\s*false\b', re.IGNORECASE)
_TOP_INDENT_FAIL_RE = re.compile(r'^(?: {1,2}|\t)"(?:valid|ok)"\s*:\s*false\b', re.IGNORECASE)
# @used-by :func:`extract_top_level_json_objects()`
def _body_without_header(text: str) -> str:
	raw = text or ''
	parts = _BG_HEADER_SPLIT_RE.split(raw, maxsplit=1)
	return parts[1] if 2 == len(parts) else raw
# @used-by :func:`extract_top_level_json_objects()`
def _decode_col0_at(dec: json.JSONDecoder, body: str, idx: int) -> tuple[dict[str, Any] | None, int, bool]:
	try:
		obj, end = dec.raw_decode(body, idx)
	except ValueError:
		r = (None, idx + 1, _truncated_top_level_failure(body[idx:]))
	else:
		r = (obj if isinstance(obj, dict) else None, end, False)
	return r
# @used-by :func:`_decode_col0_at()`
def _truncated_top_level_failure(snippet: str) -> bool:
	lines = (snippet or '').splitlines()
	if not lines:
		r = False
	else:
		first = lines[0]
		nested = first.find('{', 1)
		head = first[:nested] if 0 < nested else first
		r = bool(_INLINE_FAIL_RE.search(head)) or any((bool(_TOP_INDENT_FAIL_RE.match(ln)) for ln in lines[1:]))
	return r
# @used-by :func:`top_level_json_has_failure()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_top_level_json_parser_ignores_nested_valid_false_and_catches_top_level_failures()`
# @used-by :mod:`agent_tools.cli_output_json`
def extract_top_level_json_objects(text: str) -> tuple[list[dict[str, Any]], bool]:
	body = _body_without_header(text)
	dec = json.JSONDecoder()
	objs: list[dict[str, Any]] = []
	trunc_fail = False
	pos = 0
	for m in _COL0_BRACE_RE.finditer(body):
		idx = m.start()
		if idx < pos:
			continue
		obj, pos, failed = _decode_col0_at(dec, body, idx)
		if None is not obj:
			objs.append(obj)
		elif failed:
			trunc_fail = True
	return (objs, trunc_fail)
# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_classify_shadow_output()`
# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.is_passing_output()`
# @used-by :meth:`Df.Harness.Grounding.Doc5RequirementChecker.Doc5RequirementChecker.is_failed_cli_output()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_top_level_json_parser_ignores_nested_valid_false_and_catches_top_level_failures()`
# @used-by :mod:`agent_tools.cli_output_json`
def top_level_json_has_failure(text: str) -> bool:
	objs, trunc_fail = extract_top_level_json_objects(text)
	return trunc_fail or any((False is obj.get('valid') or False is obj.get('ok') for obj in objs))
__all__ = ['extract_top_level_json_objects', 'top_level_json_has_failure']
