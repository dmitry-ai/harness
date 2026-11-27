# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.configuration import DISCOVERY_KINDS, configure_codex_project, is_linked_path, load_discovery_manifest, project_discovery_entries
from agent_tools.runtime import PRIMARY as PRIMARY_AGENTS_DIR, settings
from agent_tools.storage import create_bytes, replace_bytes
from copy import deepcopy
import hashlib
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ProjectConfigurator:
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__run_configure()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_docx_pdf_csv_and_config_coverage()`
	def __init__(self, project_root, primary_agents_dir=PRIMARY_AGENTS_DIR, job_url=None, domain_or_topic=None, *, platform=None, settings_fn=None) -> None:
		self.__root, self.__primary = (Path(project_root).resolve(), Path(primary_agents_dir).resolve())
		self.__job_url, self.__domain_or_topic, self.__platform = (job_url, domain_or_topic, platform)
		self.__settings_fn = settings if None is settings_fn else settings_fn
	# @used-by :meth:`ProjectConfigurator.__sync_context_config()`
	@staticmethod
	def __known_legacy_contexts(context_config: dict) -> tuple[dict, dict, dict]:
		v_no_drafts, v_no_excl = (deepcopy(context_config), deepcopy(context_config))
		next((s for s in v_no_drafts['sections'] if 'Proposals' == s['title'])).pop('drafts')
		next((s for s in v_no_excl['sections'] if 'Agent KB' == s['title'])).pop('exclude')
		v_neither = deepcopy(v_no_drafts)
		next((s for s in v_neither['sections'] if 'Agent KB' == s['title'])).pop('exclude')
		return (v_no_drafts, v_no_excl, v_neither)
	# @used-by :meth:`ProjectConfigurator.configure()`
	def __prepare_agents_dirs(self, pp) -> tuple[Path, Path]:
		agents = pp.agents_config_dir if pp.agents_config_dir.resolve() != self.__primary else (self.__root / '.agents')
		if is_linked_path(agents):
			raise ValueError('Configuration must be project-local; existing linked directory is preserved')
		agents.mkdir(parents=True, exist_ok=True)
		rules = agents / 'rules'
		if is_linked_path(rules):
			raise ValueError('Local rules directory is linked; preserved without conversion')
		rules.mkdir(exist_ok=True)
		return (agents, rules)
	# @used-by :meth:`ProjectConfigurator.configure()`
	def __sync_context_config(self, pp, agents: Path) -> None:
		from Df.Harness.Project.OnceFileWriter import OnceFileWriter
		context_path = pp.context_config if pp.agents_config_dir.resolve() != self.__primary else (agents / 'context.json')
		context_config = self.default_context_config(self.__root if (pp.has_overlay or 2 <= pp.fs_version) else None)
		if not context_path.exists():
			OnceFileWriter(context_path, OnceFileWriter.json_bytes(context_config).decode('utf-8')).write()
		elif json.loads(context_path.read_text(encoding='utf-8-sig')) in self.__known_legacy_contexts(context_config):
			previous = context_path.read_bytes()
			history = pp.data_dir / 'config-history' / (hashlib.sha256(previous).hexdigest() + '-context.json')
			history.parent.mkdir(parents=True, exist_ok=True)
			if not history.exists():
				create_bytes(history, previous)
			replace_bytes(context_path, OnceFileWriter.json_bytes(context_config))
	# @used-by :meth:`ProjectConfigurator.configure()`
	def __sync_manifests(self, agents: Path, relocated_codes: list[Path]) -> None:
		from Df.Harness.Project.OnceFileWriter import OnceFileWriter
		for kind in DISCOVERY_KINDS:
			expected = project_discovery_entries(self.__primary, kind, require_dir=True)
			relocated_shared = {(rc / kind).as_posix() for rc in relocated_codes}
			path = agents / f'{kind}.json'
			if not path.exists():
				OnceFileWriter(path, OnceFileWriter.json_bytes({'entries': expected}).decode('utf-8')).write()
			else:
				existing = load_discovery_manifest(path, missing_ok=False, entries_error=f'Native manifest needs an entries list; preserved: {path}')
				cur = [e for e in existing.get('entries', []) if not (isinstance(e, dict) and set(e) == {'path'} and isinstance(e.get('path'), str) and Path(e['path']).as_posix() in relocated_shared)]
				missing = [entry for entry in expected if entry not in cur]
				if cur != existing.get('entries', []) or missing:
					existing['entries'] = [*cur, *missing]
					replace_bytes(path, OnceFileWriter.json_bytes(existing))
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__run_configure()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_docx_pdf_csv_and_config_coverage()`
	def configure(self) -> Path:
		from agent_tools.journal import ensure_project_journal_upgraded
		from agent_tools.path_registry import project_paths, relocated_harness_code_dirs
		from Df.Harness.Project.OnceFileWriter import OnceFileWriter
		ensure_project_journal_upgraded(self.__root)
		pp = project_paths(self.__root, exact_root=True)
		agents, rules = self.__prepare_agents_dirs(pp)
		self.__sync_manifests(agents, relocated_harness_code_dirs(primary=self.__primary))
		self.__sync_context_config(pp, agents)
		OnceFileWriter(rules / '90-project.md', '\n'.join(['---', 'trigger: always_on', 'description: "Project parameters"', '---', '', '# Project', f"Job post: {self.__job_url or 'not specified'}.  ", f'Folder name: `{self.__domain_or_topic or self.__root.name}`; domain ownership is not proven by this.  ', 'Paths and boundaries: shared rules KB-1 and FILE-4.  ', ''])).write()
		cfg = self.__settings_fn(self.__primary / 'runtime.json') if self.__primary != Path(PRIMARY_AGENTS_DIR).resolve() and (self.__primary / 'runtime.json').is_file() else self.__settings_fn()
		if 'codex' in (cfg.get('platforms') or {}):
			configure_codex_project(self.__root, self.__primary, self.__job_url, self.__domain_or_topic)
		return agents
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :meth:`ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	@staticmethod
	def default_context_config(root: Path | None=None) -> dict:
		out_rel, overview_rel, manual_kb_glob, agent_kb_glob, ev_excl, journal_rel, proposals_rel, letters_my, letters_client = ('ꙮ/0/Context.md', '.md', 'KB/**/*.md', 'ꘖ/KB/**/*.md', '\ua616/KB/Evidence/**', 'ꙮ', 'result', 'Letters/my', 'Letters/client')
		if None is not root:
			from agent_tools.path_registry import project_paths
			from Df.Harness.lib.project import dfh_resolve_overview_md
			pp = project_paths(root, exact_root=True)
			if pp.context_output.is_relative_to(pp.root):
				out_rel = pp.context_output.relative_to(pp.root).as_posix()
			overview_rel = pp.rel_to_root(dfh_resolve_overview_md(pp))
			manual_kb_glob, agent_kb_glob, ev_excl = (f'{pp.rel_to_root(pp.manual_kb_dir)}/**/*.md', f'{pp.rel_to_root(pp.kb_dir)}/**/*.md', f'{pp.rel_to_root(pp.evidence_dir)}/**')
			journal_rel, proposals_rel = (pp.rel_to_root(pp.journal_dir), pp.rel_to_root(pp.path('proposals_dir', pp.root / 'result')))
			let_rel = pp.rel_to_root(pp.path('letters_dir', pp.root / 'Letters'))
			letters_my = let_rel if 2 <= pp.fs_version else f'{let_rel}/my'
			letters_client = pp.rel_to_root(pp.path('client_letters_dir', pp.root / '\u2c0f/\u227a/\U0001f582/\ua19c')) if 2 <= pp.fs_version else f'{let_rel}/client'
		return {'version': 1, 'output': out_rel, 'sections': [{'title': 'Project', 'files': [overview_rel]}, {'title': 'Manual KB', 'globs': [manual_kb_glob], 'optional': True}, {'title': 'Agent KB', 'globs': [agent_kb_glob], 'exclude': [ev_excl], 'optional': True}, {'title': 'Analysis', 'journals': [journal_rel], 'optional': True}, {'title': 'Proposals', 'globs': [f'{proposals_rel}/**/final/*.md', f'{proposals_rel}/**/final.md'], 'drafts': [proposals_rel], 'optional': True}, {'title': 'Correspondence', 'optional': True, 'letters': [{'root': letters_my, 'author': 'Consultant', 'languages': ['EN', 'RU']}, {'root': letters_client, 'author': 'Client', 'languages': ['EN', 'RU']}]}]}
