# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.AttachmentExtractor import AttachmentExtractor
from pathlib import Path
import re
_VIDEO_URL_RE = re.compile('https?://(?:www\\.)?(?:loom\\.com/(?:share|embed)/[A-Za-z0-9_-]+|youtube\\.com/(?:watch\\?[^\\s)"\\\'>]+|embed/[A-Za-z0-9_-]+|shorts/[A-Za-z0-9_-]+)|youtu\\.be/[A-Za-z0-9_-]+|vimeo\\.com/\\d+|player\\.vimeo\\.com/video/\\d+|[^\\s)"\\\'>]+\\.(?:mp4|mov|webm|m4v)(?:\\?[^\\s)"\\\'>]*)?)', re.I)
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class VideoDetector:
	# @used-by :meth:`VideoDetector.detect()`
	@staticmethod
	def __scan_attachments(saved_attachments, seen_keys: set[str], out: list[dict]) -> None:
		for item in saved_attachments or []:
			name = Path(item.get('filename') or item.get('name') or item.get('file') or '').name
			key = f'file:{name}'
			if name and 'video' == AttachmentExtractor.classify(name) and key not in seen_keys:
				seen_keys.add(key)
				out.append({'kind': 'file', 'video_id': item.get('sha256'), 'filename': name, 'sha256': item.get('sha256'), 'label': f'`{name}`', 'heading': f'Description in `{name}`'})
	# @used-by :meth:`VideoDetector.detect()`
	@classmethod
	def __scan_text_urls(cls, texts: list[str], seen_keys: set[str], out: list[dict]) -> None:
		for text in texts:
			for match in _VIDEO_URL_RE.finditer(text or ''):
				raw_url = match.group(0).rstrip('.,;!)')
				canon = cls.canonical_video_url(raw_url)
				if canon not in seen_keys:
					seen_keys.add(canon)
					loom_m = re.match('^https?://(?:www\\.)?loom\\.com/share/([A-Za-z0-9]+)', canon, re.I)
					out.append({'kind': 'loom' if loom_m else 'url', 'video_id': loom_m.group(1) if loom_m else None, 'url': canon, 'raw_url': raw_url, 'label': canon, 'heading': f'Description in {canon}'})
	# @used-by :func:`agent_tools.upwork_data.canonical_video_url()`
	# @used-by :meth:`Df.Harness.Upwork.LoomVideoExtractor.LoomVideoExtractor.extract()`
	# @used-by :meth:`VideoDetector.__scan_text_urls()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def canonical_video_url(url: str) -> str:
		u = url.strip().rstrip('.,;!?')
		m = re.match('^https?://(?:www\\.)?loom\\.com/(?:share|embed)/([A-Za-z0-9]+)', u, re.I)
		return f'https://loom.com/share/{m.group(1)}' if m else u
	# @used-by :func:`agent_tools.upwork_data.detect_client_videos()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.build()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_videos()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def detect(cls, description: str='', document_markdowns: list[str] | tuple[str, ...]=(), saved_attachments: list[dict] | tuple[dict, ...]=()) -> list[dict]:
		r: list[dict] = []
		seen_keys: set[str] = set()
		cls.__scan_text_urls([description or '', *(document_markdowns or ())], seen_keys, r)
		cls.__scan_attachments(saved_attachments, seen_keys, r)
		return r
