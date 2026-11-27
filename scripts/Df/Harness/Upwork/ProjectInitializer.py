# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.platforms.antigravity import register as register_antigravity_default
from agent_tools.runtime import PRIMARY as PRIMARY_AGENTS_DIR, platform_name, platform_settings, request_day, settings
from agent_tools.storage import locked, replace_bytes
from datetime import datetime, timezone
from Df.Harness.Project.AttachmentInventory import AttachmentInventory
from Df.Harness.Project.ExtraSourceBuilder import ExtraSourceBuilder
from Df.Harness.Project.InitLabelResolver import InitLabelResolver
from Df.Harness.Project.KbPopulator import KbPopulator
from Df.Harness.Project.LabelStateUpdater import LabelStateUpdater
from Df.Harness.Project.OnceFileWriter import OnceFileWriter
from Df.Harness.Project.Registry import Registry
from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from Df.Harness.Upwork.KbProjectMdFormatter import KbProjectMdFormatter
from Df.Harness.Upwork.ProjectConfigurator import ProjectConfigurator
from Df.Harness.Upwork.ProjectDirResolver import ProjectDirResolver
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ProjectInitializer:
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_init()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def __init__(self, url_or_id: str, domain_or_topic=None, date_str=None, daily_root=None, primary_agents_dir=PRIMARY_AGENTS_DIR, extracted_data=None, register_antigravity=None, antigravity_projects_dir=None, antigravity_folders_json=None, site_hypothesis=None, platform=None, register_native=None, all_platforms=None, launcher_root=None, conversation_id=None, topic=None, *, default_daily_root=None, platform_settings_fn=None, configure_fn=None, resolve_dir_fn=None, register_ag_fn=None, extra_sources_fn=None) -> None:
		self.__url_or_id, self.__domain_or_topic, self.__topic, self.__date_str = (url_or_id, domain_or_topic, topic, date_str)
		self.__daily_root, self.__primary_agents_dir, self.__extracted_data = (daily_root, primary_agents_dir, extracted_data)
		self.__register_antigravity, self.__register_native, self.__all_platforms = (register_antigravity, register_native, all_platforms)
		self.__ag_projects_dir, self.__ag_folders_json, self.__site_hypothesis = (antigravity_projects_dir, antigravity_folders_json, site_hypothesis)
		self.__platform, self.__launcher_root, self.__conversation_id = (platform, launcher_root, conversation_id)
		self.__default_daily_root, self.__extra_sources_fn = (default_daily_root, extra_sources_fn)
		self.__platform_settings_fn = platform_settings if None is platform_settings_fn else platform_settings_fn
		self.__configure_fn, self.__resolve_dir_fn = (configure_fn, resolve_dir_fn)
		self.__register_ag_fn = register_antigravity_default if None is register_ag_fn else register_ag_fn
	# @used-by :meth:`ProjectInitializer.initialize()`
	def __init_locked_state(self, root: Path, job_id: str, day, data: dict, label_kind: str, platform: str) -> tuple[dict, Path]:
		from agent_tools.journal import journal_pair_dirs
		from agent_tools.path_registry import project_paths
		state = self.__load_and_prepare_fs(root, job_id)
		self.__run_configure(root, job_id, platform)
		pp = project_paths(root, exact_root=True)
		for folder in (pp.manual_kb_dir, pp.kb_dir, *journal_pair_dirs(pp.journal_dir)):
			folder.mkdir(parents=True, exist_ok=True)
		assets = AttachmentInventory(root).sync(data.get('saved_attachments') or [])
		extra_sources = ExtraSourceBuilder(root, data, assets).build() if None is self.__extra_sources_fn else self.__extra_sources_fn(root, data, assets)
		if not state['initialized']:
			OnceFileWriter(pp.path('overview_md', root / '.md'), f"# {data['title']}\n\n{JobUrlParser.canonical_job_url(job_id)}\n").write()
			OnceFileWriter(pp.manual_kb_dir / 'Project.md', KbProjectMdFormatter({**data, 'extra_sources': extra_sources, **({'site_hypothesis': self.__site_hypothesis} if self.__site_hypothesis else {})}).render()).write()
		snapshot = KbPopulator(root, {**data, 'asset_evidence': [{'file': a['file'], 'sha256': a['sha256']} for a in assets], 'extra_sources': extra_sources}).populate()
		if not state['initialized'] and 'conflict' == WebsiteCardSyncer.sync_initial(root, snapshot, self.__site_hypothesis)['status']:
			raise ValueError('Initial website card conflicts with a manual block; preserve and reconcile it')
		LabelStateUpdater(state, root, snapshot, day, label_kind).update()
		replace_bytes(pp.project_json, OnceFileWriter.json_bytes(state))
		return (state, snapshot)
	# @used-by :meth:`ProjectInitializer.__init_locked_state()`
	@staticmethod
	def __load_and_prepare_fs(root: Path, job_id: str) -> dict:
		state_file = root / '\ua616/project.json'
		existing = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else None
		state = existing if None is not existing else {'job_id': job_id, 'initialized': False, 'created_by': 'upwork-init', 'created_at': datetime.now(timezone.utc).isoformat()}
		if state['job_id'] != job_id:
			raise ValueError('Project identity mismatch')
		is_v1 = (isinstance(existing, dict) and 1 == existing.get('fs_version')) or ((root / 'KB/Project.md').is_file() and not (root / '\U0001f56e').is_dir() and not (root / '\u2c0f').is_dir())
		if not is_v1:
			for v2_dir in (root / '\U0001f56e', root / '\u2c0f/\u227b', root / '\u2c0f/\u227a'):
				v2_dir.mkdir(parents=True, exist_ok=True)
			state['fs_version'] = 2
			state.setdefault('journal_version', 3)
		else:
			state.setdefault('fs_version', 1)
		replace_bytes(state_file, OnceFileWriter.json_bytes(state))
		return state
	# @used-by :meth:`ProjectInitializer.initialize()`
	def __maybe_handoff(self, root: Path, job_id: str) -> list[dict]:
		r: list[dict] = []
		if None is not self.__launcher_root:
			try:
				from agent_tools.completion import handoff_launcher_turn
				r = handoff_launcher_turn(self.__launcher_root, root, job_id, conversation_id=self.__conversation_id)
			except (OSError, ValueError):
				r = []
		return r
	# @used-by :meth:`ProjectInitializer.initialize()`
	def __maybe_register(self, root: Path, initial_day: str, platform: str, daily: Path, default_daily: Path) -> dict | None:
		should = self.__register_native if None is not self.__register_native else self.__register_antigravity
		if None is should:
			caps = self.__platform_settings_fn(platform).get('capabilities')
			should = daily == default_daily and (None is caps or 'upwork_registration' in caps)
		r = None
		if should:
			both = self.__all_platforms if None is not self.__all_platforms else daily == default_daily
			registrars = {'antigravity': lambda project, label, day: self.__register_ag_fn(project, label, day, projects_dir=self.__ag_projects_dir, folders_json_path=self.__ag_folders_json)}
			r = Registry(root, root.name.split(' - ', 1)[1], initial_day).register(platform=platform, targets=None if both else [platform], registrars=registrars, single=False)
		return r
	# @used-by :meth:`ProjectInitializer.__init_locked_state()`
	def __run_configure(self, root: Path, job_id: str, platform: str) -> None:
		label_part = root.name.split(' - ', 1)[-1]
		if None is self.__configure_fn:
			ProjectConfigurator(root, self.__primary_agents_dir, JobUrlParser.canonical_job_url(job_id), label_part, platform=platform).configure()
		else:
			self.__configure_fn(root, self.__primary_agents_dir, JobUrlParser.canonical_job_url(job_id), label_part, platform=platform)
	# @used-by :meth:`ProjectInitializer.initialize()`
	def __validate_capture(self, job_id: str) -> dict:
		if None is self.__extracted_data:
			raise ValueError('Capture once with inspect; initialize from that capture')
		data = self.__extracted_data
		if not isinstance(data, dict):
			raise ValueError('Capture must be a JSON object')
		if data.get('job_id') != job_id or not data.get('title') or (not data.get('description')):
			raise ValueError('A capture with matching job ID, title and full description is required')
		return data
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_init()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def initialize(self) -> dict:
		platform = platform_name(self.__platform)
		job_id, day = (JobUrlParser.normalize_job_id(self.__url_or_id), request_day(self.__date_str))
		data = self.__validate_capture(job_id)
		label, label_kind, label_warning = InitLabelResolver(domain=self.__domain_or_topic, topic=self.__topic, fallback_title=data['title']).resolve()
		default_daily = Path(self.__default_daily_root).resolve() if None is not self.__default_daily_root else (Path(settings()['workspace_root']).resolve() / settings()['daily_root'])
		daily = Path(self.__daily_root).resolve() if None is not self.__daily_root else default_daily
		root = ProjectDirResolver(job_id, label, day.isoformat(), daily, default_daily_root=default_daily).resolve_or_create() if None is self.__resolve_dir_fn else self.__resolve_dir_fn(job_id, label, day.isoformat(), daily)
		(root / '\ua616/data').mkdir(parents=True, exist_ok=True)
		with locked(root / '\ua616/data/init.lock'):
			state, snapshot = self.__init_locked_state(root, job_id, day, data, label_kind, platform)
		info = self.__maybe_register(root, state['request_date'], platform, daily, default_daily)
		handoffs = self.__maybe_handoff(root, job_id)
		r = {'project_dir': str(root), 'job_id': job_id, 'domain_or_topic': label, 'context_path': None, 'snapshot': str(snapshot), 'registration': info, 'platform': platform, 'registrations': info['registrations'] if info else {}, 'antigravity': info['registrations'].get('antigravity') if info else None, 'analysis_status': 'pending; initialization is not a completed analysis', 'label_kind': state['label_kind']}
		if None is not label_warning:
			r['label_warning'] = label_warning
		if handoffs:
			r['launcher_handoff'] = handoffs
		return r
