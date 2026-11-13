# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify projection publishing, _ManagedLink link lifecycle, and .agents/*.json manifest helpers across native_profiles.py, configuration.py, upwork_project.py, and text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/71
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import tomllib
from .runtime import PRIMARY, settings, profile_name
from .storage import create_bytes, data_dir_for, locked, replace_bytes
DISCOVERY_KINDS = ('rules', 'skills', 'agents')
def _digest(data):
	return hashlib.sha256(data).hexdigest()
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
					config = root / '.codex/config.toml'
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
START = '<!-- upwork-init:instructions:start -->'
END = '<!-- upwork-init:instructions:end -->'
def _managed_block(value):
	return extract_managed_block(value)
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
def _native_config(root, instructions=None):
	config_path = root / '.codex/config.toml'
	actual = config_path.read_bytes() if config_path.exists() else None
	existing = actual.decode('utf-8') if None is not actual else ''
	_, _, receipt = load_project_receipt(root)
	owned = receipt.get(str(config_path), {})
	legacy = root / 'CODEX.md'
	legacy_bytes = len(legacy.read_bytes()) if legacy.exists() and receipt_sha256(receipt.get(str(legacy))) == _digest(legacy.read_bytes()) else None
	wanted = _root_options(existing, instructions, legacy_bytes=legacy_bytes, expected_block=owned.get('block_sha256') if isinstance(owned, dict) else None)
	return (config_path, wanted, {config_path: actual})
def _loader(primary, local=(), *, restore_global=True):
	paths = [*sorted((primary / 'rules').glob('*.md')), primary / 'platforms/codex.md', *local]
	lines = ['Read the listed canonical rule sources before executing the task.  ', 'Shared always_on rules and the Codex adapter are mandatory in every new chat, including child subagents.  ', 'For project-specific sources, honor the frontmatter trigger; links are not copies of the rules.  ']
	if restore_global:
		lines.extend([f'''First run the Python tool "{(primary / 'scripts/harness.py').as_posix()}" policy-instructions --platform codex; apply the returned global developer_instructions of the active profile in addition to these rules.  ''', 'That command reads only the required TOML key rather than the entire configuration file.  '])
	lines.extend((f'- {path.as_posix()}' for path in dict.fromkeys(paths)))
	lines.extend(['Then, in the exact project root of the current chat, read local .agents/rules/*.md and .agents/rules.json.  ', 'Read all additional path sources from rules.json while honoring their trigger; you do not need to re-read the shared rules directory.  ', 'Never pick a neighboring project.  ', 'If the root of the current task is unknown, determine it from the explicit chat binding.  ', f'''For the established root of every turn, run the Python tool "{(primary / 'scripts/harness.py').as_posix()}" turn-begin "<exact root of current chat>" --platform codex; the UUID is read from CODEX_THREAD_ID and the profile from CODEX_HOME.  ''', 'FILE-3 and EXEC-5 also apply to ordinary analytical responses and .agents investigations; the article/proposal profile does not define their scope.  ', 'Run read-only Git checks with `--no-optional-locks` so the index is not updated as a side effect (or via harness.py git-read; read rules in batches without Get-Content output truncation and do not bundle git calls with initial rule reading before turn-begin completes).  ', 'Before publishing the final response, the primary agent runs answer-prepare with the exact UTF-8 bytes per references/turn-completion.md; a child subagent does not maintain the user journal.  '])
	r = '\n'.join(lines)
	return r
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
def global_codex_instructions():
	homes = settings()['platforms']['codex']['homes']
	try:
		name = profile_name()
		names = [name]
	except ValueError:
		names = list(homes)
	values = []
	for name in names:
		path = Path(homes[name]) / 'config.toml'
		value = tomllib.loads(path.read_bytes().decode('utf-8-sig')).get('developer_instructions', '') if path.exists() else ''
		if not isinstance(value, str):
			raise ValueError('Global developer_instructions must be a string')
		values.append(value)
	if 1 != len(set(values)):
		raise ValueError('Global profile instructions differ; select the actual --codex-profile instead of combining accounts')
	r = {'developer_instructions': values[0], 'profile': names[0] if 1 == len(names) else 'identical across configured profiles'}
	return r
def _project_rule_paths(root, primary):
	agents = root / '.agents'
	paths = list(sorted((agents / 'rules').glob('*.md')))
	data = load_discovery_manifest(agents / 'rules.json', entries_error='rules.json needs an entries list')
	if data.get('inherits'):
		raise ValueError('Codex projection does not support rules.json inherits; preserve it and resolve explicitly')
	shared = (primary / 'rules').resolve()
	for entry in data.get('entries', []):
		source, has_extra = resolve_manifest_entry(agents, entry)
		if None is source:
			raise ValueError('Each rules.json entry needs a path')
		if has_extra:
			raise ValueError('Codex projection does not support filtered rules.json entries; preserve them and resolve explicitly')
		if source != shared:
			if source.is_dir():
				paths.extend(sorted(source.rglob('*.md')))
			elif source.is_file() and '.md' == source.suffix:
				paths.append(source)
			else:
				raise ValueError(f'Configured rule source is missing or unsupported: {source}')
	return list(dict.fromkeys((path.resolve() for path in paths if not path.resolve().is_relative_to(shared))))
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
def configure_codex_project(root, primary=PRIMARY, job_url=None, label=None, *, check=False):
	from .native_profiles import legacy_project_projection_paths
	root, primary = (Path(root).resolve(), Path(primary).resolve())
	if root == Path(settings()['workspace_root']).resolve():
		r = {'valid': True, 'issues': [], 'written': []}
	else:
		r = None
		try:
			paths = _project_rule_paths(root, primary)
		except (ValueError, OSError) as exc:
			if not check:
				raise
			r = {'valid': False, 'issues': [{'file': str(root / '.agents/rules.json'), 'message': str(exc)}], 'written': []}
		if None is r:
			try:
				native = root / '.codex/config.toml'
				data = tomllib.loads(native.read_bytes().decode('utf-8')) if native.exists() else {}
				current = data.get('developer_instructions', '')
				manual = current.replace(extract_managed_block(current), '').strip()
				path, text, merge = _native_config(root, _loader(primary, paths, restore_global=False) if manual else None)
				r = _publish(root, {path: text} if text or path.exists() else {}, check=check, merge=merge, retire=[root / 'CODEX.md', *legacy_project_projection_paths(root, primary)])
			except ValueError as exc:
				if not check:
					raise
				r = {'valid': False, 'issues': [{'file': str(root / '.codex/config.toml'), 'message': str(exc)}], 'written': []}
			if not check and (not r['valid']):
				raise ValueError(r['issues'])
	return r
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
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
def build_native(root=None, *, primary=PRIMARY, check=False):
	from .native_profiles import build_shared_native, shared_native_outputs, legacy_project_projection_paths
	config = settings()
	root = Path(root or config['workspace_root']).resolve()
	primary = Path(primary).resolve()
	source_paths = [primary / 'runtime.json', *sorted((primary / 'rules').glob('*.md')), primary / 'platforms/codex.md', primary / 'agents/worker.md', *sorted((primary / 'skills').glob('*/SKILL.md'))]
	source_hash = _digest(b''.join((p.read_bytes() for p in source_paths)))
	native = root / '.codex/config.toml'
	current = tomllib.loads(native.read_bytes().decode('utf-8')).get('developer_instructions', '') if native.exists() else ''
	old_block = extract_managed_block(current)
	restore_global = 'policy-instructions' in old_block if old_block else not bool(current.strip())
	local_rules = _project_rule_paths(root, primary) if (root / '.agents/rules').is_dir() else ()
	instructions = _loader(primary, local_rules, restore_global=restore_global)
	guidance = f'# Codex: Upwork\n\n<!-- Generated from {primary.as_posix()}; run harness.py build-native to update. -->\n\n' + instructions + '\n'
	outputs = {root / 'AGENTS.md': guidance}
	try:
		path, text, merge = _native_config(root, instructions)
		outputs[path] = text
		publication = {'merge': merge, 'retire': [root / 'CODEX.md', *legacy_project_projection_paths(root, primary)], 'disown': list(shared_native_outputs(primary))}
		preflight = _publish(root, outputs, preflight=True, **publication) if not check else None
		if None is not preflight and (not preflight['valid']):
			r = preflight
		else:
			shared = build_shared_native(primary, check=check)
			if not shared['valid'] and (not check):
				r = {'valid': False, 'issues': [], 'written': []}
			else:
				publication['disown'].extend(shared['removed'])
				r = _publish(root, outputs, check=check, **publication)
			r.update(valid=r['valid'] and shared['valid'], issues=[*shared['issues'], *r['issues']], written=[*shared['written'], *r['written']], removed=[*shared['removed'], *r.get('removed', [])], shared=shared)
		r.update(source_sha256=source_hash, policy_bytes=len(instructions.encode('utf-8')), canonical_runtime=str(primary / 'runtime.json'))
	except ValueError as exc:
		r = {'valid': False, 'issues': [{'file': str(root / '.codex/config.toml'), 'message': str(exc)}], 'written': []}
	return r
def extract_managed_block(value, start_marker=START, end_marker=END, *, error_message='Malformed managed developer instructions; configuration preserved'):
	if start_marker not in value and end_marker not in value:
		r = ''
	elif 1 != value.count(start_marker) or 1 != value.count(end_marker) or value.index(start_marker) > value.index(end_marker):
		raise ValueError(error_message)
	else:
		r = value[value.index(start_marker):value.index(end_marker) + len(end_marker)]
	return r
def has_linked_ancestor(path, *, include_self=True):
	resolved = Path(os.path.abspath(path))
	candidates = (resolved, *resolved.parents) if include_self else resolved.parents
	return next((item for item in candidates if is_linked_path(item)), None)
def is_linked_path(path):
	candidate = Path(path)
	return candidate.is_symlink() or bool(getattr(candidate, 'is_junction', lambda: False)())
def load_discovery_manifest(path, *, missing_ok=True, entries_error='Manifest needs an entries list', check_inherits=False):
	target = Path(path)
	data = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() or (not missing_ok) else {}
	if not isinstance(data, dict) or not isinstance(data.get('entries', []), list) or (check_inherits and (not isinstance(data.get('inherits', []), list))):
		raise ValueError(entries_error)
	return data
def load_project_receipt(target, *, by_path=False, error_message='Project native ownership receipt must be an object; preserved'):
	path = Path(target) if by_path else data_dir_for(target) / 'native-config.json'
	raw = path.read_bytes() if path.exists() else None
	data = json.loads(raw.decode('utf-8-sig')) if None is not raw else {}
	if not isinstance(data, dict):
		raise ValueError(error_message)
	return (path, raw, data)
def project_discovery_entries(primary, kind, *, require_dir=False):
	shared = Path(primary) / kind
	if require_dir and (not shared.is_dir()):
		raise FileNotFoundError(shared)
	return [{'path': shared.as_posix()}, *([{'path': 'rules'}] if 'rules' == kind else [])]
def receipt_sha256(entry):
	return entry.get('sha256') if isinstance(entry, dict) else entry
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
def resolve_manifest_entry(agents_dir, entry):
	if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
		r = (None, False)
	else:
		r = ((Path(agents_dir) / Path(entry['path']).expanduser()).resolve(), bool(set(entry) - {'path'}))
	return r
def store_content_backup(backup_root, path, payload, *, error_message=None):
	digest = _digest(payload)
	backup = Path(backup_root) / _digest(str(path).encode('utf-8')) / (digest + '.bin')
	backup.parent.mkdir(parents=True, exist_ok=True)
	if not backup.exists():
		create_bytes(backup, payload)
	if backup.read_bytes() != payload:
		raise ValueError(error_message or f'Backup hash collision or modification; preserved: {backup}')
	return (backup, digest)
