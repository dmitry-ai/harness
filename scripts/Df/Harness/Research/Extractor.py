# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urldefrag
from Df.Harness.Research.ChallengeClassifier import ChallengeClassifier
from Df.Harness.Research.Collector import Collector
from Df.Harness.Research.HtmlData import HtmlData
from Df.Harness.Research.JsonCollectionSummarizer import JsonCollectionSummarizer
from Df.Harness.Research.MarkdownExtractor import MarkdownExtractor
from Df.Harness.Research.SitemapExtractor import SitemapExtractor
from Df.Harness.lib.research import PROFILES, dfh_compact_extraction_for_disk, dfh_extractor_version, dfh_inside, dfh_json_data, dfh_research_max_bytes, dfh_research_seam
import hashlib
import io
import json
import mimetypes
import re
import xml.etree.ElementTree as ET
import zipfile
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Extractor:
	# @used-by :func:`agent_tools.research.extract_bytes()`
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__attach_grep()`
	# @used-by :meth:`Extractor.extract_file()`
	# @used-by :meth:`Extractor.extract_observation()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_extractor_docx_pdf_tracking_and_sitemap_images()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def __init__(self, body: bytes, content_type: str, profile: str, charset: str='utf-8', *, status=None) -> None:
		self.__body = body
		self.__content_type = content_type
		self.__profile = profile
		self.__charset = charset
		self.__status = status
	# @used-by :meth:`Extractor.extract()`
	def __extract_document_text(self, text: str, ct_low: str, is_md: bool) -> dict:
		out: dict = {'paragraphs': text.splitlines(), 'text': text, 'layout_checked': False}
		if is_md:
			md_info = MarkdownExtractor(text).extract()
			for k in ('title', 'headings', 'anchors', 'ambiguous_anchors', 'word_count', 'browser_check_required'):
				out[k] = md_info[k]
		elif 'application/json' == ct_low or text.lstrip().startswith(('{', '[')):
			try:
				parsed = json.loads(text)
				if isinstance(parsed, (dict, list)):
					out['summary'] = JsonCollectionSummarizer(parsed).summarize()
			except ValueError:
				pass
		return out
	# @used-by :meth:`Extractor.extract()`
	def __extract_docx(self) -> dict:
		from agent_tools.upwork_data import extract_docx_markdown
		with zipfile.ZipFile(io.BytesIO(self.__body)) as doc:
			item = doc.getinfo('word/document.xml')
			if dfh_research_max_bytes() < item.file_size:
				raise ValueError('Document XML exceeds 16 MiB')
			xml = ET.fromstring(doc.read(item))
			non_text = [name for name in doc.namelist() if name.startswith(('word/media/', 'word/charts/', 'word/embeddings/'))]
		ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
		paragraphs = [''.join(p.itertext()) for p in xml.findall('.//w:p', ns)]
		try:
			md = extract_docx_markdown(self.__body)
		except Exception:
			md = '\n'.join(paragraphs)
		return {'paragraphs': paragraphs, 'text': '\n'.join(paragraphs), 'markdown': md, 'layout_checked': False, 'non_text_parts': non_text}
	# @used-by :meth:`Extractor.extract()`
	def __extract_html(self, text: str) -> dict:
		parser = HtmlData()
		parser.feed(text)
		result = parser.result()
		result['tracking_summary'] = {'identifiers': sorted(set(re.findall('\\b(?:GTM-[A-Z0-9]+|G-[A-Z0-9]+|UA-\\d+-\\d+|AW-\\d+)\\b', text))), 'gsc_verification': bool(result['meta'].get('google-site-verification')), 'cms_technical_domains': sorted(set(re.findall('\\b[a-z0-9-]+\\.(?:squarespace\\.com|myshopify\\.com|webflow\\.io|wixsite\\.com|wpengine\\.com)\\b', text, flags=re.I)))}
		sitemap = SitemapExtractor(text).extract()
		if None is not sitemap:
			result['sitemap'] = sitemap
		if 'tracking' == self.__profile:
			configs, failures = self.__extract_tracking_configs(text)
			result['identifiers'] = sorted(set(re.findall('\\b(?:GTM-[A-Z0-9]+|G-[A-Z0-9]+|AW-\\d+)\\b', text)))
			result['embedded_json'] = configs
			result['embedded_json_unparsed'] = failures
			result['execution_checked'] = False
		result['browser_check_required'] = ChallengeClassifier(text, parsed=result, status=self.__status).is_challenge()
		return result
	# @used-by :meth:`Extractor.extract()`
	def __extract_pdf(self) -> dict:
		from agent_tools.upwork_data import extract_pdf_markdown
		md = extract_pdf_markdown(self.__body)
		paragraphs = [line for line in md.splitlines() if line.strip()]
		return {'paragraphs': paragraphs, 'text': md, 'markdown': md, 'layout_checked': True}
	# @used-by :meth:`Extractor.extract()`
	@staticmethod
	def __extract_shopify(text: str) -> dict:
		value = json.loads(text)
		if not isinstance(value, dict) or not any((k in value for k in ('product', 'products', 'variants', 'id'))):
			raise ValueError('Expected Shopify product/collection JSON')
		return {'data': value, 'summary': JsonCollectionSummarizer(value).summarize(), 'text': text, 'scope': 'public JSON response; not Merchant Center feed or admin configuration'}
	# @used-by :meth:`Extractor.__extract_html()`
	@staticmethod
	def __extract_tracking_configs(text: str) -> tuple[dict, list[dict]]:
		configs: dict = {}
		failures: list[dict] = []
		for key in ('webPixelsConfigList', 'wpmLoader', 'resource'):
			for match in re.finditer('[\\"\\\']?\\b' + key + '\\b[\\"\\\']?\\s*[:=]\\s*', text):
				try:
					value, _ = json.JSONDecoder().raw_decode(text[match.end():])
					if isinstance(value, str):
						try:
							value = json.loads(value)
						except ValueError:
							pass
					configs.setdefault(key, []).append(value)
				except ValueError:
					failures.append({'key': key, 'offset': match.end(), 'reason': 'Not literal JSON; inspect saved source without evaluating JavaScript'})
		return (configs, failures)
	# @used-by :meth:`Extractor.__write_cached()`
	@staticmethod
	def __read_cached(target: Path, version: str, sha_key: str, sha_value: str) -> dict | None:
		r: dict | None = None
		if target.is_file():
			try:
				cached = json.loads(target.read_text(encoding='utf-8'))
				if isinstance(cached, dict) and version == cached.get('extractor_version') and sha_value == cached.get(sha_key):
					r = cached
			except (OSError, ValueError):
				r = None
		return r
	# @used-by :meth:`Extractor.extract_file()`
	# @used-by :meth:`Extractor.extract_observation()`
	@classmethod
	def __write_cached(cls, target: Path, legacy_pattern: str, sha_key: str, sha_value: str, build_fn) -> dict:
		from agent_tools.storage import create_bytes, replace_bytes
		version = dfh_research_seam('extractor_version', dfh_extractor_version)()
		target.parent.mkdir(parents=True, exist_ok=True)
		r = cls.__read_cached(target, version, sha_key, sha_value)
		if None is r:
			r = build_fn(version)
			payload = dfh_json_data(r)
			if dfh_research_max_bytes() < len(payload):
				raise ValueError('Extracted JSON exceeds 16 MiB')
			replace_bytes(target, payload) if target.exists() else create_bytes(target, payload)
			for legacy in target.parent.glob(legacy_pattern):
				try:
					legacy.unlink()
				except OSError:
					pass
		return r
	# @used-by :func:`agent_tools.research.extract_bytes()`
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__attach_grep()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_extractor_docx_pdf_tracking_and_sitemap_images()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def extract(self) -> dict:
		if self.__profile not in PROFILES:
			raise ValueError(f'Unknown profile: {self.__profile}; choose {PROFILES}')
		ct_low = (self.__content_type or '').split(';', 1)[0].strip().lower()
		is_md = ct_low in ('text/markdown', 'text/x-markdown')
		if 'document' == self.__profile and self.__body.startswith(b'%PDF-'):
			r = self.__extract_pdf()
		elif 'document' == self.__profile and self.__body.startswith(b'PK'):
			r = self.__extract_docx()
		else:
			text = self.__body.decode(self.__charset, errors='replace')
			if 'shopify' == self.__profile:
				r = self.__extract_shopify(text)
			elif is_md and 'html' == self.__profile:
				r = MarkdownExtractor(text).extract()
			elif 'document' == self.__profile and ct_low not in ('text/html', 'application/xhtml+xml'):
				r = self.__extract_document_text(text, ct_low, is_md)
			else:
				r = self.__extract_html(text)
		return r
	# @used-by :func:`agent_tools.research.extract_file()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	@classmethod
	def extract_file(cls, root, file, profile: str='document') -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		file_p = dfh_inside(pp.root, file)
		body = file_p.read_bytes()
		if dfh_research_max_bytes() < len(body):
			raise ValueError('Source file exceeds 16 MiB')
		kind = mimetypes.guess_type(file_p.name)[0] or 'text/plain'
		source_sha = hashlib.sha256(body).hexdigest()
		target = pp.evidence_dir / 'Extracted' / source_sha / f'{profile}.json'
		cls.__write_cached(target, f'{profile}-*.json', 'source_sha256', source_sha, lambda version: {'profile': profile, 'source': file_p.relative_to(pp.root).as_posix(), 'source_sha256': source_sha, 'extractor_version': version, **dfh_compact_extraction_for_disk(cls(body, kind, profile).extract())})
		return {'extraction': target.relative_to(pp.kb_dir.resolve()).as_posix(), 'source_sha256': source_sha}
	# @used-by :func:`agent_tools.research.extract_observation()`
	# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.__build_item()`
	# @used-by :meth:`Df.Harness.Research.DomCapturer.DomCapturer.capture()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__try_extract()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	@classmethod
	def extract_observation(cls, root, reference: str, profile: str='html') -> dict:
		from agent_tools.path_registry import project_paths
		kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
		meta = Collector.load_observation(root, reference)
		folder = dfh_inside(kb_dir, urldefrag(reference)[0]).parent
		if meta.get('error') or ('http' == meta.get('kind', 'http') and (not 200 <= meta['status'] < 300)):
			raise ValueError('Observation is unavailable; preserve it and choose a different check method')
		target = folder / f'extracted-{profile}.json'
		data = cls.__write_cached(target, f'extracted-{profile}-*.json', 'body_sha256', meta['body_sha256'], lambda version: {'profile': profile, 'extractor_version': version, 'observation': reference, 'body_sha256': meta['body_sha256'], 'observed_at': meta['observed_at'], **dfh_compact_extraction_for_disk(cls((folder / 'response.bin').read_bytes(), meta['content_type'], profile, meta.get('charset') or 'utf-8', status=meta.get('status')).extract())})
		r: dict = {'extraction': target.relative_to(kb_dir).as_posix(), 'observation': reference, 'profile': profile, 'observed_at': meta['observed_at']}
		if 'browser_check_required' in data:
			r['browser_check_required'] = bool(data['browser_check_required'])
		if 'word_count' in data:
			r['word_count'] = data['word_count']
		return r