# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import tomllib
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
from .runtime import PRIMARY, extract_platform_instances, profile_name, settings
from .storage import create_bytes, data_dir_for, locked, replace_bytes
# 2026-11-14
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
DISCOVERY_KINDS = ('rules', 'skills', 'agents')
# @used-by :func:`_native_config()`
# @used-by :func:`_publish()`
# @used-by :func:`replace_managed_block()`
# @used-by :func:`store_content_backup()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.run()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_guidance_uses_current_canonical_loader_without_copying_rule_bodies()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
# @used-by :meth:`test_portability.ProjectionTests.test_verified_legacy_migrates_but_manual_configuration_and_fallback_survive()`
def _digest(data):
	return hashlib.sha256(data).hexdigest()
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-02
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
# 2026-11-14
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
# @used-by :func:`configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_disabled()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
def _publish(root, outputs, *, check=False, merge=None, retire=(), disown=(), preflight=False):
	root = Path(root).resolve()
	if not outputs and (not any((Path(path).exists() for path in retire))):
		r = {'valid': True, 'issues': [], 'written': [], 'outputs': [], 'removed': []}
	else:
		with nullcontext() if check or preflight else locked(data_dir_for(root) / 'native-config.lock'):
			manifest, receipt_bytes, previous = load_project_receipt(root)
			issues, planned, removed, preimages = ([], {}, [], {})
			disowned = {str(Path(path).resolve()) for path in disown} & set(previous)
			if check:
				issues.extend({'file': path, 'message': 'Shared definition ownership must move to the central native profile registry'} for path in sorted(disowned))
			for target, text in outputs.items():
				target = Path(target)
				if has_linked_ancestor(target):
					issues.append({'file': str(target), 'message': 'Linked native configuration preserved'})
					continue
				payload = text.encode('utf-8')
				actual = target.read_bytes() if target.exists() else None
				key = str(target.resolve())
				if actual != payload:
					owned = receipt_sha256(previous.get(key))
					if None is not actual and owned != _digest(actual) and ((merge or {}).get(target) != actual):
						issues.append({'file': key, 'message': 'Manual/unowned native configuration preserved'})
					elif check:
						issues.append({'file': key, 'message': 'Native projection is missing or stale; run build-native'})
					else:
						planned[target] = payload
						preimages[target] = actual
			for target in retire:
				target = Path(target)
				if has_linked_ancestor(target):
					issues.append({'file': str(target), 'message': 'Linked legacy file preserved'})
					continue
				target = target.resolve()
				if not target.is_relative_to(root):
					raise ValueError('Retirement must stay inside the configured root')
				if target.exists():
					if receipt_sha256(previous.get(str(target))) != _digest(target.read_bytes()):
						issues.append({'file': str(target), 'message': 'Manual/unowned legacy file preserved'})
					elif check:
						issues.append({'file': str(target), 'message': 'Owned legacy file needs migration'})
					else:
						removed.append(target)
			if issues:
				r = {'valid': False, 'issues': issues, 'written': []}
			else:
				if not check and (not preflight):
					for target in removed:
						payload = target.read_bytes()
						if _digest(payload) != receipt_sha256(previous[str(target)]):
							raise ValueError('Legacy file changed before backup; external edit preserved')
						store_content_backup(data_dir_for(root) / 'native-retired', target, payload, error_message='Retired native backup differs; configuration preserved')
					for target, payload in planned.items():
						if (target.read_bytes() if target.exists() else None) != preimages[target]:
							raise ValueError('Native configuration changed during publication; external edit preserved')
						replace_bytes(target, payload)
					for key in disowned:
						previous.pop(key, None)
					previous.update({str(Path(p).resolve()): _digest(text.encode('utf-8')) for p, text in outputs.items()})
					for target in removed:
						if _digest(target.read_bytes()) != receipt_sha256(previous[str(target)]):
							raise ValueError('Legacy file changed during migration')
						target.unlink()
						previous.pop(str(target), None)
					# 2026-11-19
					# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
					# https://github.com/dmitry-ai/harness/issues/96
					from .path_registry import project_paths
					config = project_paths(root, exact_root=True).codex_config_toml
					if config in outputs:
						if outputs[config].strip():
							value = tomllib.loads(outputs[config]).get('developer_instructions', '')
							previous[str(config)] = {'sha256': _digest(outputs[config].encode()), 'block_sha256': _digest(extract_managed_block(value).encode())}
						else:
							if config.read_bytes() != outputs[config].encode('utf-8'):
								raise ValueError('Empty projection changed during retirement; external edit preserved')
							config.unlink()
							previous.pop(str(config), None)
							try:
								config.parent.rmdir()
							except OSError:
								pass
					if (manifest.read_bytes() if manifest.exists() else None) != receipt_bytes:
						raise ValueError('Ownership receipt changed during publication; external edit preserved')
					if previous:
						replace_bytes(manifest, (json.dumps(previous, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
					elif manifest.exists():
						manifest.unlink()
				r = {'valid': True, 'issues': [], 'written': [] if preflight else [str(p) for p in planned], 'outputs': [str(p) for p in outputs], 'removed': [] if preflight else [str(p) for p in removed]}
	return r
# @used-by :func:`_root_options()`
def _toml_statements(text):
	start = index = depth = 0
	quote, comment = (None, False)
	while index < len(text):
		char = text[index]
		if comment:
			if '\n' == char:
				comment = False
			else:
				index += 1
				continue
		elif quote:
			if quote.startswith('"') and '\\' == char:
				index += 2
				continue
			if text.startswith(quote, index):
				index += len(quote)
				if 3 == len(quote):
					while index < len(text) and text[index] == quote[0]:
						index += 1
				quote = None
				continue
			index += 1
			continue
		elif char in '"\'':
			quote = char * 3 if text.startswith(char * 3, index) else char
			index += len(quote)
			continue
		elif '#' == char:
			comment = True
		elif char in '[{':
			depth += 1
		elif char in ']}':
			depth -= 1
		if '\n' == char and 0 == depth:
			yield (start, index + 1)
			start = index + 1
		index += 1
	if start < len(text):
		yield (start, len(text))
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
START = '<!-- upwork-init:instructions:start -->'
END = '<!-- upwork-init:instructions:end -->'
# @used-by unused
def _managed_block(value):
	return extract_managed_block(value)
# @used-by :func:`_native_config()`
# @used-by :meth:`test_portability.ProjectionTests.test_multiline_toml_values_do_not_damage_unrelated_settings()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
def _root_options(text, instructions=None, *, legacy_bytes=None, expected_block=None):
	data = tomllib.loads(text) if text.strip() else {}
	block = START + '\n' + instructions.strip() + '\n' + END if instructions else ''
	value = replace_managed_block(data.get('developer_instructions', ''), block, expected_sha256=expected_block)
	values = {'developer_instructions': json.dumps(value, ensure_ascii=False) if value.strip() else None} if 'developer_instructions' in data or block else {}
	if None is not legacy_bytes:
		names = data.get('project_doc_fallback_filenames', [])
		if 'CODEX.md' in names:
			remaining = [name for name in names if 'CODEX.md' != name]
			values['project_doc_fallback_filenames'] = json.dumps(remaining) if remaining else None
		if data.get('project_doc_max_bytes') in (65536, 65536 + legacy_bytes):
			values['project_doc_max_bytes'] = None
	edits, found = ([], set())
	for start, end in _toml_statements(text):
		statement = text[start:end].lstrip()
		if statement.startswith('['):
			break
		for key, value in values.items():
			if re.match('^(?:' + key + '|"' + key + '"|\'' + key + "')\\s*=", statement):
				newline = '\r\n' if text[start:end].endswith('\r\n') else '\n'
				edits.append((start, end, '' if None is value else key + ' = ' + value + newline))
				found.add(key)
	for start, end, replacement in reversed(edits):
		text = text[:start] + replacement + text[end:]
	text = ''.join((key + ' = ' + value + '\n' for key, value in values.items() if key not in found and None is not value)) + text
	tomllib.loads(text)
	return text
# @used-by :func:`configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
def _native_config(root, instructions=None):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	config_path = project_paths(root, exact_root=True).codex_config_toml
	actual = config_path.read_bytes() if config_path.exists() else None
	existing = actual.decode('utf-8') if None is not actual else ''
	_, _, receipt = load_project_receipt(root)
	owned = receipt.get(str(config_path), {})
	legacy = root / 'CODEX.md'
	legacy_bytes = len(legacy.read_bytes()) if legacy.exists() and receipt_sha256(receipt.get(str(legacy))) == _digest(legacy.read_bytes()) else None
	wanted = _root_options(existing, instructions, legacy_bytes=legacy_bytes, expected_block=owned.get('block_sha256') if isinstance(owned, dict) else None)
	return (config_path, wanted, {config_path: actual})
# 2026-11-25
# "Support model_decision trigger class in doctor and Codex loader":
# https://github.com/dmitry-ai/harness/issues/241
# 2026-11-25
# "Refactor shared rules into compact three-layer M-2 architecture":
# https://github.com/dmitry-ai/harness/issues/242
# @used-by :func:`agent_tools.native_profiles._legacy_role()`
# @used-by :func:`agent_tools.native_profiles._profile_agents()`
# @used-by :func:`agent_tools.native_profiles.shared_native_outputs()`
# @used-by :func:`configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.legacy_codex()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_loader_omits_on_demand_header_when_all_rules_are_always_on()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_loader_separates_always_on_and_catalogs_model_decision_with_description()`
def _loader(primary, local=(), *, restore_global=True, display_root=None):
	from .rules_manifest import render_codex_loader
	return render_codex_loader(primary, local, restore_global=restore_global, display_root=display_root)
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_portability.ProjectionTests.test_global_instructions_are_read_safely_and_local_override_keeps_its_priority()`
def global_codex_instructions():
	codex_cfg = settings()['platforms'].get('codex') or {}
	all_insts = extract_platform_instances(codex_cfg, platform='codex', include_disabled=True)
	enabled_insts = {k: v for k, v in all_insts.items() if v['enabled']}
	try:
		name = profile_name()
		names = [name]
		pool = all_insts
	except ValueError:
		names = list(enabled_insts)
		pool = enabled_insts
	if not names:
		return {'developer_instructions': '', 'profile': 'codex disabled (no enabled instances)'}
	values = []
	for name in names:
		inst = pool.get(name) or {}
		cfg_toml = inst.get('system_paths', {}).get('config_toml')
		path = Path(cfg_toml) if cfg_toml else Path(inst['home']) / 'config.toml'
		value = tomllib.loads(path.read_bytes().decode('utf-8-sig')).get('developer_instructions', '') if path.exists() else ''
		if not isinstance(value, str):
			raise ValueError('Global developer_instructions must be a string')
		values.append(value)
	if 1 != len(set(values)):
		raise ValueError('Global profile instructions differ; select the actual --codex-profile instead of combining accounts')
	r = {'developer_instructions': values[0], 'profile': names[0] if 1 == len(names) else 'identical across configured profiles'}
	return r
# @used-by :func:`agent_tools.completion._instruction_snapshot()`
# @used-by :func:`configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`test_portability.ProjectionTests.test_extra_rule_sources_are_projected_and_unsupported_selectors_reported()`
def _project_rule_paths(root, primary):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	# 2026-11-20
	# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
	# https://github.com/dmitry-ai/harness/issues/100
	from .path_registry import project_paths, relocated_harness_code_dirs
	pp = project_paths(root, exact_root=True)
	agents = pp.agents_config_dir if pp.agents_config_dir.resolve() != Path(primary).resolve() else (root / '.agents')
	paths = list(sorted((agents / 'rules').glob('*.md')))
	data = load_discovery_manifest(agents / 'rules.json', entries_error='rules.json needs an entries list')
	if data.get('inherits'):
		raise ValueError('Codex projection does not support rules.json inherits; preserve it and resolve explicitly')
	shared = (primary / 'rules').resolve()
	shared_equivalents = {shared, *((rc / 'rules').resolve() for rc in relocated_harness_code_dirs(primary=primary))}
	for entry in data.get('entries', []):
		source, has_extra = resolve_manifest_entry(agents, entry)
		if None is source:
			raise ValueError('Each rules.json entry needs a path')
		if has_extra:
			raise ValueError('Codex projection does not support filtered rules.json entries; preserve them and resolve explicitly')
		if source not in shared_equivalents:
			if source.is_dir():
				paths.extend(sorted(source.rglob('*.md')))
			elif source.is_file() and '.md' == source.suffix:
				paths.append(source)
			else:
				raise ValueError(f'Configured rule source is missing or unsupported: {source}')
	return list(dict.fromkeys((path.resolve() for path in paths if not any((path.resolve().is_relative_to(sh) for sh in shared_equivalents)))))
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# @used-by :func:`configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.run()`
def _primary_settings(primary):
	p = Path(primary).resolve()
	rt = p / 'runtime.json'
	if p != Path(PRIMARY).resolve() and rt.is_file():
		return settings(rt)
	return settings()
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :meth:`test_portability.ProjectionTests.test_project_rules_feed_both_systems_and_detect_stale_codex_projection()`
def configure_codex_project(root, primary=PRIMARY, job_url=None, label=None, *, check=False):
	# 2026-11-02
	# "Replace per-profile Harness projections with shared native connections":
	# https://github.com/dmitry-ai/harness/issues/35
	from .native_profiles import legacy_project_projection_paths
	root, primary = (Path(root).resolve(), Path(primary).resolve())
	cfg = _primary_settings(primary)
	if 'codex' not in (cfg.get('platforms') or {}) or root == Path(cfg['workspace_root']).resolve():
		r = {'valid': True, 'issues': [], 'written': []}
	else:
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		agents_dir = pp.agents_config_dir if pp.agents_config_dir.resolve() != primary else (root / '.agents')
		r = None
		try:
			paths = _project_rule_paths(root, primary)
		except (ValueError, OSError) as exc:
			if not check:
				raise
			r = {'valid': False, 'issues': [{'file': str(agents_dir / 'rules.json'), 'message': str(exc)}], 'written': []}
		if None is r:
			try:
				native = pp.codex_config_toml
				data = tomllib.loads(native.read_bytes().decode('utf-8')) if native.exists() else {}
				current = data.get('developer_instructions', '')
				manual = current.replace(extract_managed_block(current), '').strip()
				path, text, merge = _native_config(root, _loader(primary, paths, restore_global=False) if manual else None)
				r = _publish(root, {path: text} if text or path.exists() else {}, check=check, merge=merge, retire=[root / 'CODEX.md', *legacy_project_projection_paths(root, primary)])
			except ValueError as exc:
				if not check:
					raise
				r = {'valid': False, 'issues': [{'file': str(pp.codex_config_toml), 'message': str(exc)}], 'written': []}
			if not check and (not r['valid']):
				raise ValueError(r['issues'])
	return r
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# @used-by :func:`agent_tools.native_profiles._legacy_skill()`
# @used-by :func:`agent_tools.native_profiles._skills()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._populate_source_metadata()`
def _frontmatter(path):
	text = path.read_text(encoding='utf-8-sig')
	match = re.match('^---\\r?\\n(.*?)\\r?\\n---\\r?\\n', text, re.S)
	values = {}
	for line in match.group(1).splitlines() if match else []:
		key, sep, value = line.partition(':')
		if sep and key.strip() and (not key.startswith(' ')):
			value = value.strip()
			values[key.strip()] = json.loads(value) if value.startswith('"') else value
	r = values
	return r
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.build()`
# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_build_native_uses_shared_skills_without_project_wrappers()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_portability.ProjectionTests.test_check_does_not_create_an_uninstalled_workspace()`
# @used-by :meth:`test_portability.ProjectionTests.test_dangling_personal_guidance_links_are_preserved_before_shared_publication()`
# @used-by :meth:`test_portability.ProjectionTests.test_first_install_preserves_an_unowned_antigravity_worker()`
# @used-by :meth:`test_portability.ProjectionTests.test_generation_is_idempotent_detects_source_changes_and_preserves_manual_edits()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
# @used-by :meth:`test_portability.ProjectionTests.test_unowned_legacy_prevents_partial_migration()`
# @used-by :meth:`test_portability.ProjectionTests.test_verified_legacy_migrates_but_manual_configuration_and_fallback_survive()`
def build_native(root=None, *, primary=PRIMARY, check=False):
	from Df.Harness.Config.NativeBuilder import NativeBuilder
	return NativeBuilder(root, primary=primary, check=check).run()
# 2026-11-14
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
# @used-by :func:`_managed_block()`
# @used-by :func:`_publish()`
# @used-by :func:`configure_codex_project()`
# @used-by :func:`replace_managed_block()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def extract_managed_block(value, start_marker=START, end_marker=END, *, error_message='Malformed managed developer instructions; configuration preserved'):
	if start_marker not in value and end_marker not in value:
		r = ''
	elif 1 != value.count(start_marker) or 1 != value.count(end_marker) or value.index(start_marker) > value.index(end_marker):
		raise ValueError(error_message)
	else:
		r = value[value.index(start_marker):value.index(end_marker) + len(end_marker)]
	return r
# @used-by :func:`_publish()`
# @used-by :mod:`agent_tools.native_profiles`
def has_linked_ancestor(path, *, include_self=True):
	resolved = Path(os.path.abspath(path))
	candidates = (resolved, *resolved.parents) if include_self else resolved.parents
	return next((item for item in candidates if is_linked_path(item)), None)
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`has_linked_ancestor()`
# @used-by :mod:`agent_tools.native_profiles`
def is_linked_path(path):
	candidate = Path(path)
	return candidate.is_symlink() or bool(getattr(candidate, 'is_junction', lambda: False)())
# @used-by :func:`_project_rule_paths()`
# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_discovery_manifests()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def load_discovery_manifest(path, *, missing_ok=True, entries_error='Manifest needs an entries list', check_inherits=False):
	target = Path(path)
	data = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() or (not missing_ok) else {}
	if not isinstance(data, dict) or not isinstance(data.get('entries', []), list) or (check_inherits and (not isinstance(data.get('inherits', []), list))):
		raise ValueError(entries_error)
	return data
# @used-by :func:`_native_config()`
# @used-by :func:`_publish()`
# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._verify_projection_receipt()`
def load_project_receipt(target, *, by_path=False, error_message='Project native ownership receipt must be an object; preserved'):
	path = Path(target) if by_path else data_dir_for(target) / 'native-config.json'
	raw = path.read_bytes() if path.exists() else None
	data = json.loads(raw.decode('utf-8-sig')) if None is not raw else {}
	if not isinstance(data, dict):
		raise ValueError(error_message)
	return (path, raw, data)
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def project_discovery_entries(primary, kind, *, require_dir=False):
	shared = Path(primary) / kind
	if require_dir and (not shared.is_dir()):
		raise FileNotFoundError(shared)
	return [{'path': shared.as_posix()}, *([{'path': 'rules'}] if 'rules' == kind else [])]
# @used-by :func:`_native_config()`
# @used-by :func:`_publish()`
# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._verify_projection_receipt()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def receipt_sha256(entry):
	return entry.get('sha256') if isinstance(entry, dict) else entry
# @used-by :func:`_root_options()`
# @used-by :func:`agent_tools.native_profiles._profile_agents()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def replace_managed_block(value, block, *, start_marker=START, end_marker=END, expected_sha256=None, malformed_message='Malformed managed developer instructions; configuration preserved', edited_message='Managed developer instructions were manually edited; configuration preserved'):
	old_block = extract_managed_block(value, start_marker, end_marker, error_message=malformed_message)
	if not old_block:
		r = value + ('\n\n' if value and block else '') + block
	else:
		if old_block != block and (_digest(old_block.encode('utf-8')) != expected_sha256):
			raise ValueError(edited_message)
		index = value.index(start_marker)
		r = value[:index] + block + value[index + len(old_block):]
	return r
# @used-by :func:`_project_rule_paths()`
# @used-by :func:`agent_tools.native_profiles._manifest()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_manifest_entry()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def resolve_manifest_entry(agents_dir, entry):
	if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
		r = (None, False)
	else:
		r = ((Path(agents_dir) / Path(entry['path']).expanduser()).resolve(), bool(set(entry) - {'path'}))
	return r
# @used-by :func:`_publish()`
# @used-by :func:`agent_tools.native_profiles._backup()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def store_content_backup(backup_root, path, payload, *, error_message=None):
	digest = _digest(payload)
	backup = Path(backup_root) / _digest(str(path).encode('utf-8')) / (digest + '.bin')
	backup.parent.mkdir(parents=True, exist_ok=True)
	if not backup.exists():
		create_bytes(backup, payload)
	if backup.read_bytes() != payload:
		raise ValueError(error_message or f'Backup hash collision or modification; preserved: {backup}')
	return (backup, digest)
