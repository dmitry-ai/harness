# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import json
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class HeaderRenderer:
	HARNESS_TOP_KEYS = frozenset(('Time', 'Issue', 'Project', 'Journal', 'Agent', 'Clarifications', 'Trace'))
	LEADING_JSON_FENCE_RE = re.compile(r'^```json[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*(?:\r?\n\r?\n|\r?\n|$)')
	# @used-by :func:`agent_tools.meta.headers.render_metadata_header()`
	# @used-by :meth:`HeaderRenderer.prepend()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def __init__(self, data: dict[str, Any]) -> None:
		self.__data = data
	# @used-by :func:`agent_tools.meta.headers.render_metadata_header()`
	# @used-by :meth:`HeaderRenderer.prepend()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def render(self) -> str:
		return '```json\n' + json.dumps(self.__data, ensure_ascii=False, indent='\t') + '\n```\n\n'
	# @used-by :func:`agent_tools.meta.headers.extract_leading_metadata_header()`
	# @used-by :meth:`HeaderRenderer.strip_leading()`
	@staticmethod
	def extract_leading(text: str) -> tuple[dict[str, Any] | None, str]:
		r: tuple[dict[str, Any] | None, str] = (None, text)
		m = HeaderRenderer.LEADING_JSON_FENCE_RE.match(text) if isinstance(text, str) and text.startswith('```json') else None
		if None is not m:
			try:
				parsed = json.loads(m.group(1))
			except ValueError:
				parsed = None
			if HeaderRenderer.is_harness_metadata_obj(parsed):
				r = (parsed, text[m.end():])
		return r
	# @used-by :func:`agent_tools.meta.headers._is_harness_metadata_obj()`
	# @used-by :meth:`HeaderRenderer.extract_leading()`
	@staticmethod
	def is_harness_metadata_obj(obj: Any) -> bool:
		proj = obj.get('Project') if isinstance(obj, dict) else None
		has_proj = isinstance(proj, dict) and isinstance(proj.get('Path'), str) and bool(proj['Path'].strip())
		return bool(obj) and isinstance(obj, dict) and set(obj).issubset(HeaderRenderer.HARNESS_TOP_KEYS) and has_proj and any((k in obj for k in ('Time', 'Issue', 'Journal', 'Agent', 'Trace')))
	# @used-by :func:`agent_tools.meta.headers.prepend_metadata_header()`
	@staticmethod
	def prepend(body: str, data: dict[str, Any]) -> str:
		return HeaderRenderer(data).render() + HeaderRenderer.strip_leading(body)
	# @used-by :func:`agent_tools.meta.headers.strip_leading_metadata_header()`
	# @used-by :meth:`HeaderRenderer.prepend()`
	@staticmethod
	def strip_leading(text: str) -> str:
		return HeaderRenderer.extract_leading(text)[1]
