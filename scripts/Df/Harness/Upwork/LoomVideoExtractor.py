# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.VideoDetector import VideoDetector
import json
import re
from urllib.request import Request, urlopen
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class LoomVideoExtractor:
	# @used-by :func:`agent_tools.upwork_data.extract_loom_video()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	def __init__(self, url: str, *, timeout: float=15.0, opener=None) -> None:
		self.__url = url
		self.__timeout = timeout
		self.__open_fn = opener or (lambda req, tm: urlopen(req, timeout=tm))
	# @used-by :meth:`LoomVideoExtractor.extract()`
	def __fetch_phrases(self, state: dict) -> list[dict]:
		tdetails = next((v for k, v in state.items() if k.startswith('VideoTranscriptDetails:') and isinstance(v, dict)), {})
		r: list[dict] = []
		if tdetails.get('captions_source_url') and (not tdetails.get('source_url')):
			with self.__open_fn(Request(tdetails['captions_source_url'], headers={'User-Agent': 'Mozilla/5.0'}), self.__timeout) as vresp:
				r = self.parse_webvtt_phrases(vresp.read().decode('utf-8', errors='replace'))
		elif tdetails.get('source_url'):
			with self.__open_fn(Request(tdetails['source_url'], headers={'User-Agent': 'Mozilla/5.0'}), self.__timeout) as tresp:
				tdata = json.loads(tresp.read().decode('utf-8', errors='replace'))
			for p in tdata.get('phrases') or []:
				val = (p.get('value') or '').strip()
				if val:
					sec = int(float(p.get('ts') or 0))
					mm, ss = divmod(sec, 60)
					r.append({'ts': f'[{mm:02d}:{ss:02d}]', 'seconds': sec, 'text': val})
		return r
	# @used-by :meth:`LoomVideoExtractor.extract()`
	def __load_state(self, vid_id: str) -> dict:
		share_url = f'https://www.loom.com/share/{vid_id}'
		with self.__open_fn(Request(share_url, headers={'User-Agent': 'Mozilla/5.0'}), self.__timeout) as resp:
			html = resp.read().decode('utf-8', errors='ignore')
		state_m = re.search('window\\.__APOLLO_STATE__\\s*=\\s*(\\{.*?\\});\\s*\\n', html, re.S)
		if not state_m:
			raise ValueError(f'Loom __APOLLO_STATE__ not found for {share_url}')
		return json.loads(state_m.group(1))
	# @used-by :meth:`LoomVideoExtractor.parse_webvtt_phrases()`
	@staticmethod
	def __parse_vtt_block(block: str) -> dict | None:
		lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
		ts_line = next((ln for ln in lines if '-->' in ln), None) if lines and (not lines[0].startswith('WEBVTT')) else None
		m = re.match('^(?:(\\d+):)?(\\d{2}):(\\d{2})[.,]\\d+\\s*-->', ts_line) if ts_line else None
		r = None
		if m:
			mm, ss = (int(m.group(2)) + int(m.group(1) or 0) * 60, int(m.group(3)))
			txt = ' '.join((re.sub('<[^>]+>', '', ln).strip() for ln in lines[lines.index(ts_line) + 1:] if ln.strip())).strip()
			if txt:
				r = {'ts': f'[{mm:02d}:{ss:02d}]', 'seconds': mm * 60 + ss, 'text': txt}
		return r
	# @used-by :meth:`LoomVideoExtractor.extract()`
	@staticmethod
	def __render_markdown(speaker: str, dur_str: str, title: str, screen_type: str, phrases: list[dict]) -> str:
		speaker_str = f'Speaker: {speaker} ({dur_str}).' if speaker else f'Recording duration: {dur_str}.'
		title_str = f' Recording title: «{title}».' if title else ''
		mode_str = ' Recording format: screen share and speaker webcam (screen_cam).' if 'screen_cam' == screen_type else ''
		header = f'{speaker_str}{title_str}{mode_str}'.strip()
		key_points = [f"- ({p['ts'].strip('[]')}) {p['text']}" for p in phrases[:8]] or ['- Spoken commentary is recorded in the full transcript below.']
		transcript = [f"{p['ts']} {p['text']}" for p in phrases] or ['[00:00] (audio track is absent or contains no speech)']
		return '\n'.join(['# Video:', header, '', '# Key Spoken Commentary Points (Additions to Document Text):', *key_points, '', '# Full Audio Transcript:', *transcript])
	# @used-by :func:`agent_tools.upwork_data.extract_loom_video()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	def extract(self) -> dict:
		canon = VideoDetector.canonical_video_url(self.__url)
		loom_m = re.search('loom\\.com/(?:share|embed)/([A-Za-z0-9]+)', canon, re.I)
		if not loom_m:
			raise ValueError(f'Not a Loom video URL: {self.__url}')
		vid_id = loom_m.group(1)
		state = self.__load_state(vid_id)
		video_obj = state.get(f'RegularUserVideo:{vid_id}') or next((v for k, v in state.items() if k.startswith('RegularUserVideo:') and isinstance(v, dict)), {})
		owner_ref = (video_obj.get('owner') or {}).get('__ref') if isinstance(video_obj.get('owner'), dict) else None
		owner_obj = state.get(owner_ref, {}) if owner_ref else next((v for k, v in state.items() if k.startswith('RegularUser:') and isinstance(v, dict)), {})
		title = (video_obj.get('name') or '').strip()
		speaker = (owner_obj.get('display_name') or owner_obj.get('first_name') or '').strip()
		vprops = video_obj.get('video_properties') or {}
		duration_sec, screen_type = (vprops.get('duration'), vprops.get('screen_type') or vprops.get('recording_type') or '')
		phrases = self.__fetch_phrases(state)
		dur_str = self.format_duration_ru(duration_sec)
		md = self.__render_markdown(speaker, dur_str, title, screen_type, phrases)
		return {'kind': 'loom', 'video_id': vid_id, 'url': canon, 'title': title, 'speaker': speaker, 'duration_seconds': duration_sec, 'duration_human': dur_str, 'screen_type': screen_type, 'phrases': phrases, 'markdown': md}
	# @used-by :func:`agent_tools.upwork_data.format_duration_ru()`
	# @used-by :meth:`LoomVideoExtractor.extract()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def format_duration_ru(seconds: int | float | None) -> str:
		if not seconds or 0 >= seconds:
			r = 'duration not specified'
		else:
			mm, ss = divmod(int(round(float(seconds))), 60)
			if 0 < mm and 0 < ss:
				r = f'{mm} min {ss} sec'
			elif 0 < mm:
				r = f'{mm} min'
			else:
				r = f'{ss} sec'
		return r
	# @used-by :func:`agent_tools.upwork_data.parse_webvtt_phrases()`
	# @used-by :meth:`LoomVideoExtractor.__fetch_phrases()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def parse_webvtt_phrases(cls, vtt_text: str) -> list[dict]:
		r: list[dict] = []
		for block in re.split('\\r?\\n\\r?\\n', (vtt_text or '').strip()):
			item = cls.__parse_vtt_block(block)
			if None is not item:
				r.append(item)
		return r
