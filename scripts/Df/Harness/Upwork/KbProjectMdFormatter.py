# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.links import markdown_link
from Df.Harness.Analysis.Validator import SECTIONS, Validator
from Df.Harness.Upwork.ClientMetadataExtractor import ClientMetadataExtractor
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class KbProjectMdFormatter:
	# @used-by :func:`agent_tools.upwork_data.format_kb_project_md()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	def __init__(self, data: dict) -> None:
		self.__data = data
	# @used-by :meth:`KbProjectMdFormatter.render()`
	def __append_current_project(self, lines: list[str], job_url: str, job_title: str, structured_desc: str) -> None:
		extra_sources = self.__data.get('extra_sources') or []
		fence = MarkdownTableSanitizer.markdown_fence(structured_desc)
		if not extra_sources:
			lines.extend([job_url, fence + 'markdown', job_title, '#', structured_desc, fence])
		else:
			lines.extend(['## 2.1. Upwork Description', job_url, fence + 'markdown', job_title, '#', structured_desc, fence])
			for s_idx, src in enumerate(extra_sources, start=2):
				src_heading = (src.get('heading') or f"Description in `{src.get('name', s_idx)}`").strip()
				src_body = (src.get('body') or '').strip()
				src_fence = MarkdownTableSanitizer.markdown_fence(src_body)
				lines.extend(['', f'## 2.{s_idx}. {src_heading}', src_fence + 'markdown', src_body, src_fence])
	# @used-by :meth:`KbProjectMdFormatter.render()`
	def __site_text(self) -> str:
		r = 'unresolved; domain mentions and folder names do not prove ownership'
		if self.__data.get('site_hypothesis'):
			h = self.__data['site_hypothesis']
			analysis = {key: [h] if 'identity' == key else [] for key in SECTIONS}
			analysis['notes'] = {key: 'Separate analysis stage.' for key in SECTIONS if 'identity' != key}
			Validator(analysis).validate()
			for_s = '; '.join((f"{a['argument']} «{a['quote']}» " + markdown_link('Source', a['source']) for a in h['for']))
			ag_s = '; '.join((f"{a['argument']} «{a['quote']}» " + markdown_link('Source', a['source']) for a in h['against']))
			r = '  \n'.join([h['essence'], 'For: ' + for_s, 'Against: ' + ag_s, f"Expert plausibility: {h['probability_percent']}%.", h['assessment_basis']])
		return r
	# @used-by :func:`agent_tools.upwork_data.format_kb_project_md()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	def render(self) -> str:
		loc = (self.__data.get('buyer') or {}).get('location') or {}
		name_str = 'unresolved; names from reviews require verification' if self.__data.get('client_names') else 'unknown'
		country, city = ((loc.get('country') or 'unknown').strip(), (loc.get('city') or '').strip())
		loc_lines = ['  \n'.join([country] + ([city] if city else []))]
		job_url = JobUrlParser.canonical_job_url(self.__data.get('job_id') or self.__data.get('url') or '')
		job_title = (self.__data.get('title') or '').strip()
		structured_desc = MarkdownTableSanitizer.structure_job_description(self.__data.get('description') or '', self.__data.get('questions'))
		lines = ['# 1. Client', '## 1.1 Name', name_str, '', '## 1.2 Location', *loc_lines, '', '## 1.3 Website', self.__site_text(), '', '# 2. Current Client Project']
		self.__append_current_project(lines, job_url, job_title, structured_desc)
		lines.extend(['', '# 3. Past Client Projects', '## 3.0', 'Projects were posted by the same account; their connection to the current website is not established.', '##', 'Use these projects to understand context.  ', 'Working on these projects is outside the scope of the current task.  '])
		for idx, pjob in enumerate(ClientMetadataExtractor.collect_unique_public_past_jobs(self.__data), start=1):
			p_structured = MarkdownTableSanitizer.structure_job_description(pjob['description'])
			pfence = MarkdownTableSanitizer.markdown_fence(p_structured)
			lines.extend(['', f'## 3.{idx}', pjob['url'], pfence + 'markdown', pjob['title'], '#', p_structured, pfence])
		return '\n'.join(lines) + '\n'
