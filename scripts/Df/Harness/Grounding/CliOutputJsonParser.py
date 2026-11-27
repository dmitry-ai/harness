# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Tdd.OutcomeParser import OutcomeParser
import json
import re
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
# @used-by :mod:`agent_tools.cli_output_json`
class CliOutputJsonParser:
	__COL0_BRACE_RE = re.compile(r'(?m)^\{')
	__INLINE_FAIL_RE = re.compile(r'"(?:valid|ok)"\s*:\s*false\b', re.IGNORECASE)
	__TOP_INDENT_FAIL_RE = re.compile(r'^(?: {1,2}|\t)"(?:valid|ok)"\s*:\s*false\b', re.IGNORECASE)
	# @used-by :func:`agent_tools.cli_output_json.top_level_json_has_failure()`
	# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_cli_output_json_parser_and_facade_cover_all_branches()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`CliOutputJsonParser.extract_objects()`
	@staticmethod
	def __body_without_header(text: str) -> str:
		raw = text or ''
		parts = OutcomeParser.BG_HEADER_SPLIT_RE.split(raw, maxsplit=1)
		return parts[1] if 2 == len(parts) else raw
	# @used-by :meth:`CliOutputJsonParser.extract_objects()`
	@staticmethod
	def __decode_col0_at(dec: json.JSONDecoder, body: str, idx: int) -> tuple[dict[str, Any] | None, int, bool]:
		try:
			obj, end = dec.raw_decode(body, idx)
		except ValueError:
			r = (None, idx + 1, CliOutputJsonParser.__truncated_top_level_failure(body[idx:]))
		else:
			r = (obj if isinstance(obj, dict) else None, end, False)
		return r
	# @used-by :meth:`CliOutputJsonParser.__decode_col0_at()`
	@staticmethod
	def __truncated_top_level_failure(snippet: str) -> bool:
		lines = (snippet or '').splitlines()
		if not lines:
			r = False
		else:
			first = lines[0]
			nested = first.find('{', 1)
			head = first[:nested] if 0 < nested else first
			r = bool(CliOutputJsonParser.__INLINE_FAIL_RE.search(head)) or any((bool(CliOutputJsonParser.__TOP_INDENT_FAIL_RE.match(ln)) for ln in lines[1:]))
		return r
	# @used-by :func:`agent_tools.cli_output_json.extract_top_level_json_objects()`
	# @used-by :meth:`CliOutputJsonParser.has_failure()`
	# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_cli_output_json_parser_and_facade_cover_all_branches()`
	@staticmethod
	def extract_objects(text: str) -> tuple[list[dict[str, Any]], bool]:
		body = CliOutputJsonParser.__body_without_header(text)
		dec = json.JSONDecoder()
		objs: list[dict[str, Any]] = []
		trunc_fail = False
		pos = 0
		for m in CliOutputJsonParser.__COL0_BRACE_RE.finditer(body):
			idx = m.start()
			if idx < pos:
				continue
			obj, pos, failed = CliOutputJsonParser.__decode_col0_at(dec, body, idx)
			if None is not obj:
				objs.append(obj)
			elif failed:
				trunc_fail = True
		return (objs, trunc_fail)
	# @used-by :func:`agent_tools.cli_output_json.top_level_json_has_failure()`
	# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_cli_output_json_parser_and_facade_cover_all_branches()`
	def has_failure(self) -> bool:
		objs, trunc_fail = CliOutputJsonParser.extract_objects(self.__text)
		return trunc_fail or any((False is obj.get('valid') or False is obj.get('ok') for obj in objs))
