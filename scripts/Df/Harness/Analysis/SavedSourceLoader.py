# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.JsonPointer import JsonPointer
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
from Df.Harness.Analysis.ObservationContentLoader import ObservationContentLoader
from Df.Harness.Analysis.ObservationResolver import ObservationResolver
from agent_tools.research import extract_bytes
import html as html_lib
import json
import re
_DOC_EXTS = ('.pdf', '.docx', '.odt', '.xlsx', '.xlsm', '.rtf')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SavedSourceLoader:
	# @used-by :func:`agent_tools.evidence.saved_source()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_counter_source()`
	# @used-by :meth:`Df.Harness.Analysis.SavedQuoteVerifier.SavedQuoteVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def __init__(self, root, source: str, observation=None, *, need_sections: bool=True, extract_fn=None) -> None:
		self.__root = root
		self.__source = source
		self.__observation = observation
		self.__need_sections = need_sections
		self.__extract_fn = extract_fn
	# @used-by :meth:`SavedSourceLoader.__load_local()`
	def __load_document(self, file: Path, raw: bytes, fragment: str, sha: str) -> dict:
		from agent_tools.upwork_data import extract_attachment_markdown
		md_text = extract_attachment_markdown(file, raw)
		if fragment:
			md_text = self.__markdown_section(md_text, fragment)
		plain_text = re.sub('\\[([^\\]]+)\\]\\([^)]+\\)', '\\1', md_text).replace('**', '')
		return {'kind': 'text', 'text': md_text + '\n' + plain_text, 'fragment': unquote(fragment), 'file': file, 'sha256': sha}
	# @used-by :meth:`SavedSourceLoader.load()`
	def __load_local(self, base: str, fragment: str) -> dict:
		file = LocalSourceResolver(self.__root, base).resolve()
		raw = file.read_bytes()
		sha = df_sha256(raw)
		if re.fullmatch('[a-f0-9]{64}', file.stem.lower()) and sha != file.stem.lower():
			raise ValueError('Immutable source file differs from its content-addressed filename')
		if file.suffix.lower() in _DOC_EXTS:
			r = self.__load_document(file, raw, fragment, sha)
		else:
			r = self.__load_text_or_structured(file, raw, fragment, sha)
		return r
	# @used-by :meth:`SavedSourceLoader.__load_local()`
	def __load_text_or_structured(self, file: Path, raw: bytes, fragment: str, sha: str) -> dict:
		text = raw.decode('utf-8-sig')
		suf = file.suffix.lower()
		if '.json' == suf:
			value = JsonPointer(json.loads(text), fragment).resolve()
			rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
			r = {'kind': 'json', 'text': rendered, 'fragment': unquote(fragment), 'file': file, 'sha256': sha}
		elif suf in ('.html', '.htm'):
			r = {'kind': 'html', 'data': extract_bytes(raw, 'text/html', 'html'), 'raw': text, 'fragment': unquote(fragment), 'file': file, 'sha256': sha}
		else:
			if ('.md' == suf or '.md' == file.name) and fragment:
				text = self.__markdown_section(text, fragment)
			elif fragment:
				raise ValueError('This source format does not support a verified fragment locator')
			r = {'kind': 'text', 'text': text, 'fragment': unquote(fragment), 'file': file, 'sha256': sha}
		return r
	# @used-by :meth:`SavedSourceLoader.__load_document()`
	# @used-by :meth:`SavedSourceLoader.__load_text_or_structured()`
	def __markdown_section(self, text: str, fragment: str) -> str:
		from agent_tools.links import parse_markdown_headings
		headings, _, ambiguous, _ = parse_markdown_headings(text)
		target = unquote(fragment)
		if target in ambiguous:
			raise ValueError('Markdown section anchor is ambiguous')
		match = next((i for i, h in enumerate(headings) if target in h['section_anchors']), None)
		if None is match:
			raise ValueError('Markdown section anchor is absent')
		lines = text.splitlines(keepends=True)
		heading = headings[match]
		end = next((h['start_line'] for h in headings[match + 1:] if h['level'] <= heading['level']), len(lines))
		raw_sec = ''.join(lines[heading['start_line']:end])
		unesc_sec = html_lib.unescape(raw_sec)
		return raw_sec if unesc_sec == raw_sec else raw_sec + '\n' + unesc_sec
	# @used-by :func:`agent_tools.evidence.saved_source()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_counter_source()`
	# @used-by :meth:`Df.Harness.Analysis.SavedQuoteVerifier.SavedQuoteVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def load(self) -> dict:
		base, fragment = urldefrag(self.__source)
		if urlsplit(base).scheme.lower() not in ('http', 'https'):
			r = self.__load_local(base, fragment)
		else:
			obs_ref, meta = ObservationResolver(self.__root, base, self.__observation).resolve()
			r = ObservationContentLoader(self.__root, obs_ref, meta, fragment=fragment, need_sections=self.__need_sections, extract_fn=self.__extract_fn).load()
		return r