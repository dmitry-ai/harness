# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.links import markdown_link
from agent_tools.storage import create_bytes
from datetime import datetime, timezone
from Df.Harness.Project.ExtraSourceBuilder import ExtraSourceBuilder
from Df.Harness.Project.OnceFileWriter import OnceFileWriter
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from Df.Harness.Upwork.KbProjectMdFormatter import KbProjectMdFormatter
from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
import hashlib
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class KbPopulator:
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def __init__(self, project_root: Path, data: dict, *, extra_sources_fn=None) -> None:
		self.__project_root = project_root
		self.__data = data
		self.__extra_sources_fn = extra_sources_fn
	# @used-by :meth:`KbPopulator.render_evidence_md()`
	@staticmethod
	def __append_fenced_body(lines: list[str], body: str) -> None:
		clean = body.strip()
		if clean:
			bfence = MarkdownTableSanitizer.markdown_fence(clean, '`')
			lines.extend(['', bfence + 'markdown', clean, bfence])
		lines.append('')
	# @used-by :meth:`KbPopulator.populate()`
	def __write_kb_pages(self, pp, source: dict, extra_sources: list[dict], source_link: str, url: str) -> None:
		kb = pp.kb_dir
		manual = pp.manual_kb_dir / 'Project.md'
		proj_text = manual.read_bytes().decode('utf-8') if manual.is_file() else KbProjectMdFormatter({**self.__data, 'extra_sources': extra_sources}).render()
		OnceFileWriter(kb / 'Project.md', proj_text).write()
		when = self.__data.get('observed_at') or datetime.now(timezone.utc).isoformat(timespec='seconds')
		client = ['# Client', '', '## F-CLIENT-1', f'Upwork card snapshot captured {when}: [job post]({url}).', '', '## F-CLIENT-2', 'Account fields in this snapshot; these are platform details rather than independent verification:', '```json', json.dumps(self.__data.get('buyer') or {}, ensure_ascii=False, indent=2), '```', f'[Snapshot]({source_link}#/buyer).', '']
		if self.__data.get('client_names'):
			client.extend(['## F-CLIENT-3', 'Heuristic name matches in reviews; client identity is not established:', '```json', json.dumps(self.__data['client_names'], ensure_ascii=False, indent=2), '```', f'[Reviews]({source_link}#/client_names).', ''])
		OnceFileWriter(kb / 'Client.md', '\n'.join(client)).write()
		website = ['# Website', '', '## F-SITE-1', 'Website ownership is not established by automated extraction.  ', 'The folder name and discovered URLs do not confirm ownership.  ', '', '## F-SITE-2', 'Domains mentioned in source texts:', '```json', json.dumps(self.__data.get('candidate_domains') or [], ensure_ascii=False, indent=2), '```', f'[Snapshot]({source_link}#/candidate_domains).', '']
		OnceFileWriter(kb / 'Website.md', '\n'.join(website)).write()
		OnceFileWriter(kb / 'Projects.md', self.render_projects_md(self.__data, url, source_link, extra_sources, pp.root)).write()
		ev_md = self.render_evidence_md(source.get('asset_evidence') or [], extra_sources, pp.root)
		if None is not ev_md:
			OnceFileWriter(kb / 'Evidence.md', ev_md).write()
		OnceFileWriter(kb / 'Glossary.md', '# Glossary\n\nDefinitions are added when used; each term includes a link to its source.\n').write()
		OnceFileWriter(kb / '.md', '# Knowledge Base\n\n[Client](Client.md) · [Website](Website.md) · [Projects](Projects.md) · [Glossary](Glossary.md) · [Initial Description](Project.md).\n\nF — observation or quoted source words; H — hypothesis; M — solution method.  \nFor H/M: essence, for, against, score in %, assessment basis; links point to primary data.  \n').write()
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def populate(self) -> Path:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__project_root, exact_root=True)
		pp.evidence_dir.mkdir(parents=True, exist_ok=True)
		source = {k: v for k, v in self.__data.items() if k not in ('saved_attachments', 'cookies', 'extra_sources', 'media_descriptions', 'site_hypothesis')}
		if 'asset_evidence' in source and isinstance(source['asset_evidence'], list):
			source['asset_evidence'] = [{'file': x['file'], 'sha256': x['sha256']} for x in source['asset_evidence']]
		raw = OnceFileWriter.json_bytes(source)
		fingerprint = hashlib.sha256(raw).hexdigest()
		snapshot = pp.evidence_dir / f'{fingerprint}.json'
		if not snapshot.exists():
			create_bytes(snapshot, raw)
		source_link = snapshot.relative_to(pp.kb_dir).as_posix() if snapshot.is_relative_to(pp.kb_dir) else f'Evidence/{fingerprint}.json'
		extra_sources = self.__data.get('extra_sources')
		if None is extra_sources:
			extra_sources = ExtraSourceBuilder(pp.root, self.__data, self.__data.get('asset_evidence')).build() if None is self.__extra_sources_fn else self.__extra_sources_fn(pp.root, self.__data, self.__data.get('asset_evidence'))
		self.__write_kb_pages(pp, source, extra_sources, source_link, JobUrlParser.canonical_job_url(self.__data['job_id']))
		return snapshot
	# @used-by :func:`agent_tools.knowledge._render_evidence_md()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`KbPopulator.__write_kb_pages()`
	@classmethod
	def render_evidence_md(cls, asset_evidence: list[dict], extra_sources: list[dict], project_root: Path | None=None) -> str | None:
		if not asset_evidence and (not extra_sources):
			r = None
		else:
			ev_lines = ['# Attachments', '']
			extra_by_sha = {e.get('sha256'): e for e in extra_sources if e.get('sha256')}
			for x in asset_evidence:
				fname, sha = (Path(x['file']).name, x['sha256'])
				has_src = None is project_root or (project_root / 'source' / fname).is_file()
				link = f"[{fname}](<{x['file']}>) · [source/{fname}](<../../source/{fname}>) — SHA-256 `{sha}`." if has_src else f"[{fname}](<{x['file']}>) — SHA-256 `{sha}`."
				ev_lines.extend([f'## {fname}', link])
				cls.__append_fenced_body(ev_lines, (extra_by_sha.get(sha) or {}).get('body') or '')
			for e in extra_sources:
				if 'video' == e.get('kind') and e.get('url') and (not e.get('sha256')):
					ev_lines.extend([f"## {e['heading']}", markdown_link(None, e['url']) + '.'])
					cls.__append_fenced_body(ev_lines, e.get('body') or '')
			r = '\n'.join(ev_lines).rstrip() + '\n'
		return r
	# @used-by :func:`agent_tools.knowledge._render_projects_md()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`KbPopulator.__write_kb_pages()`
	@staticmethod
	def render_projects_md(data: dict, url: str, source_link: str, extra_sources: list[dict], project_root: Path | None=None) -> str:
		fence = MarkdownTableSanitizer.markdown_fence(data.get('description', ''), '`')
		projects = ['# Projects', '', '## F-PROJECT-1', f'[Current job post]({url}).', fence + 'markdown', data.get('title', ''), data.get('description', ''), fence, f'[Source text]({source_link}#/description).', '']
		for idx, extra in enumerate(extra_sources, start=1):
			ebody = (extra.get('body') or '').strip()
			efence = MarkdownTableSanitizer.markdown_fence(ebody, '`')
			projects.extend([f'## F-PROJECT-ATTACHMENT-{idx}', f"### {extra['heading']}"])
			has_src = bool(extra.get('source_file') and (None is project_root or (project_root / extra['source_file']).is_file()))
			if extra.get('file') and has_src:
				projects.append(f"[Primary file](<{extra['file']}>) · [File in source](<../../{extra['source_file']}>).")
			elif extra.get('file'):
				projects.append(f"[Primary file](<{extra['file']}>).")
			elif extra.get('url'):
				projects.append(markdown_link('Video source', extra['url']) + '.')
			if ebody:
				projects.extend([efence + 'markdown', ebody, efence])
			projects.append('')
		projects.extend(['## F-PROJECT-2', 'History actually returned by the page; connection of all jobs to a single website is not established.', '```json', json.dumps({k: data.get(k) for k in ('work_history', 'open_jobs', 'related_descriptions', 'coverage')}, ensure_ascii=False, indent=2), '```', f'[Snapshot]({source_link}).', ''])
		return '\n'.join(projects)
