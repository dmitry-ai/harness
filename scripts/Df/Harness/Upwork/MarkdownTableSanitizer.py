# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
_BULLET_RE = re.compile('^(?:[•*]|\\-(?=[A-Za-z\\u0410-\\u042f\\u0401\\u0430-\\u044f\\u04510-9"\\\'`])|\\-\\s+)\\s*(.+)$')
_HEADING_STOPWORDS = ('we', "we're", 'i', 'the', 'this', 'there', 'please', 'see', 'as', 'and', 'so', 'if', 'in', 'for', 'most', 'all')
_SENTENCE_SPLIT_RE = re.compile('(?<!\\be\\.g)(?<!\\bi\\.e)(?<!\\bvs)(?<!\\betc)(?<!\\bMr)(?<!\\bDr)(?<!\\bSt)(?<!\\bNB)(?<=[.!?])\\s+(?=[A-Z\\u0410-\\u042f\\u0401"«(])')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class MarkdownTableSanitizer:
	# @used-by :meth:`MarkdownTableSanitizer.structure_job_description()`
	@staticmethod
	def __append_questions(out_lines: list[str], questions: list[str] | None) -> None:
		clean_q = [q.strip() for q in questions or () if q and q.strip()]
		if clean_q:
			if out_lines:
				out_lines.append('')
			out_lines.append('# Questions')
			for q in clean_q:
				out_lines.append(f'- {q}')
	# @used-by :meth:`MarkdownTableSanitizer.__process_line()`
	@staticmethod
	def __is_heading(idx: int, line: str, lines: list[str]) -> bool:
		prev_empty = 0 == idx or not lines[idx - 1]
		words = line.split()
		ok = prev_empty and 1 <= len(words) <= 8 and (70 >= len(line)) and line[0].isupper() and (not line.startswith(('http://', 'https://', '#', '-'))) and (not re.match('^\\d+[.)]\\s', line))
		ends = line.endswith(':') or (not line.endswith(('.', '!', '?', ';', ',')) and idx + 1 < len(lines))
		r = bool(ok and ends)
		if r and words[0].lower() in _HEADING_STOPWORDS and (not line.endswith(':')):
			r = False
		return r
	# @used-by :meth:`MarkdownTableSanitizer.structure_job_description()`
	@classmethod
	def __process_line(cls, idx: int, line: str, lines: list[str], out_lines: list[str]) -> None:
		bullet = _BULLET_RE.match(line)
		if not line:
			if out_lines and '' != out_lines[-1]:
				out_lines.append('')
		elif bullet:
			sentences = cls.split_sentences_one_per_line(bullet.group(1).strip())
			if sentences:
				out_lines.append(f'- {sentences[0]}')
				out_lines.extend(sentences[1:])
		elif cls.__is_heading(idx, line, lines):
			if out_lines and '' != out_lines[-1]:
				out_lines.append('')
			out_lines.append(f"# {line[:-1].strip() if line.endswith(':') else line}")
		else:
			out_lines.extend(cls.split_sentences_one_per_line(line))
	# @used-by :func:`agent_tools.upwork_data.format_table_bullet_rows()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_csv()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__parse_table()`
	# @used-by :meth:`MarkdownTableSanitizer.sanitize_kb_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def format_table_bullet_rows(rows: list[list[str]], headers: list[str] | None=None) -> list[str]:
		hdrs = [h.strip() for h in headers or ()]
		r: list[str] = []
		for row in rows:
			pairs = [f'{hdrs[idx]}: {val.strip()}' if idx < len(hdrs) and hdrs[idx] else val.strip() for idx, val in enumerate(row) if val and val.strip()]
			if pairs:
				r.append('- ' + '; '.join(pairs))
		return r
	# @used-by :func:`agent_tools.upwork_data.markdown_fence()`
	# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.__append_current_project()`
	# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.render()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def markdown_fence(text: str, marker: str='~') -> str:
		return marker * max(3, 1 + max((len(m[0]) for m in re.finditer(re.escape(marker) + '+', text)), default=0))
	# @used-by :func:`agent_tools.upwork_data.sanitize_kb_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_json()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_odt()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_text_like()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.extract_xlsx()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__render_items()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_pdftotext()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_raw_streams()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__render_blocks()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def sanitize_kb_markdown(cls, text: str) -> str:
		lines = (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
		out: list[str] = []
		i = 0
		while i < len(lines):
			line = lines[i]
			is_sep = i + 1 < len(lines) and (bool(re.match('^\\s*\\|?\\s*:?-{3,}(?:\\s*\\|\\s*:?-{3,})+\\s*\\|?\\s*$', lines[i + 1])) or bool(re.match('^\\s*\\|(?:\\s*:?-{3,}\\s*\\|)+\\s*$', lines[i + 1])))
			if not (is_sep and re.match('^\\s*\\|.*\\|\\s*$', line)):
				out.append(re.sub('(?i)<a\\s+[^>]*(?:name|id)\\s*=\\s*["\\\'][^"\\\']*["\\\'][^>]*>(.*?)</a>', '\\1', line))
				i += 1
			else:
				headers = [c.strip() for c in line.strip().strip('|').split('|')]
				i += 2
				table_rows: list[list[str]] = []
				while i < len(lines) and re.match('^\\s*\\|.*\\|\\s*$', lines[i]):
					table_rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
					i += 1
				out.extend(cls.format_table_bullet_rows(table_rows, headers))
		return '\n'.join(out).strip()
	# @used-by :func:`agent_tools.upwork_data.split_sentences_one_per_line()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_odt()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__render_items()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__render_blocks()`
	# @used-by :meth:`MarkdownTableSanitizer.__process_line()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def split_sentences_one_per_line(text: str) -> list[str]:
		parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text.strip()) if p.strip()]
		return parts or ([text.strip()] if text.strip() else [])
	# @used-by :func:`agent_tools.upwork_data.structure_job_description()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_text_like()`
	# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.render()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_pdftotext()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_raw_streams()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def structure_job_description(cls, description: str, questions: list[str] | None=None) -> str:
		raw = (description or '').replace('\r\n', '\n').replace('\r', '\n').strip()
		lines = [line.strip() for line in raw.split('\n')]
		out_lines: list[str] = []
		for idx, line in enumerate(lines):
			cls.__process_line(idx, line, lines, out_lines)
		while out_lines and '' == out_lines[-1]:
			out_lines.pop()
		cls.__append_questions(out_lines, questions)
		return '\n'.join(out_lines)
