# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Config.ProjectionPublisher import ProjectionPublisher
from Df.Harness.lib.config_blocks import dfh_digest, dfh_extract_managed_block
from Df.Harness.lib.config_codex import dfh_loader, dfh_native_config, dfh_primary_settings, dfh_project_rule_paths
from Df.Harness.lib.path_resolve import dfh_project_paths, dfh_var_value
import tomllib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class NativeBuilder:
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	def __init__(self, root: str | Path | None=None, primary: str | Path | None=None, *, check: bool=False, settings_fn: Any=None) -> None:
		self.__root_arg = root
		self.__primary = primary
		self.__check = check
		self.__settings_fn = settings_fn
	# @used-by :meth:`NativeBuilder.run()`
	def __build_codex_disabled(self, root: Path, primary: Path, source_hash: str) -> dict:
		from Df.Harness.lib.native_ag_plan import dfh_legacy_project_projection_paths, dfh_shared_native_outputs
		from Df.Harness.lib.native_codex_plan import dfh_build_shared_native
		try:
			publication = {'disown': list(dfh_shared_native_outputs(primary, settings_fn=self.__settings_fn)), 'retire': [root / 'CODEX.md', *dfh_legacy_project_projection_paths(root, primary, settings_fn=self.__settings_fn)]}
			shared = dfh_build_shared_native(primary, check=self.__check, settings_fn=self.__settings_fn)
			if not shared['valid'] and (not self.__check):
				r: dict[str, Any] = {'issues': [], 'valid': False, 'written': []}
			else:
				publication['disown'].extend(shared['removed'])
				r = ProjectionPublisher(root, {}, check=self.__check, **publication).run()
			r.update(canonical_runtime=str(primary / 'runtime.json'), issues=[*shared['issues'], *r['issues']], policy_bytes=0, removed=[*shared['removed'], *r.get('removed', [])], shared=shared, source_sha256=source_hash, valid=r['valid'] and shared['valid'], written=[*shared['written'], *r['written']])
		except ValueError as exc:
			r = {'issues': [{'file': str(root), 'message': str(exc)}], 'valid': False, 'written': []}
		return r
	# @used-by :meth:`NativeBuilder.run()`
	def __build_codex_enabled(self, root: Path, primary: Path, source_hash: str) -> dict:
		from Df.Harness.lib.native_ag_plan import dfh_legacy_project_projection_paths, dfh_shared_native_outputs
		from Df.Harness.lib.native_codex_plan import dfh_build_shared_native
		instructions, outputs = self.__prepare_codex_outputs(root, primary)
		try:
			path, text, merge = dfh_native_config(root, instructions)
			outputs[path] = text
			publication = {'disown': list(dfh_shared_native_outputs(primary, settings_fn=self.__settings_fn)), 'merge': merge, 'retire': [root / 'CODEX.md', *dfh_legacy_project_projection_paths(root, primary, settings_fn=self.__settings_fn)]}
			preflight = ProjectionPublisher(root, outputs, preflight=True, **publication).run() if not self.__check else None
			if None is not preflight and (not preflight['valid']):
				r = preflight
			else:
				shared = dfh_build_shared_native(primary, check=self.__check, settings_fn=self.__settings_fn)
				r = {'issues': [], 'valid': False, 'written': []} if not shared['valid'] and (not self.__check) else ProjectionPublisher(root, outputs, check=self.__check, **{**publication, 'disown': [*publication['disown'], *shared['removed']]}).run()
				r.update(issues=[*shared['issues'], *r['issues']], removed=[*shared['removed'], *r.get('removed', [])], shared=shared, valid=r['valid'] and shared['valid'], written=[*shared['written'], *r['written']])
			r.update(canonical_runtime=str(primary / 'runtime.json'), policy_bytes=len(instructions.encode('utf-8')), source_sha256=source_hash)
		except ValueError as exc:
			r = {'issues': [{'file': str(root / '.codex/config.toml'), 'message': str(exc)}], 'valid': False, 'written': []}
		return r
	# @used-by :meth:`NativeBuilder.__build_codex_enabled()`
	@staticmethod
	def __prepare_codex_outputs(root: Path, primary: Path) -> tuple[str, dict]:
		pp = dfh_project_paths(root, exact_root=True)
		native = pp.codex_config_toml
		current = tomllib.loads(native.read_bytes().decode('utf-8')).get('developer_instructions', '') if native.exists() else ''
		old_block = dfh_extract_managed_block(current)
		restore_global = 'policy-instructions' in old_block if old_block else not bool(current.strip())
		agents_dir = pp.agents_config_dir if pp.agents_config_dir.resolve() != primary else root / '.agents'
		local_rules = dfh_project_rule_paths(root, primary) if (agents_dir / 'rules').is_dir() else ()
		instructions = dfh_loader(primary, local_rules, restore_global=restore_global)
		guidance = f'# Codex: Upwork\n\n<!-- Generated from {primary.as_posix()}; run harness.py build-native to update. -->\n\n' + instructions + '\n'
		return (instructions, {root / 'AGENTS.md': guidance})
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	def run(self) -> dict:
		primary = Path(dfh_var_value('HARNESS_CODE') if None is self.__primary else self.__primary).resolve()
		config = dfh_primary_settings(primary, settings_fn=self.__settings_fn)
		plats = config.get('platforms') or {}
		root = Path(self.__root_arg or config['workspace_root']).resolve()
		platform_docs = [p for plat in plats for p in (primary / f'platforms/{plat}.md',) if p.is_file()]
		source_paths = [primary / 'runtime.json', *sorted((primary / 'rules').glob('*.md')), *platform_docs, *(p for p in (primary / 'agents/worker.md',) if p.is_file()), *sorted((primary / 'skills').glob('*/SKILL.md'))]
		source_hash = dfh_digest(b''.join((p.read_bytes() for p in source_paths)))
		return self.__build_codex_disabled(root, primary, source_hash) if 'codex' not in plats else self.__build_codex_enabled(root, primary, source_hash)
