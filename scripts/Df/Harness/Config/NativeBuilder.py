# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import tomllib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class NativeBuilder:
	# @used-by :func:`agent_tools.configuration.build_native()`
	def __init__(self, root: str | Path | None=None, primary: str | Path | None=None, *, check: bool=False) -> None:
		self.__root_arg = root
		self.__primary = primary
		self.__check = check
	# @used-by :meth:`NativeBuilder.run()`
	def __build_codex_disabled(self, root: Path, primary: Path, source_hash: str) -> dict:
		from agent_tools import configuration as cfg
		from agent_tools.native_profiles import build_shared_native, legacy_project_projection_paths, shared_native_outputs
		try:
			publication = {'disown': list(shared_native_outputs(primary)), 'retire': [root / 'CODEX.md', *legacy_project_projection_paths(root, primary)]}
			shared = build_shared_native(primary, check=self.__check)
			if not shared['valid'] and (not self.__check):
				r = {'issues': [], 'valid': False, 'written': []}
			else:
				publication['disown'].extend(shared['removed'])
				r = cfg._publish(root, {}, check=self.__check, **publication)
			r.update(canonical_runtime=str(primary / 'runtime.json'), issues=[*shared['issues'], *r['issues']], policy_bytes=0, removed=[*shared['removed'], *r.get('removed', [])], shared=shared, source_sha256=source_hash, valid=r['valid'] and shared['valid'], written=[*shared['written'], *r['written']])
		except ValueError as exc:
			r = {'issues': [{'file': str(root), 'message': str(exc)}], 'valid': False, 'written': []}
		return r
	# @used-by :meth:`NativeBuilder.run()`
	def __build_codex_enabled(self, root: Path, primary: Path, source_hash: str) -> dict:
		from agent_tools import configuration as cfg
		from agent_tools.native_profiles import build_shared_native, legacy_project_projection_paths, shared_native_outputs
		instructions, outputs = self.__prepare_codex_outputs(root, primary)
		try:
			path, text, merge = cfg._native_config(root, instructions)
			outputs[path] = text
			publication = {'disown': list(shared_native_outputs(primary)), 'merge': merge, 'retire': [root / 'CODEX.md', *legacy_project_projection_paths(root, primary)]}
			preflight = cfg._publish(root, outputs, preflight=True, **publication) if not self.__check else None
			if None is not preflight and (not preflight['valid']):
				r = preflight
			else:
				shared = build_shared_native(primary, check=self.__check)
				r = {'issues': [], 'valid': False, 'written': []} if not shared['valid'] and (not self.__check) else cfg._publish(root, outputs, check=self.__check, **{**publication, 'disown': [*publication['disown'], *shared['removed']]})
				r.update(issues=[*shared['issues'], *r['issues']], removed=[*shared['removed'], *r.get('removed', [])], shared=shared, valid=r['valid'] and shared['valid'], written=[*shared['written'], *r['written']])
			r.update(canonical_runtime=str(primary / 'runtime.json'), policy_bytes=len(instructions.encode('utf-8')), source_sha256=source_hash)
		except ValueError as exc:
			r = {'issues': [{'file': str(root / '.codex/config.toml'), 'message': str(exc)}], 'valid': False, 'written': []}
		return r
	# @used-by :meth:`NativeBuilder.__build_codex_enabled()`
	@staticmethod
	def __prepare_codex_outputs(root: Path, primary: Path) -> tuple[str, dict]:
		from agent_tools import configuration as cfg
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		native = pp.codex_config_toml
		current = tomllib.loads(native.read_bytes().decode('utf-8')).get('developer_instructions', '') if native.exists() else ''
		old_block = cfg.extract_managed_block(current)
		restore_global = 'policy-instructions' in old_block if old_block else not bool(current.strip())
		agents_dir = pp.agents_config_dir if pp.agents_config_dir.resolve() != primary else root / '.agents'
		local_rules = cfg._project_rule_paths(root, primary) if (agents_dir / 'rules').is_dir() else ()
		instructions = cfg._loader(primary, local_rules, restore_global=restore_global)
		guidance = f'# Codex: Upwork\n\n<!-- Generated from {primary.as_posix()}; run harness.py build-native to update. -->\n\n' + instructions + '\n'
		return (instructions, {root / 'AGENTS.md': guidance})
	# @used-by :func:`agent_tools.configuration.build_native()`
	def run(self) -> dict:
		from agent_tools import configuration as cfg
		primary = Path(cfg.PRIMARY if None is self.__primary else self.__primary).resolve()
		config = cfg._primary_settings(primary)
		plats = config.get('platforms') or {}
		root = Path(self.__root_arg or config['workspace_root']).resolve()
		platform_docs = [p for plat in plats for p in (primary / f'platforms/{plat}.md',) if p.is_file()]
		source_paths = [primary / 'runtime.json', *sorted((primary / 'rules').glob('*.md')), *platform_docs, *(p for p in (primary / 'agents/worker.md',) if p.is_file()), *sorted((primary / 'skills').glob('*/SKILL.md'))]
		source_hash = cfg._digest(b''.join((p.read_bytes() for p in source_paths)))
		if 'codex' not in plats:
			r = self.__build_codex_disabled(root, primary, source_hash)
		else:
			r = self.__build_codex_enabled(root, primary, source_hash)
		return r
