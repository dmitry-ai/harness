# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import hashlib
import json
from pathlib import Path
import re
import tomllib
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from .configuration import DISCOVERY_KINDS, _frontmatter, load_discovery_manifest, load_project_receipt, receipt_sha256, resolve_manifest_entry
from .path_registry import project_paths
from .runtime import PRIMARY, extract_platform_instances, settings
from .storage import data_dir_for
# 2026-11-23
# "Extract SourceDiagnosticsScanner class from diagnose_sources in text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/68
class SourceDiagnosticsScanner:
	# @used-by :func:`diagnose_sources()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_class_methods_and_wrapper_parity()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_detects_missing_manifest_target_and_invalid_receipt()`
	def __init__(self, root, *, platform=None, profile=None, config=None, primary=PRIMARY):
		if None is root or (not str(root).strip()):
			raise ValueError('An explicit project root is required')
		self.root, self.primary = (Path(root).expanduser().resolve(), Path(primary).resolve())
		if not self.root.is_dir():
			raise ValueError(f'Project root is not a directory: {self.root}')
		self.config = settings() if None is config else config
		if None is not platform and platform not in self.config.get('platforms', {}):
			raise ValueError(f'Unknown platform: {platform}')
		self.platform, self.profile = (platform, profile)
		self.workspace = Path(self.config['workspace_root']).resolve()
		self.ancestry = [self.root] + ([p for p in self.root.parents if p.is_relative_to(self.workspace)] if self.root.is_relative_to(self.workspace) else [])
		self.sources: list[dict] = []
		self.by_path: dict[str, dict] = {}
		self.conflicts: list[dict] = []
		self.native_declarations: list[dict] = []
	# @used-by :meth:`SourceDiagnosticsScanner._apply_native_toml_data()`
	# @used-by :meth:`SourceDiagnosticsScanner._discover_references()`
	# @used-by :meth:`SourceDiagnosticsScanner._inspect_native_fallbacks()`
	# @used-by :meth:`SourceDiagnosticsScanner._inspect_native_toml()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_ancestry_scope()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_canonical_sources()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_discovery_manifests()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_manifest_entry()`
	# @used-by :meth:`SourceDiagnosticsScanner._verify_projection_receipt()`
	def _add_source(self, path, kind: str, via: str, *, required: bool=False) -> dict:
		resolved = Path(path).expanduser().resolve()
		key = str(resolved)
		if key in self.by_path:
			item = self.by_path[key]
			if via not in item['configured_via']:
				item['configured_via'].append(via)
			r = item
		else:
			item = {'path': key, 'kind': kind, 'configured_via': [via], 'exists': resolved.is_file(), 'injection': 'unknown'}
			self.by_path[key] = item
			self.sources.append(item)
			if not item['exists']:
				if required:
					self._record_issue('MISSING-SOURCE', resolved, 'An explicitly configured source does not exist')
			else:
				self._populate_source_metadata(resolved, item)
			r = item
		return r
	# @used-by :meth:`SourceDiagnosticsScanner._inspect_native_toml()`
	def _apply_native_toml_data(self, native: Path, item: dict, data: dict, scope: Path | None) -> None:
		instructions = data.get('developer_instructions')
		fallbacks = data.get('project_doc_fallback_filenames', [])
		item['developer_instructions_configured'] = bool(instructions)
		item['project_doc_fallback_filenames'] = fallbacks
		if not isinstance(fallbacks, list):
			raise ValueError('project_doc_fallback_filenames must be a list')
		if None is not instructions and not isinstance(instructions, str):
			raise ValueError('developer_instructions must be a string')
		if None is not instructions:
			item['developer_instructions_sha256'] = hashlib.sha256(instructions.encode()).hexdigest()
			self.native_declarations.append(item)
		for ref in self._referenced_paths(instructions or ''):
			self._add_source(Path(ref), 'native-loader-reference', str(native), required=True)
		if None is not scope:
			self._inspect_native_fallbacks(native, scope, fallbacks)
	# @used-by :meth:`SourceDiagnosticsScanner.run()`
	def _check_native_overrides(self) -> None:
		local_native = [item for item in self.native_declarations if not item.get('configured_profile')]
		if 1 < len(local_native):
			self._record_issue('NATIVE-KEY-OVERRIDE', local_native[-1]['path'], 'Multiple workspace/project developer_instructions keys exist; selected platform resolution is not proven', 'warning')
		global_native = [item for item in self.native_declarations if item.get('configured_profile')]
		if 1 < len({item['developer_instructions_sha256'] for item in global_native}):
			self._record_issue('PROFILE-INSTRUCTIONS-DIFFER', self.primary, 'Configured profile instructions differ; they are separate candidates, not combined effective instructions', 'warning')
	# @used-by :meth:`SourceDiagnosticsScanner.run()`
	def _check_rule_and_skill_divergence(self) -> None:
		canonical_rules = {Path(item['path']).name: item for item in self.sources if 'canonical-rule' == item['kind']}
		for item in self.sources:
			canonical = canonical_rules.get(Path(item['path']).name)
			if 'local-rule' == item['kind'] and canonical and item.get('sha256') != canonical.get('sha256'):
				item['canonical'] = canonical['path']
				self._record_issue('POLICY-DIVERGENCE', item['path'], 'Local bytes differ from the same-named canonical rule; compare intent and precedence explicitly', 'warning')
		named_skills: dict[str, list[dict]] = {}
		for item in self.sources:
			name = item.get('frontmatter', {}).get('name') if 'skill' in item['kind'] and item.get('exists') else None
			if name:
				named_skills.setdefault(name, []).append(item)
		for name, cands in named_skills.items():
			self._check_skill_candidates(name, cands)
	# @used-by :meth:`SourceDiagnosticsScanner._check_rule_and_skill_divergence()`
	def _check_skill_candidates(self, name: str, candidates: list[dict]) -> None:
		canonical = [v for v in candidates if 'canonical-skill' == v['kind']]
		if canonical:
			for cand in candidates:
				if 'local-skill' != cand['kind']:
					continue
				refs = [v for v in candidates if cand['path'] in v['configured_via']]
				if cand.get('sha256') != canonical[0].get('sha256') and (not any((ref['path'] == canonical[0]['path'] for ref in refs))):
					self._record_issue('SKILL-DIVERGENCE', cand['path'], f'Skill {name} has a separate local body instead of a reference to its canonical source', 'warning')
	# @used-by :meth:`SourceDiagnosticsScanner._scan_ancestry_scope()`
	def _discover_references(self, path: Path, kind: str) -> None:
		item = self.by_path[str(path.resolve())]
		if item.get('exists'):
			try:
				for ref in self._referenced_paths(path.read_text(encoding='utf-8-sig')):
					target = Path(ref) if Path(ref).is_absolute() else (path.parent / ref)
					if target.suffix.casefold() in ('.md', '.toml', '.json'):
						self._add_source(target, kind, str(path), required=True)
			except (OSError, UnicodeError) as exc:
				self._record_issue('UNREADABLE-REFERENCE', path, str(exc))
	# @used-by :meth:`SourceDiagnosticsScanner._apply_native_toml_data()`
	def _inspect_native_fallbacks(self, native: Path, scope: Path, filenames: list) -> None:
		for filename in filenames:
			if not isinstance(filename, str) or Path(filename).name != filename:
				self._record_issue('UNSUPPORTED-DOC-SELECTOR', native, 'Fallback document name is not a simple filename')
			elif (scope / filename).is_file():
				self._add_source(scope / filename, 'native-project-document', str(native))
	# @used-by :meth:`SourceDiagnosticsScanner._scan_ancestry_scope()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_codex_profiles()`
	def _inspect_native_toml(self, native: Path, via: str, *, scope: Path | None=None, profile_name: str | None=None) -> None:
		item = self._add_source(native, 'native-codex-config', via)
		if profile_name:
			item['configured_profile'] = profile_name
		if item['exists']:
			try:
				data = tomllib.loads(native.read_text(encoding='utf-8-sig'))
				self._apply_native_toml_data(native, item, data, scope)
			except (OSError, ValueError, UnicodeError, TypeError) as exc:
				self._record_issue('INVALID-NATIVE-CONFIG', native, str(exc))
	# @used-by :meth:`SourceDiagnosticsScanner._add_source()`
	def _populate_source_metadata(self, resolved: Path, item: dict) -> None:
		try:
			raw = resolved.read_bytes()
			item.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
			if '.md' == resolved.suffix.casefold():
				meta = _frontmatter(resolved)
				item['frontmatter'] = meta
				item['trigger'] = meta.get('trigger', 'unspecified')
				item['version'] = meta.get('version')
				item['selection'] = 'declared-always-on' if 'always_on' == meta.get('trigger') else 'conditional-or-manual' if meta.get('trigger') else 'unspecified'
		except (OSError, ValueError, UnicodeError) as exc:
			self._record_issue('UNREADABLE-SOURCE', resolved, str(exc))
	# @used-by :meth:`SourceDiagnosticsScanner._add_source()`
	# @used-by :meth:`SourceDiagnosticsScanner._check_native_overrides()`
	# @used-by :meth:`SourceDiagnosticsScanner._check_rule_and_skill_divergence()`
	# @used-by :meth:`SourceDiagnosticsScanner._check_skill_candidates()`
	# @used-by :meth:`SourceDiagnosticsScanner._discover_references()`
	# @used-by :meth:`SourceDiagnosticsScanner._inspect_native_fallbacks()`
	# @used-by :meth:`SourceDiagnosticsScanner._inspect_native_toml()`
	# @used-by :meth:`SourceDiagnosticsScanner._populate_source_metadata()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_discovery_manifests()`
	# @used-by :meth:`SourceDiagnosticsScanner._scan_manifest_entry()`
	# @used-by :meth:`SourceDiagnosticsScanner._verify_projection_receipt()`
	def _record_issue(self, code: str, path, message: str, severity: str='error') -> None:
		self.conflicts.append({'code': code, 'path': str(path), 'message': message, 'severity': severity})
	# @used-by :meth:`SourceDiagnosticsScanner._apply_native_toml_data()`
	# @used-by :meth:`SourceDiagnosticsScanner._discover_references()`
	def _referenced_paths(self, text: str) -> list[str]:
		values = re.findall('\\]\\(<([^>]+)>\\)', text) + re.findall('^\\s*-\\s+((?:[A-Za-z]:[/\\\\]|/)[^\\r\\n]+)', text, re.M)
		# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
		return dfa_unique_fast(values)
	# @used-by :meth:`SourceDiagnosticsScanner.run()`
	def _scan_ancestry_scope(self, scope: Path) -> None:
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		scope_pp = project_paths(scope, exact_root=True)
		agents = scope_pp.agents_config_dir if scope_pp.agents_config_dir.resolve() != self.primary else (scope / '.agents')
		for path in sorted((agents / 'rules').glob('*.md')):
			self._add_source(path, 'local-rule', f'project-discovery:{scope}')
		for path in sorted((agents / 'skills').glob('*/SKILL.md')):
			self._add_source(path, 'local-skill', f'project-discovery:{scope}')
			self._discover_references(path, 'skill-reference')
		self._scan_discovery_manifests(scope, agents)
		self._inspect_native_toml(scope_pp.codex_config_toml, f'optional-discovery:{scope}', scope=scope)
		for filename in ('AGENTS.md', 'AGENTS.override.md'):
			if (scope / filename).is_file():
				self._add_source(scope / filename, 'native-project-document', f'optional-discovery:{scope}')
		self._verify_projection_receipt(scope)
	# @used-by :meth:`SourceDiagnosticsScanner.run()`
	def _scan_canonical_sources(self) -> None:
		self._add_source(self.primary / 'runtime.json', 'canonical-runtime', 'runtime.PRIMARY', required=True)
		for path in sorted((self.primary / 'rules').glob('*.md')):
			self._add_source(path, 'canonical-rule', 'runtime.PRIMARY')
		for path in sorted((self.primary / 'skills').glob('*/SKILL.md')):
			self._add_source(path, 'canonical-skill', 'runtime.PRIMARY')
		# 2026-11-18
		# "Externalize agent environments and per-instance system paths into runtime.json":
		# https://github.com/dmitry-ai/harness/issues/86
		plats = [(self.platform, self.config.get('platforms', {}).get(self.platform, {}))] if self.platform else self.config.get('platforms', {}).items()
		for name, plat_cfg in plats:
			adapter_name = plat_cfg.get('adapter') or name if isinstance(plat_cfg, dict) else name
			adapter_file = self.primary / 'platforms' / f'{adapter_name}.md'
			if adapter_file.is_file() or (isinstance(plat_cfg, dict) and plat_cfg.get('enabled', True)):
				self._add_source(adapter_file, 'platform-adapter', 'runtime.platforms')
	# 2026-11-18
	# "Externalize agent environments and per-instance system paths into runtime.json":
	# https://github.com/dmitry-ai/harness/issues/86
	# @used-by :meth:`SourceDiagnosticsScanner.run()`
	def _scan_codex_profiles(self) -> None:
		codex_cfg = self.config.get('platforms', {}).get('codex', {})
		all_insts = extract_platform_instances(codex_cfg, platform='codex', include_disabled=True)
		if None is not self.profile and self.profile not in all_insts:
			raise ValueError('Unknown configured Codex profile')
		if self.platform in (None, 'codex'):
			pool = all_insts if self.profile else {k: v for k, v in all_insts.items() if v['enabled']}
			for name in [self.profile] if self.profile else pool:
				inst = pool[name]
				cfg_path = inst['system_paths'].get('config_toml') or str(Path(inst['home']).expanduser().resolve() / 'config.toml')
				self._inspect_native_toml(Path(cfg_path).expanduser().resolve(), f'runtime.platforms.codex.instances.{name}', profile_name=name)
	# 2026-11-14
	# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
	# https://github.com/dmitry-ai/harness/issues/71
	# @used-by :meth:`SourceDiagnosticsScanner._scan_ancestry_scope()`
	def _scan_discovery_manifests(self, scope: Path, agents: Path) -> None:
		for category in DISCOVERY_KINDS:
			manifest = agents / f'{category}.json'
			if not self._add_source(manifest, f'{category}-manifest', f'optional-discovery:{scope}')['exists']:
				continue
			try:
				data = load_discovery_manifest(manifest, missing_ok=False)
				if data.get('inherits'):
					self._record_issue('UNRESOLVED-INHERITANCE', manifest, 'Manifest inheritance needs platform-specific resolution; no loading is inferred', 'warning')
				for entry in data.get('entries', []):
					self._scan_manifest_entry(agents, manifest, category, entry)
			except (OSError, ValueError, UnicodeError) as exc:
				self._record_issue('INVALID-MANIFEST', manifest, str(exc))
	# 2026-11-14
	# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
	# https://github.com/dmitry-ai/harness/issues/71
	# @used-by :meth:`SourceDiagnosticsScanner._scan_discovery_manifests()`
	def _scan_manifest_entry(self, agents: Path, manifest: Path, category: str, entry) -> None:
		target, has_extra = resolve_manifest_entry(agents, entry)
		if None is target:
			self._record_issue('UNSUPPORTED-SELECTOR', manifest, 'Entry has no path; selector cannot be resolved')
		else:
			if has_extra:
				self._record_issue('CONDITIONAL-SOURCE', manifest, f'Additional selector fields for {target}; applicability is unknown', 'warning')
			if not target.is_dir():
				self._add_source(target, f'configured-{category}', str(manifest), required=True)
			else:
				pattern = '*.md' if 'rules' == category else 'SKILL.md' if 'skills' == category else '*'
				for path in sorted(target.rglob(pattern)):
					if path.is_file():
						self._add_source(path, f'configured-{category}', str(manifest), required=True)
	# @used-by :meth:`SourceDiagnosticsScanner._scan_ancestry_scope()`
	def _verify_projection_receipt(self, scope: Path) -> None:
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		receipt_path = data_dir_for(scope) / 'native-config.json'
		if self._add_source(receipt_path, 'projection-receipt', f'optional-discovery:{scope}')['exists']:
			try:
				# 2026-11-14
				# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
				# https://github.com/dmitry-ai/harness/issues/71
				_, _, receipt = load_project_receipt(receipt_path, by_path=True, error_message='Projection receipt must be an object')
				for path, expected in receipt.items():
					proj = self._add_source(Path(path), 'native-projection', str(receipt_path), required=True)
					proj['projection'] = 'matches-receipt' if proj.get('sha256') == receipt_sha256(expected) else 'differs-from-receipt'
					if 'matches-receipt' != proj['projection']:
						self._record_issue('PROJECTION-DRIFT', path, 'Projection differs from its publication receipt; no file was changed')
			except (OSError, ValueError, UnicodeError) as exc:
				self._record_issue('INVALID-RECEIPT', receipt_path, str(exc))
	# @used-by :func:`diagnose_sources()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_class_methods_and_wrapper_parity()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_detects_missing_manifest_target_and_invalid_receipt()`
	def run(self) -> dict:
		self._scan_canonical_sources()
		self._scan_codex_profiles()
		for scope in reversed(self.ancestry):
			self._scan_ancestry_scope(scope)
		self._check_rule_and_skill_divergence()
		self._check_native_overrides()
		fingerprint = hashlib.sha256(json.dumps(sorted(((item['path'], item.get('sha256')) for item in self.sources)), ensure_ascii=False).encode()).hexdigest()
		return {'schema_version': 1, 'root': str(self.root), 'workspace_root': str(self.workspace), 'canonical': str(self.primary), 'platform': self.platform, 'selected_profile': self.profile, 'sources': self.sources, 'configuration_sha256': fingerprint, 'conflicts': self.conflicts, 'valid': not any(('error' == item['severity'] for item in self.conflicts)), 'platform_injection': {'status': 'unknown', 'detail': 'Configured paths and disk versions are observable; actual platform injection and model reading are not proven by this diagnostic'}}
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_class_methods_and_wrapper_parity()`
# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.report()`
# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_explicit_root_required_and_sibling_not_discovered()`
# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_profile_instructions_are_separate_candidates_without_guessing_active_account()`
def diagnose_sources(root, *, platform=None, profile=None, config=None, primary=PRIMARY):
	return SourceDiagnosticsScanner(root, platform=platform, profile=profile, config=config, primary=primary).run()
