# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import tomllib
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from agent_tools.configuration import DISCOVERY_KINDS, _frontmatter, load_discovery_manifest, load_project_receipt, receipt_sha256, resolve_manifest_entry
from agent_tools.path_registry import project_paths
from agent_tools.runtime import PRIMARY, extract_platform_instances, settings
from agent_tools.storage import data_dir_for
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DiagnosticsScanner:
	# @used-by :func:`agent_tools.text_diagnostics.diagnose_sources()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_diagnostics_scanner_and_response_checker()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_class_methods_and_wrapper_parity()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_detects_missing_manifest_target_and_invalid_receipt()`
	def __init__(self, root, *, platform=None, profile=None, config=None, primary=PRIMARY) -> None:
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
	# @used-by unused
	def __getattr__(self, name: str):
		compat = {'_add_source': self.__add_source, '_check_rule_and_skill_divergence': self.__check_rule_and_skill_divergence, '_inspect_native_toml': self.__inspect_native_toml, '_record_issue': self.__record_issue}
		if name not in compat:
			raise AttributeError(name)
		return compat[name]
	# @used-by :meth:`DiagnosticsScanner.__apply_native_toml_data()`
	# @used-by :meth:`DiagnosticsScanner.__discover_references()`
	# @used-by :meth:`DiagnosticsScanner.__getattr__()`
	# @used-by :meth:`DiagnosticsScanner.__inspect_native_fallbacks()`
	# @used-by :meth:`DiagnosticsScanner.__inspect_native_toml()`
	# @used-by :meth:`DiagnosticsScanner.__scan_ancestry_scope()`
	# @used-by :meth:`DiagnosticsScanner.__scan_canonical_sources()`
	# @used-by :meth:`DiagnosticsScanner.__scan_discovery_manifests()`
	# @used-by :meth:`DiagnosticsScanner.__scan_manifest_entry()`
	# @used-by :meth:`DiagnosticsScanner.__verify_projection_receipt()`
	def __add_source(self, path, kind: str, via: str, *, required: bool=False) -> dict:
		resolved = Path(path).expanduser().resolve()
		key = str(resolved)
		if key in self.by_path:
			r = self.by_path[key]
			if via not in r['configured_via']:
				r['configured_via'].append(via)
		else:
			r = {'path': key, 'kind': kind, 'configured_via': [via], 'exists': resolved.is_file(), 'injection': 'unknown'}
			self.by_path[key] = r
			self.sources.append(r)
			if not r['exists']:
				if required:
					self.__record_issue('MISSING-SOURCE', resolved, 'An explicitly configured source does not exist')
			else:
				self.__populate_source_metadata(resolved, r)
		return r
	# @used-by :meth:`DiagnosticsScanner.__inspect_native_toml()`
	def __apply_native_toml_data(self, native: Path, item: dict, data: dict, scope: Path | None) -> None:
		instructions, fallbacks = (data.get('developer_instructions'), data.get('project_doc_fallback_filenames', []))
		item['developer_instructions_configured'] = bool(instructions)
		item['project_doc_fallback_filenames'] = fallbacks
		if not isinstance(fallbacks, list):
			raise ValueError('project_doc_fallback_filenames must be a list')
		if None is not instructions and (not isinstance(instructions, str)):
			raise ValueError('developer_instructions must be a string')
		if None is not instructions:
			item['developer_instructions_sha256'] = hashlib.sha256(instructions.encode()).hexdigest()
			self.native_declarations.append(item)
		for ref in self.__referenced_paths(instructions or ''):
			self.__add_source(Path(ref), 'native-loader-reference', str(native), required=True)
		if None is not scope:
			self.__inspect_native_fallbacks(native, scope, fallbacks)
	# @used-by :meth:`DiagnosticsScanner.run()`
	def __check_native_overrides(self) -> None:
		local_native = [item for item in self.native_declarations if not item.get('configured_profile')]
		if 1 < len(local_native):
			self.__record_issue('NATIVE-KEY-OVERRIDE', local_native[-1]['path'], 'Multiple workspace/project developer_instructions keys exist; selected platform resolution is not proven', 'warning')
		global_native = [item for item in self.native_declarations if item.get('configured_profile')]
		if 1 < len({item['developer_instructions_sha256'] for item in global_native}):
			self.__record_issue('PROFILE-INSTRUCTIONS-DIFFER', self.primary, 'Configured profile instructions differ; they are separate candidates, not combined effective instructions', 'warning')
	# @used-by :meth:`DiagnosticsScanner.__getattr__()`
	# @used-by :meth:`DiagnosticsScanner.run()`
	def __check_rule_and_skill_divergence(self) -> None:
		canonical_rules = {Path(item['path']).name: item for item in self.sources if 'canonical-rule' == item['kind']}
		for item in self.sources:
			canonical = canonical_rules.get(Path(item['path']).name)
			if 'local-rule' == item['kind'] and canonical and item.get('sha256') != canonical.get('sha256'):
				item['canonical'] = canonical['path']
				self.__record_issue('POLICY-DIVERGENCE', item['path'], 'Local bytes differ from the same-named canonical rule; compare intent and precedence explicitly', 'warning')
		named_skills: dict[str, list[dict]] = {}
		for item in self.sources:
			name = item.get('frontmatter', {}).get('name') if 'skill' in item['kind'] and item.get('exists') else None
			if name:
				named_skills.setdefault(name, []).append(item)
		for name, cands in named_skills.items():
			self.__check_skill_candidates(name, cands)
	# @used-by :meth:`DiagnosticsScanner.__check_rule_and_skill_divergence()`
	def __check_skill_candidates(self, name: str, candidates: list[dict]) -> None:
		canonical = [v for v in candidates if 'canonical-skill' == v['kind']]
		if canonical:
			for cand in candidates:
				if 'local-skill' != cand['kind']:
					continue
				refs = [v for v in candidates if cand['path'] in v['configured_via']]
				if cand.get('sha256') != canonical[0].get('sha256') and (not any((ref['path'] == canonical[0]['path'] for ref in refs))):
					self.__record_issue('SKILL-DIVERGENCE', cand['path'], f'Skill {name} has a separate local body instead of a reference to its canonical source', 'warning')
	# @used-by :meth:`DiagnosticsScanner.__scan_ancestry_scope()`
	def __discover_references(self, path: Path, kind: str) -> None:
		item = self.by_path[str(path.resolve())]
		if item.get('exists'):
			try:
				for ref in self.__referenced_paths(path.read_text(encoding='utf-8-sig')):
					target = Path(ref) if Path(ref).is_absolute() else (path.parent / ref)
					if target.suffix.casefold() in ('.md', '.toml', '.json'):
						self.__add_source(target, kind, str(path), required=True)
			except (OSError, UnicodeError) as exc:
				self.__record_issue('UNREADABLE-REFERENCE', path, str(exc))
	# @used-by :meth:`DiagnosticsScanner.__apply_native_toml_data()`
	def __inspect_native_fallbacks(self, native: Path, scope: Path, filenames: list) -> None:
		for filename in filenames:
			if not isinstance(filename, str) or Path(filename).name != filename:
				self.__record_issue('UNSUPPORTED-DOC-SELECTOR', native, 'Fallback document name is not a simple filename')
			elif (scope / filename).is_file():
				self.__add_source(scope / filename, 'native-project-document', str(native))
	# @used-by :meth:`DiagnosticsScanner.__getattr__()`
	# @used-by :meth:`DiagnosticsScanner.__scan_ancestry_scope()`
	# @used-by :meth:`DiagnosticsScanner.__scan_codex_profiles()`
	def __inspect_native_toml(self, native: Path, via: str, *, scope: Path | None=None, profile_name: str | None=None) -> None:
		item = self.__add_source(native, 'native-codex-config', via)
		if profile_name:
			item['configured_profile'] = profile_name
		if item['exists']:
			try:
				data = tomllib.loads(native.read_text(encoding='utf-8-sig'))
				self.__apply_native_toml_data(native, item, data, scope)
			except (OSError, ValueError, UnicodeError, TypeError) as exc:
				self.__record_issue('INVALID-NATIVE-CONFIG', native, str(exc))
	# @used-by :meth:`DiagnosticsScanner.__add_source()`
	def __populate_source_metadata(self, resolved: Path, item: dict) -> None:
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
			self.__record_issue('UNREADABLE-SOURCE', resolved, str(exc))
	# @used-by :meth:`DiagnosticsScanner.__add_source()`
	# @used-by :meth:`DiagnosticsScanner.__check_native_overrides()`
	# @used-by :meth:`DiagnosticsScanner.__check_rule_and_skill_divergence()`
	# @used-by :meth:`DiagnosticsScanner.__check_skill_candidates()`
	# @used-by :meth:`DiagnosticsScanner.__discover_references()`
	# @used-by :meth:`DiagnosticsScanner.__getattr__()`
	# @used-by :meth:`DiagnosticsScanner.__inspect_native_fallbacks()`
	# @used-by :meth:`DiagnosticsScanner.__inspect_native_toml()`
	# @used-by :meth:`DiagnosticsScanner.__populate_source_metadata()`
	# @used-by :meth:`DiagnosticsScanner.__scan_discovery_manifests()`
	# @used-by :meth:`DiagnosticsScanner.__scan_manifest_entry()`
	# @used-by :meth:`DiagnosticsScanner.__verify_projection_receipt()`
	def __record_issue(self, code: str, path, message: str, severity: str='error') -> None:
		self.conflicts.append({'code': code, 'path': str(path), 'message': message, 'severity': severity})
	# @used-by :meth:`DiagnosticsScanner.__apply_native_toml_data()`
	# @used-by :meth:`DiagnosticsScanner.__discover_references()`
	@staticmethod
	def __referenced_paths(text: str) -> list[str]:
		values = re.findall('\\]\\(<([^>]+)>\\)', text) + re.findall('^\\s*-\\s+((?:[A-Za-z]:[/\\\\]|/)[^\\r\\n]+)', text, re.M)
		return dfa_unique_fast(values)
	# @used-by :meth:`DiagnosticsScanner.run()`
	def __scan_ancestry_scope(self, scope: Path) -> None:
		scope_pp = project_paths(scope, exact_root=True)
		agents = scope_pp.agents_config_dir if scope_pp.agents_config_dir.resolve() != self.primary else (scope / '.agents')
		for path in sorted((agents / 'rules').glob('*.md')):
			self.__add_source(path, 'local-rule', f'project-discovery:{scope}')
		for path in sorted((agents / 'skills').glob('*/SKILL.md')):
			self.__add_source(path, 'local-skill', f'project-discovery:{scope}')
			self.__discover_references(path, 'skill-reference')
		self.__scan_discovery_manifests(scope, agents)
		self.__inspect_native_toml(scope_pp.codex_config_toml, f'optional-discovery:{scope}', scope=scope)
		for filename in ('AGENTS.md', 'AGENTS.override.md'):
			if (scope / filename).is_file():
				self.__add_source(scope / filename, 'native-project-document', f'optional-discovery:{scope}')
		self.__verify_projection_receipt(scope)
	# @used-by :meth:`DiagnosticsScanner.run()`
	def __scan_canonical_sources(self) -> None:
		self.__add_source(self.primary / 'runtime.json', 'canonical-runtime', 'runtime.PRIMARY', required=True)
		for path in sorted((self.primary / 'rules').glob('*.md')):
			self.__add_source(path, 'canonical-rule', 'runtime.PRIMARY')
		for path in sorted((self.primary / 'skills').glob('*/SKILL.md')):
			self.__add_source(path, 'canonical-skill', 'runtime.PRIMARY')
		plats = [(self.platform, self.config.get('platforms', {}).get(self.platform, {}))] if self.platform else self.config.get('platforms', {}).items()
		for name, plat_cfg in plats:
			adapter_name = plat_cfg.get('adapter') or name if isinstance(plat_cfg, dict) else name
			adapter_file = self.primary / 'platforms' / f'{adapter_name}.md'
			if adapter_file.is_file() or (isinstance(plat_cfg, dict) and plat_cfg.get('enabled', True)):
				self.__add_source(adapter_file, 'platform-adapter', 'runtime.platforms')
	# @used-by :meth:`DiagnosticsScanner.run()`
	def __scan_codex_profiles(self) -> None:
		codex_cfg = self.config.get('platforms', {}).get('codex', {})
		all_insts = extract_platform_instances(codex_cfg, platform='codex', include_disabled=True)
		if None is not self.profile and self.profile not in all_insts:
			raise ValueError('Unknown configured Codex profile')
		if self.platform in (None, 'codex'):
			pool = all_insts if self.profile else {k: v for k, v in all_insts.items() if v['enabled']}
			for name in [self.profile] if self.profile else pool:
				inst = pool[name]
				cfg_path = inst['system_paths'].get('config_toml') or str(Path(inst['home']).expanduser().resolve() / 'config.toml')
				self.__inspect_native_toml(Path(cfg_path).expanduser().resolve(), f'runtime.platforms.codex.instances.{name}', profile_name=name)
	# @used-by :meth:`DiagnosticsScanner.__scan_ancestry_scope()`
	def __scan_discovery_manifests(self, scope: Path, agents: Path) -> None:
		for category in DISCOVERY_KINDS:
			manifest = agents / f'{category}.json'
			if not self.__add_source(manifest, f'{category}-manifest', f'optional-discovery:{scope}')['exists']:
				continue
			try:
				data = load_discovery_manifest(manifest, missing_ok=False)
				if data.get('inherits'):
					self.__record_issue('UNRESOLVED-INHERITANCE', manifest, 'Manifest inheritance needs platform-specific resolution; no loading is inferred', 'warning')
				for entry in data.get('entries', []):
					self.__scan_manifest_entry(agents, manifest, category, entry)
			except (OSError, ValueError, UnicodeError) as exc:
				self.__record_issue('INVALID-MANIFEST', manifest, str(exc))
	# @used-by :meth:`DiagnosticsScanner.__scan_discovery_manifests()`
	def __scan_manifest_entry(self, agents: Path, manifest: Path, category: str, entry) -> None:
		target, has_extra = resolve_manifest_entry(agents, entry)
		if None is target:
			self.__record_issue('UNSUPPORTED-SELECTOR', manifest, 'Entry has no path; selector cannot be resolved')
		else:
			if has_extra:
				self.__record_issue('CONDITIONAL-SOURCE', manifest, f'Additional selector fields for {target}; applicability is unknown', 'warning')
			if not target.is_dir():
				self.__add_source(target, f'configured-{category}', str(manifest), required=True)
			else:
				pattern = '*.md' if 'rules' == category else 'SKILL.md' if 'skills' == category else '*'
				for path in sorted(target.rglob(pattern)):
					if path.is_file():
						self.__add_source(path, f'configured-{category}', str(manifest), required=True)
	# @used-by :meth:`DiagnosticsScanner.__scan_ancestry_scope()`
	def __verify_projection_receipt(self, scope: Path) -> None:
		receipt_path = data_dir_for(scope) / 'native-config.json'
		if self.__add_source(receipt_path, 'projection-receipt', f'optional-discovery:{scope}')['exists']:
			try:
				_, _, receipt = load_project_receipt(receipt_path, by_path=True, error_message='Projection receipt must be an object')
				for path, expected in receipt.items():
					proj = self.__add_source(Path(path), 'native-projection', str(receipt_path), required=True)
					proj['projection'] = 'matches-receipt' if proj.get('sha256') == receipt_sha256(expected) else 'differs-from-receipt'
					if 'matches-receipt' != proj['projection']:
						self.__record_issue('PROJECTION-DRIFT', path, 'Projection differs from its publication receipt; no file was changed')
			except (OSError, ValueError, UnicodeError) as exc:
				self.__record_issue('INVALID-RECEIPT', receipt_path, str(exc))
	# @used-by :func:`agent_tools.text_diagnostics.diagnose_sources()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_diagnostics_scanner_and_response_checker()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_class_methods_and_wrapper_parity()`
	# @used-by :meth:`test_source_diagnostics_scanner.SourceDiagnosticsScannerTests.test_scanner_detects_missing_manifest_target_and_invalid_receipt()`
	def run(self) -> dict:
		self.__scan_canonical_sources()
		self.__scan_codex_profiles()
		for scope in reversed(self.ancestry):
			self.__scan_ancestry_scope(scope)
		self.__check_rule_and_skill_divergence()
		self.__check_native_overrides()
		fingerprint = hashlib.sha256(json.dumps(sorted(((item['path'], item.get('sha256')) for item in self.sources)), ensure_ascii=False).encode()).hexdigest()
		return {'schema_version': 1, 'root': str(self.root), 'workspace_root': str(self.workspace), 'canonical': str(self.primary), 'platform': self.platform, 'selected_profile': self.profile, 'sources': self.sources, 'configuration_sha256': fingerprint, 'conflicts': self.conflicts, 'valid': not any(('error' == item['severity'] for item in self.conflicts)), 'platform_injection': {'status': 'unknown', 'detail': 'Configured paths and disk versions are observable; actual platform injection and model reading are not proven by this diagnostic'}}
