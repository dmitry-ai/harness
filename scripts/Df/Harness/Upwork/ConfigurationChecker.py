# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.configuration import DISCOVERY_KINDS, configure_codex_project, load_discovery_manifest, project_discovery_entries
from agent_tools.runtime import PRIMARY as PRIMARY_AGENTS_DIR, settings
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ConfigurationChecker:
	# @used-by :func:`agent_tools.upwork_project.check_configuration()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def __init__(self, project_root, primary_agents_dir=PRIMARY_AGENTS_DIR, *, settings_fn=None) -> None:
		self.__root, self.__primary = (Path(project_root).resolve(), Path(primary_agents_dir).resolve())
		self.__settings_fn = settings if None is settings_fn else settings_fn
	# @used-by :meth:`ConfigurationChecker.check()`
	def __check_kind(self, kind: str, agents: Path, relocated_codes: list[Path], result: dict) -> None:
		path = agents / f'{kind}.json'
		try:
			entries = load_discovery_manifest(path, entries_error='Native manifest needs an entries list').get('entries', [])
		except (ValueError, OSError) as exc:
			result['valid'] = False
			result['issues'].append({'file': str(path), 'message': str(exc)})
			entries = None
		if None is not entries:
			shared_equivs = {e['path'] for e in project_discovery_entries(self.__primary, kind) if 'rules' != e['path']} | {(rc / kind).as_posix() for rc in relocated_codes if (rc / kind).is_dir()}
			entry_paths = {Path(e['path']).as_posix() if Path(e['path']).is_absolute() else e['path'] for e in entries if isinstance(e, dict) and isinstance(e.get('path'), str)}
			if (not bool(entry_paths & shared_equivs)) or ('rules' == kind and 'rules' not in entry_paths):
				result['valid'] = False
				result['issues'].append({'file': str(path), 'message': 'Antigravity common/local discovery entry is missing; run configure'})
	# @used-by :func:`agent_tools.upwork_project.check_configuration()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def check(self) -> dict:
		from agent_tools.path_registry import project_paths, relocated_harness_code_dirs
		pp = project_paths(self.__root, exact_root=True)
		agents = pp.agents_config_dir if pp.agents_config_dir.resolve() != self.__primary else (self.__root / '.agents')
		cfg = self.__settings_fn(self.__primary / 'runtime.json') if self.__primary != Path(PRIMARY_AGENTS_DIR).resolve() and (self.__primary / 'runtime.json').is_file() else self.__settings_fn()
		r = configure_codex_project(self.__root, self.__primary, check=True) if 'codex' in (cfg.get('platforms') or {}) else {'valid': True, 'issues': [], 'written': []}
		relocated_codes = relocated_harness_code_dirs(primary=self.__primary)
		for kind in DISCOVERY_KINDS:
			self.__check_kind(kind, agents, relocated_codes, r)
		return r
