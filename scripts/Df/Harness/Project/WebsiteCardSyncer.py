# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.links import markdown_link
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Project.CardSyncer import CardSyncer
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Project.OnceFileWriter import OnceFileWriter
from Df.Harness.lib.project import dfh_resolve_overview_md
import json
from pathlib import Path
from urllib.parse import urlsplit
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class WebsiteCardSyncer:
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def __init__(self, root, value: dict, *, selections=None, check: bool=False) -> None:
		self.__root, self.__value, self.__selections, self.__check = (root, value, selections, check)
	# @used-by :meth:`WebsiteCardSyncer.website_issues()`
	@staticmethod
	def __is_valid_url(url) -> bool:
		try:
			if not isinstance(url, str):
				raise ValueError('Website URL must be a string')
			parsed = urlsplit(url)
			r = bool(parsed.scheme in ('https', 'http') and parsed.hostname and (not parsed.username) and (not parsed.password) and (not any((c.isspace() for c in url))))
			_ = parsed.port
		except (TypeError, ValueError):
			r = False
		return r
	# @used-by :meth:`WebsiteCardSyncer.__sync_selected()`
	@staticmethod
	def __render_selected(selected: list[dict], identities: dict, analysis_rel: str) -> tuple[list[dict], list[str]] | None:
		stored, lines = ([], ['## Client and Project Website', ''])
		r: tuple[list[dict], list[str]] | None = (stored, lines)
		for site in selected:
			index, claim = identities[site['basis_id']]
			sha = df_sha256(OnceFileWriter.json_bytes(claim))
			if site.get('basis_sha256', sha) != sha:
				r = None
				break
			label = 'Client website' if 'client' == site['role'] else 'Target project website'
			url = site.get('url')
			address = markdown_link(None, url) if url else '**unresolved from available data**'
			prob = claim.get('probability_percent')
			assessment = f' Identification score: {prob}%.' if None is not prob else ''
			lines.append(f"- **{label}:** {address}.{assessment} [Basis: {claim['id']}](<{analysis_rel}#/identity/{index}>).")
			stored.append({'url': url, 'role': site['role'], 'basis_id': site['basis_id'], 'basis_sha256': sha})
		return r
	# @used-by :meth:`WebsiteCardSyncer.sync()`
	def __sync_selected(self, pp, overview_md: Path, selected: list[dict]) -> dict:
		issues = self.website_issues({**self.__value, 'websites': selected})
		if issues:
			raise ValueError(issues)
		identities = {claim['id']: (idx, claim) for idx, claim in enumerate(self.__value['identity'])}
		analysis_json = pp.kb_dir / 'Analysis.json'
		built = self.__render_selected(selected, identities, pp.rel_to_root(analysis_json))
		if None is built:
			r = {'status': 'conflict', 'target': str(overview_md), 'detail': 'Website identity evidence changed; reassess its explicit selection'}
		else:
			stored, lines = built
			r = CardSyncer(pp.root, overview_md, 'websites', '\n'.join(lines) + '\n', position='after-title', check=self.__check, source=analysis_json, attributes=stored).sync()
		return r
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def sync(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		overview_md = dfh_resolve_overview_md(pp)
		state = json.loads(pp.rendered_json.read_bytes()) if pp.rendered_json.exists() else {}
		cached = state.get(str(overview_md), {}).get('managed_blocks', {}).get('websites', {}).get('data')
		selected = self.__selections if None is not self.__selections else self.__value.get('websites', cached)
		return {'status': 'unassessed', 'target': str(overview_md)} if None is selected else self.__sync_selected(pp, overview_md, selected)
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
	# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	@classmethod
	def sync_initial(cls, root, snapshot, hypothesis=None) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		overview_md = dfh_resolve_overview_md(pp)
		if not hypothesis:
			source = Path(snapshot).resolve()
			content = f'## Client and Project Website\n\nURL is not yet established by initial extraction; identification requires analysis.  \n[Source job post](<{source.relative_to(pp.root).as_posix()}#/description>).  \n'
			r = CardSyncer(pp.root, overview_md, 'websites', content, source=source).sync()
		elif 'website_url' not in hypothesis:
			r = {'status': 'unassessed'}
		else:
			url = hypothesis['website_url']
			issues = cls.website_issues({'identity': [hypothesis], 'websites': [{'url': url, 'role': 'target', 'basis_id': hypothesis.get('id')}]})
			if issues:
				raise ValueError(issues)
			address = markdown_link(None, url) if url else '**unresolved**'
			manual_proj = pp.manual_kb_dir / 'Project.md'
			content = f"## Client and Project Website\n\n**Target project website:** {address}.  \nHypothesis score: {hypothesis['probability_percent']}%.  \n[Basis: {hypothesis['id']}](<{pp.rel_to_root(manual_proj)}#13-website>).  \n"
			r = CardSyncer(pp.root, overview_md, 'websites', content, source=manual_proj).sync()
		return r
	# @used-by :func:`agent_tools.knowledge.website_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	@classmethod
	def website_issues(cls, value: dict) -> list[dict]:
		if 'websites' not in value:
			r: list[dict] = []
		else:
			sites = value['websites']
			identities = {c['id'] for c in value.get('identity') or [] if isinstance(c, dict) and isinstance(c.get('id'), str)} if isinstance(value.get('identity'), list) else set()
			if not isinstance(sites, list) or not sites:
				r = [Diagnostics().problem('websites.list', '/websites', 'Record an evidenced website or an explicit unidentified selection')]
			else:
				r = []
				for idx, site in enumerate(sites):
					field = f'/websites/{idx}'
					if not isinstance(site, dict) or not isinstance(site.get('basis_id'), str) or site['basis_id'] not in identities or (site.get('role') not in ('client', 'target')):
						r.append(Diagnostics().problem('websites.basis', field, 'Use client/target and a current identity claim ID'))
					elif None is not site.get('url') and (not cls.__is_valid_url(site.get('url'))):
						r.append(Diagnostics().problem('websites.url', field + '/url', 'Use an HTTP(S) URL or null for an unidentified site'))
		return r
