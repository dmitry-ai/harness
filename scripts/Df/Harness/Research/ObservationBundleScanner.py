# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
from Df.Harness.Research.ChallengeClassifier import ChallengeClassifier
from Df.Harness.Research.MarkdownExtractor import MarkdownExtractor
from Df.Harness.lib.research import dfh_extract_github_blob_lines, dfh_extractor_version, dfh_research_max_bytes, dfh_research_seam
import html as html_lib
import json
import re
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ObservationBundleScanner:
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__summarize_bundle()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_link_auditor_and_observation_bundle_scanner()`
	def __init__(self, obs_file: Path, data: dict, valid_status: bool) -> None:
		self.__obs_file = obs_file
		self.__data = data
		self.__valid_status = valid_status
	# @used-by :meth:`ObservationBundleScanner.__scan_ext_files()`
	@classmethod
	def __apply_ext_entry(cls, ext: dict, state: dict, cur_ver: str, has_resp: bool) -> None:
		cls.__apply_ext_status(ext, state, cur_ver, has_resp)
		t_cand = ' '.join(str(ext.get('title') or '').split())
		if t_cand and (not state['title']):
			state['title'] = t_cand
		if isinstance(ext.get('word_count'), int) and None is state['word_count']:
			state['word_count'] = ext['word_count']
		cls.__merge_ext_headings(ext, state)
		cls.__merge_ext_anchors(ext, state)
		if isinstance(ext.get('text'), str) and ext['text'].strip() and (not state['plain_text']):
			state['plain_text'] = ext['text']
	# @used-by :meth:`ObservationBundleScanner.__apply_ext_entry()`
	@staticmethod
	def __apply_ext_status(ext: dict, state: dict, cur_ver: str, has_resp: bool) -> None:
		if ext.get('extractor_version') != cur_ver and has_resp:
			state['recheck_challenge'] = True
		elif True is ext.get('browser_check_required'):
			state['is_shell'], state['invalid_reason'] = (True, 'browser_check_required=True (JS/anti-bot challenge or empty SPA shell)')
		elif 'headings' in ext and None is ext.get('sitemap') and 0 == ext.get('word_count', 0):
			state['is_shell'], state['invalid_reason'] = (True, 'word_count=0 (empty HTML shell)')
	# @used-by :meth:`ObservationBundleScanner.__apply_ext_entry()`
	@staticmethod
	def __merge_ext_anchors(ext: dict, state: dict) -> None:
		if isinstance(ext.get('ambiguous_anchors'), list):
			state['ambiguous_anchors'].update((str(a) for a in ext['ambiguous_anchors'] if a))
		for a in ext.get('anchors') if isinstance(ext.get('anchors'), list) else ():
			if a:
				a_str = str(a)
				state['raw_anchors'].add(a_str)
				if a_str.startswith('user-content-') and 13 < len(a_str):
					state['raw_anchors'].add(a_str[13:])
	# @used-by :meth:`ObservationBundleScanner.__apply_ext_entry()`
	@staticmethod
	def __merge_ext_headings(ext: dict, state: dict) -> None:
		headings = ext.get('headings')
		if isinstance(headings, list):
			dict_headings = [h for h in headings if isinstance(h, dict)]
			state['headings'] = state['headings'] or dict_headings
			for ht in (' '.join(str(h['text']).split()) for h in dict_headings if 1 == h.get('level') and h.get('text')):
				if ht and ht not in state['h1_list']:
					state['h1_list'].append(ht)
		if isinstance(ext.get('sections'), list) and (not state['sections']):
			state['sections'] = [s for s in ext['sections'] if isinstance(s, dict)]
	# @used-by :meth:`ObservationBundleScanner.scan()`
	def __scan_ext_files(self, ext_files: list[Path], state: dict, has_resp: bool) -> None:
		cur_ver = dfh_research_seam('extractor_version', dfh_extractor_version)()
		for ext_file in ext_files:
			try:
				ext = json.loads(ext_file.read_text(encoding='utf-8'))
			except (OSError, ValueError):
				continue
			if isinstance(ext, dict):
				self.__apply_ext_entry(ext, state, cur_ver, has_resp)
	# @used-by :meth:`ObservationBundleScanner.__scan_raw_response()`
	def __scan_raw_html(self, raw_text: str, state: dict, has_ext: bool) -> list[str]:
		if (not has_ext or state['recheck_challenge']) and ChallengeClassifier(raw_text, status=self.__data.get('status')).is_challenge():
			state['is_shell'], state['invalid_reason'] = (True, 'unextracted HTML JS challenge or empty shell')
		for m_id in re.finditer('\\b(?:id|name)=["\\\']([^"\\\']+)["\\\']', raw_text, re.I):
			aid = m_id.group(1)
			state['raw_anchors'].add(aid)
			if aid.startswith('user-content-') and 13 < len(aid):
				state['raw_anchors'].add(aid[13:])
		if not state['title']:
			m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
			t_raw = html_lib.unescape(' '.join(m_t.group(1).split())) if m_t else ''
			if t_raw:
				state['title'] = t_raw
		parsed_u = urlsplit(str(self.__data.get('final_url') or self.__data.get('url') or '').strip())
		return dfh_extract_github_blob_lines(raw_text) if 'github.com' == (parsed_u.hostname or '').lower() and '/blob/' in (parsed_u.path or '') else []
	# @used-by :meth:`ObservationBundleScanner.__scan_raw_response()`
	@staticmethod
	def __scan_raw_json_title(raw_text: str, state: dict) -> None:
		try:
			jbody = json.loads(raw_text)
			if isinstance(jbody, dict) and isinstance(jbody.get('title'), str) and jbody['title'].strip():
				state['title'] = ' '.join(jbody['title'].split())
			if not state['plain_text']:
				state['plain_text'] = raw_text
		except ValueError:
			pass
	# @used-by :meth:`ObservationBundleScanner.__scan_raw_response()`
	@staticmethod
	def __scan_raw_markdown(raw_text: str, state: dict) -> None:
		md_info = MarkdownExtractor(raw_text).extract()
		if 0 == md_info.get('word_count', 0):
			state['is_shell'], state['invalid_reason'] = (True, 'word_count=0 (empty Markdown response)')
		if md_info.get('title') and (not state['title']):
			state['title'] = ' '.join(str(md_info['title']).split())
		if None is state['word_count']:
			state['word_count'] = md_info.get('word_count')
		state['raw_anchors'].update((str(a) for a in md_info.get('anchors') or [] if a))
		state['ambiguous_anchors'].update((str(a) for a in md_info.get('ambiguous_anchors') or [] if a))
		state['sections'] = state['sections'] or list(md_info.get('sections') or [])
		state['headings'] = state['headings'] or list(md_info.get('headings') or [])
		state['plain_text'] = state['plain_text'] or str(md_info.get('text') or '')
	# @used-by :meth:`ObservationBundleScanner.scan()`
	def __scan_raw_response(self, resp_bin: Path, state: dict, has_ext: bool) -> tuple[str, list[str]]:
		raw_text, blob_lines = ('', [])
		if resp_bin.is_file():
			try:
				if dfh_research_max_bytes() >= resp_bin.stat().st_size:
					raw_text = resp_bin.read_bytes().decode(self.__data.get('charset') or 'utf-8', errors='replace')
					ctype = (self.__data.get('content_type') or '').split(';', 1)[0].strip().lower()
					is_md = ctype in ('text/markdown', 'text/x-markdown')
					is_html = (not is_md) and ('html' in ctype or '<title' in raw_text[:4000].lower() or raw_text.lstrip().lower().startswith(('<!doctype html', '<html')))
					if is_md and (not has_ext):
						self.__scan_raw_markdown(raw_text, state)
					elif is_html:
						blob_lines = self.__scan_raw_html(raw_text, state, has_ext)
					elif ('json' in ctype or raw_text.lstrip().startswith('{')) and self.__valid_status and (not state['title']):
						self.__scan_raw_json_title(raw_text, state)
					if (not state['plain_text']) and (not is_html):
						state['plain_text'] = raw_text
			except OSError:
				pass
		return (raw_text, blob_lines)
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__summarize_bundle()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_link_auditor_and_observation_bundle_scanner()`
	def scan(self) -> tuple[dict, str, list[str]]:
		state: dict = {'is_shell': False, 'invalid_reason': None, 'title': None, 'h1_list': [], 'word_count': None, 'raw_anchors': set(), 'ambiguous_anchors': set(), 'sections': [], 'headings': [], 'plain_text': '', 'recheck_challenge': False}
		ext_files = sorted(self.__obs_file.parent.glob('extracted-*.json'))
		resp_bin = self.__obs_file.parent / 'response.bin'
		self.__scan_ext_files(ext_files, state, resp_bin.is_file())
		raw_text, blob_lines = self.__scan_raw_response(resp_bin, state, bool(ext_files))
		return (state, raw_text, blob_lines)