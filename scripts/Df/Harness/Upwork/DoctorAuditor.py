# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.runtime import PRIMARY as PRIMARY_AGENTS_DIR, all_instances, platform_name, platform_settings, role_settings, settings
from copy import deepcopy
from Df.Harness.Upwork.GlobalCustomizationManager import GlobalCustomizationManager
import hashlib
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class DoctorAuditor:
	# @used-by :func:`agent_tools.upwork_project.doctor()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_global_custom_and_doctor()`
	def __init__(self, primary=None, *, git_ignore_path=None, settings_fn=None, platform_settings_fn=None, check_global_fn=None) -> None:
		self.__primary, self.__git_ignore_path = (primary, git_ignore_path)
		self.__settings_fn = settings if None is settings_fn else settings_fn
		self.__platform_settings_fn = platform_settings if None is platform_settings_fn else platform_settings_fn
		self.__check_global_fn = check_global_fn
	# @used-by :meth:`DoctorAuditor.audit()`
	@staticmethod
	def __paths_map(primary: Path, files: list[Path]) -> dict:
		return {'rules': [str(p.resolve()) for p in files], 'reference': str((primary / 'scripts/README-agent-tools.md').resolve()), 'analysis_contract': str((primary / 'scripts/agent_tools/analysis.py').resolve()), 'workflow_reference': str((primary / 'skills/upwork-init/references/workflow.md').resolve()), 'examples': str((primary / 'skills/upwork-init/references').resolve()), 'example_files': [str(p.resolve()) for p in sorted((primary / 'skills/upwork-init/references').glob('*.json'))]}
	# @used-by :meth:`DoctorAuditor.audit()`
	def __resolve_platform_cfg(self, primary: Path) -> tuple[dict, str, dict]:
		cfg_file = primary / 'runtime.json'
		doc_cfg = self.__settings_fn(cfg_file) if cfg_file.is_file() else ({} if primary.resolve() != PRIMARY_AGENTS_DIR.resolve() else self.__settings_fn())
		active = platform_name(config=doc_cfg) if doc_cfg else platform_name()
		plat_cfg = deepcopy(doc_cfg['platforms'][active]) if doc_cfg else self.__platform_settings_fn(active)
		return (doc_cfg, active, plat_cfg)
	# @used-by :meth:`DoctorAuditor.audit()`
	@staticmethod
	def __tool_version(primary: Path) -> str:
		version_files = sorted((p for p in primary.rglob('*') if p.is_file() and (p.suffix in ('.py', '.md', '.json') or p.name in ('.py', '.md')) and ('__pycache__' not in p.parts)))
		return hashlib.sha256(b''.join((p.relative_to(primary).as_posix().encode() + hashlib.sha256(p.read_bytes()).digest() for p in version_files))).hexdigest()
	# @used-by :func:`agent_tools.upwork_project.doctor()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_global_custom_and_doctor()`
	def audit(self) -> dict:
		from agent_tools.operations import COMMANDS
		from agent_tools.path_registry import load_registry, paths_report
		from agent_tools.rules_manifest import resolve_rules_primary, validate_shared_rules_for_doctor
		primary = resolve_rules_primary(self.__primary, PRIMARY_AGENTS_DIR)
		files, sizes, rule_meta = validate_shared_rules_for_doctor(primary)
		doc_cfg, active, plat_cfg = self.__resolve_platform_cfg(primary)
		roles_cfg, env_inv = (plat_cfg.get('roles') or {}, all_instances(config=doc_cfg or None, check_exists=True))
		glob = GlobalCustomizationManager.check_global(primary=primary, git_ignore_path=self.__git_ignore_path) if None is self.__check_global_fn else self.__check_global_fn(primary=primary, git_ignore_path=self.__git_ignore_path)
		p_rep = paths_report(check=True, registry=load_registry((primary / 'paths.json') if (primary / 'paths.json').is_file() else None, primary=primary))
		r = {'tool_version': self.__tool_version(primary), 'rules': len(files), 'rule_bytes': sum(sizes.values()), 'per_file_bytes': sizes, **rule_meta, 'skills': sorted((p.parent.name for p in (primary / 'skills').glob('*/SKILL.md'))), 'resolved_role_defaults': {role: role_settings(active, role) for role in ('AA', 'AF') if role in roles_cfg}, 'subagent_policy': plat_cfg.get('subagents', {'selection': 'configured_roles'}), 'surface': plat_cfg.get('surface'), 'delegation': plat_cfg.get('delegation'), 'actual_session_models_verified': False, 'environments': env_inv['environments'], 'enabled_environments': env_inv['enabled_environments'], 'instances': env_inv['instances'], 'available_handoff_targets': env_inv['available_handoff_targets'], 'paths': self.__paths_map(primary, files), 'workflow_commands': list(COMMANDS), 'internal_knowledge': 'ꘖ/KB', 'context_purpose': 'complete external export for Gemini DeepThink or another external agent', 'global_customizations': glob, 'git_ignore': glob.get('git_ignore'), 'paths_registry': {'file': p_rep['registry_file'], 'valid': p_rep['valid'], 'overlays': len(p_rep['discovered_overlays']), 'issues': p_rep['issues']}, 'valid': glob['valid'] and p_rep['valid']}
		return r
