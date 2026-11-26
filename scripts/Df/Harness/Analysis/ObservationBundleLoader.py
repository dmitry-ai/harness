# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
from agent_tools.research import classify_html_challenge, extract_github_blob_lines, extract_markdown, extractor_version
import json
import re
_MD_CTYPES = ('text/markdown', 'text/x-markdown')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ObservationBundleLoader:
	# @used-by :func:`agent_tools.evidence_loader.load_observation_bundle()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def __init__(self, jfile: Path, data: dict, *, max_bytes: int) -> None:
		self.__jfile = Path(jfile)
		self.__data = data
		self.__max_bytes = max_bytes
	# @used-by :meth:`ObservationBundleLoader.__collect_ext_metadata()`
	# @used-by :meth:`ObservationBundleLoader.__extract_html()`
	# @used-by :meth:`ObservationBundleLoader.__extract_markdown()`
	def __add_anchor(self, anchors: set[str], value: str) -> None:
		if value:
			anchors.add(value)
			if value.startswith('user-content-') and 13 < len(value):
				anchors.add(value[13:])
	# @used-by :meth:`ObservationBundleLoader.__inspect_ext_file()`
	def __collect_ext_metadata(self, ext: dict, state: dict) -> None:
		title = (ext.get('title') or '').strip() or self.__first_h1(ext.get('headings'))
		if title:
			state['titles'].append(title)
		if isinstance(ext.get('anchors'), list):
			state['has_html_anchors'] = True
			for raw_a in ext['anchors']:
				self.__add_anchor(state['anchors'], str(raw_a) if raw_a else '')
		if isinstance(ext.get('text'), str) and ext['text'].strip():
			state['texts'].append(ext['text'])
	# @used-by :meth:`ObservationBundleLoader.__inspect_resp_bin()`
	def __extract_html(self, raw_text: str, urls_here: list[str], host: str, state: dict) -> None:
		if ((not state['has_ext']) or state['recheck']) and classify_html_challenge(raw_text, status=self.__data.get('status')):
			state['shell_reason'] = 'unextracted HTML JS challenge or empty shell'
		state['has_html_anchors'] = True
		for m_id in re.finditer('\\b(?:id|name)=["\']([^"\']+)["\']', raw_text, re.I):
			self.__add_anchor(state['anchors'], m_id.group(1))
		m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
		if m_t:
			title = ' '.join(m_t.group(1).split())
			if title:
				state['titles'].append(title)
		if 'github.com' == host and any(('/blob/' in (urlsplit(u).path or '') for u in urls_here)):
			gh_lines = extract_github_blob_lines(raw_text)
			if gh_lines:
				state['texts'].append('\n'.join(gh_lines))
				state['anchors'].update((f'LC{ln}' for ln in range(1, len(gh_lines) + 1)))
	# @used-by :meth:`ObservationBundleLoader.__inspect_resp_bin()`
	def __extract_markdown(self, raw_text: str, state: dict) -> None:
		md_info = extract_markdown(raw_text)
		if 0 == md_info.get('word_count', 0):
			state['shell_reason'] = 'word_count=0 (empty Markdown response)'
		if md_info.get('title'):
			state['titles'].append(md_info['title'])
		state['has_html_anchors'] = True
		for anchor in md_info.get('anchors') or []:
			self.__add_anchor(state['anchors'], str(anchor))
		if md_info.get('text'):
			state['texts'].append(md_info['text'])
	# @used-by :meth:`ObservationBundleLoader.__collect_ext_metadata()`
	def __first_h1(self, headings) -> str:
		return next((h.get('text', '').strip() for h in headings if isinstance(h, dict) and 1 == h.get('level') and h.get('text')), '') if isinstance(headings, list) else ''
	# @used-by :meth:`ObservationBundleLoader.__scan_ext_files()`
	def __inspect_ext_file(self, ext: dict, cur_ext_ver, has_resp_bin: bool, state: dict) -> None:
		if ext.get('extractor_version') != cur_ext_ver and has_resp_bin:
			state['recheck'] = True
		elif True is ext.get('browser_check_required'):
			state['shell_reason'] = 'browser_check_required=True (JS/anti-bot challenge or empty SPA shell)'
		elif 'headings' in ext and None is ext.get('sitemap') and (0 == ext.get('word_count', 0)):
			state['shell_reason'] = 'word_count=0 (empty HTML shell)'
		self.__collect_ext_metadata(ext, state)
	# @used-by :meth:`ObservationBundleLoader.load()`
	def __inspect_resp_bin(self, resp_bin: Path, urls_here: list[str], host: str, valid_status: bool, state: dict) -> None:
		try:
			if resp_bin.stat().st_size <= self.__max_bytes:
				raw_text = resp_bin.read_bytes().decode(self.__data.get('charset') or 'utf-8', errors='replace')
				ctype = (self.__data.get('content_type') or '').split(';', 1)[0].strip().lower()
				is_md = ctype in _MD_CTYPES
				is_html = (not is_md) and ('html' in ctype or '<title' in raw_text[:4000].lower() or raw_text.lstrip().lower().startswith(('<!doctype html', '<html')))
				if is_md:
					self.__extract_markdown(raw_text, state)
				elif is_html:
					self.__extract_html(raw_text, urls_here, host, state)
				if raw_text.strip():
					state['texts'].append(raw_text)
				if ('json' in ctype or raw_text.lstrip().startswith('{')) and valid_status and (not state['shell_reason']):
					state['json_payload'] = json.loads(raw_text)
		except (OSError, ValueError):
			pass
	# @used-by :meth:`ObservationBundleLoader.load()`
	def __scan_ext_files(self, ext_files: list[Path], has_resp_bin: bool, state: dict) -> None:
		cur_ext_ver = extractor_version()
		for ext_file in ext_files:
			try:
				ext = json.loads(ext_file.read_text(encoding='utf-8'))
				if isinstance(ext, dict):
					self.__inspect_ext_file(ext, cur_ext_ver, has_resp_bin, state)
			except (OSError, ValueError):
				continue
	# @used-by :func:`agent_tools.evidence_loader.load_observation_bundle()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def load(self) -> dict:
		urls_here = [u for u in (self.__data.get('url'), self.__data.get('final_url')) if isinstance(u, str) and u.startswith(('http://', 'https://'))]
		host = (urlsplit(urls_here[0]).hostname or '').lower() if urls_here else ''
		valid_status = (not self.__data.get('error')) and ('dom' == self.__data.get('kind') or 200 <= (self.__data.get('status') or 0) < 300)
		resp_bin = self.__jfile.parent / 'response.bin'
		has_resp_bin = resp_bin.is_file()
		ext_files = list(self.__jfile.parent.glob('extracted-*.json'))
		state = {'has_ext': bool(ext_files), 'recheck': False, 'shell_reason': None, 'titles': [], 'anchors': set(), 'texts': [], 'has_html_anchors': False, 'json_payload': None}
		self.__scan_ext_files(ext_files, has_resp_bin, state)
		if has_resp_bin:
			self.__inspect_resp_bin(resp_bin, urls_here, host, valid_status, state)
		ok = valid_status and (not state['shell_reason'])
		reason = state['shell_reason'] or f"error={self.__data.get('error')} status={self.__data.get('status')}"
		return {'urls': urls_here, 'host': host, 'valid': ok, 'reason': None if ok else reason, 'titles': state['titles'], 'anchors': state['anchors'], 'has_html_anchors': state['has_html_anchors'], 'texts': state['texts'], 'json_payload': state['json_payload']}