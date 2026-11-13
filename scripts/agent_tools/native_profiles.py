# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib
import uuid
from .configuration import DISCOVERY_KINDS as KINDS, _frontmatter, _loader, has_linked_ancestor, is_linked_path, load_discovery_manifest, load_project_receipt, receipt_sha256, replace_managed_block, resolve_manifest_entry, store_content_backup
from .runtime import PRIMARY, settings
from .storage import create_bytes, data_dir_for, locked, replace_bytes
ISSUE = 'https://github.com/dmitry-ai/harness/issues/35'
START = '<!-- harness:native-loader:start -->'
END = '<!-- harness:native-loader:end -->'
PURPOSES = {'AA': 'Independent substantive review of the five stages and KB consistency.', 'AF': 'Collection and extraction of evidence for an assigned question.'}
_linked = is_linked_path
_linked_ancestor = has_linked_ancestor
def _absolute(path):
	return Path(os.path.abspath(path))
def _hash(data):
	return hashlib.sha256(data).hexdigest()
def _json(data):
	return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def _configuration(primary):
	path = Path(primary) / 'runtime.json'
	return settings(path) if path.is_file() else settings()
def _exists(path):
	return os.path.lexists(path)
def _same_path(first, second):
	return Path(first).resolve() == Path(second).resolve()
def _normalized(text):
	return text.replace('\r\n', '\n').replace('/scripts/upwork_project.py', '/scripts/harness.py').replace('via upwork_project.py git-read', 'via harness.py git-read').replace('run upwork_project.py build-native', 'run harness.py build-native').strip()
def _skills(primary):
	r = {}
	for path in sorted((Path(primary) / 'skills').glob('*/SKILL.md')):
		metadata = _frontmatter(path)
		if not metadata.get('name') or not metadata.get('description'):
			raise ValueError(f'Shared skill needs name and description: {path}')
		r[path.parent.name] = (path, metadata)
	return r
def _role_values(primary):
	config = _configuration(primary)['platforms']['codex']
	values = [(role, config['roles'][role]['agent'], PURPOSES[role], config['roles'][role]) for role in ('AA', 'AF') if role in config['roles']]
	if any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name) for _, name, _, _ in values) or len({name for _, name, _, _ in values}) != len(values):
		raise ValueError('Native role identifiers must be distinct safe filenames')
	return values
def _model_fields(primary, role):
	config = _configuration(primary)['platforms']['codex']
	value = config['roles'][role]
	return '' if 'parent' == config.get('subagents', {}).get('selection') or value.get('selection') in ('parent', 'inherit') else f"model = {json.dumps(value['model'])}\nmodel_reasoning_effort = {json.dumps(value['effort'])}\n"
def shared_native_outputs(primary=PRIMARY):
	primary = Path(primary).resolve()
	r = {primary / f'platforms/antigravity/{kind}.json': _json({'entries': [{'path': (primary / kind).as_posix()}]}).decode('utf-8') for kind in KINDS}
	bootstrap = primary / 'platforms/codex/AGENTS.md'
	r[bootstrap] = f'# Harness: Codex\n\n<!-- Generated from canonical rules; {ISSUE} -->\n\n' + _loader(primary) + '\n'
	for role, name, purpose, _ in _role_values(primary):
		instructions = f'Role: {role}.  \n{purpose}  \nRead and execute the shared Codex bootstrap before work, including all mandatory rule sources: {bootstrap.as_posix()}  \nAlso read the worker protocol: {(primary / "agents/worker.md").as_posix()}  '
		r[primary / f'platforms/codex/agents/{name}.toml'] = f'# Generated from runtime.json and agents/worker.md; do not edit.\n# {ISSUE}\nname = {json.dumps(name)}\ndescription = {json.dumps(purpose)}\n' + _model_fields(primary, role) + f'developer_instructions = {json.dumps(instructions)}\n'
	flash = _configuration(primary)['platforms']['antigravity']['roles']['AF']
	r[primary / 'agents/af-worker.md'] = f'---\nname: af-worker\ndescription: "Extracts and verifies Upwork evidence for an assigned question."\nmodel: {flash["tier"]}\nsubagent: true\nmainAgent: false\n---\nRead the shared worker protocol: {(primary / "agents/worker.md").as_posix()}  \nEnvironment: Antigravity.  \nFollow the platform protocol and runtime.json; the configured tier does not prove the exact model.  \n'
	return r
def _legacy_skill(name, primary):
	path = Path(primary) / f'skills/{name}/SKILL.md'
	description = _frontmatter(path).get('description', '')
	if 'upwork-init' == name:
		description = 'Creates a project workspace and performs the full analysis of an Upwork job post; resumes it after an interruption.'
	elif 'upwork-cleanup' == name:
		description = 'Cleans up empty Upwork projects older than 72 hours in Antigravity and Codex while preserving on-disk history.'
	if re.search(':\\s|\\s#|^[\\\'"\\[{>|*&!%@`]', description):
		description = json.dumps(description, ensure_ascii=False)
	r = f'---\nname: {name}\ndescription: {description}\n---\nRead and execute the shared skill [SKILL.md](<{path.as_posix()}>).  \n'
	if 'upwork-init' == name:
		r += 'Determine the active UI platform from the conversation and use the corresponding platform adapter of the shared skill.  \n'
	elif 'upwork-cleanup' == name:
		r += 'Determine the active UI platform from the conversation; a normal run cleans both platforms.  \n'
	return r
def _legacy_role(primary, role, name, purpose):
	instructions = f'Role: {role}.  \n{purpose}  \n' + _loader(Path(primary)) + f'\nAlso read the worker protocol: {(Path(primary) / "agents/worker.md").as_posix()}  '
	return f'# Generated from runtime.json and agents/worker.md; do not edit.\nname = {json.dumps(name)}\ndescription = {json.dumps(purpose)}\n' + _model_fields(primary, role) + f'developer_instructions = {json.dumps(instructions, ensure_ascii=False)}\n'
def _compact_loader(primary):
	bootstrap = Path(primary) / 'platforms/codex/AGENTS.md'
	return f'{START}\n# Codex: Harness\n\nRead and execute the shared Codex bootstrap [AGENTS.md](<{bootstrap.as_posix()}>) before doing any work.  \nIt applies in every new chat and every child subagent.  \n{END}\n'
def _profile_agents(text, primary, owned):
	wanted = _compact_loader(primary)
	marker = '# Codex: Upwork\n'
	plain = text.replace('\r\n', '\n')
	if START in text or END in text:
		r = replace_managed_block(text, wanted.rstrip('\n'), start_marker=START, end_marker=END, expected_sha256=owned.get('managed_block_sha256'), malformed_message='Malformed Harness instruction block; personal instructions preserved', edited_message='Harness instruction block was edited; personal instructions preserved')
	elif marker not in plain:
		separator = '' if not text or text.endswith('\n\n') else '\n' if text.endswith('\n') else '\n\n'
		r = text + separator + wanted
	else:
		if 1 != plain.count(marker):
			raise ValueError('Ambiguous legacy instruction blocks; personal instructions preserved')
		legacy = f'# Codex: Upwork\n\n<!-- Generated from {Path(primary).as_posix()}; run harness.py build-native to update. -->\n\n' + _loader(Path(primary)) + '\n'
		if _normalized(plain[plain.index(marker):]) != _normalized(legacy):
			raise ValueError('Legacy instruction block differs from its exact generated template; preserved')
		match = re.search('(?m)^# Codex: Upwork\\r?\\n', text)
		r = text[:match.start()] + wanted
	return r
def _state_path(primary):
	return data_dir_for(primary) / 'native-profiles' / 'ownership.json'
def _load_state(primary):
	path = _state_path(primary)
	data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'shared': {}, 'profiles': {}, 'backups': {}}
	if not isinstance(data, dict) or data.get('schema_version') != 1 or any(not isinstance(data.get(key, {}), dict) for key in ('shared', 'profiles', 'backups')):
		raise ValueError('Native profile ownership receipt is malformed; preserved')
	return data
class _ApplyFailure(ValueError):
	def __init__(self, error, rollback, backups, recovery=None):
		super().__init__(f'{error}; rollback {rollback["status"]}' + (f'; recovery receipt: {recovery}' if recovery else ''))
		self.rollback, self.backups, self.recovery = (rollback, backups, recovery)
class _ManagedLink:
	def __init__(self, path, target, kind, *, label='skill', legacy_dir=False):
		self.path = _absolute(path)
		self.target = target if isinstance(target, str) and kind in ('directory-junction', 'directory-symlink') else Path(target)
		self.kind = kind
		self.label = label
		self.legacy_dir = legacy_dir
	def backup_payload(self):
		return _json(self.identity_dict())
	def create(self, primary):
		if _linked_ancestor(self.path, include_self=False):
			raise ValueError(f'Linked {self.label} parent directory appeared before creation; preserved: {self.path}')
		if self.legacy_dir:
			self.path.rmdir()
		if 'file-symlink' == self.kind:
			_file_link(self.target, self.path, primary)
		else:
			_directory_link(self.target, self.path, primary)
	def identity_dict(self):
		target = os.readlink(self.path) if 'file-symlink' == self.kind else str(self.target)
		return {'kind': self.kind, 'target': target}
	def readonly_issue(self, *, retired=False):
		if retired:
			message = 'Obsolete owned role file link needs retirement' if 'file-symlink' == self.kind else 'Obsolete owned skill directory link needs retirement'
		else:
			message = f'Shared role file link is missing: {self.target}' if 'file-symlink' == self.kind else f'Shared skill directory link is missing: {self.target}'
		return {'file': str(self.path), 'message': message}
	def remove_created(self):
		_remove_link(self.path, self.target)
	def restore_retired(self, primary):
		if 'file-symlink' == self.kind:
			if _exists(self.path) or _linked_ancestor(self.path, include_self=False):
				raise ValueError('Obsolete role destination changed before rollback; preserved')
			_file_link(self.target, self.path, primary)
		else:
			if _exists(self.path) or _linked(self.path) or _linked_ancestor(self.path, include_self=False):
				raise ValueError('Obsolete skill destination changed before rollback; preserved')
			_restore_directory_link(self.path, self.identity_dict(), primary)
			self.verify_retired()
	def retire(self):
		if 'file-symlink' == self.kind:
			_remove_link(self.path, self.target)
		else:
			_retire_directory_link(self.path, self.identity_dict())
	def verify_before_create(self, files):
		if _linked_ancestor(self.path, include_self=False):
			raise ValueError(f'Linked {self.label} parent directory appeared during migration; preserved: {self.path}')
		if 'file-symlink' == self.kind:
			if _exists(self.path) and (self.path not in files or None is not files[self.path][1]):
				raise ValueError(f'Role destination appeared during migration; preserved: {self.path}')
		elif self.legacy_dir:
			if not self.path.is_dir() or ['SKILL.md'] != sorted((p.name for p in self.path.iterdir())):
				raise ValueError(f'Legacy skill directory changed during migration; preserved: {self.path}')
		elif _exists(self.path):
			raise ValueError(f'Skill destination appeared during migration; preserved: {self.path}')
	def verify_created(self):
		if 'file-symlink' == self.kind:
			target = Path(self.target)
			if not self.path.is_symlink() or not self.path.is_file() or (not _same_path(self.path, target)) or (not self.path.samefile(target)) or (self.path.read_bytes() != target.read_bytes()):
				raise ValueError(f'New role link failed read-back verification: {self.path}')
		elif not self.path.is_dir() or (not _same_path(self.path, self.target)):
			raise ValueError(f'New skill link failed read-back verification: {self.path}')
	def verify_retired(self):
		if 'file-symlink' != self.kind:
			_verify_retired_directory_link(self.path, self.identity_dict())
		elif _linked_ancestor(self.path, include_self=False) or not self.path.is_symlink() or (not _same_path(self.path, self.target)):
			raise ValueError(f'Obsolete role link changed during migration; preserved: {self.path}')
class _Plan:
	def __init__(self):
		self.details = {}
		self.files = {}
		self.issues = []
		self.managed_links = {}
		self.profiles = {}
		self.removed_shared = set()
		self.retired_links = {}
		self.shared = {}
	def file(self, path, after):
		path = _absolute(path)
		if _linked_ancestor(path):
			self.issue(path, 'Linked native configuration preserved')
		elif path.exists() and (not path.is_file()):
			self.issue(path, 'Expected a regular configuration file; preserved')
		else:
			before = path.read_bytes() if path.exists() else None
			if before != after:
				self.files[path] = (before, after)
	def issue(self, path, message):
		self.issues.append({'file': str(path), 'message': message})
	def readonly_issues(self):
		active = [link.readonly_issue() for link in self.managed_links.values()]
		retired = [link.readonly_issue(retired=True) for link in self.retired_links.values()]
		return self.issues + [{'file': str(path), 'message': 'Native connection is missing, stale or requires owned legacy retirement'} for path in self.files] + active + retired
def _shared_plan(plan, primary, state):
	for path, text in shared_native_outputs(primary).items():
		if _linked_ancestor(path):
			plan.issue(path, 'Linked shared native definition preserved')
			continue
		actual = path.read_bytes() if path.is_file() else None
		payload = text.encode('utf-8')
		if actual != payload and None is not actual and (state.get('shared', {}).get(str(path)) != _hash(actual)):
			plan.issue(path, 'Shared native definition was modified without ownership; preserved')
			continue
		plan.file(path, payload)
		plan.shared[str(path)] = _hash(payload)
def _role_identity(path, target, home, primary):
	path, target = (_absolute(path), _absolute(target))
	return path.parent == _absolute(home) / 'agents' and '.toml' == path.suffix and bool(re.fullmatch('[A-Za-z0-9_-]+', path.stem)) and (target == _absolute(primary) / 'platforms/codex/agents' / path.name)
def _retire_profile_roles(plan, profile, previous, home, primary, state):
	wanted = {_absolute(home) / f'agents/{name}.toml' for _, name, _, _ in _role_values(primary)}
	prior = previous.get('role_targets', {})
	if not isinstance(prior, dict):
		plan.issue(home / 'agents', 'Previous role link ownership is malformed; preserved')
	else:
		for raw_path, raw_target in prior.items():
			if not isinstance(raw_path, str) or not isinstance(raw_target, str) or (not _role_identity(raw_path, raw_target, home, primary)):
				plan.issue(home / 'agents', 'Previous role link ownership is outside its exact managed paths; preserved')
				continue
			path, target = (_absolute(raw_path), _absolute(raw_target))
			if path not in wanted:
				if _linked_ancestor(path, include_self=False):
					plan.issue(path, 'Linked obsolete role parent directory preserved')
				elif _exists(path) and (not path.is_symlink() or (not _same_path(path, target))):
					plan.issue(path, 'Obsolete managed role link changed; preserved')
				elif _exists(path) and target.is_file() and (state.get('shared', {}).get(str(target)) != _hash(target.read_bytes())):
					plan.issue(target, 'Obsolete shared role definition changed; preserved')
				else:
					if _exists(path):
						plan.retired_links[path] = _ManagedLink(path, target, 'file-symlink', label='obsolete role')
					if str(path) not in profile['retired']:
						profile['retired'].append(str(path))
def _directory_link_identity(path):
	return {'kind': 'directory-junction' if bool(getattr(path, 'is_junction', lambda: False)()) else 'directory-symlink', 'target': os.readlink(path)}
def _verify_retired_directory_link(path, identity):
	if _linked_ancestor(path, include_self=False) or not _linked(path) or _directory_link_identity(path) != identity:
		raise ValueError(f'Obsolete skill link changed during migration; preserved: {path}')
def _retire_directory_link(path, identity):
	_verify_retired_directory_link(path, identity)
	path.rmdir() if 'directory-junction' == identity['kind'] else path.unlink()
def _retire_profile_skills(plan, profile, previous, home, primary, skills):
	wanted = {_absolute(home) / 'skills' / name for name in skills}
	prior = previous.get('links', {})
	if not isinstance(prior, dict):
		plan.issue(home / 'skills', 'Previous link ownership is malformed; preserved')
	else:
		for raw_path, raw_target in prior.items():
			if not isinstance(raw_path, str) or not isinstance(raw_target, str):
				plan.issue(home / 'skills', 'Previous link ownership has invalid path types; preserved')
				continue
			path, target = (_absolute(raw_path), _absolute(raw_target))
			if path.parent != _absolute(home) / 'skills':
				if raw_path not in previous.get('role_targets', {}):
					profile['links'].setdefault(raw_path, raw_target)
			elif path not in wanted:
				if target != _absolute(primary) / 'skills' / path.name:
					plan.issue(path, 'Obsolete skill link ownership is outside its exact managed target; preserved')
				elif _linked_ancestor(path, include_self=False):
					plan.issue(path, 'Linked obsolete skill parent directory preserved')
				elif (_exists(path) or _linked(path)) and (not _linked(path) or (not _same_path(path, target))):
					plan.issue(path, 'Obsolete managed skill link changed; preserved')
				else:
					if _exists(path) or _linked(path):
						identity = _directory_link_identity(path)
						plan.retired_links[path] = _ManagedLink(path, identity['target'], identity['kind'], label='obsolete skill')
					if str(path) not in profile['retired']:
						profile['retired'].append(str(path))
def _retire_shared_roles(plan, primary, state):
	profiles = {**state.get('profiles', {}), **plan.profiles}
	if not any(('codex' == profile.get('platform') and 'file-links' != profile.get('role_registration') for profile in profiles.values())):
		referenced = {_absolute(target) for profile in profiles.values() for target in profile.get('role_targets', {}).values() if isinstance(target, str)}
		for raw_path, owned in state.get('shared', {}).items():
			path = _absolute(raw_path)
			if str(path) in plan.shared or path.parent != _absolute(primary) / 'platforms/codex/agents' or '.toml' != path.suffix or (not re.fullmatch('[A-Za-z0-9_-]+', path.stem)) or (path in referenced):
				continue
			if _linked_ancestor(path) or (path.exists() and (not path.is_file() or _hash(path.read_bytes()) != owned)):
				plan.issue(path, 'Obsolete shared role definition changed or is linked; preserved')
				continue
			plan.file(path, None)
			plan.removed_shared.add(str(path))
def _manifest(payload, kind, config, primary):
	if not isinstance(payload, dict):
		raise ValueError('Discovery manifest must be a JSON object; preserved')
	r = deepcopy(payload)
	entries, inherits = (r.get('entries', []), r.get('inherits', []))
	if not isinstance(entries, list) or not isinstance(inherits, list):
		raise ValueError('Discovery manifest entries/inherits must be lists; preserved')
	legacy, shared = (Path(primary) / kind, Path(primary) / f'platforms/antigravity/{kind}.json')
	remaining = []
	for entry in entries:
		source, has_extra = resolve_manifest_entry(config, entry)
		if None is source or (not _same_path(source, legacy)):
			remaining.append(entry)
		elif has_extra:
			raise ValueError('Filtered legacy Harness discovery entry needs explicit reconciliation; preserved')
	if 'entries' in r or remaining:
		r['entries'] = remaining
	already = False
	for entry in inherits:
		source, has_extra = resolve_manifest_entry(config, entry)
		if None is not source and _same_path(source, shared):
			if has_extra:
				raise ValueError('Filtered inherited Harness manifest needs explicit reconciliation; preserved')
			already = True
	if not already:
		r['inherits'] = [*inherits, {'path': shared.as_posix()}]
	return r
def _profile_state(state, name, path):
	previous = state.get('profiles', {}).get(name, {})
	return previous if previous.get('path') == str(_absolute(path)) else {}
def _antigravity_plan(plan, name, config, primary, state):
	from .upwork_project import canonical_global_hooks
	config = _absolute(config)
	previous = _profile_state(state, name, config)
	profile = {'platform': 'antigravity', 'path': str(config), 'files': {}, 'hook_hashes': {}}
	plan.details[name] = {'added_entries': [], 'added_hooks': []}
	for kind in KINDS:
		path = config / f'{kind}.json'
		try:
			payload = load_discovery_manifest(path, entries_error='Discovery manifest entries/inherits must be lists; preserved', check_inherits=True)
			wanted = _json(_manifest(payload, kind, config, primary))
			plan.file(path, wanted)
			if path in plan.files:
				plan.details[name]['added_entries'].append(kind)
			profile['files'][str(path)] = _hash(wanted)
		except (ValueError, OSError) as exc:
			plan.issue(path, str(exc))
	path = config / 'hooks.json'
	try:
		hooks = json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
		if not isinstance(hooks, dict):
			raise ValueError('hooks.json must be a JSON object; preserved')
		for hook, desired in canonical_global_hooks(primary).items():
			if hook in hooks and hooks[hook] != desired and (previous.get('hook_hashes', {}).get(hook) != _hash(_json(hooks[hook]))):
				plan.issue(path, f'Existing hook {hook} differs from its owned definition; preserved')
			else:
				if hooks.get(hook) != desired:
					plan.details[name]['added_hooks'].append(hook)
				hooks[hook] = desired
			profile['hook_hashes'][hook] = _hash(_json(desired))
		wanted = _json(hooks)
		plan.file(path, wanted)
		profile['files'][str(path)] = _hash(wanted)
	except (ValueError, OSError) as exc:
		plan.issue(path, str(exc))
	plan.profiles[name] = profile
def _legacy_role_config(text, definitions):
	data = tomllib.loads(text) if text.strip() else {}
	agents = data.get('agents', {})
	if not isinstance(agents, dict):
		raise ValueError('agents must be a TOML table; preserved')
	additional = []
	for name, desired in definitions.items():
		if name not in agents:
			additional.append(f'[agents.{json.dumps(name)}]\ndescription = {json.dumps(desired["description"])}\nconfig_file = {json.dumps(desired["config_file"])}\n')
		elif agents[name] != desired:
			raise ValueError(f'Existing role {name} differs from shared native role configuration; preserved')
	if additional:
		text += ('' if not text or text.endswith('\n\n') else '\n' if text.endswith('\n') else '\n\n') + f'# Shared Harness roles; {ISSUE}\n' + '\n'.join(additional)
		tomllib.loads(text)
	return text
def _role_config(text, definitions, previous, state, path, primary):
	data = tomllib.loads(text) if text.strip() else {}
	agents = data.get('agents', {})
	if not isinstance(agents, dict):
		raise ValueError('agents must be a TOML table; preserved')
	marker = f'# Shared Harness roles; {ISSUE}\n'
	if not any((name in agents for name in definitions)):
		if marker in text:
			raise ValueError('Former role configuration needs reconciliation for renamed or removed roles; preserved')
		r = text
	else:
		if 1 != text.count(marker):
			raise ValueError('Existing same-name role tables are not the exact owned installer block; preserved')
		owned = previous.get('files', {}).get(str(path))
		if not isinstance(owned, str):
			raise ValueError('Former role configuration has no ownership proof; preserved')
		index = text.index(marker)
		originals = ['', text[:index]]
		backup_root = data_dir_for(primary) / 'native-profiles/backups'
		for key, saved in state.get('backups', {}).items():
			if not key.startswith(str(path) + ':') or (not isinstance(saved, str)):
				continue
			backup = Path(saved)
			if not backup.resolve().is_relative_to(backup_root.resolve()) or (not backup.is_file()):
				continue
			payload = backup.read_bytes()
			if _hash(payload) == key.rsplit(':', 1)[-1]:
				originals.append(payload.decode('utf-8-sig'))
		blocks = set()
		for original in originals:
			try:
				generated = _legacy_role_config(original, definitions)
				offset = generated.find(marker, len(original))
				if offset >= 0 and _hash(generated.encode('utf-8')) == owned:
					blocks.add(generated[offset:])
			except (ValueError, KeyError):
				continue
		matching = [block for block in blocks if text.startswith(block, index)]
		if 1 != len(matching):
			raise ValueError('Former role configuration differs from its exact owned generated block; preserved')
		r = text[:index] + text[index + len(matching[0]):]
		remaining = tomllib.loads(r) if r.strip() else {}
		if any((name in remaining.get('agents', {}) for name in definitions)):
			raise ValueError('Same-name role tables outside the owned installer block are preserved')
	return r
def _plan_codex_link(plan, profile, link, active_valid, active_error, retire_path, legacy_valid, legacy_error):
	path = link.path
	profile['links'][str(path)] = str(link.target)
	profile['retired'] = [item for item in profile['retired'] if str(path) != item]
	if _linked_ancestor(path, include_self=False):
		plan.issue(path, f'Linked {link.label} parent directory preserved')
	elif _linked(path):
		if not active_valid():
			plan.issue(path, active_error)
	elif not _exists(path):
		plan.managed_links[path] = link
	elif not legacy_valid():
		plan.issue(path, legacy_error)
	else:
		link.legacy_dir = 'directory' == link.kind
		plan.file(retire_path, None)
		plan.managed_links[path] = link
def _codex_plan(plan, name, home, primary, state):
	home = _absolute(home)
	previous = _profile_state(state, name, home)
	profile = {'platform': 'codex', 'path': str(home), 'files': {}, 'links': {}, 'retired': list(previous.get('retired', [])), 'role_registration': 'file-links', 'role_targets': {}}
	_retire_profile_roles(plan, profile, previous, home, primary, state)
	skills = _skills(primary)
	_retire_profile_skills(plan, profile, previous, home, primary, skills)
	path = home / 'AGENTS.md'
	try:
		text = path.read_bytes().decode('utf-8') if path.is_file() else ''
		wanted = _profile_agents(text, primary, previous).encode('utf-8')
		plan.file(path, wanted)
		profile['files'][str(path)] = _hash(wanted)
		profile['managed_block_sha256'] = _hash(_compact_loader(primary).rstrip('\n').encode('utf-8'))
	except (ValueError, OSError) as exc:
		plan.issue(path, str(exc))
	definitions = {agent: {'description': purpose, 'config_file': (Path(primary) / f'platforms/codex/agents/{agent}.toml').as_posix()} for _, agent, purpose, _ in _role_values(primary)}
	path = home / 'config.toml'
	try:
		actual = path.read_bytes() if path.is_file() else b''
		wanted = _role_config(actual.decode('utf-8-sig'), definitions, previous, state, path, primary).encode('utf-8')
		if actual.startswith(b'\xef\xbb\xbf'):
			wanted = b'\xef\xbb\xbf' + wanted
		if actual or wanted or path.exists():
			plan.file(path, wanted)
			profile['files'][str(path)] = _hash(wanted)
	except (ValueError, OSError) as exc:
		plan.issue(path, str(exc))
	for skill, (source, _) in skills.items():
		skill_path, skill_target = (home / 'skills' / skill, source.parent.resolve())
		wrapper = skill_path / 'SKILL.md'
		_plan_codex_link(plan, profile, _ManagedLink(skill_path, skill_target, 'directory', label='skill'), lambda p=skill_path, t=skill_target: p.is_dir() and _same_path(p, t), 'Skill link points to a different or missing directory; preserved', wrapper, lambda p=skill_path, w=wrapper, s=skill: p.is_dir() and ['SKILL.md'] == sorted((c.name for c in p.iterdir())) and (not _linked(w)) and w.is_file() and (_normalized(w.read_text(encoding='utf-8-sig')) == _normalized(_legacy_skill(s, primary))), 'Existing skill directory is not an exact generated wrapper; preserved')
	for role, agent, purpose, _ in _role_values(primary):
		role_path, role_target = (home / f'agents/{agent}.toml', Path(primary) / f'platforms/codex/agents/{agent}.toml')
		profile['role_targets'][str(_absolute(role_path))] = str(role_target)
		_plan_codex_link(plan, profile, _ManagedLink(role_path, role_target, 'file-symlink', label='role'), lambda p=role_path, t=role_target: p.is_symlink() and p.is_file() and _same_path(p, t) and (p.read_bytes() == t.read_bytes()), 'Role link points to a different or missing file; preserved', role_path, lambda p=role_path, rl=role, ag=agent, pr=purpose: p.is_file() and _normalized(p.read_text(encoding='utf-8-sig')) == _normalized(_legacy_role(primary, rl, ag, pr)), 'Legacy role differs from its exact generated template; preserved')
	plan.profiles[name] = profile
def _prepare_link_parent(path, label, action='creation'):
	if _linked_ancestor(path, include_self=False):
		raise ValueError(f'Linked {label} parent directory appeared before {action}; preserved: {path}')
	path.parent.mkdir(parents=True, exist_ok=True)
	if _linked_ancestor(path, include_self=False):
		raise ValueError(f'Linked {label} parent directory appeared before {action}; preserved: {path}')
def _directory_link(target, path, primary):
	_prepare_link_parent(path, 'skill')
	if 'nt' != os.name:
		path.symlink_to(target, target_is_directory=True)
	else:
		node = _configuration(primary)['platforms']['codex'].get('node', 'node')
		result = subprocess.run([node, '-e', "require('node:fs').symlinkSync(process.argv[1],process.argv[2],'junction')", str(target), str(path)], capture_output=True, text=True, timeout=15)
		if result.returncode:
			raise OSError(f'Directory junction creation failed: {result.stderr.strip()}')
def _file_link(target, path, primary):
	_prepare_link_parent(path, 'role')
	path.symlink_to(target, target_is_directory=False)
def _restore_directory_link(path, identity, primary):
	if 'directory-junction' == identity['kind']:
		_directory_link(identity['target'], path, primary)
	else:
		_prepare_link_parent(path, 'obsolete skill', 'restoration')
		path.symlink_to(identity['target'], target_is_directory=True)
def _remove_link(path, target):
	if _linked_ancestor(path, include_self=False) or not _linked(path) or (not _same_path(path, target)):
		raise ValueError(f'Created link changed before rollback; preserved: {path}')
	path.rmdir() if bool(getattr(path, 'is_junction', lambda: False)()) else path.unlink()
def _verify(plan):
	for path, (before, _) in plan.files.items():
		if _linked_ancestor(path) or (path.read_bytes() if path.is_file() else None) != before:
			raise ValueError(f'Configuration changed during migration; external edit preserved: {path}')
	for link in plan.managed_links.values():
		link.verify_before_create(plan.files)
	for link in plan.retired_links.values():
		link.verify_retired()
def _backup(primary, state, path, payload):
	backup, digest = store_content_backup(data_dir_for(primary) / 'native-profiles/backups', path, payload)
	state.setdefault('backups', {})[str(path) + ':' + digest] = str(backup)
	return str(backup)
def _rollback(plan, applied, created_links, retired_links, primary):
	issues, restored = ([], [])
	for link in reversed(created_links):
		try:
			link.remove_created()
			restored.append(str(link.path))
		except (ValueError, OSError, subprocess.SubprocessError) as exc:
			issues.append({'file': str(link.path), 'message': str(exc)})
	for path in reversed(applied):
		try:
			before, after = plan.files[path]
			if _linked_ancestor(path):
				raise ValueError('Linked path prevents rollback; backup retained')
			actual = path.read_bytes() if path.is_file() else None
			if actual != after:
				raise ValueError('Concurrent edit prevents rollback; backup retained')
			if None is before:
				path.unlink(missing_ok=True)
			else:
				replace_bytes(path, before)
			restored.append(str(path))
		except (ValueError, OSError, subprocess.SubprocessError) as exc:
			issues.append({'file': str(path), 'message': str(exc)})
	for link in reversed(retired_links):
		try:
			link.restore_retired(primary)
			restored.append(str(link.path))
		except (ValueError, OSError, subprocess.SubprocessError) as exc:
			issues.append({'file': str(link.path), 'message': str(exc)})
	return {'status': 'partial' if issues else 'complete', 'restored': restored, 'issues': issues}
def _apply(plan, primary, state):
	receipt = _state_path(primary)
	receipt_before = receipt.read_bytes() if receipt.exists() else None
	if None is not receipt_before and json.loads(receipt_before) != state:
		raise ValueError('Native ownership changed before migration; preserved')
	_verify(plan)
	updated = deepcopy(state)
	backups = [_backup(primary, updated, path, before) for path, (before, _) in plan.files.items() if None is not before]
	backups.extend((_backup(primary, updated, path, link.backup_payload()) for path, link in plan.retired_links.items()))
	_verify(plan)
	applied, created_links, retired_links = ([], [], [])
	try:
		for path, (before, after) in plan.files.items():
			if _linked_ancestor(path) or (path.read_bytes() if path.is_file() else None) != before:
				raise ValueError(f'Configuration changed before write; preserved: {path}')
			if None is after:
				path.unlink()
			else:
				replace_bytes(path, after)
			applied.append(path)
		for link in plan.retired_links.values():
			link.retire()
			retired_links.append(link)
		for link in plan.managed_links.values():
			link.create(primary)
			created_links.append(link)
			link.verify_created()
		for path, (_, after) in plan.files.items():
			if None is not after and path.read_bytes() != after:
				raise ValueError(f'Native configuration read-back differs: {path}')
		updated.setdefault('shared', {}).update(plan.shared)
		for path in plan.removed_shared:
			updated['shared'].pop(path, None)
		updated.setdefault('profiles', {}).update(plan.profiles)
		payload = _json(updated)
		if (receipt.read_bytes() if receipt.exists() else None) != receipt_before:
			raise ValueError('Native ownership changed during migration; preserved')
		if not receipt.exists() or receipt.read_bytes() != payload:
			replace_bytes(receipt, payload)
	except (ValueError, OSError, subprocess.SubprocessError) as exc:
		rollback = _rollback(plan, applied, created_links, retired_links, primary)
		recovery = None
		if 'partial' == rollback['status']:
			recovery = data_dir_for(primary) / 'native-profiles/recovery' / f'{uuid.uuid4().hex}.json'
			try:
				recovery.parent.mkdir(parents=True, exist_ok=True)
				create_bytes(recovery, _json({'schema_version': 1, 'error': str(exc), 'rollback': rollback, 'backups': updated.get('backups', {}), 'files': {str(path): {'before_sha256': _hash(before) if None is not before else None, 'after_sha256': _hash(after) if None is not after else None} for path, (before, after) in plan.files.items()}, 'created_links': {str(link.path): str(link.target) for link in created_links}, 'retired_links': {str(link.path): str(link.target) for link in retired_links if 'file-symlink' == link.kind}, 'retired_directory_links': {str(link.path): link.identity_dict() for link in retired_links if 'file-symlink' != link.kind}}))
			except OSError as recovery_error:
				rollback['issues'].append({'file': str(recovery), 'message': f'Recovery receipt could not be saved: {recovery_error}'})
				recovery = None
		raise _ApplyFailure(exc, rollback, backups, str(recovery) if recovery else None) from exc
	for path in applied:
		if None is plan.files[path][1]:
			parent = path.parent
			if 'SKILL.md' == path.name and 'skills' == parent.parent.name and ('.agents' == parent.parent.parent.name):
				if _linked(parent):
					continue
				try:
					parent.rmdir()
				except OSError:
					continue
				parent = parent.parent
			while parent.name in ('agents', '.codex', 'skills', '.agents') and parent.is_dir() and (not _linked(parent)):
				try:
					parent.rmdir()
				except OSError:
					break
				parent = parent.parent
	return {'written': [str(path) for path, (_, value) in plan.files.items() if None is not value], 'removed': [str(path) for path, (_, value) in plan.files.items() if None is value] + [str(path) for path in plan.retired_links], 'linked': [str(path) for path in plan.managed_links], 'backups': backups}
def _execute(plan, primary, state, *, check=False):
	issues = plan.readonly_issues() if check else plan.issues
	result = {'valid': not issues, 'issues': issues, 'profiles': deepcopy(plan.profiles), 'verification': 'filesystem-only', 'written': [], 'removed': [], 'linked': [], 'backups': []}
	if not issues and not check:
		try:
			result.update(_apply(plan, primary, state))
		except (ValueError, OSError, subprocess.SubprocessError) as exc:
			result['valid'] = False
			result['issues'].append({'file': str(primary), 'message': str(exc)})
			if isinstance(exc, _ApplyFailure):
				result.update(rollback=exc.rollback, backups=exc.backups, recovery_receipt=exc.recovery)
				result['issues'].extend(exc.rollback['issues'])
	for name, profile in result['profiles'].items():
		base = Path(profile['path'])
		local = [issue for issue in result['issues'] if _absolute(issue['file']).is_relative_to(base)]
		global_issues = [issue for issue in result['issues'] if not any(_absolute(issue['file']).is_relative_to(Path(item['path'])) for item in result['profiles'].values())]
		profile.update(config=str(base), valid=not local and not global_issues, issues=[*global_issues, *local], written=[path for path in result['written'] if _absolute(path).is_relative_to(base)], removed=[path for path in result['removed'] if _absolute(path).is_relative_to(base)], link_targets=profile.pop('links', {}), links=[path for path in result['linked'] if _absolute(path).is_relative_to(base)], **plan.details.get(name, {}))
	return result
def build_shared_native(primary=PRIMARY, *, check=False):
	primary = Path(primary).resolve()
	with nullcontext() if check else locked(data_dir_for(primary) / 'native-profiles/install.lock'):
		state, plan = _load_state(primary), _Plan()
		_shared_plan(plan, primary, state)
		_retire_shared_roles(plan, primary, state)
		return _execute(plan, primary, state, check=check)
def install_native_profiles(target_profiles=None, *, check=False, primary=PRIMARY, config_dirs=None, codex_homes=None):
	primary = Path(primary).resolve()
	config = _configuration(primary)
	gravity = {name: Path(home) / '.gemini/config' for name, home in config['platforms']['antigravity'].get('homes', {}).items()} if config_dirs is None else {name: Path(path) for name, path in config_dirs.items()}
	codex = {name: Path(home) for name, home in config['platforms']['codex'].get('homes', {}).items()} if codex_homes is None else {name: Path(path) for name, path in codex_homes.items()}
	if set(gravity) & set(codex):
		raise ValueError('Antigravity and Codex profile identifiers must be distinct')
	names = list(dict.fromkeys([*gravity, *codex] if target_profiles is None else target_profiles))
	if not names or any(name not in gravity and name not in codex for name in names):
		raise ValueError('Select existing target profile names from runtime.json')
	if len({_absolute(gravity[name] if name in gravity else codex[name]) for name in names}) != len(names):
		raise ValueError('Selected profile configuration directories must be distinct')
	with nullcontext() if check else locked(data_dir_for(primary) / 'native-profiles/install.lock'):
		state, plan = _load_state(primary), _Plan()
		_shared_plan(plan, primary, state)
		for name in names:
			if name in gravity:
				_antigravity_plan(plan, name, gravity[name], primary, state)
			else:
				_codex_plan(plan, name, codex[name], primary, state)
		_retire_shared_roles(plan, primary, state)
		return _execute(plan, primary, state, check=check)
def legacy_project_projection_paths(root, primary=PRIMARY):
	root = Path(root).resolve()
	paths = [root / f'.agents/skills/{name}/SKILL.md' for name in _skills(primary)] + [root / f'.codex/agents/{name}.toml' for _, name, _, _ in _role_values(primary)]
	return [path for path in paths if not _linked_ancestor(path)]
def retire_owned_project_projections(root, *, check=False, primary=PRIMARY):
	root, primary = (Path(root).resolve(), Path(primary).resolve())
	receipt, _, previous = load_project_receipt(root)
	with nullcontext() if check else locked(data_dir_for(primary) / 'native-profiles/install.lock'):
		state, plan, remaining = (_load_state(primary), _Plan(), deepcopy(previous))
		for path in legacy_project_projection_paths(root, primary):
			if path.is_file():
				if receipt_sha256(previous.get(str(path.resolve()))) != _hash(path.read_bytes()):
					plan.issue(path, 'Legacy project projection is edited or unowned; preserved')
				else:
					plan.file(path, None)
					remaining.pop(str(path.resolve()), None)
		if remaining != previous:
			plan.file(receipt, _json(remaining) if remaining else None)
		return _execute(plan, primary, state, check=check)
