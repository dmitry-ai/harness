# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.AttachmentExtractor import AttachmentExtractor
from Df.Harness.Upwork.ClientMetadataExtractor import ClientMetadataExtractor
from Df.Harness.Upwork.DocxExtractor import DocxExtractor as DocxMarkdownExtractor
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from Df.Harness.Upwork.KbProjectMdFormatter import KbProjectMdFormatter
from Df.Harness.Upwork.LoomVideoExtractor import LoomVideoExtractor
from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
from Df.Harness.Upwork.PdfExtractor import PdfExtractor as PdfMarkdownExtractor
from Df.Harness.Upwork.PdfLigatureRepairer import PdfLigatureRepairer
from Df.Harness.Upwork.VideoDetector import VideoDetector
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
IMAGE_EXTENSIONS = AttachmentExtractor.IMAGE_EXTENSIONS
LIGATURE_MAP = PdfLigatureRepairer.LIGATURE_MAP
TEXT_DOC_EXTENSIONS = AttachmentExtractor.TEXT_DOC_EXTENSIONS
VIDEO_EXTENSIONS = AttachmentExtractor.VIDEO_EXTENSIONS
# @used-by :mod:`agent_tools.upwork_data`
def _extract_xlsx_markdown(raw_bytes: bytes) -> str:
	return AttachmentExtractor.extract_xlsx(raw_bytes)
# @used-by :func:`extract_pdf_markdown()`
# @used-by :mod:`agent_tools.upwork_data`
def _find_poppler_tool(name: str) -> str | None:
	return PdfMarkdownExtractor.find_poppler_tool(name)
# @used-by :mod:`agent_tools.upwork_data`
def _join_wrapped_lines(prev: str, nxt: str) -> str:
	return PdfMarkdownExtractor.join_wrapped_lines(prev, nxt)
# @used-by :mod:`agent_tools.upwork_data`
def _parse_pdf_streams(pdf_bytes: bytes, *, text_ops_only: bool=False) -> tuple[dict[int, str], list[str], dict[int, str]]:
	return PdfLigatureRepairer.parse_streams(pdf_bytes, text_ops_only=text_ops_only)
# @used-by :mod:`agent_tools.upwork_data`
def canonical_job_url(url_or_id: str) -> str:
	return JobUrlParser.canonical_job_url(url_or_id)
# @used-by :mod:`agent_tools.upwork_data`
def canonical_video_url(url: str) -> str:
	return VideoDetector.canonical_video_url(url)
# @used-by :mod:`agent_tools.upwork_data`
def classify_attachment(filename_or_path, raw_bytes: bytes | None=None) -> str:
	return AttachmentExtractor.classify(filename_or_path, raw_bytes)
# @used-by :mod:`agent_tools.upwork_data`
def collect_unique_public_past_jobs(data: dict) -> list[dict]:
	return ClientMetadataExtractor.collect_unique_public_past_jobs(data)
# @used-by :mod:`agent_tools.upwork_data`
def detect_client_videos(description: str='', document_markdowns: list[str] | tuple[str, ...]=(), saved_attachments: list[dict] | tuple[dict, ...]=()) -> list[dict]:
	return VideoDetector.detect(description, document_markdowns, saved_attachments)
# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_pdf_extractor_xml_layout_and_raw_stream_ligature_fallback()`
# @used-by :mod:`agent_tools.upwork_data`
def discover_pdf_ligature_repairs(pdf_bytes: bytes) -> dict[str, str]:
	return PdfLigatureRepairer.discover_repairs(pdf_bytes)
# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_shared_table_bullet_rows_across_markdown_and_csv()`
# @used-by :mod:`agent_tools.upwork_data`
def extract_attachment_markdown(path_or_name, raw_bytes: bytes | None=None) -> str:
	return AttachmentExtractor.extract_markdown(path_or_name, raw_bytes, pdf_fn=extract_pdf_markdown, docx_fn=extract_docx_markdown)
# @used-by :meth:`test_onboarding.EvidenceTests.test_domain_mentions_include_vendors_and_keep_full_hostnames()`
# @used-by :mod:`agent_tools.upwork_data`
def extract_candidate_domains(texts: list[str]) -> list[str]:
	return ClientMetadataExtractor.extract_candidate_domains(texts)
# @used-by :mod:`agent_tools.upwork_data`
def extract_client_names(work_history: list[dict]) -> list[dict]:
	return ClientMetadataExtractor.extract_client_names(work_history)
# @used-by :func:`agent_tools.research.extract_bytes()`
# @used-by :func:`extract_attachment_markdown()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_docx_hyperlinks_are_readable_without_altering_their_visible_source_text()`
# @used-by :mod:`agent_tools.upwork_data`
def extract_docx_markdown(raw_bytes: bytes) -> str:
	return DocxMarkdownExtractor(raw_bytes).extract()
# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
# @used-by :mod:`agent_tools.upwork_data`
def extract_loom_video(url: str, timeout: float=15.0, opener=None) -> dict:
	return LoomVideoExtractor(url, timeout=timeout, opener=opener).extract()
# @used-by :func:`agent_tools.research.extract_bytes()`
# @used-by :func:`extract_attachment_markdown()`
# @used-by :mod:`agent_tools.upwork_data`
def extract_pdf_markdown(raw_bytes: bytes, pdf_path=None) -> str:
	return PdfMarkdownExtractor(raw_bytes, pdf_path=pdf_path, poppler_finder=_find_poppler_tool).extract()
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
# @used-by :mod:`agent_tools.upwork_data`
def extract_upwork_job_url_id(url: str, *, allow_query_or_fragment: bool=False) -> str | None:
	return JobUrlParser.extract_upwork_job_url_id(url, allow_query_or_fragment=allow_query_or_fragment)
# @used-by :mod:`agent_tools.upwork_data`
def format_duration_ru(seconds: int | float | None) -> str:
	return LoomVideoExtractor.format_duration_ru(seconds)
# @used-by :meth:`test_onboarding.EvidenceTests.test_embedded_fences_do_not_end_the_manual_description()`
# @used-by :mod:`agent_tools.upwork_data`
def format_kb_project_md(data: dict) -> str:
	return KbProjectMdFormatter(data).render()
# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_shared_table_bullet_rows_across_markdown_and_csv()`
# @used-by :mod:`agent_tools.upwork_data`
def format_table_bullet_rows(rows: list[list[str]], headers: list[str] | None=None) -> list[str]:
	return MarkdownTableSanitizer.format_table_bullet_rows(rows, headers)
# @used-by :mod:`agent_tools.upwork_data`
def markdown_fence(text: str, marker: str='~') -> str:
	return MarkdownTableSanitizer.markdown_fence(text, marker)
# @used-by :mod:`agent_tools.upwork_data`
def normalize_job_id(url_or_id: str) -> str:
	return JobUrlParser.normalize_job_id(url_or_id)
# @used-by :mod:`agent_tools.upwork_data`
def normalize_pdf_ligatures(text: str, repairs: dict[str, str] | None=None) -> str:
	return PdfLigatureRepairer.normalize_ligatures(text, repairs)
# @used-by :mod:`agent_tools.upwork_data`
def parse_webvtt_phrases(vtt_text: str) -> list[dict]:
	return LoomVideoExtractor.parse_webvtt_phrases(vtt_text)
# @used-by :mod:`agent_tools.upwork_data`
def resolve_nuxt_devalue(arr: list, idx: int=0, seen: set[int] | None=None):
	return JobUrlParser.resolve_nuxt_devalue(arr, idx, seen)
# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_shared_table_bullet_rows_across_markdown_and_csv()`
# @used-by :mod:`agent_tools.upwork_data`
def sanitize_kb_markdown(text: str) -> str:
	return MarkdownTableSanitizer.sanitize_kb_markdown(text)
# @used-by :mod:`agent_tools.upwork_data`
def split_sentences_one_per_line(text: str) -> list[str]:
	return MarkdownTableSanitizer.split_sentences_one_per_line(text)
# @used-by :mod:`agent_tools.upwork_data`
def structure_job_description(description: str, questions: list[str] | None=None) -> str:
	return MarkdownTableSanitizer.structure_job_description(description, questions)
__all__ = ['DocxMarkdownExtractor', 'IMAGE_EXTENSIONS', 'LIGATURE_MAP', 'PdfMarkdownExtractor', 'TEXT_DOC_EXTENSIONS', 'VIDEO_EXTENSIONS', '_extract_xlsx_markdown', '_find_poppler_tool', '_join_wrapped_lines', '_parse_pdf_streams', 'canonical_job_url', 'canonical_video_url', 'classify_attachment', 'collect_unique_public_past_jobs', 'detect_client_videos', 'discover_pdf_ligature_repairs', 'extract_attachment_markdown', 'extract_candidate_domains', 'extract_client_names', 'extract_docx_markdown', 'extract_loom_video', 'extract_pdf_markdown', 'extract_upwork_job_url_id', 'format_duration_ru', 'format_kb_project_md', 'format_table_bullet_rows', 'markdown_fence', 'normalize_job_id', 'normalize_pdf_ligatures', 'parse_webvtt_phrases', 'resolve_nuxt_devalue', 'sanitize_kb_markdown', 'split_sentences_one_per_line', 'structure_job_description']
