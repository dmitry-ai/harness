# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sqlite3
PRIMARY = Path(__file__).resolve().parents[2]
HARNESS_ROOT = PRIMARY.parent if (PRIMARY.parent / '_').is_dir() else PRIMARY.parent.parent
HARNESS_META = HARNESS_ROOT / '_' if (HARNESS_ROOT / '_').is_dir() else HARNESS_ROOT
LEGACY_PRIMARY = Path('C:/work/upwork/code/AI/primary') / 'result/.agents'
os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
_SHIM_DIR = str((PRIMARY / 'scripts/shim').resolve())
if _SHIM_DIR not in os.environ.get('PATH', '').split(os.pathsep):
	os.environ['PATH'] = _SHIM_DIR + os.pathsep + os.environ.get('PATH', '')
_platform = ContextVar('upwork_platform', default=None)
_profile = ContextVar('upwork_profile', default=None)
_instance = ContextVar('upwork_instance', default=None)
def _expand_path(value):
	return Path(os.path.expanduser(str(value))).as_posix()
def _validate_runtime(value):
	if 2 != value.get('version') or not value.get('workspace_root') or (not isinstance(value.get('platforms'), dict)) or (not value['platforms']):
		raise ValueError('runtime.json needs version 2, workspace_root and platforms')
	for plat_id, plat_cfg in value['platforms'].items():
		if not isinstance(plat_id, str) or not plat_id.strip() or (not isinstance(plat_cfg, dict)):
			raise ValueError('Each runtime.json platform must map a non-empty name to an object')
		if 'enabled' in plat_cfg and (not isinstance(plat_cfg['enabled'], bool)):
			raise ValueError(f'runtime.json platforms.{plat_id}.enabled must be a boolean')
		if 'instances' in plat_cfg:
			raw = plat_cfg['instances']
			if not isinstance(raw, dict):
				raise ValueError(f'runtime.json platforms.{plat_id}.instances must be an object')
			for inst_id, inst_cfg in raw.items():
				if not isinstance(inst_id, str) or not inst_id.strip() or (not isinstance(inst_cfg, dict)):
					raise ValueError(f'runtime.json platforms.{plat_id}.instances entries must map IDs to objects')
				if 'enabled' in inst_cfg and (not isinstance(inst_cfg['enabled'], bool)):
					raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.enabled must be a boolean')
				if 'home' in inst_cfg and (not isinstance(inst_cfg['home'], str) or not inst_cfg['home'].strip()):
					raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.home must be a non-empty path')
				if 'user_data_dir' in inst_cfg and (None is not inst_cfg['user_data_dir']) and (not isinstance(inst_cfg['user_data_dir'], str) or not inst_cfg['user_data_dir'].strip()):
					raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.user_data_dir must be a non-empty path')
				if 'system_paths' in inst_cfg:
					sp = inst_cfg['system_paths']
					if not isinstance(sp, dict) or any((not isinstance(k, str) or not k.strip() or (not isinstance(v, str)) or (not v.strip()) for k, v in sp.items())):
						raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.system_paths must map non-empty keys to path strings')
				if not inst_cfg.get('home') and (not inst_cfg.get('system_paths')):
					raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id} requires home or system_paths')
		if 'homes' in plat_cfg and (not isinstance(plat_cfg['homes'], dict)):
			raise ValueError(f'runtime.json platforms.{plat_id}.homes must map profile names to home directories')
		if 'homes' in plat_cfg and 'instances' in plat_cfg:
			raise ValueError(f'runtime.json platforms.{plat_id} cannot define both instances and legacy homes')
def settings(path=None):
	value = json.loads(Path(path or PRIMARY / 'runtime.json').read_text(encoding='utf-8-sig'))
	_validate_runtime(value)
	r = value
	return r
def platform_adapter_name(platform, plat_cfg=None, *, config=None):
	if None is plat_cfg:
		plat_cfg = (config or settings()).get('platforms', {}).get(platform) or {}
	return plat_cfg.get('adapter') or platform
def default_system_paths(platform, inst_id, inst_cfg, plat_cfg=None):
	plat_cfg = plat_cfg if isinstance(plat_cfg, dict) else {}
	adapter_kind = platform_adapter_name(platform, plat_cfg)
	paths = {}
	raw_home = inst_cfg.get('home')
	home = Path(os.path.expanduser(raw_home)) if isinstance(raw_home, str) and raw_home.strip() else None
	if home:
		paths['home'] = home.as_posix()
	raw_udd = inst_cfg.get('user_data_dir')
	udd = Path(os.path.expanduser(raw_udd)) if isinstance(raw_udd, str) and raw_udd.strip() else None
	if udd:
		paths['user_data_dir'] = udd.as_posix()
	if 'antigravity' == adapter_kind:
		if home:
			gemini = home / '.gemini'
			cfg_dir = gemini / 'config'
			backend = gemini / 'antigravity'
			paths.update({
				'gemini_dir': gemini.as_posix(),
				'config_dir': cfg_dir.as_posix(),
				'config_json': (cfg_dir / 'config.json').as_posix(),
				'hooks_json': (cfg_dir / 'hooks.json').as_posix(),
				'mcp_config_json': (cfg_dir / 'mcp_config.json').as_posix(),
				'rules_json': (cfg_dir / 'rules.json').as_posix(),
				'skills_json': (cfg_dir / 'skills.json').as_posix(),
				'agents_json': (cfg_dir / 'agents.json').as_posix(),
				'projects_dir': (cfg_dir / 'projects').as_posix(),
				'backend_dir': backend.as_posix(),
				'conversations_db': (backend / 'conversation_summaries.db').as_posix(),
				'conversations_dir': (backend / 'conversations').as_posix(),
				'brain_dir': (backend / 'brain').as_posix(),
				'annotations_dir': (backend / 'annotations').as_posix(),
				'knowledge_dir': (backend / 'knowledge').as_posix(),
			})
		if udd:
			paths.setdefault('logs_dir', (udd / 'logs').as_posix())
			paths.setdefault('local_state', (udd / 'Local State').as_posix())
			paths.setdefault('preferences', (udd / 'Preferences').as_posix())
			paths.setdefault('window_state', (udd / 'window_state.json').as_posix())
		if isinstance(plat_cfg.get('folders_json'), str) and plat_cfg['folders_json'].strip():
			paths['folders_json'] = _expand_path(plat_cfg['folders_json'])
		if isinstance(plat_cfg.get('addons_profiles_json'), str) and plat_cfg['addons_profiles_json'].strip():
			paths['addons_profiles_json'] = _expand_path(plat_cfg['addons_profiles_json'])
	elif 'codex' == adapter_kind:
		if home:
			paths.update({
				'config_toml': (home / 'config.toml').as_posix(),
				'agents_md': (home / 'AGENTS.md').as_posix(),
				'agents_dir': (home / 'agents').as_posix(),
				'skills_dir': (home / 'skills').as_posix(),
				'sessions_dir': (home / 'sessions').as_posix(),
				'session_index': (home / 'session_index.jsonl').as_posix(),
				'state_db_glob': (home / 'state_*.sqlite').as_posix(),
				'logs_db': (home / 'logs_2.sqlite').as_posix(),
				'memories_db': (home / 'memories_1.sqlite').as_posix(),
				'models_cache_json': (home / 'models_cache.json').as_posix(),
				'global_state': (home / '.codex-global-state.json').as_posix(),
				'ui_folders': (home / 'ui-folders.json').as_posix(),
			})
		if isinstance(plat_cfg.get('ui_manage'), str) and plat_cfg['ui_manage'].strip():
			paths['ui_manage'] = _expand_path(plat_cfg['ui_manage'])
	explicit = inst_cfg.get('system_paths') or {}
	if not isinstance(explicit, dict):
		raise ValueError(f'system_paths for {platform}/{inst_id} must be an object')
	for key, val in explicit.items():
		if not isinstance(key, str) or not key.strip() or (not isinstance(val, str)) or (not val.strip()):
			raise ValueError(f'system_paths.{key} for {platform}/{inst_id} must be a non-empty string')
		paths[key] = _expand_path(val)
	if 'antigravity' == adapter_kind:
		if 'config_dir' not in paths and 'projects_dir' in paths and 'projects' == Path(paths['projects_dir']).name:
			paths['config_dir'] = Path(paths['projects_dir']).parent.as_posix()
		if 'config_dir' in paths:
			cfg_dir = Path(paths['config_dir'])
			paths.setdefault('projects_dir', (cfg_dir / 'projects').as_posix())
			for key, fname in (('config_json', 'config.json'), ('hooks_json', 'hooks.json'), ('mcp_config_json', 'mcp_config.json'), ('rules_json', 'rules.json'), ('skills_json', 'skills.json'), ('agents_json', 'agents.json')):
				paths.setdefault(key, (cfg_dir / fname).as_posix())
		if 'backend_dir' not in paths:
			for key in ('conversations_db', 'brain_dir', 'conversations_dir', 'annotations_dir', 'knowledge_dir'):
				if key in paths:
					paths['backend_dir'] = Path(paths[key]).parent.as_posix()
					break
		if 'backend_dir' in paths:
			backend = Path(paths['backend_dir'])
			paths.setdefault('conversations_db', (backend / 'conversation_summaries.db').as_posix())
			paths.setdefault('conversations_dir', (backend / 'conversations').as_posix())
			paths.setdefault('brain_dir', (backend / 'brain').as_posix())
			paths.setdefault('annotations_dir', (backend / 'annotations').as_posix())
			paths.setdefault('knowledge_dir', (backend / 'knowledge').as_posix())
	elif 'codex' == adapter_kind:
		if 'home' not in paths:
			for key in ('config_toml', 'agents_md', 'session_index', 'global_state', 'ui_folders', 'logs_db', 'memories_db', 'models_cache_json', 'sessions_dir', 'agents_dir', 'skills_dir', 'state_db_glob'):
				if key in paths:
					paths['home'] = Path(paths[key]).parent.as_posix()
					break
		if 'home' in paths:
			c_home = Path(paths['home'])
			paths.setdefault('sessions_dir', (c_home / 'sessions').as_posix())
			paths.setdefault('state_db_glob', (c_home / 'state_*.sqlite').as_posix())
			paths.setdefault('config_toml', (c_home / 'config.toml').as_posix())
	if 'home' not in paths and 'config_dir' in paths:
		cfg_p = Path(paths['config_dir'])
		if 'config' == cfg_p.name and '.gemini' == cfg_p.parent.name:
			paths['home'] = cfg_p.parent.parent.as_posix()
	return paths
def extract_platform_instances(plat_cfg, *, platform='', include_disabled=False):
	if not isinstance(plat_cfg, dict):
		return {}
	plat_enabled = plat_cfg.get('enabled', True)
	if not isinstance(plat_enabled, bool):
		raise ValueError(f'runtime.json platforms.{platform or "<platform>"}.enabled must be a boolean')
	raw_instances = plat_cfg.get('instances')
	if 'homes' in plat_cfg and isinstance(plat_cfg['homes'], dict):
		raw_homes = plat_cfg.get('homes') or {}
		raw_instances = {name: {'enabled': True, 'home': str(home)} for name, home in raw_homes.items()}
	elif None is raw_instances:
		raw_homes = plat_cfg.get('homes') or {}
		if not isinstance(raw_homes, dict):
			raise ValueError(f'runtime.json platforms.{platform or "<platform>"}.homes must map profile names to home directories')
		raw_instances = {name: {'enabled': True, 'home': str(home)} for name, home in raw_homes.items()}
	elif not isinstance(raw_instances, dict):
		raise ValueError(f'runtime.json platforms.{platform or "<platform>"}.instances must be an object')
	out = {}
	for inst_id, inst_cfg in raw_instances.items():
		if not isinstance(inst_cfg, dict):
			raise ValueError(f'Instance {platform}/{inst_id} configuration must be an object')
		inst_enabled = inst_cfg.get('enabled', True)
		if not isinstance(inst_enabled, bool):
			raise ValueError(f'Instance {platform}/{inst_id}.enabled must be a boolean')
		effective = bool(plat_enabled and inst_enabled)
		if not include_disabled and (not effective):
			continue
		paths = default_system_paths(platform, inst_id, inst_cfg, plat_cfg)
		home_str = paths.get('home') or (str(inst_cfg['home']) if inst_cfg.get('home') else None)
		entry = deepcopy(inst_cfg)
		entry.update({
			'id': inst_id,
			'platform': platform,
			'adapter': platform_adapter_name(platform, plat_cfg),
			'surface': plat_cfg.get('surface'),
			'enabled': effective,
			'platform_enabled': plat_enabled,
			'instance_enabled': inst_enabled,
			'home': home_str,
			'system_paths': paths,
		})
		out[inst_id] = entry
	return out
def extract_platform_homes(plat_cfg, *, platform='', include_disabled=False):
	return {name: item['home'] for name, item in extract_platform_instances(plat_cfg, platform=platform, include_disabled=include_disabled).items() if item.get('home')}
def platform_enabled(platform, *, config=None):
	cfg = (config or settings())['platforms'].get(platform)
	if not isinstance(cfg, dict):
		raise ValueError(f'Unknown Upwork platform: {platform}')
	val = cfg.get('enabled', True)
	if not isinstance(val, bool):
		raise ValueError(f'runtime.json platforms.{platform}.enabled must be a boolean')
	return val
def platform_instances(platform, *, config=None, include_disabled=False):
	cfg = (config or settings())['platforms'].get(platform)
	if None is cfg:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	return extract_platform_instances(cfg, platform=platform, include_disabled=include_disabled)
def platform_homes(platform, *, config=None, include_disabled=False):
	cfg = (config or settings())['platforms'].get(platform)
	if None is cfg:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	return extract_platform_homes(cfg, platform=platform, include_disabled=include_disabled)
def platform_active(platform, *, config=None):
	cfg_all = config or settings()
	plat_cfg = cfg_all['platforms'].get(platform)
	if not isinstance(plat_cfg, dict) or (not platform_enabled(platform, config=cfg_all)):
		return False
	declared = extract_platform_instances(plat_cfg, platform=platform, include_disabled=True)
	if declared:
		return any((item['enabled'] for item in declared.values()))
	return True
def enabled_platforms(*, config=None):
	cfg_all = config or settings()
	return [name for name in cfg_all['platforms'] if platform_active(name, config=cfg_all)]
def instance_entry(instance_id, *, platform=None, config=None, include_disabled=True):
	cfg_all = config or settings()
	matches = []
	targets = [platform] if platform else list(cfg_all['platforms'])
	for plat_id in targets:
		if plat_id not in cfg_all['platforms']:
			raise ValueError(f'Unknown Upwork platform: {plat_id}')
		insts = platform_instances(plat_id, config=cfg_all, include_disabled=include_disabled)
		if instance_id in insts:
			matches.append(insts[instance_id])
	if not matches:
		scope = f'platform {platform}' if platform else 'runtime.json'
		raise ValueError(f'Unknown instance {instance_id!r} in {scope}')
	if 1 < len(matches):
		raise ValueError(f'Instance {instance_id!r} exists in multiple platforms; specify --platform')
	return matches[0]
def instance_paths(instance_id, *, platform=None, config=None, include_disabled=True):
	return instance_entry(instance_id, platform=platform, config=config, include_disabled=include_disabled)['system_paths']
def _exists_flag(path_str):
	text = str(path_str)
	if '*' in text or '?' in text:
		p = Path(text)
		return p.parent.is_dir() and bool(list(p.parent.glob(p.name)))
	return Path(text).exists()
def all_instances(*, config=None, platform=None, include_disabled=True, check_exists=False):
	cfg_all = config or settings()
	if platform and platform not in cfg_all['platforms']:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	plat_names = [platform] if platform else list(cfg_all['platforms'])
	envs = {}
	flat = {}
	for plat_id in plat_names:
		plat_cfg = cfg_all['platforms'][plat_id]
		insts = extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=include_disabled)
		all_decl = extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=True)
		env_entry = {
			'enabled': platform_enabled(plat_id, config=cfg_all),
			'active': platform_active(plat_id, config=cfg_all),
			'label': plat_cfg.get('label', plat_id),
			'surface': plat_cfg.get('surface'),
			'adapter': platform_adapter_name(plat_id, plat_cfg),
			'capabilities': list(plat_cfg.get('capabilities') or []),
			'handoff': deepcopy(plat_cfg.get('handoff') or {}),
			'enabled_instances': [k for k, v in all_decl.items() if v['enabled']],
			'disabled_instances': [k for k, v in all_decl.items() if not v['enabled']],
			'instances': {},
		}
		for iid, item in insts.items():
			record = {
				'id': iid,
				'platform': plat_id,
				'adapter': item['adapter'],
				'surface': item.get('surface'),
				'label': item.get('label', iid),
				'enabled': item['enabled'],
				'platform_enabled': item['platform_enabled'],
				'instance_enabled': item['instance_enabled'],
				'home': item.get('home'),
				'user_data_dir': item.get('user_data_dir'),
				'disabled_reason': item.get('disabled_reason'),
				'system_paths': deepcopy(item['system_paths']),
			}
			if check_exists:
				record['paths_exist'] = {k: _exists_flag(v) for k, v in item['system_paths'].items()}
			env_entry['instances'][iid] = record
			key = f'{plat_id}:{iid}' if iid in flat else iid
			flat[key] = record
		envs[plat_id] = env_entry
	handoff_targets = [{'id': iid, 'platform': plat_id, 'label': inst['label'], 'home': inst['home'], 'system_paths': inst['system_paths']} for plat_id, env in envs.items() for iid, inst in env['instances'].items() if inst['enabled']]
	return {'environments': envs, 'instances': flat, 'enabled_environments': [p for p, e in envs.items() if e['active']], 'available_handoff_targets': handoff_targets}
def _antigravity_backend_has_conversation(backend_dir, conversation_id, *, system_paths=None):
	backend = Path(backend_dir) if backend_dir else None
	if not re.fullmatch('[a-f0-9-]{36}', str(conversation_id or '')):
		return False
	sp = system_paths or {}
	brain_dir = Path(sp['brain_dir']) if sp.get('brain_dir') else (backend / 'brain' if backend else None)
	conv_dir = Path(sp['conversations_dir']) if sp.get('conversations_dir') else (backend / 'conversations' if backend else None)
	if (brain_dir and (brain_dir / conversation_id).is_dir()) or (conv_dir and ((conv_dir / f'{conversation_id}.pb').is_file() or (conv_dir / f'{conversation_id}.db').is_file())):
		return True
	db_path = Path(sp['conversations_db']) if sp.get('conversations_db') else (backend / 'conversation_summaries.db' if backend else None)
	if db_path and db_path.is_file():
		try:
			conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
			try:
				row = conn.execute('SELECT 1 FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
				return bool(row)
			finally:
				conn.close()
		except sqlite3.Error:
			return False
	return False
def _codex_home_conversation_trace(home_dir, conversation_id, *, system_paths=None):
	home = Path(home_dir) if home_dir else None
	if not re.fullmatch('[a-f0-9-]{36}', str(conversation_id or '')):
		return None
	sp = system_paths or {}
	glob_raw = sp.get('state_db_glob')
	db_files = sorted(Path(glob_raw).parent.glob(Path(glob_raw).name)) if glob_raw else (sorted(home.glob('state_*.sqlite')) if home else [])
	for db_file in db_files:
		try:
			conn = sqlite3.connect(db_file.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
			try:
				row = conn.execute('SELECT rollout_path FROM threads WHERE id=?', (conversation_id,)).fetchone()
				if row and row[0]:
					return str(Path(row[0]))
			finally:
				conn.close()
		except sqlite3.Error:
			continue
	sessions = Path(sp['sessions_dir']) if sp.get('sessions_dir') else (home / 'sessions' if home else None)
	if sessions and sessions.is_dir():
		matches = sorted(sessions.rglob(f'*{conversation_id}*.jsonl'))
		if matches:
			return str(matches[0])
	return None
def find_conversation_instance(conversation_id, *, platform=None, config=None, include_disabled=True):
	cfg_all = config or settings()
	targets = [platform] if platform else list(cfg_all['platforms'])
	found = []
	for plat_id in targets:
		if plat_id not in cfg_all['platforms']:
			raise ValueError(f'Unknown Upwork platform: {plat_id}')
		plat_cfg = cfg_all['platforms'][plat_id]
		adapter_kind = platform_adapter_name(plat_id, plat_cfg)
		for iid, item in extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=include_disabled).items():
			sp = item['system_paths']
			if 'antigravity' == adapter_kind:
				backend_str = sp.get('backend_dir')
				if (backend_str or sp.get('brain_dir') or sp.get('conversations_dir') or sp.get('conversations_db')) and _antigravity_backend_has_conversation(backend_str, conversation_id, system_paths=sp):
					backend = Path(backend_str) if backend_str else None
					brain_root = Path(sp['brain_dir']) if sp.get('brain_dir') else (backend / 'brain' if backend else None)
					trace = None
					if brain_root:
						logs_dir = brain_root / conversation_id / '.system_generated/logs'
						full_trace = logs_dir / 'transcript_full.jsonl'
						compact_trace = logs_dir / 'transcript.jsonl'
						trace = full_trace if full_trace.is_file() else compact_trace if compact_trace.is_file() else None
					found.append({'id': iid, 'platform': plat_id, 'enabled': item['enabled'], 'backend_dir': str(backend) if backend else None, 'trace_file': str(trace) if trace else None, 'system_paths': sp})
			elif 'codex' == adapter_kind:
				home_str = sp.get('home')
				if home_str or sp.get('state_db_glob') or sp.get('sessions_dir'):
					trace = _codex_home_conversation_trace(home_str, conversation_id, system_paths=sp)
					if trace:
						found.append({'id': iid, 'platform': plat_id, 'enabled': item['enabled'], 'backend_dir': str(Path(home_str)) if home_str else None, 'trace_file': trace, 'system_paths': sp})
	return found
def resolve_antigravity_paths(backend=None, *, instance=None, conversation_id=None, config=None):
	cfg_all = config
	if None is cfg_all:
		try:
			cfg_all = settings()
		except (OSError, ValueError):
			if None is backend:
				raise
			cfg_all = None
	ag_cfg = ((cfg_all or {}).get('platforms') or {}).get('antigravity')
	ag_insts = extract_platform_instances(ag_cfg, platform='antigravity', include_disabled=True) if isinstance(ag_cfg, dict) else {}
	explicit_inst = instance or _instance.get() or os.environ.get('UPWORK_INSTANCE')
	matched_entry = None
	if None is not backend:
		backend_p = Path(backend)
		backend_res = backend_p.resolve()
		if explicit_inst and explicit_inst in ag_insts:
			cand = ag_insts[explicit_inst]
			cand_bd = cand['system_paths'].get('backend_dir')
			if cand_bd and Path(cand_bd).resolve() == backend_res:
				matched_entry = cand
		if None is matched_entry:
			matches = [cand for cand in ag_insts.values() if cand['system_paths'].get('backend_dir') and Path(cand['system_paths']['backend_dir']).resolve() == backend_res]
			if 1 == len(matches):
				matched_entry = matches[0]
			elif 1 < len(matches):
				if conversation_id:
					conv_matches = [cand for cand in matches if _antigravity_backend_has_conversation(backend_p, conversation_id, system_paths=cand['system_paths'])]
					if 1 == len(conv_matches):
						matched_entry = conv_matches[0]
					elif 1 < len(conv_matches):
						ids = ', '.join((c['id'] for c in conv_matches))
						raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Antigravity instances ({ids}); pass --instance')
				if None is matched_entry:
					matched_entry = matches[0]
		sp = dict((matched_entry or {}).get('system_paths') or {})
	else:
		if explicit_inst:
			matched_entry = instance_entry(explicit_inst, platform='antigravity', config=cfg_all, include_disabled=True)
		elif conversation_id and cfg_all and ('antigravity' in cfg_all.get('platforms', {})):
			matches = find_conversation_instance(conversation_id, platform='antigravity', config=cfg_all, include_disabled=True)
			if 1 == len(matches):
				matched_entry = ag_insts.get(matches[0]['id']) or {'id': matches[0]['id'], 'system_paths': matches[0]['system_paths']}
			elif 1 < len(matches):
				ids = ', '.join((m['id'] for m in matches))
				raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Antigravity instances ({ids}); pass --instance')
		if None is matched_entry:
			home_backend = Path.home() / '.gemini/antigravity'
			home_res = home_backend.resolve()
			home_matches = [cand for cand in ag_insts.values() if cand['system_paths'].get('backend_dir') and Path(cand['system_paths']['backend_dir']).resolve() == home_res]
			if 1 == len(home_matches):
				matched_entry = home_matches[0]
			backend_p = Path(matched_entry['system_paths']['backend_dir']) if matched_entry and matched_entry['system_paths'].get('backend_dir') else home_backend
		else:
			backend_p = Path(matched_entry['system_paths']['backend_dir']) if matched_entry['system_paths'].get('backend_dir') else Path.home() / '.gemini/antigravity'
		sp = dict((matched_entry or {}).get('system_paths') or {})
	backend_res = backend_p.resolve()
	return {
		'instance': matched_entry.get('id') if matched_entry else None,
		'backend_dir': backend_p,
		'brain_dir': Path(sp['brain_dir']) if sp.get('brain_dir') else backend_p / 'brain',
		'conversations_dir': Path(sp['conversations_dir']) if sp.get('conversations_dir') else backend_p / 'conversations',
		'conversations_db': Path(sp['conversations_db']) if sp.get('conversations_db') else backend_p / 'conversation_summaries.db',
		'projects_dir': Path(sp['projects_dir']) if sp.get('projects_dir') else backend_res.parent / 'config/projects',
		'folders_json': Path(sp['folders_json']) if sp.get('folders_json') else None,
		'system_paths': sp,
	}
def resolve_antigravity_backend(backend=None, *, instance=None, conversation_id=None, config=None):
	if None is not backend:
		return Path(backend)
	return resolve_antigravity_paths(backend=None, instance=instance, conversation_id=conversation_id, config=config)['backend_dir']
def resolve_codex_home(backend=None, *, instance=None, conversation_id=None, config=None, codex_cfg=None):
	if None is not backend:
		return Path(backend).resolve()
	cfg_all = config or settings()
	if None is not codex_cfg:
		cfg_all = {**cfg_all, 'platforms': {**cfg_all['platforms'], 'codex': codex_cfg}}
	if 'codex' not in cfg_all['platforms']:
		raise ValueError('Unknown Upwork platform: codex')
	resolved_codex_cfg = cfg_all['platforms']['codex']
	homes = extract_platform_homes(resolved_codex_cfg, platform='codex', include_disabled=True)
	explicit_profile = _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE')
	if explicit_profile:
		if explicit_profile not in homes:
			raise ValueError('Unknown Codex profile')
		return Path(homes[explicit_profile]).resolve()
	if instance:
		entry = instance_entry(instance, platform='codex', config=cfg_all, include_disabled=True)
		if not entry.get('home'):
			raise ValueError('Unknown Codex profile')
		return Path(entry['home']).resolve()
	context_inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
	if context_inst and context_inst in homes:
		return Path(homes[context_inst]).resolve()
	if not os.environ.get('CODEX_HOME') and conversation_id:
		matches = find_conversation_instance(conversation_id, platform='codex', config=cfg_all, include_disabled=True)
		if 1 == len(matches):
			return Path(matches[0]['backend_dir']).resolve()
		if 1 < len(matches):
			ids = ', '.join((m['id'] for m in matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Codex instances ({ids}); pass --instance or --codex-profile')
	name = profile_name(config=cfg_all, include_disabled=True)
	if name not in homes:
		raise ValueError('Unknown Codex profile')
	return Path(homes[name]).resolve()
def resolve_codex_paths(backend=None, *, instance=None, conversation_id=None, config=None, codex_cfg=None):
	home_p = resolve_codex_home(backend, instance=instance, conversation_id=conversation_id, config=config, codex_cfg=codex_cfg)
	resolved_codex_cfg = codex_cfg
	if None is resolved_codex_cfg:
		cfg_all = config
		if None is cfg_all:
			try:
				cfg_all = settings()
			except (OSError, ValueError):
				cfg_all = None
		resolved_codex_cfg = ((cfg_all or {}).get('platforms') or {}).get('codex')
	all_insts = extract_platform_instances(resolved_codex_cfg, platform='codex', include_disabled=True) if isinstance(resolved_codex_cfg, dict) else {}
	explicit_id = _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE') or instance or _instance.get() or os.environ.get('UPWORK_INSTANCE')
	matched_entry = None
	if explicit_id and explicit_id in all_insts:
		cand = all_insts[explicit_id]
		if not cand.get('home') or Path(cand['home']).resolve() == home_p:
			matched_entry = cand
	if None is matched_entry:
		matches = [inst for inst in all_insts.values() if inst.get('home') and Path(inst['home']).resolve() == home_p]
		if 1 == len(matches):
			matched_entry = matches[0]
		elif 1 < len(matches):
			if conversation_id:
				conv_matches = [inst for inst in matches if _codex_home_conversation_trace(inst.get('home'), conversation_id, system_paths=inst['system_paths'])]
				if 1 == len(conv_matches):
					matched_entry = conv_matches[0]
			if None is matched_entry:
				matched_entry = matches[0]
	sp = dict((matched_entry or {}).get('system_paths') or {})
	return {
		'instance': matched_entry.get('id') if matched_entry else None,
		'home': home_p,
		'state_db_glob': sp.get('state_db_glob') or (home_p / 'state_*.sqlite').as_posix(),
		'sessions_dir': Path(sp['sessions_dir']) if sp.get('sessions_dir') else home_p / 'sessions',
		'config_toml': Path(sp['config_toml']) if sp.get('config_toml') else home_p / 'config.toml',
		'system_paths': sp,
	}
def platform_name(value=None, *, config=None):
	cfg_all = config or settings()
	name = value or _platform.get() or os.environ.get('UPWORK_PLATFORM')
	if not name:
		inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
		if inst:
			try:
				name = instance_entry(inst, config=cfg_all, include_disabled=True)['platform']
			except ValueError:
				name = None
	if not name:
		plats = cfg_all['platforms']
		if 'antigravity' in plats and platform_active('antigravity', config=cfg_all):
			name = 'antigravity'
		else:
			active = enabled_platforms(config=cfg_all)
			name = active[0] if active else ('antigravity' if 'antigravity' in plats else next(iter(plats)))
	if name not in cfg_all['platforms']:
		raise ValueError(f'Unknown Upwork platform: {name}')
	r = name
	return r
def profile_name(value=None, *, config=None, include_disabled=True):
	cfg_all = config or settings()
	codex_cfg = cfg_all['platforms'].get('codex')
	if not isinstance(codex_cfg, dict):
		raise ValueError('Unknown Upwork platform: codex')
	all_insts = extract_platform_instances(codex_cfg, platform='codex', include_disabled=True)
	homes = extract_platform_homes(codex_cfg, platform='codex', include_disabled=include_disabled)
	explicit_inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
	if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE'):
		r = value or _profile.get() or os.environ['UPWORK_CODEX_PROFILE']
	elif explicit_inst and explicit_inst in all_insts:
		if not include_disabled and explicit_inst not in homes:
			raise ValueError(f'Codex profile {explicit_inst} is disabled in runtime.json')
		r = explicit_inst
	else:
		current = os.environ.get('CODEX_HOME')
		matches = [name for name, home in homes.items() if current and Path(home).resolve() == Path(current).resolve()]
		if 1 != len(matches):
			choices = '/'.join(homes) if homes else 'none'
			raise ValueError(f'Select --codex-profile {choices} or use a recognized CODEX_HOME')
		r = matches[0]
	return r
def registration_profile_name(value=None, *, config=None):
	cfg_all = config or settings()
	if 'codex' not in cfg_all['platforms']:
		raise ValueError('Unknown Upwork platform: codex')
	plat_cfg = cfg_all['platforms']['codex']
	enabled_homes = extract_platform_homes(plat_cfg, platform='codex', include_disabled=False)
	all_homes = extract_platform_homes(plat_cfg, platform='codex', include_disabled=True)
	if not enabled_homes:
		raise ValueError('Codex has no enabled instances in runtime.json')
	explicit_inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
	if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE') or os.environ.get('CODEX_HOME') or (explicit_inst and explicit_inst in all_homes):
		name = profile_name(value, config=cfg_all, include_disabled=True)
	else:
		name = plat_cfg.get('registration_profile')
		if not name:
			default_inst = [iid for iid, item in extract_platform_instances(plat_cfg, platform='codex', include_disabled=False).items() if item.get('default_registration')]
			if 1 == len(default_inst):
				name = default_inst[0]
		if not name:
			raise ValueError('Select a Codex registration profile or configure registration_profile')
	if name not in all_homes:
		raise ValueError(f'Unknown Codex registration profile: {name}')
	if name not in enabled_homes:
		raise ValueError(f'Codex registration profile {name} is disabled in runtime.json')
	r = name
	return r
def platform_settings(name=None):
	return deepcopy(settings()['platforms'][platform_name(name)])
def role_settings(platform, role, seen=()):
	if role in seen:
		raise ValueError('Cyclic model role inheritance')
	plat = platform_settings(platform)
	roles = plat.get('roles') or {}
	if role not in roles:
		raise ValueError(f'Missing role {role} for platform {platform}')
	value = roles[role]
	fallback = value.get('inherit') or value.get('fallback')
	if fallback:
		r = {**role_settings(platform, fallback, (*seen, role)), **{k: v for k, v in value.items() if 'inherit' != k}}
	else:
		if value.get('selection') not in ('parent', 'inherit') and (not value.get('model') or not value.get('effort')):
			raise ValueError(f'Missing model/effort for {platform}/{role}')
		r = value
	return r
@contextmanager
def using(platform=None, profile=None, instance=None):
	first, second, third = (_platform.set(platform_name(platform)), _profile.set(profile), _instance.set(instance))
	try:
		yield
	finally:
		_platform.reset(first)
		_profile.reset(second)
		_instance.reset(third)
def request_day(value=None):
	from datetime import date, datetime
	from zoneinfo import ZoneInfo
	r = date.fromisoformat(value) if value else datetime.now(ZoneInfo(settings()['timezone'])).date()
	return r
