# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import json
import re
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
_HARNESS_TOP_KEYS = frozenset(('Time', 'Issue', 'Project', 'Journal', 'Agent', 'Trace'))
_LEADING_JSON_FENCE_RE = re.compile(r'^```json[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*(?:\r?\n\r?\n|\r?\n|$)')
def _is_harness_metadata_obj(obj: Any) -> bool:
	proj = obj.get('Project') if isinstance(obj, dict) else None
	has_proj = isinstance(proj, dict) and isinstance(proj.get('Path'), str) and bool(proj['Path'].strip())
	return bool(obj) and isinstance(obj, dict) and set(obj).issubset(_HARNESS_TOP_KEYS) and has_proj and any((k in obj for k in ('Time', 'Issue', 'Journal', 'Agent', 'Trace')))
def extract_leading_metadata_header(text: str) -> tuple[dict[str, Any] | None, str]:
	r: tuple[dict[str, Any] | None, str] = (None, text)
	m = _LEADING_JSON_FENCE_RE.match(text) if isinstance(text, str) and text.startswith('```json') else None
	if None is not m:
		try:
			parsed = json.loads(m.group(1))
		except ValueError:
			parsed = None
		if _is_harness_metadata_obj(parsed):
			r = (parsed, text[m.end():])
	return r
def prepend_metadata_header(body: str, data: dict[str, Any]) -> str:
	return render_metadata_header(data) + strip_leading_metadata_header(body)
def render_metadata_header(data: dict[str, Any]) -> str:
	return '```json\n' + json.dumps(data, ensure_ascii=False, indent='\t') + '\n```\n\n'
def strip_leading_metadata_header(text: str) -> str:
	return extract_leading_metadata_header(text)[1]
