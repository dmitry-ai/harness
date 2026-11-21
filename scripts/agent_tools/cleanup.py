# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Initialize new Upwork projects in the V2 filesystem layout":
# https://github.com/dmitry-ai/harness/issues/110
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
# https://github.com/dmitry-ai/harness/issues/86
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add /upwork-cleanup skill and cross-platform empty project pruner with timestamped audit logs":
# https://github.com/dmitry-ai/harness/issues/8
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import base64
import glob
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo
from .platforms.trace_common import extract_resource_uri, local_uri_to_path, open_readonly_sqlite
from .research import json_data
from .runtime import HARNESS_META, LEGACY_PRIMARY, PRIMARY, extract_platform_homes, platform_active, platform_adapter_name, platform_instances, platform_name, settings
from .storage import create_bytes, locked, replace_bytes
_ACTIVE_CODEX_GLOBS = ContextVar('upwork_cleanup_codex_globs', default=None)
@contextmanager
def _codex_glob_scope(globs):
	token = _ACTIVE_CODEX_GLOBS.set(globs or {})
	try:
		yield
	finally:
		_ACTIVE_CODEX_GLOBS.reset(token)
_STATUS_NAMES = ('recent', 'preserved', 'eligible', 'removed', 'pending', 'blocked', 'already-absent')
# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add /upwork-cleanup skill and cross-platform empty project pruner with timestamped audit logs":
# https://github.com/dmitry-ai/harness/issues/8
def record_cleanup_answer(body, *, now=None, log_root=None):
	if not isinstance(body, str) or not body.strip():
		raise ValueError('Cleanup answer must not be empty')
	moment = now or datetime.now(timezone.utc)
	if None is moment.tzinfo or None is moment.utcoffset():
		raise ValueError('Cleanup report time must include a timezone')
	local = moment.astimezone(ZoneInfo('Europe/Istanbul'))
	offset = int(local.utcoffset().total_seconds() / 60)
	hours, minutes = divmod(abs(offset), 60)
	zone = f"UTC{('+' if offset >= 0 else '-')}{hours}" + (f':{minutes:02d}' if minutes else '')
	timestamp = f'{local:%Y-%m-%d %H:%M} {zone}'
	answer = timestamp + '\n\n' + body
	payload = answer.encode('utf-8')
	from .path_registry import store_value, workspace_override
	ws = Path(settings()['workspace_root']).resolve()
	ovr_log = workspace_override(ws, 'cleanup_log_dir')
	default_log = Path(ovr_log) if ovr_log else ws / str(store_value('workspace_cleanup_log_rel'))
	root = Path(log_root or default_log).absolute()
	directory = root / f'{local:%Y/%m}'
	if linked(directory):
		raise ValueError('Cleanup log directory must not be linked')
	directory.mkdir(parents=True, exist_ok=True)
	number = 1
	while True:
		suffix = '' if 1 == number else f'--{number}'
		target = directory / f'{local:%d--%H-%M}{suffix}.md'
		try:
			create_bytes(target, payload)
			break
		except FileExistsError:
			number += 1
	if target.read_bytes() != payload:
		raise OSError('Cleanup answer log read-back mismatch')
	return {'path': str(target), 'timestamp': timestamp, 'answer': answer}
def path_key(value):
	return str(local_uri_to_path(value, require_absolute=True)).replace('\\', '/').rstrip('/').casefold()
def linked(path):
	return any((p.is_symlink() or p.is_junction() for p in (path, *path.parents)))
def _json(path):
	if linked(path):
		raise ValueError(f'Linked store preserved: {path}')
	r = json.loads(path.read_text(encoding='utf-8-sig'))
	if not isinstance(r, dict):
		raise ValueError(f'Expected a JSON object: {path}')
	return r
def _age(root, state, config):
	if state.get('created_at'):
		created = datetime.fromisoformat(state['created_at'].replace('Z', '+00:00'))
		if None is created.tzinfo:
			raise ValueError('created_at must include its timezone')
		r = (created, 'project.created_at')
	else:
		day = datetime.fromisoformat(state['request_date']).replace(tzinfo=ZoneInfo(config['timezone']))
		birth = getattr(root.stat(), 'st_birthtime', None)
		r = (max(day, datetime.fromtimestamp(birth, timezone.utc)), 'legacy-directory-birthtime') if None is not birth else (day + timedelta(days=1), 'legacy-request-day-upper-bound')
	return r
def _belongs_cached(raw_path, wanted, prefix, key_cache):
	key = key_cache.get(raw_path) if isinstance(raw_path, str) else None
	if None is key:
		key = path_key(raw_path)
		if isinstance(raw_path, str):
			key_cache[raw_path] = key
	return key == wanted or key.startswith(prefix)
def _collect_folder_ancestors(by_id, assignments, project_ids, error_msg):
	r = set()
	for ident in project_ids:
		folder = assignments.get(ident)
		seen = set()
		while None is not folder:
			if folder in seen or folder not in by_id:
				raise ValueError(error_msg)
			seen.add(folder)
			r.add(folder)
			folder = by_id[folder].get('parentId')
	return r
def _count_indexed_conversations(root, ag_projects, homes, catalog, index):
	wanted = path_key(root)
	prefix = wanted + '/'
	ag_rows, codex_rows, key_cache = index
	if isinstance(ag_projects, dict):
		r = {}
		ag_total = 0
		for iid, items in ag_projects.items():
			ag_ids = {p['id'] for p in items}
			rows_i = ag_rows.get(iid, [])
			cnt = sum((proj_id in ag_ids or any((_belongs_cached(uri, wanted, prefix, key_cache) for uri in uris)) for proj_id, uris in rows_i))
			r['antigravity:' + iid] = cnt
			ag_total += cnt
		if ag_projects:
			r['antigravity'] = ag_total
	else:
		ag_ids = {p['id'] for p in ag_projects}
		r = {'antigravity': sum((proj_id in ag_ids or any((_belongs_cached(uri, wanted, prefix, key_cache) for uri in uris)) for proj_id, uris in ag_rows))}
	for profile in homes:
		cx_ids = {p['bindings'][profile] for p in catalog}
		r['codex:' + profile] = len({tid for tid, proj_id, cwd in codex_rows[profile] if proj_id in cx_ids or _belongs_cached(cwd, wanted, prefix, key_cache)})
	return r
def _guard_history_db(database):
	if not database.is_file() or linked(database):
		raise ValueError(f'Native history unavailable: {database}')
def _read_ag_rows(backend_dir, *, allow_missing=False, db_path=None):
	db = Path(db_path) if None is not db_path else Path(backend_dir) / 'conversation_summaries.db'
	if allow_missing and (not db.exists()) and (not db.is_symlink()):
		return []
	ag_rows = []
	with open_readonly_sqlite(db, guard=_guard_history_db, query_only=True, row_factory=sqlite3.Row, timeout=5) as conn:
		for row in conn.execute('SELECT project_id, workspace_uris FROM conversation_summaries'):
			uris = json.loads(row['workspace_uris']) if row['workspace_uris'] else []
			if not isinstance(uris, list):
				raise ValueError('Unknown Antigravity workspace_uris format')
			ag_rows.append((row['project_id'], uris))
	return ag_rows
def _load_conversation_index(backend, homes):
	if isinstance(backend, dict):
		ag_rows = {}
		for iid, b_info in backend.items():
			if isinstance(b_info, tuple):
				if 3 <= len(b_info):
					b_dir, allow_missing, db_path = b_info[:3]
				else:
					b_dir, allow_missing = b_info
					db_path = None
			else:
				b_dir, allow_missing, db_path = (b_info, False, None)
			ag_rows[iid] = _read_ag_rows(b_dir, allow_missing=allow_missing, db_path=db_path)
	else:
		ag_rows = _read_ag_rows(backend, allow_missing=False)
	codex_globs = _ACTIVE_CODEX_GLOBS.get() or {}
	codex_rows = {}
	for profile, home in homes.items():
		glob_raw = codex_globs.get(profile)
		if glob_raw:
			if Path(glob_raw).is_absolute():
				databases = sorted((Path(p) for p in glob.glob(glob_raw, recursive=True) if Path(p).is_file()))
			elif None is not home:
				databases = sorted((Path(p) for p in glob.glob((Path(home) / glob_raw).as_posix(), recursive=True) if Path(p).is_file()))
			else:
				databases = []
		elif None is not home:
			databases = sorted((p for p in Path(home).glob('state_*.sqlite') if p.is_file()))
		else:
			databases = []
		if not databases:
			raise ValueError(f'Native Codex history unavailable: {profile}')
		p_rows = []
		for database in databases:
			with open_readonly_sqlite(database, guard=_guard_history_db, query_only=True, row_factory=sqlite3.Row, timeout=5) as conn:
				p_rows.extend(((row['id'], row['project_id'], row['cwd']) for row in conn.execute('SELECT id, project_id, cwd FROM threads')))
		codex_rows[profile] = p_rows
	return (ag_rows, codex_rows, {})
def legacy_initialization(root):
	agents = root / '.agents'
	rule = agents / 'rules/90-project.md'
	kb = next((p for p in (root / '\U0001f56e/Project.md', root / 'KB/Project.md') if p.is_file()), root / 'KB/Project.md')
	manifests = [agents / (kind + '.json') for kind in ('rules', 'skills', 'agents')]
	if not all((p.is_file() for p in [rule, kb, *manifests])):
		return None
	for kind, manifest in zip(('rules', 'skills', 'agents'), manifests):
		entries = _json(manifest).get('entries')
		if not isinstance(entries, list):
			raise ValueError('Legacy discovery manifest requires entries[]')
		paths = [Path(entry['path']) for entry in entries if isinstance(entry, dict) and isinstance(entry.get('path'), str)]
		allowed_roots = {(PRIMARY / kind).resolve(), (LEGACY_PRIMARY / kind).resolve()}
		if not any(((p if p.is_absolute() else agents / p).resolve() in allowed_roots for p in paths)):
			return None
	if linked(rule) or linked(kb):
		raise ValueError('Linked legacy initialization evidence preserved')
	pattern = 'https?://(?:www\\.)?upwork\\.com/jobs/[^\\s`"<>]*?(~[A-Za-z0-9]+)'
	ids = set(re.findall(pattern, rule.read_text(encoding='utf-8-sig')))
	current = re.search('^#\\s*2\\.\\s*(?:Current Client Project|\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442 \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)[^\\n]*\\n(.*?)(?=^#\\s|\\Z)', kb.read_text(encoding='utf-8-sig'), re.M | re.S)
	current_ids = re.findall(pattern, current.group(1)) if current else []
	if 1 != len(ids) or not current_ids or current_ids[0] not in ids:
		raise ValueError('Legacy project rule and current-job KB do not establish one job ID')
	if not re.fullmatch('~\\d+', current_ids[0]):
		raise ValueError('Unsupported historical job ID preserved without cleanup')
	day = datetime(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name)).date()
	return {'job_id': current_ids[0], 'initialized': True, 'request_date': day.isoformat()}
def candidates(daily, config, now):
	values, issues = ([], [])
	for root in sorted(daily.glob('????/??/??/*')):
		if not root.is_dir():
			continue
		marker = root / 'ꘖ/project.json'
		try:
			if linked(marker) or not root.resolve().is_relative_to(daily):
				raise ValueError('Linked or escaped archive entry preserved')
			state = _json(marker) if marker.exists() else legacy_initialization(root)
			if None is state or True is not state.get('initialized') or not re.fullmatch('~\\d+', state.get('job_id', '')):
				continue
			created, basis = _age(root, state, config)
			values.append({'root': str(root.resolve()), 'job_id': state['job_id'], 'initialization_basis': 'project.json' if marker.exists() else 'legacy-manifests-rule-and-kb', 'created_at': created.isoformat(), 'age_basis': basis, 'old_enough': now - created > timedelta(days=3)})
		except (OSError, ValueError, TypeError, KeyError) as exc:
			issues.append({'root': str(root), 'error': str(exc)})
	return (values, issues)
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Canonicalize relocated Codex, Antigravity, and Harness project roots and support v2Migrated gitFolder project resources":
# https://github.com/dmitry-ai/harness/issues/29
def _resource_uri(res):
	return extract_resource_uri(res)
def antigravity_projects(directory, root):
	target_key = path_key(root)
	r = []
	for path in sorted(directory.glob('*.json')):
		value = _json(path)
		resources = (value.get('projectResources') or {}).get('resources') or []
		roots = [path_key(_resource_uri(res)) for res in resources if _resource_uri(res)]
		if target_key in roots:
			if roots != [target_key]:
				raise ValueError('Antigravity multi-root project preserved')
			if not value.get('id') or path.stem != value['id']:
				raise ValueError('Antigravity project identity is ambiguous')
			r.append({'id': value['id'], 'file': str(path), 'sha': path.read_bytes()})
	pending_file = directory / 'ꘖ/data/cleanup-pending.json'
	pending = _json(pending_file) if pending_file.exists() else {}
	for saved in pending.get(target_key, {}).get('projects', []):
		ident = saved['id']
		if not isinstance(ident, str) or not re.fullmatch('[a-f0-9-]{36}', ident):
			raise ValueError('Invalid pending Antigravity cleanup identity')
		path = directory / (ident + '.json')
		if not any((p['id'] == ident for p in r)):
			if path.exists():
				raise ValueError('Pending Antigravity project changed its workspace')
			payload = base64.b64decode(saved['payload'], validate=True)
			restored = json.loads(payload.decode('utf-8-sig'))
			roots = [path_key(_resource_uri(res)) for res in restored['projectResources']['resources'] if _resource_uri(res)]
			if restored.get('id') != ident or roots != [target_key]:
				raise ValueError('Pending Antigravity payload changed identity')
			r.append({'id': ident, 'file': str(path), 'sha': None, 'restore': payload})
	return r
def conversations(root, ag_projects, backend, homes, catalog):
	return _count_indexed_conversations(root, ag_projects, homes, catalog, _load_conversation_index(backend, homes))
_DEFAULT_CONVERSATIONS = conversations
def catalog_projects(catalog, root, homes):
	if not homes:
		return []
	if not isinstance(catalog, dict) or not isinstance(catalog.get('projects'), dict) or (not isinstance(catalog.get('profiles'), dict)):
		raise ValueError('Shared-Projects catalogue unavailable')
	if not set(homes).issubset(set(catalog['profiles'])):
		raise ValueError('Configured Codex profiles differ from Shared-Projects')
	target_key = path_key(root)
	r = []
	for ident, project in catalog['projects'].items():
		roots = [path_key(path) for path in project['rootPaths']]
		if target_key not in roots:
			continue
		if roots != [target_key]:
			raise ValueError('Codex multi-root project preserved')
		bindings = {}
		for profile in homes:
			data = catalog['profiles'][profile]
			binding = data['bindings'].get(ident)
			if not binding or not binding.get('desktopId'):
				raise ValueError('Codex profile binding is missing')
			bindings[profile] = binding['desktopId']
		r.append({'id': ident, 'bindings': bindings, 'cleanup_hold': bool(project.get('cleanupHold'))})
	if 1 < len(r):
		raise ValueError('Ambiguous Shared-Projects root')
	return r
def prune_folders(value, removed_ids):
	nodes, assignments = (value['folders'], value['projectFolderMap'])
	if not isinstance(nodes, list) or not isinstance(assignments, dict):
		raise ValueError('Invalid Folders store')
	by_id = {node['id']: node for node in nodes}
	if len(by_id) != len(nodes):
		raise ValueError('Duplicate Folders identities')
	affected = _collect_folder_ancestors(by_id, assignments, removed_ids, 'Broken Folders ancestry')
	for ident in removed_ids:
		assignments.pop(ident, None)
	r = []
	while True:
		empty = {ident for ident in affected if ident in by_id and ident not in assignments.values() and (not any((n.get('parentId') == ident for n in by_id.values())))}
		if not empty:
			break
		for ident in empty:
			r.append(ident)
			del by_id[ident]
	value['folders'] = [n for n in nodes if n['id'] in by_id]
	for key in ('collapsedFolders', 'collapsedFolderIds'):
		if key in value:
			value[key] = [ident for ident in value[key] if ident not in r]
	return r
def _finish_pending(directory, root):
	path = directory / 'ꘖ/data/cleanup-pending.json'
	if path.exists():
		pending = _json(path)
		pending.pop(path_key(root), None)
		if not pending:
			path.unlink()
		else:
			replace_bytes(path, json_data(pending))
def restore_antigravity(root, directory, folders):
	with locked(directory / 'ꘖ/data/registration.lock'):
		path = directory / 'ꘖ/data/cleanup-pending.json'
		if not path.exists():
			r = {'complete': True, 'restored_projects': []}
		else:
			pending = _json(path).get(path_key(root))
			if not pending:
				r = {'complete': True, 'restored_projects': []}
			else:
				restored = []
				for project in antigravity_projects(directory, root):
					if None is project['sha']:
						target = Path(project['file'])
						if linked(target) or target.parent.resolve() != directory.resolve():
							raise ValueError('Unsafe Antigravity restoration path')
						create_bytes(target, project['restore'])
						restored.append(project['id'])
				before = folders.read_bytes()
				value = _json(folders)
				ids = {n['id'] for n in value['folders']}
				for node in pending['folders']:
					if node['id'] not in ids:
						value['folders'].append(node)
						ids.add(node['id'])
				for ident, folder in pending['assignments'].items():
					value['projectFolderMap'].setdefault(ident, folder)
				if any((folder not in ids for folder in value['projectFolderMap'].values())) or any((None is not n.get('parentId') and n['parentId'] not in ids for n in value['folders'])):
					raise ValueError('Restored Folders ancestry is incomplete')
				if folders.read_bytes() != before:
					raise ValueError('Folders changed during restoration')
				replace_bytes(folders, json_data(value))
				_finish_pending(directory, root)
				r = {'complete': True, 'restored_projects': restored}
	return r
def remove_antigravity(root, directory, folders, expected, check):
	with locked(directory / 'ꘖ/data/registration.lock'):
		check()
		current = antigravity_projects(directory, root)
		if [(p['id'], p['sha']) for p in current] != [(p['id'], p['sha']) for p in expected]:
			raise ValueError('Antigravity registration changed; retry cleanup')
		before = folders.read_bytes()
		value = _json(folders)
		original = json.loads(before.decode('utf-8-sig'))
		pruned = prune_folders(value, [p['id'] for p in current])
		if folders.read_bytes() != before:
			raise ValueError('Folders changed; retry cleanup')
		pending_file = directory / 'ꘖ/data/cleanup-pending.json'
		pending = _json(pending_file) if pending_file.exists() else {}
		ancestry = _collect_folder_ancestors({node['id']: node for node in original['folders']}, original['projectFolderMap'], (p['id'] for p in current), 'Invalid pending Folders ancestry')
		pending.setdefault(path_key(root), {'projects': [{'id': p['id'], 'payload': base64.b64encode(p['sha'] if None is not p['sha'] else p['restore']).decode('ascii')} for p in current], 'folders': [node for node in original['folders'] if node['id'] in ancestry], 'assignments': {p['id']: original['projectFolderMap'][p['id']] for p in current if p['id'] in original['projectFolderMap']}})
		replace_bytes(pending_file, json_data(pending))
		removed = []
		for project in current:
			path = Path(project['file'])
			actual = path.read_bytes() if path.exists() else None
			if path.parent.resolve() != directory.resolve() or linked(path) or actual != project['sha']:
				raise ValueError('Native project changed before removal')
			check()
			if linked(path) or (path.read_bytes() if path.exists() else None) != project['sha']:
				raise ValueError('Native project changed during the final conversation check')
			if None is not actual:
				path.unlink()
			removed.append(project['id'])
		check()
		if folders.read_bytes() != before:
			raise ValueError('Folders changed after native deletion; retry cleanup')
		payload = json_data(value)
		replace_bytes(folders, payload)
		if folders.read_bytes() != payload:
			raise ValueError('Folders did not confirm cleanup; retry')
		r = {'complete': True, 'removed_projects': removed, 'removed_folders': pruned, 'awaiting_commit': True}
	return r
class ProjectCleanupScanner:
	def __init__(self, *, apply=False, daily_root=None, now=None, config=None, ag_directory=None, ag_backend=None, folders=None, control=None):
		self.apply = apply
		self.config = config or settings()
		daily = Path(daily_root or Path(self.config['workspace_root']) / self.config['daily_root']).absolute()
		if linked(daily) or not daily.is_dir():
			raise ValueError('Daily archive must be an existing unlinked directory')
		self.daily = daily.resolve()
		self.now = now or datetime.now(timezone.utc)
		if None is self.now.tzinfo:
			raise ValueError('Cleanup time must include a timezone')
		self.single_ag_mode = None is not ag_directory or None is not ag_backend
		self.ag_stores = {}
		platforms_cfg = self.config.get('platforms') or {}
		ag_plats = [pid for pid, pcfg in platforms_cfg.items() if isinstance(pcfg, dict) and 'antigravity' == platform_adapter_name(pid, pcfg) and platform_active(pid, config=self.config)]
		cx_plats = [pid for pid, pcfg in platforms_cfg.items() if isinstance(pcfg, dict) and 'codex' == platform_adapter_name(pid, pcfg) and platform_active(pid, config=self.config)]
		from .path_registry import default_platform_paths
		if self.single_ag_mode:
			def_ag = default_platform_paths('antigravity')
			p_dir = Path(ag_directory or def_ag['projects_dir']).absolute()
			b_dir = Path(ag_backend or def_ag['backend_dir']).absolute()
			if not p_dir.is_dir() or linked(p_dir):
				raise ValueError('Antigravity native stores unavailable or linked')
			if p_dir.is_relative_to(self.daily):
				raise ValueError('Native stores must be outside the preserved daily archive')
			self.ag_stores['default'] = {'directory': p_dir, 'backend': b_dir, 'allow_missing_db': False}
			self.directory, self.backend = (p_dir, b_dir)
		else:
			self.directory, self.backend = (None, None)
			ag_insts = {}
			for pid in ag_plats:
				ag_insts.update(platform_instances(pid, config=self.config, include_disabled=False))
			for iid, inst in ag_insts.items():
				sp = inst['system_paths']
				home_dir = Path(inst['home']).absolute() if inst.get('home') else None
				home_ag = default_platform_paths('antigravity', home=home_dir) if home_dir else {}
				p_dir = Path(sp['projects_dir']).absolute() if sp.get('projects_dir') else (Path(home_ag['projects_dir']).absolute() if home_ag.get('projects_dir') else None)
				b_dir = Path(sp['backend_dir']).absolute() if sp.get('backend_dir') else (Path(home_ag['backend_dir']).absolute() if home_ag.get('backend_dir') else None)
				conv_dir = Path(sp['conversations_dir']).absolute() if sp.get('conversations_dir') else (b_dir / 'conversations' if b_dir else None)
				brain_dir = Path(sp['brain_dir']).absolute() if sp.get('brain_dir') else (b_dir / 'brain' if b_dir else None)
				conv_db = Path(sp['conversations_db']).absolute() if sp.get('conversations_db') else (b_dir / 'conversation_summaries.db' if b_dir else None)
				if not p_dir or linked(p_dir) or (b_dir and linked(b_dir)) or (conv_dir and linked(conv_dir)) or (brain_dir and linked(brain_dir)) or (conv_db and linked(conv_db)) or (home_dir and linked(home_dir)):
					raise ValueError(f'Antigravity native stores unavailable or linked ({iid})')
				has_any_store = p_dir.is_dir() or (conv_dir and conv_dir.is_dir()) or (brain_dir and brain_dir.is_dir()) or (conv_db and conv_db.is_file()) or (home_dir and home_dir.is_dir())
				if not has_any_store:
					raise ValueError(f'Antigravity native stores unavailable or linked ({iid})')
				if p_dir.is_relative_to(self.daily) or (b_dir and b_dir.is_relative_to(self.daily)) or (conv_dir and conv_dir.is_relative_to(self.daily)) or (brain_dir and brain_dir.is_relative_to(self.daily)) or (conv_db and conv_db.is_relative_to(self.daily)):
					raise ValueError('Native stores must be outside the preserved daily archive')
				has_history = bool((conv_db and conv_db.is_file()) or (conv_dir and conv_dir.is_dir() and any(conv_dir.iterdir())) or (brain_dir and brain_dir.is_dir() and any(brain_dir.iterdir())))
				self.ag_stores[iid] = {'directory': p_dir, 'backend': b_dir or (conv_db.parent if conv_db else p_dir), 'conversations_dir': conv_dir, 'brain_dir': brain_dir, 'conversations_db': conv_db, 'allow_missing_db': not has_history, 'folders_json': sp.get('folders_json')}
			first_store = next(iter(self.ag_stores.values()), None)
			self.directory = first_store['directory'] if first_store else None
			self.backend = {iid: (s['backend'], s['allow_missing_db'], s['conversations_db']) for iid, s in self.ag_stores.items()} if self.ag_stores else {}
		ag_plat_folders = next(((platforms_cfg.get(pid) or {}).get('folders_json') for pid in ag_plats if (platforms_cfg.get(pid) or {}).get('folders_json')), None)
		folders_raw = folders or next((s.get('folders_json') for s in self.ag_stores.values() if s.get('folders_json')), None) or ag_plat_folders
		if (self.ag_stores or None is not folders) and (not folders_raw):
			raise ValueError('Antigravity folders_json is not configured in runtime.json')
		self.folder_file = Path(folders_raw).absolute() if (self.ag_stores or None is not folders) else None
		if self.folder_file is not None:
			if linked(self.folder_file) or (self.single_ag_mode and not self.folder_file.is_file()):
				raise ValueError('Antigravity native stores unavailable or linked')
			if self.folder_file.is_relative_to(self.daily):
				raise ValueError('Native stores must be outside the preserved daily archive')
		codex_insts = {}
		for pid in cx_plats:
			codex_insts.update(platform_instances(pid, config=self.config, include_disabled=False))
		self.homes = {iid: Path(inst['home']) if inst.get('home') else None for iid, inst in codex_insts.items() if inst.get('home') or inst['system_paths'].get('state_db_glob')}
		self.home_globs = {iid: inst['system_paths'].get('state_db_glob') for iid, inst in codex_insts.items() if (inst.get('home') or inst['system_paths'].get('state_db_glob')) and inst['system_paths'].get('state_db_glob')}
		skipped_disabled = {}
		for plat_id in platforms_cfg:
			disabled_ids = [iid for iid, v in platform_instances(plat_id, config=self.config, include_disabled=True).items() if not v['enabled']]
			if disabled_ids:
				skipped_disabled[plat_id] = disabled_ids
		if None is control:
			from .platforms.codex import shared_control
			control = shared_control
		self.control = control
		self.catalog = None
		self._history = None
		self.result = {
			'complete': True,
			'mode': 'apply' if apply else 'dry-run',
			'platform': platform_name(config=self.config),
			'cutoff': (self.now - timedelta(days=3)).isoformat(),
			'archive_preserved': str(self.daily),
			'active_instances': {'antigravity': list(self.ag_stores), 'codex': list(self.homes)},
			'skipped_disabled_instances': skipped_disabled,
			'projects': [],
			'issues': [],
		}
	def _ag_flat(self, ag):
		return ag if self.single_ag_mode else [p for plist in ag.values() for p in plist]
	def _apply_removal(self, entry, root, ag, cx, live_check):
		live_check()
		ag_flat = self._ag_flat(ag)
		raw_ag_dbs = [self.backend / 'conversation_summaries.db'] if self.single_ag_mode else [s['conversations_db'] for s in self.ag_stores.values()]
		ag_dbs = [str(p) for p in sorted(raw_ag_dbs, key=lambda p: (0 if p.is_file() else 1))]
		ag_meta = {'database': ag_dbs[0] if ag_dbs else None, 'databases': ag_dbs, 'projectIds': [p['id'] for p in ag_flat]}
		proceed = True
		if cx:
			entry['codex'] = self.control({'command': 'shared-cleanup-project', 'deferCommit': True, 'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings'], 'antigravity': ag_meta})
			if True is not entry['codex'].get('complete'):
				entry['status'], self.result['complete'], proceed = ('pending', False, False)
		if proceed and ag_flat:
			if self.single_ag_mode:
				entry['antigravity'] = remove_antigravity(root, self.directory, self.folder_file, ag, live_check)
			else:
				ag_results = {}
				for iid, plist in ag.items():
					if plist:
						ag_results[iid] = remove_antigravity(root, self.ag_stores[iid]['directory'], self.folder_file, plist, live_check)
				entry['antigravity'] = {'complete': True, 'instances': ag_results, 'removed_projects': [pid for res in ag_results.values() for pid in res['removed_projects']], 'removed_folders': [fid for res in ag_results.values() for fid in res['removed_folders']]}
		if proceed and cx:
			entry['codex_commit'] = self.control({'command': 'shared-cleanup-project', 'commit': True, 'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings'], 'antigravity': ag_meta})
			if True is not entry['codex_commit'].get('complete'):
				entry['status'], self.result['complete'], proceed = ('pending', False, False)
		if proceed:
			for store in self.ag_stores.values():
				if store['directory'].is_dir():
					with locked(store['directory'] / 'ꘖ/data/registration.lock'):
						_finish_pending(store['directory'], root)
			entry['status'] = 'removed'
			if self.homes:
				self.catalog = self.control({'command': 'shared-catalog'})
	def _discover_conversations(self, root, ag, cx):
		if conversations is not _DEFAULT_CONVERSATIONS:
			r = conversations(root, ag, self.backend, self.homes, cx)
		else:
			if None is self._history:
				self._history = _load_conversation_index(self.backend, self.homes)
			r = _count_indexed_conversations(root, ag, self.homes, cx, self._history)
		return r
	def _collect_ag_projects(self, root):
		if self.single_ag_mode:
			return antigravity_projects(self.directory, root)
		return {iid: antigravity_projects(store['directory'], root) if store['directory'].is_dir() else [] for iid, store in self.ag_stores.items()}
	def _inspect_candidate(self, item):
		root = Path(item['root'])
		entry = {**item, 'status': 'recent' if not item['old_enough'] else 'checking'}
		self.result['projects'].append(entry)
		if item['old_enough']:
			cx, ag = ([], [] if self.single_ag_mode else {iid: [] for iid in self.ag_stores})
			try:
				ag = self._collect_ag_projects(root)
				cx = catalog_projects(self.catalog, root, self.homes)
				counts = self._discover_conversations(root, ag, cx)
				entry['conversations'] = counts
				ag_flat = self._ag_flat(ag)
				if not ag_flat and (not cx) and (not any(counts.values())):
					entry['status'] = 'already-absent'
				elif any(counts.values()):
					entry.update(status='preserved', error='Project has conversations')
					self._recover_preserved(entry, root, cx)
				else:
					entry['status'] = 'eligible'
					entry['native_projects'] = {'antigravity': [p['id'] for p in ag_flat], 'codex': [p['id'] for p in cx]}
					if not self.single_ag_mode:
						entry['native_projects']['antigravity_instances'] = {iid: [p['id'] for p in plist] for iid, plist in ag.items() if plist}
					if self.apply:
						def live_check():
							live = conversations(root, ag, self.backend, self.homes, cx)
							entry['conversations'] = live
							if any(live.values()):
								raise ValueError('Project has conversations')
						self._apply_removal(entry, root, ag, cx, live_check)
			except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error) as exc:
				try:
					entry['conversations'] = conversations(root, ag, self.backend, self.homes, cx)
				except (OSError, ValueError, TypeError, sqlite3.Error):
					pass
				entry.update(status='preserved' if any(entry.get('conversations', {}).values()) else 'blocked', error=str(exc))
				if 'preserved' == entry['status']:
					self._recover_preserved(entry, root, cx)
				elif 'blocked' == entry['status']:
					self.result['complete'] = False
	def _inspect_unresolved(self, issues):
		for issue in issues:
			root = Path(issue['root'])
			preserved = False
			try:
				if linked(root) or not root.resolve().is_relative_to(self.daily):
					raise ValueError('Linked or escaped archive entry preserved')
				ag = self._collect_ag_projects(root)
				cx = catalog_projects(self.catalog, root, self.homes)
				counts = self._discover_conversations(root, ag, cx)
				if any(counts.values()):
					entry = {'root': str(root), 'status': 'preserved', 'conversations': counts}
					self.result['projects'].append(entry)
					self.result['discovery']['excluded_with_conversations'] += 1
					self._recover_preserved(entry, root, cx)
					preserved = True
			except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error):
				pass
			if not preserved:
				self.result['issues'].append(issue)
		self.result['discovery']['unresolved_entries'] = len(self.result['issues'])
	def _recover_preserved(self, entry, root, cx):
		if self.apply:
			try:
				if self.single_ag_mode:
					entry['antigravity_recovery'] = restore_antigravity(root, self.directory, self.folder_file)
				elif self.ag_stores:
					rec = {}
					for iid, store in self.ag_stores.items():
						if store['directory'].is_dir():
							rec[iid] = restore_antigravity(root, store['directory'], self.folder_file)
					entry['antigravity_recovery'] = {'complete': all((r.get('complete') for r in rec.values())), 'instances': rec}
				if cx:
					current_cx = catalog_projects(self.control({'command': 'shared-catalog'}), root, self.homes)
					if any((p['cleanup_hold'] for p in current_cx)):
						entry['recovery'] = self.control({'command': 'shared-cleanup-project', 'preserve': True, 'sharedId': cx[0]['id'], 'rootPaths': [str(root)], 'bindings': cx[0]['bindings']})
						if True is not entry['recovery'].get('complete'):
							self.result['complete'] = False
			except (OSError, ValueError, RuntimeError) as recovery_error:
				entry['recovery_error'] = str(recovery_error)
				self.result['complete'] = False
	def run(self):
		from .path_registry import store_path
		lock = store_path('cleanup_lock')
		with locked(lock) if self.apply else nullcontext(), _codex_glob_scope(self.home_globs):
			found, issues = candidates(self.daily, self.config, self.now)
			self.result['discovery'] = {'verified_projects': len(found), 'modern_projects': sum(('project.json' == p['initialization_basis'] for p in found)), 'legacy_projects': sum(('project.json' != p['initialization_basis'] for p in found)), 'excluded_with_conversations': 0, 'unresolved_entries': len(issues)}
			ready = True
			try:
				if self.homes:
					self.catalog = self.control({'command': 'shared-catalog'})
					if not isinstance(self.catalog, dict):
						raise RuntimeError('Shared-Projects is initializing; retry cleanup')
				if self.folder_file is not None:
					_json(self.folder_file)
			except (OSError, ValueError, RuntimeError) as exc:
				self.result.update(complete=False, issues=[*issues, {'error': str(exc)}])
				ready = False
			if ready:
				self._inspect_unresolved(issues)
				for item in found:
					self._inspect_candidate(item)
				if self.result['issues']:
					self.result['complete'] = False
				self.result['counts'] = {name: sum((p['status'] == name for p in self.result['projects'])) for name in _STATUS_NAMES}
		return self.result
# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add /upwork-cleanup skill and cross-platform empty project pruner with timestamped audit logs":
# https://github.com/dmitry-ai/harness/issues/8
def cleanup_projects(*, apply=False, daily_root=None, now=None, config=None, ag_directory=None, ag_backend=None, folders=None, control=None):
	return ProjectCleanupScanner(apply=apply, daily_root=daily_root, now=now, config=config, ag_directory=ag_directory, ag_backend=ag_backend, folders=folders, control=control).run()
