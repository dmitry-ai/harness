# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import hashlib
import json
from pathlib import Path
import re
import tomllib
from .configuration import DISCOVERY_KINDS, _frontmatter, load_discovery_manifest, load_project_receipt, receipt_sha256, resolve_manifest_entry
from .runtime import PRIMARY, settings
def diagnose_sources(root, *, platform=None, profile=None, config=None, primary=PRIMARY):
	if None is root or not str(root).strip():
		raise ValueError('An explicit project root is required')
	root, primary = (Path(root).expanduser().resolve(), Path(primary).resolve())
	if not root.is_dir():
		raise ValueError(f'Project root is not a directory: {root}')
	config = settings() if None is config else config
	if None is not platform and platform not in config.get('platforms', {}):
		raise ValueError(f'Unknown platform: {platform}')
	workspace = Path(config['workspace_root']).resolve()
	ancestry = [root]
	if root.is_relative_to(workspace):
		ancestry += [path for path in root.parents if path.is_relative_to(workspace)]
	sources, by_path, conflicts, native_declarations = ([], {}, [], [])
	def issue(code, path, message, severity='error'):
		conflicts.append({'code': code, 'path': str(path), 'message': message, 'severity': severity})
	def add(path, kind, via, *, required=False):
		path = Path(path).expanduser().resolve()
		key = str(path)
		if key in by_path:
			item = by_path[key]
			if via not in item['configured_via']:
				item['configured_via'].append(via)
			r = item
		else:
			item = {'path': key, 'kind': kind, 'configured_via': [via], 'exists': path.is_file(), 'injection': 'unknown'}
			by_path[key] = item
			sources.append(item)
			if not item['exists']:
				if required:
					issue('MISSING-SOURCE', path, 'An explicitly configured source does not exist')
				r = item
			else:
				try:
					raw = path.read_bytes()
					item.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
					if '.md' == path.suffix.casefold():
						meta = _frontmatter(path)
						item['frontmatter'] = meta
						item['trigger'] = meta.get('trigger', 'unspecified')
						item['version'] = meta.get('version')
						item['selection'] = 'declared-always-on' if 'always_on' == meta.get('trigger') else 'conditional-or-manual' if meta.get('trigger') else 'unspecified'
				except (OSError, ValueError, UnicodeError) as exc:
					issue('UNREADABLE-SOURCE', path, str(exc))
				r = item
		return r
	def referenced_paths(text):
		values = re.findall('\\]\\(<([^>]+)>\\)', text)
		values += re.findall('^\\s*-\\s+((?:[A-Za-z]:[/\\\\]|/)[^\\r\\n]+)', text, re.M)
		r = list(dict.fromkeys(values))
		return r
	def discover_references(path, kind):
		item = by_path[str(path.resolve())]
		if not item.get('exists'):
			return
		try:
			for ref in referenced_paths(path.read_text(encoding='utf-8-sig')):
				target = Path(ref)
				if not target.is_absolute():
					target = path.parent / target
				if target.suffix.casefold() in ('.md', '.toml', '.json'):
					add(target, kind, str(path), required=True)
		except (OSError, UnicodeError) as exc:
			issue('UNREADABLE-REFERENCE', path, str(exc))
	def inspect_native(native, via, *, scope=None, profile_name=None):
		item = add(native, 'native-codex-config', via)
		if profile_name:
			item['configured_profile'] = profile_name
		if not item['exists']:
			return
		try:
			data = tomllib.loads(native.read_text(encoding='utf-8-sig'))
			instructions = data.get('developer_instructions')
			item['developer_instructions_configured'] = bool(instructions)
			item['project_doc_fallback_filenames'] = data.get('project_doc_fallback_filenames', [])
			if not isinstance(item['project_doc_fallback_filenames'], list):
				raise ValueError('project_doc_fallback_filenames must be a list')
			if None is not instructions and (not isinstance(instructions, str)):
				raise ValueError('developer_instructions must be a string')
			if None is not instructions:
				item['developer_instructions_sha256'] = hashlib.sha256(instructions.encode()).hexdigest()
				native_declarations.append(item)
			for ref in referenced_paths(instructions or ''):
				add(Path(ref), 'native-loader-reference', str(native), required=True)
			if None is not scope:
				for filename in item['project_doc_fallback_filenames']:
					if not isinstance(filename, str) or Path(filename).name != filename:
						issue('UNSUPPORTED-DOC-SELECTOR', native, 'Fallback document name is not a simple filename')
						continue
					candidate = scope / filename
					if candidate.is_file():
						add(candidate, 'native-project-document', str(native))
		except (OSError, ValueError, UnicodeError, TypeError) as exc:
			issue('INVALID-NATIVE-CONFIG', native, str(exc))
	add(primary / 'runtime.json', 'canonical-runtime', 'runtime.PRIMARY', required=True)
	for path in sorted((primary / 'rules').glob('*.md')):
		add(path, 'canonical-rule', 'runtime.PRIMARY')
	for path in sorted((primary / 'skills').glob('*/SKILL.md')):
		add(path, 'canonical-skill', 'runtime.PRIMARY')
	for name in [platform] if platform else config.get('platforms', {}):
		add(primary / 'platforms' / f'{name}.md', 'platform-adapter', 'runtime.platforms')
	homes = config.get('platforms', {}).get('codex', {}).get('homes', {})
	if None is not profile and profile not in homes:
		raise ValueError('Unknown configured Codex profile')
	if platform in (None, 'codex'):
		for name in [profile] if profile else homes:
			inspect_native(Path(homes[name]).expanduser().resolve() / 'config.toml', f'runtime.platforms.codex.homes.{name}', profile_name=name)
	for scope in reversed(ancestry):
		agents = scope / '.agents'
		for path in sorted((agents / 'rules').glob('*.md')):
			add(path, 'local-rule', f'project-discovery:{scope}')
		for path in sorted((agents / 'skills').glob('*/SKILL.md')):
			add(path, 'local-skill', f'project-discovery:{scope}')
			discover_references(path, 'skill-reference')
		for category in DISCOVERY_KINDS:
			manifest = agents / f'{category}.json'
			item = add(manifest, f'{category}-manifest', f'optional-discovery:{scope}')
			if not item['exists']:
				continue
			try:
				data = load_discovery_manifest(manifest, missing_ok=False)
				if data.get('inherits'):
					issue('UNRESOLVED-INHERITANCE', manifest, 'Manifest inheritance needs platform-specific resolution; no loading is inferred', 'warning')
				for entry in data.get('entries', []):
					target, has_extra = resolve_manifest_entry(agents, entry)
					if None is target:
						issue('UNSUPPORTED-SELECTOR', manifest, 'Entry has no path; selector cannot be resolved')
						continue
					if has_extra:
						issue('CONDITIONAL-SOURCE', manifest, f'Additional selector fields for {target}; applicability is unknown', 'warning')
					if not target.is_dir():
						add(target, f'configured-{category}', str(manifest), required=True)
					else:
						pattern = '*.md' if 'rules' == category else 'SKILL.md' if 'skills' == category else '*'
						for path in sorted(target.rglob(pattern)):
							if path.is_file():
								add(path, f'configured-{category}', str(manifest), required=True)
			except (OSError, ValueError, UnicodeError) as exc:
				issue('INVALID-MANIFEST', manifest, str(exc))
		native = scope / '.codex/config.toml'
		inspect_native(native, f'optional-discovery:{scope}', scope=scope)
		for filename in ('AGENTS.md', 'AGENTS.override.md'):
			if (scope / filename).is_file():
				add(scope / filename, 'native-project-document', f'optional-discovery:{scope}')
		receipt_path = scope / 'ꘖ/data/native-config.json'
		receipt_item = add(receipt_path, 'projection-receipt', f'optional-discovery:{scope}')
		if receipt_item['exists']:
			try:
				_, _, receipt = load_project_receipt(receipt_path, by_path=True, error_message='Projection receipt must be an object')
				for path, expected in receipt.items():
					projection = add(Path(path), 'native-projection', str(receipt_path), required=True)
					projection['projection'] = 'matches-receipt' if projection.get('sha256') == receipt_sha256(expected) else 'differs-from-receipt'
					if 'matches-receipt' != projection['projection']:
						issue('PROJECTION-DRIFT', path, 'Projection differs from its publication receipt; no file was changed')
			except (OSError, ValueError, UnicodeError) as exc:
				issue('INVALID-RECEIPT', receipt_path, str(exc))
	canonical_rules = {Path(item['path']).name: item for item in sources if 'canonical-rule' == item['kind']}
	for item in sources:
		canonical = canonical_rules.get(Path(item['path']).name)
		if 'local-rule' == item['kind'] and canonical and (item.get('sha256') != canonical.get('sha256')):
			item['canonical'] = canonical['path']
			issue('POLICY-DIVERGENCE', item['path'], 'Local bytes differ from the same-named canonical rule; compare intent and precedence explicitly', 'warning')
	named_skills = {}
	for item in sources:
		if 'skill' not in item['kind'] or not item.get('exists'):
			continue
		name = item.get('frontmatter', {}).get('name')
		if name:
			named_skills.setdefault(name, []).append(item)
	for name, candidates in named_skills.items():
		for candidate in candidates:
			if 'local-skill' != candidate['kind']:
				continue
			references = [value for value in candidates if candidate['path'] in value['configured_via']]
			canonical = [value for value in candidates if 'canonical-skill' == value['kind']]
			if canonical and candidate.get('sha256') != canonical[0].get('sha256') and (not any((ref['path'] == canonical[0]['path'] for ref in references))):
				issue('SKILL-DIVERGENCE', candidate['path'], f'Skill {name} has a separate local body instead of a reference to its canonical source', 'warning')
	local_native = [item for item in native_declarations if not item.get('configured_profile')]
	if len(local_native) > 1:
		issue('NATIVE-KEY-OVERRIDE', local_native[-1]['path'], 'Multiple workspace/project developer_instructions keys exist; selected platform resolution is not proven', 'warning')
	global_native = [item for item in native_declarations if item.get('configured_profile')]
	if len({item['developer_instructions_sha256'] for item in global_native}) > 1:
		issue('PROFILE-INSTRUCTIONS-DIFFER', primary, 'Configured profile instructions differ; they are separate candidates, not combined effective instructions', 'warning')
	fingerprint = hashlib.sha256(json.dumps(sorted(((item['path'], item.get('sha256')) for item in sources)), ensure_ascii=False).encode()).hexdigest()
	return {'schema_version': 1, 'root': str(root), 'workspace_root': str(workspace), 'canonical': str(primary), 'platform': platform, 'selected_profile': profile, 'sources': sources, 'configuration_sha256': fingerprint, 'conflicts': conflicts, 'valid': not any(('error' == item['severity'] for item in conflicts)), 'platform_injection': {'status': 'unknown', 'detail': 'Configured paths and disk versions are observable; actual platform injection and model reading are not proven by this diagnostic'}}
