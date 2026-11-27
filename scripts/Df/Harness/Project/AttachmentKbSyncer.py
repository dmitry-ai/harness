# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.storage import replace_bytes
from Df.Harness.Project.AttachmentInventory import AttachmentInventory
from Df.Harness.Project.ExtraSourceBuilder import ExtraSourceBuilder
from Df.Harness.Project.KbPopulator import KbPopulator
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from Df.Harness.Upwork.KbProjectMdFormatter import KbProjectMdFormatter
import json
from pathlib import Path
import re
_SEC2_RE = '(?m)^# 2\\. (?:Current Client Project|\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442 \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)\\n(.*?)(?=^# 3\\. (?:Past Client Projects|\\u041f\\u0440\\u043e\\u0448\\u043b\\u044b\\u0435 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442\\u044b \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)\\n|\\Z)'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AttachmentKbSyncer:
	# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def __init__(self, project_root: Path, media_descriptions: dict | None=None, *, fetch_videos: bool=True, extra_sources_fn=None) -> None:
		self.__project_root = project_root
		self.__media_descriptions = media_descriptions
		self.__fetch_videos = fetch_videos
		self.__extra_sources_fn = extra_sources_fn
	# @used-by :func:`agent_tools.knowledge._replace_section2_in_project_md()`
	# @used-by :meth:`AttachmentKbSyncer.sync()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	@staticmethod
	def replace_section2(existing_md: str, data: dict, extra_sources: list[dict]) -> str:
		fresh_md = KbProjectMdFormatter({**data, 'extra_sources': extra_sources}).render()
		m_fresh = re.search(_SEC2_RE, fresh_md, re.S)
		if not m_fresh:
			r = fresh_md
		else:
			m_exist = re.search(_SEC2_RE, existing_md, re.S)
			r = existing_md[:m_exist.start()] + '# 2. Current Client Project\n' + m_fresh.group(1) + existing_md[m_exist.end():] if m_exist else fresh_md
		return r
	# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def sync(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__project_root, exact_root=True)
		if not pp.project_json.is_file():
			raise ValueError(f'Missing project.json in {pp.root}')
		pj = json.loads(pp.project_json.read_text(encoding='utf-8'))
		snapshot_path = pp.root / pj['snapshot']
		snapshot_data = json.loads(snapshot_path.read_text(encoding='utf-8'))
		assets = AttachmentInventory(pp.root).sync(asset_evidence=snapshot_data.get('asset_evidence'))
		merged = {**snapshot_data, 'asset_evidence': assets, **({'media_descriptions': self.__media_descriptions} if self.__media_descriptions else {})}
		extra_sources = ExtraSourceBuilder(pp.root, merged, assets, fetch_videos=self.__fetch_videos).build() if None is self.__extra_sources_fn else self.__extra_sources_fn(pp.root, merged, assets, fetch_videos=self.__fetch_videos)
		manual_kb = pp.manual_kb_dir / 'Project.md'
		updated_md = self.replace_section2(manual_kb.read_text(encoding='utf-8'), merged, extra_sources) if manual_kb.is_file() else KbProjectMdFormatter({**merged, 'extra_sources': extra_sources}).render()
		replace_bytes(manual_kb, updated_md.encode('utf-8'))
		replace_bytes(pp.kb_dir / 'Project.md', updated_md.encode('utf-8'))
		replace_bytes(pp.kb_dir / 'Projects.md', KbPopulator.render_projects_md(merged, JobUrlParser.canonical_job_url(pj['job_id']), snapshot_path.relative_to(pp.kb_dir).as_posix(), extra_sources, pp.root).encode('utf-8'))
		ev_md = KbPopulator.render_evidence_md([{'file': a['file'], 'sha256': a['sha256']} for a in assets], extra_sources, pp.root)
		if None is not ev_md:
			replace_bytes(pp.kb_dir / 'Evidence.md', ev_md.encode('utf-8'))
		return {'project_root': str(pp.root), 'source_files': [a['source_file'] for a in assets], 'extra_sources': [{'kind': e['kind'], 'name': e['name'], 'heading': e['heading'], 'has_body': bool((e.get('body') or '').strip())} for e in extra_sources]}
