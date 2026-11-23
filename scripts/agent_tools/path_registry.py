# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce similar_projects parity gate, hooks, and documented CLI contract across turn completion and issue lifecycle":
# https://github.com/dmitry-ai/harness/issues/123
# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add declarative similar_projects registry groups and project overlay resolution":
# https://github.com/dmitry-ai/harness/issues/122
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate OS user home from instance USERPROFILE and auto-detect active Antigravity instance":
# https://github.com/dmitry-ai/harness/issues/115
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
# https://github.com/dmitry-ai/harness/issues/108
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
from collections import OrderedDict
from copy import deepcopy
import glob
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
from .path_cache import clear_path_cache, get_ttl_overlay_links, lookup_fast_project_paths, lru_get, lru_put, mark_overlay_links_refreshed, overlay_signature_for_roots, resolve_reverse_map, store_fast_project_paths
_CODE_ANCHOR = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_FILE = _CODE_ANCHOR / 'paths.json'
_VAR_NAME_RE = re.compile('^[A-Za-z_][A-Za-z0-9_]*$')
_TOKEN_RE = re.compile('\\$\\$\\{|%%|\\$\\{([^}]*)\\}|%([A-Za-z_][A-Za-z0-9_]*)%')
_URI_SCHEME_RE = re.compile('^[A-Za-z][A-Za-z0-9+.-]*://')
_ESC_DOLLAR = '\x00HARNESS_DOLLAR_LBRACE\x00'
_ESC_PERCENT = '\x00HARNESS_PERCENT\x00'
_INITIAL_HOME = Path.home().as_posix().rstrip('/')
_REGISTRY_CACHE: dict[tuple, 'PathRegistry'] = {}
_PROJECT_PATHS_CACHE: OrderedDict[tuple, 'ProjectPaths'] = OrderedDict()
_OVERLAY_REVERSE_MAP: dict[str, Path] = {}
_SIMILAR_REVERSE_MAP: dict[tuple[str, str], list[Path]] = {}
_DISCOVERY_STATE: dict[str, Any] = {'roots_key': None, 'candidate_roots': (), 'fingerprint': None, 'links': {}, 'similar_links': {}}
def clear_registry_cache() -> None:
	from .issues.repo_locator import clear_repo_locator_cache
	_REGISTRY_CACHE.clear()
	_PROJECT_PATHS_CACHE.clear()
	_OVERLAY_REVERSE_MAP.clear()
	_SIMILAR_REVERSE_MAP.clear()
	_DISCOVERY_STATE.update({'roots_key': None, 'candidate_roots': (), 'fingerprint': None, 'links': {}, 'similar_links': {}})
	clear_path_cache()
	clear_repo_locator_cache()
def escape_template_literal(value: str) -> str:
	return str(value).replace('%', '%%').replace('${', '$${')
def _is_linked(path: Path, stop_at: Path | None=None) -> bool:
	stop_norm = os.path.normcase(os.path.abspath(stop_at)) if None is not stop_at else None
	cur = Path(os.path.abspath(path))
	while True:
		if None is not stop_norm and os.path.normcase(str(cur)) == stop_norm:
			break
		try:
			if os.path.lexists(cur) and (cur.is_symlink() or cur.is_junction()):
				return True
		except OSError:
			pass
		if cur.parent == cur:
			break
		cur = cur.parent
	return False
def _path_key(value: str | Path) -> str:
	return str(value).replace('\\', '/').rstrip('/').casefold()
def _resolve_process_home(environ) -> str:
	home = None
	for hk in ('USERPROFILE', 'HOME'):
		for k, v in environ.items():
			if k.upper() == hk and str(v).strip():
				home = normalize_path_str(str(v)).rstrip('/')
				break
		if home:
			break
	if not home:
		try:
			home = Path.home().as_posix().rstrip('/')
		except RuntimeError:
			home = _INITIAL_HOME
	return home
def _resolve_os_user_home(environ) -> str:
	proc_home = _resolve_process_home(environ)
	raw_appdata = None
	for k, v in environ.items():
		if 'APPDATA' == k.upper() and str(v).strip():
			raw_appdata = normalize_path_str(str(v)).rstrip('/')
			break
	if raw_appdata and raw_appdata.casefold().endswith('/appdata/roaming'):
		proc_key = _path_key(proc_home)
		app_key = _path_key(raw_appdata)
		if proc_key == app_key or proc_key.startswith(app_key + '/'):
			app_p = Path(raw_appdata)
			if 2 <= len(app_p.parents):
				cand = app_p.parents[1].as_posix().rstrip('/')
				if cand and Path(cand).parent != Path(cand):
					return cand
	return proc_home
def _lookup_env(name: str, env: dict[str, str] | None=None) -> str | None:
	environ = os.environ if None is env else env
	if name in environ and str(environ[name]).strip():
		return str(environ[name]).replace('\\', '/')
	upper = name.upper()
	for k, v in environ.items():
		if k.upper() == upper and str(v).strip():
			return str(v).replace('\\', '/')
	if 'OS_USER_HOME' == upper:
		return _resolve_os_user_home(environ)
	home = _resolve_process_home(environ)
	if 'USERPROFILE' == upper or 'HOME' == upper:
		return home
	if 'APPDATA' == upper:
		return f'{home}/AppData/Roaming'
	if 'LOCALAPPDATA' == upper:
		return f'{home}/AppData/Local'
	if 'PROGRAMFILES' == upper:
		return 'C:/Program Files'
	if 'SYSTEMROOT' == upper or 'WINDIR' == upper:
		return 'C:/Windows'
	return None
def normalize_path_str(raw: str, *, preserve_trailing_slash: bool=False) -> str:
	if not isinstance(raw, str):
		raise TypeError('Path template value must be a string')
	if not raw:
		return raw
	if _URI_SCHEME_RE.match(raw) or raw.startswith('mailto:'):
		return raw
	had_trailing = raw.endswith(('/', '\\'))
	text = raw.replace('\\', '/')
	if text.startswith('~'):
		text = os.path.expanduser(text).replace('\\', '/')
	is_unc = text.startswith('//') and (not text.startswith('///'))
	drive = ''
	rest = text
	if is_unc:
		rest = text[2:]
	elif re.match('^[A-Za-z]:(?:/|$)', text):
		drive = text[:2]
		rest = text[2:]
	is_abs = bool(drive) or is_unc or rest.startswith('/')
	parts = [seg for seg in rest.split('/') if seg and '.' != seg]
	resolved_parts: list[str] = []
	for seg in parts:
		if '..' == seg:
			if resolved_parts and '..' != resolved_parts[-1] and ('*' not in resolved_parts[-1]) and ('?' not in resolved_parts[-1]):
				resolved_parts.pop()
			elif not is_abs:
				resolved_parts.append(seg)
		else:
			resolved_parts.append(seg)
	joined = '/'.join(resolved_parts)
	if is_unc:
		out = '//' + joined
	elif drive:
		out = f'{drive}/{joined}' if joined else f'{drive}/'
	elif is_abs:
		out = '/' + joined
	else:
		out = joined or '.'
	if preserve_trailing_slash and had_trailing and (not out.endswith('/')):
		out += '/'
	return out
def expand_template(template: str, variables: dict[str, str], *, env: dict[str, str] | None=None, normalize: bool=True, _resolving: tuple[str, ...]=()) -> str:
	if not isinstance(template, str):
		raise TypeError(f'Template must be a string, got {type(template).__name__}')
	if 32 < len(_resolving):
		raise ValueError(f"Path template recursion depth exceeded: {' -> '.join(_resolving)}")
	if '$' not in template and '%' not in template:
		return normalize_path_str(template) if normalize else template
	unclosed_check = template.replace('$${', '')
	if '${' in unclosed_check and None is re.search('\\$\\{[^}]*\\}', unclosed_check):
		raise ValueError(f'Unclosed template variable in {template!r}')
	def _replace(match: re.Match) -> str:
		full = match.group(0)
		if '$${' == full:
			return _ESC_DOLLAR
		if '%%' == full:
			return _ESC_PERCENT
		braced = match.group(1)
		pct = match.group(2)
		if None is not pct:
			val = _lookup_env(pct, env)
			if None is val:
				raise ValueError(f'Unresolved environment variable in path template: %{pct}%')
			return val.replace('${', _ESC_DOLLAR).replace('%', _ESC_PERCENT)
		expr = (braced or '').strip()
		if expr.upper().startswith('ENV:'):
			env_name = expr[4:].strip()
			if not _VAR_NAME_RE.match(env_name):
				raise ValueError(f'Invalid environment variable name in template: ${{{braced}}}')
			val = _lookup_env(env_name, env)
			if None is val:
				raise ValueError(f'Unresolved environment variable in path template: ${{{braced}}}')
			return val.replace('${', _ESC_DOLLAR).replace('%', _ESC_PERCENT)
		if not _VAR_NAME_RE.match(expr):
			raise ValueError(f'Invalid path template variable syntax: ${{{braced}}}')
		if expr in _resolving:
			chain = ' -> '.join((*_resolving, expr))
			raise ValueError(f'Cyclic path template variable reference: {chain}')
		if expr not in variables:
			raise ValueError(f'Unknown path template variable: ${{{expr}}}')
		raw_target = variables[expr]
		resolved_target = expand_template(raw_target, variables, env=env, normalize=False, _resolving=(*_resolving, expr))
		return normalize_path_str(resolved_target, preserve_trailing_slash=True)
	expanded = _TOKEN_RE.sub(_replace, template)
	rem_check = expanded.replace(_ESC_DOLLAR, '')
	if '${' in rem_check:
		raise ValueError(f'Malformed template variable syntax in {template!r}')
	if _resolving:
		return normalize_path_str(expanded) if normalize else expanded
	expanded = expanded.replace(_ESC_DOLLAR, '${').replace(_ESC_PERCENT, '%')
	return normalize_path_str(expanded) if normalize else expanded
def expand_structure(value: Any, variables: dict[str, str], *, env: dict[str, str] | None=None) -> Any:
	if isinstance(value, str):
		if '${' in value or '$${' in value or '%%' in value or re.search('%[A-Za-z_][A-Za-z0-9_]*%', value):
			return expand_template(value, variables, env=env, normalize=True)
		return value
	if isinstance(value, list):
		return [expand_structure(item, variables, env=env) for item in value]
	if isinstance(value, tuple):
		return tuple((expand_structure(item, variables, env=env) for item in value))
	if isinstance(value, dict):
		return {expand_structure(k, variables, env=env) if isinstance(k, str) else k: expand_structure(v, variables, env=env) for k, v in value.items()}
	return value
def _validate_variables_map(raw: Any, label: str) -> dict[str, str]:
	if None is raw:
		return {}
	if not isinstance(raw, dict):
		raise ValueError(f'{label} must be an object mapping variable names to strings')
	out: dict[str, str] = {}
	for k, v in raw.items():
		if not isinstance(k, str) or not _VAR_NAME_RE.match(k):
			raise ValueError(f'{label} contains invalid variable name: {k!r}')
		if not isinstance(v, str) or not v.strip():
			raise ValueError(f'{label}.{k} must be a non-empty string')
		out[k] = v
	return out
def _validate_string_map(raw: Any, label: str) -> dict[str, str]:
	if None is raw:
		return {}
	if not isinstance(raw, dict):
		raise ValueError(f'{label} must be an object')
	out: dict[str, str] = {}
	for k, v in raw.items():
		if not isinstance(k, str) or not k.strip() or (not isinstance(v, str)) or (not v.strip()):
			raise ValueError(f'{label} entries must map non-empty keys to non-empty path strings')
		out[k] = v
	return out
def _validate_string_list(raw: Any, label: str) -> list[str]:
	if None is raw:
		return []
	if not isinstance(raw, list) or any((not isinstance(x, str) or not x.strip() for x in raw)):
		raise ValueError(f'{label} must be a list of non-empty path strings')
	return list(raw)
_SIMILAR_GROUP_ID_RE = re.compile('^[A-Za-z0-9_.-]+$')
def _validate_similar_project_groups(raw: Any, variables: dict[str, str], *, env: dict[str, str] | None=None) -> tuple[dict[str, Any], ...]:
	if None is raw:
		return ()
	if not isinstance(raw, list):
		raise ValueError('paths.json similar_projects must be a list of group objects')
	seen_ids: set[str] = set()
	groups: list[dict[str, Any]] = []
	for idx, grp in enumerate(raw):
		if not isinstance(grp, dict):
			raise ValueError(f'paths.json similar_projects[{idx}] must be an object')
		unknown_g = set(grp) - {'id', 'members', 'projects', 'notes'}
		if unknown_g:
			raise ValueError(f"Unknown keys in similar_projects[{idx}]: {', '.join(sorted(unknown_g))}")
		gid = grp.get('id')
		if not isinstance(gid, str) or not _SIMILAR_GROUP_ID_RE.fullmatch(gid.strip()):
			raise ValueError(f'similar_projects[{idx}].id must be a valid identifier string')
		gid = gid.strip()
		if gid in seen_ids:
			raise ValueError(f'Duplicate similar_projects group id: {gid}')
		seen_ids.add(gid)
		if 'members' in grp and 'projects' in grp:
			raise ValueError(f'similar_projects.{gid} cannot specify both members and projects')
		raw_members = grp.get('members') if 'members' in grp else grp.get('projects')
		if not isinstance(raw_members, list) or 2 > len(raw_members):
			raise ValueError(f'similar_projects.{gid} requires at least 2 members')
		member_keys: set[str] = set()
		aff_owners: list[tuple[Path, str]] = []
		members_out: list[dict[str, Any]] = []
		for m_idx, item in enumerate(raw_members):
			if isinstance(item, str):
				proj_tpl = item
				raw_aff: list[str] = []
			elif isinstance(item, dict):
				unknown_m = set(item) - {'project', 'affiliated_paths', 'notes'}
				if unknown_m:
					raise ValueError(f"Unknown keys in similar_projects.{gid}.members[{m_idx}]: {', '.join(sorted(unknown_m))}")
				proj_tpl = item.get('project')
				raw_aff = _validate_string_list(item.get('affiliated_paths'), f'similar_projects.{gid}.members[{m_idx}].affiliated_paths')
			else:
				raise ValueError(f'similar_projects.{gid}.members[{m_idx}] must be a path string or member object')
			if not isinstance(proj_tpl, str) or not proj_tpl.strip():
				raise ValueError(f'similar_projects.{gid}.members[{m_idx}].project must be a non-empty path string')
			proj_resolved = expand_template(proj_tpl, variables, env=env, normalize=True)
			proj_abs = Path(os.path.abspath(proj_resolved)).as_posix()
			m_key = _path_key(proj_abs)
			if m_key in member_keys:
				raise ValueError(f'Duplicate member project {proj_resolved} in similar_projects.{gid}')
			member_keys.add(m_key)
			aff_resolved_list: list[str] = []
			seen_local_aff: set[str] = set()
			for aff_tpl in raw_aff:
				aff_res = expand_template(aff_tpl, variables, env=env, normalize=True)
				aff_p = Path(os.path.abspath(aff_res))
				a_key = _path_key(aff_p)
				for prev_p, prev_owner in aff_owners:
					if prev_owner != m_key and (a_key == _path_key(prev_p) or aff_p.is_relative_to(prev_p) or prev_p.is_relative_to(aff_p)):
						raise ValueError(f'Overlapping affiliated_paths in similar_projects.{gid}: {aff_res}')
				if a_key not in seen_local_aff:
					seen_local_aff.add(a_key)
					aff_owners.append((aff_p, m_key))
					aff_resolved_list.append(aff_p.as_posix())
			members_out.append({'project': proj_abs, 'affiliated_paths': tuple(aff_resolved_list)})
		groups.append({'id': gid, 'members': tuple(members_out)})
	return tuple(groups)
def _infer_harness_anchor(anchor_code: Path) -> tuple[Path, Path, int]:
	if '\u26ef' == anchor_code.name and 4 <= len(anchor_code.parents) and (anchor_code.parent.name, anchor_code.parents[1].name, anchor_code.parents[2].name) in (('\u2655', '\u227b', '\u2c0f'), ('Deliverables', '\u227b', 'Artifacts')):
		root = anchor_code.parents[3].resolve()
		return (root, root, 2)
	root = anchor_code.parent.resolve()
	meta = (root / '_').resolve() if (root / '_').is_dir() else root
	return (root, meta, 1)
class PathRegistry:
	def __init__(self, source_path: Path, raw: dict[str, Any], *, primary: Path | None=None, env: dict[str, str] | None=None):
		self.source_path = Path(source_path).resolve()
		self.env = dict(env) if None is not env else None
		if not isinstance(raw, dict) or 1 != raw.get('version'):
			raise ValueError(f'{self.source_path.name} requires version 1')
		variables = _validate_variables_map(raw.get('variables'), 'paths.json variables')
		if not variables:
			raise ValueError('paths.json requires non-empty variables')
		anchor_code = Path(primary).resolve() if None is not primary else self.source_path.parent.resolve()
		self.anchor_code = anchor_code
		self.has_synthetic_primary = None is not primary and _path_key(anchor_code) != _path_key(self.source_path.parent.resolve())
		configured_code = expand_template(variables['HARNESS_CODE'], variables, env=self.env, normalize=True) if 'HARNESS_CODE' in variables else ''
		if _path_key(anchor_code) != _path_key(configured_code) or _path_key(anchor_code) != _path_key(_CODE_ANCHOR):
			anchor_root, anchor_meta, anchor_ver = _infer_harness_anchor(anchor_code)
			overrides = {'HARNESS_CODE': escape_template_literal(anchor_code.as_posix()), 'HARNESS_ROOT': escape_template_literal(anchor_root.as_posix()), 'HARNESS_META': escape_template_literal(anchor_meta.as_posix())}
			if 1 == anchor_ver and 'HARNESS_CLEANUP_LOG_DIR' in variables:
				overrides['HARNESS_CLEANUP_LOG_DIR'] = escape_template_literal((anchor_meta / 'Data/Log/cleanup').as_posix())
			variables = {**variables, **overrides}
		self.raw = deepcopy(raw)
		self.raw_variables = variables
		self.resolved_variables = {name: expand_template(val, variables, env=self.env, normalize=True) for name, val in variables.items()}
		if not isinstance(raw.get('tools'), dict):
			raise ValueError('paths.json requires a tools object')
		self.tools = expand_structure(raw['tools'], variables, env=self.env)
		if not isinstance(raw.get('harness_stores'), dict):
			raise ValueError('paths.json requires a harness_stores object')
		self.harness_stores = expand_structure(raw['harness_stores'], variables, env=self.env)
		raw_ws = raw.get('workspace_overrides') or {}
		if not isinstance(raw_ws, dict):
			raise ValueError('paths.json workspace_overrides must be an object')
		self.workspace_overrides: dict[str, dict[str, Any]] = {}
		for ws_tpl, ws_cfg in raw_ws.items():
			if not isinstance(ws_cfg, dict):
				raise ValueError('paths.json workspace_overrides values must be objects')
			ws_resolved = expand_template(ws_tpl, variables, env=self.env, normalize=True)
			self.workspace_overrides[_path_key(ws_resolved)] = {'root': ws_resolved, **expand_structure(ws_cfg, variables, env=self.env)}
		raw_untracked = _validate_string_list(raw.get('untracked_workspaces'), 'paths.json untracked_workspaces')
		self.untracked_workspaces: frozenset[str] = frozenset((_path_key(Path(os.path.abspath(expand_template(item, variables, env=self.env, normalize=True)))) for item in raw_untracked))
		raw_reloc = _validate_string_map(raw.get('relocations') or {}, 'paths.json relocations')
		self.relocations = {_path_key(expand_template(src, variables, env=self.env, normalize=True)): expand_template(dst, variables, env=self.env, normalize=True) for src, dst in raw_reloc.items()}
		raw_plats = raw.get('platform_layouts') or {}
		if not isinstance(raw_plats, dict):
			raise ValueError('paths.json platform_layouts must be an object')
		self.platform_layouts = deepcopy(raw_plats)
		raw_overlays = raw.get('project_overlays') or {}
		if not isinstance(raw_overlays, dict):
			raise ValueError('paths.json project_overlays must be an object')
		self.overlay_candidates = [expand_template(c, variables, env=self.env, normalize=True) for c in _validate_string_list(raw_overlays.get('candidates') or ['.agents/paths.json'], 'project_overlays.candidates')]
		self.overlay_discovery_roots = [expand_template(r, variables, env=self.env, normalize=True) for r in _validate_string_list(raw_overlays.get('discovery_roots') or [], 'project_overlays.discovery_roots')]
		self.overlay_discovery_globs = [expand_template(g, variables, env=self.env, normalize=True) for g in _validate_string_list(raw_overlays.get('discovery_globs') or [], 'project_overlays.discovery_globs')]
		self.similar_project_groups = _validate_similar_project_groups(raw.get('similar_projects'), variables, env=self.env)
		raw_profiles = raw.get('project_profiles') or {}
		if not isinstance(raw_profiles, dict) or 'default' not in raw_profiles:
			raise ValueError('paths.json project_profiles must define at least "default"')
		self.project_profiles = deepcopy(raw_profiles)
		for prof_name in self.project_profiles:
			self._resolve_profile_chain(prof_name)
	def _resolve_profile_chain(self, name: str, seen: tuple[str, ...]=()) -> dict[str, Any]:
		if name in seen:
			raise ValueError(f"Cyclic project profile inheritance: {' -> '.join((*seen, name))}")
		if name not in self.project_profiles:
			raise ValueError(f'Unknown project path profile: {name!r}')
		cfg = self.project_profiles[name]
		if not isinstance(cfg, dict):
			raise ValueError(f'project_profiles.{name} must be an object')
		parent_name = cfg.get('extends')
		if None is not parent_name:
			if not isinstance(parent_name, str) or not parent_name.strip():
				raise ValueError(f'project_profiles.{name}.extends must be a profile name')
			base = self._resolve_profile_chain(parent_name, (*seen, name))
		else:
			base = {'fs_version': 1, 'journal_version': 1, 'variables': {}, 'paths': {}, 'tools': {}, 'code_repos': [], 'auxiliary_repos': {}, 'linked_roots': [], 'similar_projects': [], 'journal_legacy_fallbacks': []}
		raw_fs_ver = cfg.get('fs_version', base['fs_version'])
		if int is not type(raw_fs_ver) or raw_fs_ver not in (1, 2):
			raise ValueError(f'project_profiles.{name}.fs_version must be 1 or 2')
		raw_j_ver = cfg.get('journal_version', base['journal_version'])
		if int is not type(raw_j_ver) or raw_j_ver not in (1, 2, 3):
			raise ValueError(f'project_profiles.{name}.journal_version must be 1, 2, or 3')
		prof_vars = _validate_variables_map(cfg.get('variables'), f'project_profiles.{name}.variables')
		prof_paths = _validate_string_map(cfg.get('paths'), f'project_profiles.{name}.paths')
		prof_tools = deepcopy(cfg.get('tools') or {})
		if not isinstance(prof_tools, dict):
			raise ValueError(f'project_profiles.{name}.tools must be an object')
		prof_code = _validate_string_list(cfg.get('code_repos'), f'project_profiles.{name}.code_repos')
		prof_aux = _validate_string_map(cfg.get('auxiliary_repos'), f'project_profiles.{name}.auxiliary_repos')
		prof_links = _validate_string_list(cfg.get('linked_roots'), f'project_profiles.{name}.linked_roots')
		prof_sim = _validate_string_list(cfg.get('similar_projects'), f'project_profiles.{name}.similar_projects')
		prof_jfb = _validate_string_list(cfg.get('journal_legacy_fallbacks'), f'project_profiles.{name}.journal_legacy_fallbacks')
		return {
			'fs_version': raw_fs_ver,
			'journal_version': raw_j_ver,
			'variables': {**base['variables'], **prof_vars},
			'paths': {**base['paths'], **prof_paths},
			'tools': {**base['tools'], **prof_tools},
			'code_repos': prof_code if 'code_repos' in cfg else list(base['code_repos']),
			'auxiliary_repos': {**base['auxiliary_repos'], **prof_aux},
			'linked_roots': prof_links if 'linked_roots' in cfg else list(base['linked_roots']),
			'similar_projects': prof_sim if 'similar_projects' in cfg else list(base['similar_projects']),
			'journal_legacy_fallbacks': prof_jfb if 'journal_legacy_fallbacks' in cfg else list(base['journal_legacy_fallbacks']),
		}
	def expand(self, template: str, extra_variables: dict[str, str] | None=None) -> str:
		merged = self.raw_variables if not extra_variables else {**self.raw_variables, **extra_variables}
		return expand_template(template, merged, env=self.env, normalize=True)
	def expand_data(self, data: Any, extra_variables: dict[str, str] | None=None) -> Any:
		merged = self.raw_variables if not extra_variables else {**self.raw_variables, **extra_variables}
		return expand_structure(data, merged, env=self.env)
def _env_fingerprint(env: dict[str, str] | None) -> tuple:
	if None is env:
		keys = ('OS_USER_HOME', 'USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'SYSTEMROOT', 'HARNESS_PATHS_FILE')
		return tuple(((k, os.environ.get(k)) for k in keys))
	return tuple(sorted(((str(k), str(v)) for k, v in env.items())))
def load_registry(registry_path: str | Path | None=None, *, primary: str | Path | None=None, env: dict[str, str] | None=None) -> PathRegistry:
	explicit_env = (env if None is not env else os.environ).get('HARNESS_PATHS_FILE')
	if None is not registry_path:
		target = Path(registry_path)
	elif None is not primary and (Path(primary) / 'paths.json').is_file():
		target = Path(primary) / 'paths.json'
	elif explicit_env:
		target = Path(explicit_env)
	else:
		target = DEFAULT_REGISTRY_FILE
	target_abs = Path(os.path.abspath(target))
	try:
		lst = os.lstat(target_abs)
		if stat.S_ISLNK(lst.st_mode) or target_abs.is_junction():
			raise ValueError(f'Linked paths.json registry refused: {target}')
	except FileNotFoundError:
		if _is_linked(target):
			raise ValueError(f'Linked paths.json registry refused: {target}')
		raise
	primary_key = os.path.normcase(os.path.abspath(primary)) if None is not primary else ''
	fast_key = (os.path.normcase(str(target_abs)), lst.st_mtime_ns, lst.st_size, primary_key, _env_fingerprint(env))
	cached = _REGISTRY_CACHE.get(fast_key)
	if None is not cached:
		return cached
	if _is_linked(target):
		raise ValueError(f'Linked paths.json registry refused: {target}')
	resolved = target.resolve()
	raw = json.loads(resolved.read_text(encoding='utf-8-sig'))
	reg = PathRegistry(resolved, raw, primary=Path(primary) if None is not primary else None, env=env)
	if 64 < len(_REGISTRY_CACHE):
		_REGISTRY_CACHE.clear()
	_REGISTRY_CACHE[fast_key] = reg
	return reg
def var_value(name: str, *, registry: PathRegistry | None=None) -> str:
	reg = registry or load_registry()
	if name not in reg.resolved_variables:
		raise KeyError(f'Unknown registry variable: {name}')
	return reg.resolved_variables[name]
def store_value(name: str, *, registry: PathRegistry | None=None) -> Any:
	reg = registry or load_registry()
	if name not in reg.harness_stores:
		raise KeyError(f'Unknown harness store entry: {name}')
	return deepcopy(reg.harness_stores[name])
def store_path(name: str, *, registry: PathRegistry | None=None) -> Path:
	val = store_value(name, registry=registry)
	if not isinstance(val, str):
		raise TypeError(f'Harness store {name!r} is not a single path string')
	return Path(val)
def tool_value(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> Any:
	reg = registry or load_registry()
	if None is not project_root:
		pp = project_paths(project_root, registry=reg)
		if name in pp.tools:
			return deepcopy(pp.tools[name])
	if name not in reg.tools:
		raise KeyError(f'Unknown tool entry in paths.json: {name}')
	return deepcopy(reg.tools[name])
def tool_path(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> Path:
	val = tool_value(name, project_root=project_root, registry=registry)
	if not isinstance(val, str):
		raise TypeError(f'Tool entry {name!r} is not a single path string')
	return Path(val)
def tool_list(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> list[str]:
	val = tool_value(name, project_root=project_root, registry=registry)
	if isinstance(val, list):
		return [str(x) for x in val]
	if isinstance(val, str):
		return [val]
	raise TypeError(f'Tool entry {name!r} is not a list of strings')
def workspace_override(path: str | Path, key: str | None=None, *, registry: PathRegistry | None=None) -> Any:
	reg = registry or load_registry()
	entry = reg.workspace_overrides.get(_path_key(Path(path).resolve()))
	if None is entry:
		return None
	return entry.get(key) if None is not key else deepcopy(entry)
def relocated_roots(*, registry: PathRegistry | None=None) -> dict[str, str]:
	reg = registry or load_registry()
	return dict(reg.relocations)
def relocated_harness_code_dirs(*, primary: str | Path | None=None, registry: PathRegistry | None=None) -> tuple[Path, ...]:
	reg = registry or load_registry()
	cur_code = Path(os.path.abspath(primary)) if None is not primary else (Path(reg.resolved_variables.get('HARNESS_CODE', '')).resolve() if reg.resolved_variables.get('HARNESS_CODE') else None)
	h_root = reg.resolved_variables.get('HARNESS_ROOT')
	legacy_prim = reg.harness_stores.get('legacy_primary')
	v2_rels = ('\u2c0f/\u227b/\u2655/\u26ef', 'Artifacts/\u227b/Deliverables/\u26ef', 'code')
	cands: list[str] = []
	if None is not cur_code:
		if cur_code.parts[-4:] in (('\u2c0f', '\u227b', '\u2655', '\u26ef'), ('Artifacts', '\u227b', 'Deliverables', '\u26ef')):
			base = cur_code.parents[3]
			cands.extend((str(base / rel) for rel in v2_rels))
		elif 'code' == cur_code.name:
			base = cur_code.parent
			cands.extend((str(base / rel) for rel in v2_rels))
	if h_root:
		cands.extend((f'{h_root}/{rel}' for rel in v2_rels))
	if isinstance(legacy_prim, str):
		cands.append(legacy_prim)
	out: list[Path] = []
	for raw in cands:
		p = Path(os.path.abspath(raw))
		if (None is cur_code or _path_key(p) != _path_key(cur_code)) and all((_path_key(p) != _path_key(x) for x in out)):
			out.append(p)
	return tuple(out)
def derive_platform_system_paths(adapter_kind: str, explicit_paths: dict[str, str] | None=None, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, plat_cfg: dict[str, Any] | None=None, registry: PathRegistry | None=None) -> dict[str, str]:
	reg = registry or load_registry()
	layout = reg.platform_layouts.get(adapter_kind)
	explicit = dict(explicit_paths or {})
	plat_cfg = plat_cfg if isinstance(plat_cfg, dict) else {}
	if not isinstance(layout, dict):
		paths: dict[str, str] = {}
		if home:
			paths['home'] = normalize_path_str(str(home))
		if user_data_dir:
			paths['user_data_dir'] = normalize_path_str(str(user_data_dir))
		paths.update(explicit)
		return paths
	has_wildcard = lambda s: '*' in str(s or '') or '?' in str(s or '')
	raw_home = explicit.get('home') if 'home' in explicit else (str(home) if home else None)
	home_norm = normalize_path_str(raw_home) if isinstance(raw_home, str) and raw_home.strip() and (not has_wildcard(raw_home)) else None
	raw_udd = explicit.get('user_data_dir') if 'user_data_dir' in explicit else (str(user_data_dir) if user_data_dir else None)
	udd_norm = normalize_path_str(raw_udd) if isinstance(raw_udd, str) and raw_udd.strip() and (not has_wildcard(raw_udd)) else None
	if None is home_norm and 'codex' == adapter_kind:
		for key in ('config_toml', 'agents_md', 'session_index', 'global_state', 'ui_folders', 'logs_db', 'memories_db', 'models_cache_json', 'sessions_dir', 'agents_dir', 'skills_dir', 'state_db_glob'):
			if key in explicit and (not has_wildcard(Path(explicit[key]).parent)):
				home_norm = Path(explicit[key]).parent.as_posix()
				break
	ctx_vars = dict(reg.raw_variables)
	if home_norm:
		ctx_vars['INSTANCE_HOME'] = home_norm
	if udd_norm:
		ctx_vars['INSTANCE_USER_DATA'] = udd_norm
	if 'antigravity' == adapter_kind:
		defaults_cfg = layout.get('defaults') or {}
		gemini_norm = explicit.get('gemini_dir')
		if not gemini_norm and home_norm and defaults_cfg.get('gemini_dir'):
			gemini_norm = expand_template(defaults_cfg['gemini_dir'], ctx_vars, env=reg.env, normalize=True)
		if gemini_norm:
			ctx_vars['INSTANCE_GEMINI_DIR'] = gemini_norm
		cfg_dir_norm = explicit.get('config_dir')
		if not cfg_dir_norm:
			if 'projects_dir' in explicit and 'projects' == Path(explicit['projects_dir']).name:
				cfg_dir_norm = Path(explicit['projects_dir']).parent.as_posix()
			elif gemini_norm and defaults_cfg.get('config_dir'):
				cfg_dir_norm = expand_template(defaults_cfg['config_dir'], ctx_vars, env=reg.env, normalize=True)
		if cfg_dir_norm:
			ctx_vars['INSTANCE_CONFIG_DIR'] = cfg_dir_norm
		backend_norm = explicit.get('backend_dir')
		if not backend_norm:
			for key in ('conversations_db', 'brain_dir', 'conversations_dir', 'annotations_dir', 'knowledge_dir'):
				if key in explicit:
					backend_norm = Path(explicit[key]).parent.as_posix()
					break
		if not backend_norm and gemini_norm and defaults_cfg.get('backend_dir'):
			backend_norm = expand_template(defaults_cfg['backend_dir'], ctx_vars, env=reg.env, normalize=True)
		if backend_norm:
			ctx_vars['INSTANCE_BACKEND_DIR'] = backend_norm
	paths_out: dict[str, str] = {}
	for slot_key, tpl in (layout.get('system_paths') or {}).items():
		needed_vars = [m.group(1).strip() for m in _TOKEN_RE.finditer(tpl) if m.group(1) and (not m.group(1).strip().upper().startswith('ENV:'))]
		if all((v in ctx_vars for v in needed_vars)):
			paths_out[slot_key] = expand_template(tpl, ctx_vars, env=reg.env, normalize=True)
	if 'antigravity' == adapter_kind:
		if isinstance(plat_cfg.get('folders_json'), str) and plat_cfg['folders_json'].strip():
			paths_out['folders_json'] = reg.expand(plat_cfg['folders_json'])
		if isinstance(plat_cfg.get('addons_profiles_json'), str) and plat_cfg['addons_profiles_json'].strip():
			paths_out['addons_profiles_json'] = reg.expand(plat_cfg['addons_profiles_json'])
	elif 'codex' == adapter_kind:
		if isinstance(plat_cfg.get('ui_manage'), str) and plat_cfg['ui_manage'].strip():
			paths_out['ui_manage'] = reg.expand(plat_cfg['ui_manage'])
	paths_out.update(explicit)
	if 'antigravity' == adapter_kind:
		if 'gemini_dir' not in paths_out:
			if 'config_dir' in paths_out and 'config' == Path(paths_out['config_dir']).name:
				paths_out['gemini_dir'] = Path(paths_out['config_dir']).parent.as_posix()
			elif 'backend_dir' in paths_out and 'antigravity' == Path(paths_out['backend_dir']).name:
				paths_out['gemini_dir'] = Path(paths_out['backend_dir']).parent.as_posix()
		if 'home' not in paths_out and 'config_dir' in paths_out:
			cfg_p = Path(paths_out['config_dir'])
			if 'config' == cfg_p.name and '.gemini' == cfg_p.parent.name:
				paths_out['home'] = cfg_p.parent.parent.as_posix()
	return paths_out
def default_platform_paths(adapter_kind: str, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, registry: PathRegistry | None=None) -> dict[str, str]:
	reg = registry or load_registry()
	layout = reg.platform_layouts.get(adapter_kind) or {}
	extra_vars = None
	if None is home:
		if None is reg.env:
			try:
				extra_vars = {'USER_HOME': escape_template_literal(Path.home().as_posix())}
			except RuntimeError:
				extra_vars = None
		else:
			proc_h = _lookup_env('USERPROFILE', reg.env)
			if proc_h:
				extra_vars = {'USER_HOME': escape_template_literal(proc_h)}
	eff_home = normalize_path_str(str(home)) if None is not home else (reg.expand(layout['default_home'], extra_vars) if layout.get('default_home') else (normalize_path_str(Path.home().as_posix()) if None is reg.env else _INITIAL_HOME))
	eff_udd = normalize_path_str(str(user_data_dir)) if None is not user_data_dir else (reg.expand(layout['default_user_data_dir'], extra_vars) if layout.get('default_user_data_dir') else None)
	return derive_platform_system_paths(adapter_kind, None, home=eff_home, user_data_dir=eff_udd, registry=reg)
def discover_overlay_file(root: str | Path, *, registry: PathRegistry | None=None, _resolved_root: bool=False) -> Path | None:
	reg = registry or load_registry()
	root_p = Path(root) if _resolved_root else Path(root).resolve()
	if not root_p.is_dir():
		return None
	found: list[Path] = []
	for rel in reg.overlay_candidates:
		cand = root_p / rel
		if not os.path.lexists(cand):
			continue
		if _is_linked(cand, stop_at=root_p):
			raise ValueError(f'Linked project paths.json overlay preserved and refused: {cand}')
		if cand.is_file():
			found.append(cand.resolve())
	if 1 < len(found):
		contents = {p.read_bytes() for p in found}
		if 1 < len(contents):
			joined = ', '.join((str(p) for p in found))
			raise ValueError(f'Conflicting project paths.json overlays in {root_p}: {joined}')
	return found[0] if found else None
def _validate_overlay(raw: Any, overlay_path: Path, reg: PathRegistry) -> dict[str, Any]:
	if not isinstance(raw, dict):
		raise ValueError(f'Project overlay {overlay_path} must be a JSON object')
	version = raw.get('version', 1)
	if 1 != version:
		raise ValueError(f'Project overlay {overlay_path} requires version 1')
	allowed_keys = {'version', 'fs_version', 'journal_version', 'profile', 'extends', 'tracked', 'variables', 'paths', 'tools', 'code_repos', 'auxiliary_repos', 'linked_roots', 'similar_projects', 'deliverable_segments', 'source_dirs', 'notes'}
	unknown = set(raw) - allowed_keys
	if unknown:
		raise ValueError(f"Unknown keys in project overlay {overlay_path}: {', '.join(sorted(unknown))}")
	fs_ver = raw.get('fs_version')
	if None is not fs_ver and (int is not type(fs_ver) or fs_ver not in (1, 2)):
		raise ValueError(f'Project overlay {overlay_path} fs_version must be 1 or 2')
	j_ver = raw.get('journal_version')
	if None is not j_ver and (int is not type(j_ver) or j_ver not in (1, 2, 3)):
		raise ValueError(f'Project overlay {overlay_path} journal_version must be 1, 2, or 3')
	tracked = raw.get('tracked')
	if None is not tracked and (bool is not type(tracked)):
		raise ValueError(f'Project overlay {overlay_path} tracked must be a boolean')
	profile = raw.get('profile') or raw.get('extends')
	if None is not profile:
		if not isinstance(profile, str) or profile not in reg.project_profiles:
			raise ValueError(f'Unknown profile {profile!r} in {overlay_path}')
	return {
		'version': 1,
		'fs_version': fs_ver,
		'journal_version': j_ver,
		'profile': profile,
		'tracked': tracked,
		'variables': _validate_variables_map(raw.get('variables'), f'{overlay_path} variables'),
		'paths': _validate_string_map(raw.get('paths'), f'{overlay_path} paths'),
		'tools': deepcopy(raw.get('tools') or {}) if isinstance(raw.get('tools') or {}, dict) else (_ for _ in ()).throw(ValueError(f'{overlay_path} tools must be an object')),
		'code_repos': _validate_string_list(raw.get('code_repos'), f'{overlay_path} code_repos'),
		'auxiliary_repos': _validate_string_map(raw.get('auxiliary_repos'), f'{overlay_path} auxiliary_repos'),
		'linked_roots': _validate_string_list(raw.get('linked_roots'), f'{overlay_path} linked_roots'),
		'similar_projects': _validate_string_list(raw.get('similar_projects'), f'{overlay_path} similar_projects'),
		'deliverable_segments': _validate_string_list(raw.get('deliverable_segments'), f'{overlay_path} deliverable_segments'),
		'source_dirs': _validate_string_list(raw.get('source_dirs'), f'{overlay_path} source_dirs'),
	}
_JOURNAL_BUCKET_DIR_RE = re.compile('^(\\d+)[-\\u2013](\\d+)$')
def _canonical_journal_bucket(step: int, bucket_size: int=20) -> str:
	start = ((step - 1) // bucket_size) * bucket_size + 1
	return f'{start}\u2013{start + bucket_size - 1}'
def _inspect_journal_dir_on_disk(j_dir: Path, reg: PathRegistry) -> tuple[int | None, tuple[str, str] | None]:
	j_out = reg.resolved_variables.get('JOURNAL_OUT_DIR_NAME', '\u227b')
	j_in = reg.resolved_variables.get('JOURNAL_IN_DIR_NAME', '\u227a')
	b_raw = reg.resolved_variables.get('JOURNAL_BUCKET_SIZE', '20')
	b_size = int(b_raw) if str(b_raw).isdigit() and 0 < int(b_raw) else 20
	has_v2 = (j_dir / j_out).is_dir() or (j_dir / j_in).is_dir()
	has_v1 = (j_dir / 'req').is_dir() or (j_dir / 'res').is_dir()
	if has_v2 and (not has_v1):
		for side_name in (j_out, j_in):
			side_p = j_dir / side_name
			if not side_p.is_dir():
				continue
			try:
				children = list(side_p.iterdir())
			except OSError:
				continue
			for child in children:
				if child.is_file() and '.md' == child.suffix.lower() and child.stem.isascii() and child.stem.isdigit() and 1 <= int(child.stem):
					return (2, (j_out, j_in))
				if child.is_dir() and _JOURNAL_BUCKET_DIR_RE.fullmatch(child.name):
					try:
						b_files = [bf for bf in child.iterdir() if bf.is_file() and '.md' == bf.suffix.lower() and bf.stem.isascii() and bf.stem.isdigit() and 1 <= int(bf.stem)]
					except OSError:
						b_files = []
					if not b_files or any((child.name != _canonical_journal_bucket(int(bf.stem), b_size) for bf in b_files)):
						return (2, (j_out, j_in))
		return (3, (j_out, j_in))
	if has_v1 or j_dir.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
		return (1, ('req', 'res'))
	return (None, None)
def _journal_cache_sig(root: Path, reg: PathRegistry) -> tuple:
	j_name = reg.resolved_variables.get('JOURNAL_DIR_NAME', '\ua66e')
	j_out = reg.resolved_variables.get('JOURNAL_OUT_DIR_NAME', '\u227b')
	j_in = reg.resolved_variables.get('JOURNAL_IN_DIR_NAME', '\u227a')
	meta_name = reg.resolved_variables.get('META_DIR_NAME', '_')
	sig: list[tuple] = []
	for base in (root / j_name, root / meta_name / j_name):
		for rel in ('', j_out, j_in, 'req', 'res', '1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
			cand = base / rel if rel else base
			try:
				st = os.stat(cand)
				sig.append((rel, True, st.st_mtime_ns))
			except OSError:
				sig.append((rel, False, 0))
	return tuple(sig)
def _has_v2_markers(root: Path, reg: PathRegistry) -> bool:
	book_name = reg.resolved_variables.get('BOOK_DIR_NAME', '\U0001f56e')
	art_name = reg.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
	art_out = reg.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
	art_in = reg.resolved_variables.get('ARTIFACTS_IN_DIR_NAME', '\u227a')
	return (root / book_name).is_dir() or (root / art_name / art_out).is_dir() or (root / art_name / art_in).is_dir() or (root / 'Artifacts' / art_out).is_dir() or (root / 'Artifacts' / art_in).is_dir()
def _v2_software_deliverable_dir(root: Path, reg: PathRegistry) -> Path:
	art_name = reg.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
	art_out = reg.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
	deliv_name = reg.resolved_variables.get('DELIVERABLES_DIR_NAME', '\u2655')
	sw_name = reg.resolved_variables.get('SOFTWARE_DIR_NAME', '\u26ef')
	cand = root / art_name / art_out / deliv_name / sw_name
	if not cand.exists() and (root / 'Artifacts' / art_out / 'Deliverables' / sw_name).exists():
		return root / 'Artifacts' / art_out / 'Deliverables' / sw_name
	return cand
def canonicalize_root_dir(value: str | Path, *, registry: PathRegistry | None=None) -> Path:
	reg = registry or load_registry()
	meta_name = reg.resolved_variables.get('META_DIR_NAME', '_')
	agent_name = reg.resolved_variables.get('AGENT_DIR_NAME', '\ua616')
	sw_name = reg.resolved_variables.get('SOFTWARE_DIR_NAME', '\u26ef')
	srv_name = reg.resolved_variables.get('SERVER_DIR_NAME', '\U0001d412')
	web_name = reg.resolved_variables.get('WEBSITE_DIR_NAME', '\U0001d416')
	art_name = reg.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
	art_out = reg.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
	deliv_name = reg.resolved_variables.get('DELIVERABLES_DIR_NAME', '\u2655')
	path = Path(value).resolve()
	if path.name in ('code', meta_name) and (path.parent / 'code').is_dir() and (path.parent / meta_name).is_dir():
		path = path.parent.resolve()
	elif path.name == sw_name and 4 <= len(path.parents) and (path.parent.name, path.parents[1].name, path.parents[2].name) in ((deliv_name, art_out, art_name), ('Deliverables', art_out, 'Artifacts')):
		cand_root = path.parents[3].resolve()
		if (cand_root / agent_name).is_dir() or (cand_root / '.agents').is_dir() or _has_v2_markers(cand_root, reg):
			path = cand_root
	elif path.name in (sw_name, srv_name) or (path / '.git').exists():
		chain = (path, *path.parents)
		for idx, node in enumerate(chain):
			if node.name in (srv_name, web_name) and idx + 5 < len(chain):
				if chain[idx + 1].name == sw_name and (chain[idx + 2].name, chain[idx + 3].name) in ((deliv_name, art_out), ('Deliverables', art_out)) and chain[idx + 4].name in (art_name, 'Artifacts'):
					cand_root = chain[idx + 5].resolve()
					if (cand_root / agent_name).is_dir() or (cand_root / '.agents').is_dir() or _has_v2_markers(cand_root, reg):
						path = cand_root
						break
	for _ in range(4):
		key = _path_key(path)
		if key not in reg.relocations:
			break
		next_p = Path(reg.relocations[key]).resolve()
		if next_p == path:
			break
		path = next_p
	return path
def same_project_root(first: str | Path | None, second: str | Path | None, *, registry: PathRegistry | None=None) -> bool:
	if None is first or None is second:
		return False
	s1, s2 = (str(first).strip(), str(second).strip())
	if not s1 or not s2 or (isinstance(first, str) and (not Path(s1).is_absolute())) or (isinstance(second, str) and (not Path(s2).is_absolute())):
		return False
	reg = registry or load_registry()
	try:
		return _path_key(canonicalize_root_dir(s1, registry=reg)) == _path_key(canonicalize_root_dir(s2, registry=reg))
	except (OSError, ValueError):
		return False
def _glob_parent_stat(pattern: str) -> tuple:
	prefix = re.split('[*?\\[]', pattern, maxsplit=1)[0].rstrip('/\\')
	parent = Path(prefix) if prefix else Path('.')
	if not parent.is_dir():
		parent = parent.parent
	try:
		st = os.stat(parent)
		return (str(parent), st.st_mtime_ns, st.st_size)
	except OSError:
		return (str(parent), None, None)
def _candidate_discovery_roots(reg: PathRegistry) -> tuple[tuple, tuple[Path, ...]]:
	idx_str = reg.harness_stores.get('upwork_projects_index')
	daily_str = reg.resolved_variables.get('UPWORK_DAILY_ROOT')
	idx_stat = None
	if isinstance(idx_str, str):
		try:
			st = os.stat(idx_str)
			idx_stat = (st.st_mtime_ns, st.st_size)
		except OSError:
			idx_stat = None
	glob_stats = tuple((_glob_parent_stat(g_str) for g_str in reg.overlay_discovery_globs))
	disc_stats = []
	for r_str in reg.overlay_discovery_roots:
		disc_stats.append((r_str, os.path.isdir(r_str)))
	roots_key = (reg.source_path.as_posix(), idx_stat, glob_stats, tuple(disc_stats))
	if _DISCOVERY_STATE['roots_key'] == roots_key:
		return (roots_key, _DISCOVERY_STATE['candidate_roots'])
	candidate_roots: list[Path] = []
	seen_keys: set[str] = set()
	def _push(p: Path) -> None:
		rk = _path_key(p)
		if rk not in seen_keys:
			seen_keys.add(rk)
			candidate_roots.append(p)
	for r_str in reg.overlay_discovery_roots:
		rp = Path(r_str)
		if rp.is_dir():
			_push(rp.resolve())
	for g_str in reg.overlay_discovery_globs:
		for match in sorted(glob.glob(g_str)):
			mp = Path(match)
			if mp.is_dir():
				_push(mp.resolve())
	if None is not idx_stat and isinstance(idx_str, str) and isinstance(daily_str, str):
		idx_file = Path(idx_str)
		daily_dir = Path(daily_str)
		if daily_dir.is_dir():
			try:
				entries = json.loads(idx_file.read_text(encoding='utf-8'))
				if isinstance(entries, dict):
					for rel in entries.values():
						if isinstance(rel, str) and rel.strip():
							cand = (daily_dir / rel).resolve()
							if cand.is_dir():
								_push(cand)
							else:
								ck = _path_key(cand)
								if ck in reg.relocations:
									reloc = Path(reg.relocations[ck]).resolve()
									if reloc.is_dir():
										_push(reloc)
			except (OSError, ValueError):
				pass
	frozen = tuple(candidate_roots)
	_DISCOVERY_STATE['roots_key'] = roots_key
	_DISCOVERY_STATE['candidate_roots'] = frozen
	return (roots_key, frozen)
def _refresh_known_overlay_links(reg: PathRegistry) -> dict[str, Path]:
	ttl_links = get_ttl_overlay_links(reg, DEFAULT_REGISTRY_FILE, _DISCOVERY_STATE)
	if None is not ttl_links:
		return ttl_links
	roots_key, candidate_roots = _candidate_discovery_roots(reg)
	ov_sig = overlay_signature_for_roots(candidate_roots, reg.overlay_candidates)
	sim_fp = tuple(((g['id'], tuple((m['project'] for m in g['members']))) for g in reg.similar_project_groups))
	fp = (roots_key, ov_sig, sim_fp)
	if _DISCOVERY_STATE['fingerprint'] == fp:
		mark_overlay_links_refreshed(reg, DEFAULT_REGISTRY_FILE)
		return dict(_DISCOVERY_STATE['links'])
	links: dict[str, Path] = {}
	similar_links: dict[str, list[Path]] = {}
	for root_p in candidate_roots:
		rk = _path_key(root_p)
		try:
			ov_file = discover_overlay_file(root_p, registry=reg)
			if None is not ov_file:
				pp = ProjectPaths(root_p, registry=reg, _register_links=False)
				for ext in (*pp.linked_roots, *pp.code_repos, *pp.auxiliary_repos.values()):
					ek = _path_key(ext)
					if ek != rk:
						links[ek] = root_p
				for sp in pp._direct_similar_projects:
					sk = _path_key(sp)
					if sk != rk and all((_path_key(prev) != rk for prev in similar_links.get(sk, ()))):
						similar_links.setdefault(sk, []).append(root_p)
		except (OSError, ValueError):
			continue
	_DISCOVERY_STATE.update({'fingerprint': fp, 'links': links, 'similar_links': similar_links})
	mark_overlay_links_refreshed(reg, DEFAULT_REGISTRY_FILE)
	return dict(links)
def _find_local_marker_root(start: Path, reg: PathRegistry) -> tuple[int | None, Path | None]:
	agent_name = reg.resolved_variables.get('AGENT_DIR_NAME', '\ua616')
	journal_name = reg.resolved_variables.get('JOURNAL_DIR_NAME', '\ua66e')
	meta_name = reg.resolved_variables.get('META_DIR_NAME', '_')
	book_name = reg.resolved_variables.get('BOOK_DIR_NAME', '\U0001f56e')
	art_name = reg.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
	art_out = reg.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
	art_in = reg.resolved_variables.get('ARTIFACTS_IN_DIR_NAME', '\u227a')
	bounded: list[tuple[int, Path]] = []
	for idx, anc in enumerate((start, *start.parents)):
		ak = _path_key(anc)
		if ak in reg.workspace_overrides and anc != start:
			break
		bounded.append((idx, anc))
	for idx, anc in bounded:
		if anc.name in (agent_name, journal_name) and anc.parent.name == meta_name and anc.parent.parent.is_dir():
			return (idx, canonicalize_root_dir(anc.parent.parent, registry=reg))
		if (anc / meta_name).is_dir() and ((anc / 'code').is_dir() or (anc / meta_name / journal_name).is_dir() or (anc / meta_name / agent_name).is_dir()):
			return (idx, canonicalize_root_dir(anc, registry=reg))
		if (anc / agent_name / 'project.json').is_file():
			return (idx, anc)
		if anc.name == agent_name and anc.parent.is_dir():
			p = anc.parent
			if _path_key(p) not in reg.workspace_overrides:
				return (idx, canonicalize_root_dir(p, registry=reg))
		if (anc / agent_name).is_dir():
			return (idx, anc)
		if '.agents' == anc.name and anc.parent.is_dir():
			return (idx, canonicalize_root_dir(anc.parent, registry=reg))
		if (anc / '.agents').is_dir():
			return (idx, anc)
		if anc.name == book_name and anc.parent.is_dir() and _path_key(anc.parent) not in reg.workspace_overrides:
			return (idx, canonicalize_root_dir(anc.parent, registry=reg))
		if (anc / book_name).is_dir() or (anc / art_name / art_out).is_dir() or (anc / art_name / art_in).is_dir() or (anc / 'Artifacts' / art_out).is_dir() or (anc / 'Artifacts' / art_in).is_dir():
			return (idx, anc)
	for idx, anc in bounded:
		if anc.name == journal_name and anc.parent.is_dir() and _path_key(anc.parent) not in reg.workspace_overrides:
			return (idx, anc.parent)
		if (anc / journal_name).is_dir():
			return (idx, anc)
	return (None, None)
def resolve_project_root(target: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None) -> Path:
	reg = registry or load_registry(env=env)
	raw_p = Path(target)
	resolved = raw_p.resolve()
	start = resolved.parent if resolved.exists() and (not resolved.is_dir()) else resolved
	start = canonicalize_root_dir(start, registry=reg)
	start_key = _path_key(start)
	if start_key in reg.workspace_overrides:
		return start
	if start.name in ('.agents', '.codex') and _path_key(start.parent) in reg.workspace_overrides:
		return start.parent
	for anc in (start, *start.parents):
		ak = _path_key(anc)
		if ak in reg.workspace_overrides and anc != start:
			break
		if discover_overlay_file(anc, registry=reg, _resolved_root=True):
			return canonicalize_root_dir(anc, registry=reg)
	local_idx, local_root = _find_local_marker_root(start, reg)
	reverse_map = resolve_reverse_map(start, local_idx, local_root, reg, DEFAULT_REGISTRY_FILE, _DISCOVERY_STATE, _OVERLAY_REVERSE_MAP, _refresh_known_overlay_links)
	if reverse_map:
		ancestors = (start, *start.parents)
		bound = len(ancestors) if None is local_idx else local_idx + 1
		for anc in ancestors[:bound]:
			ak = _path_key(anc)
			if ak in reverse_map and reverse_map[ak].is_dir():
				return reverse_map[ak]
	if None is not local_root:
		return local_root
	return start
def _infer_default_profile(root: Path, overlay_file: Path | None, reg: PathRegistry, *, explicit_fs_version: int | None=None) -> str:
	meta_name = reg.resolved_variables.get('META_DIR_NAME', '_')
	agent_name = reg.resolved_variables.get('AGENT_DIR_NAME', '\ua616')
	journal_name = reg.resolved_variables.get('JOURNAL_DIR_NAME', '\ua66e')
	if 2 == explicit_fs_version:
		return 'v2_software' if (_v2_software_deliverable_dir(root, reg) / '.git').exists() and 'v2_software' in reg.project_profiles else ('v2' if 'v2' in reg.project_profiles else 'default')
	if None is not overlay_file and overlay_file.parent.name == agent_name and overlay_file.parent.parent.name == meta_name:
		return 'dual_repo'
	if (root / meta_name).is_dir() and ((root / 'code').is_dir() or (root / meta_name / journal_name).is_dir() or (root / meta_name / agent_name).is_dir()):
		return 'dual_repo'
	if 1 != explicit_fs_version and _has_v2_markers(root, reg):
		if (_v2_software_deliverable_dir(root, reg) / '.git').exists() and 'v2_software' in reg.project_profiles:
			return 'v2_software'
		if 'v2' in reg.project_profiles:
			return 'v2'
	pjson = root / agent_name / 'project.json'
	if pjson.is_file():
		if 1 != explicit_fs_version and 'v2' in reg.project_profiles:
			try:
				pdata = json.loads(pjson.read_text(encoding='utf-8-sig'))
				if isinstance(pdata, dict) and 2 == pdata.get('fs_version'):
					return 'v2'
			except (OSError, ValueError):
				pass
		return 'upwork'
	return 'default'
class ProjectPaths:
	def __init__(self, root: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None, _register_links: bool=True):
		self.registry = registry or load_registry(env=env)
		self.root = canonicalize_root_dir(root, registry=self.registry)
		self.overlay_file = discover_overlay_file(self.root, registry=self.registry)
		self.overlay = _validate_overlay(json.loads(self.overlay_file.read_text(encoding='utf-8-sig')), self.overlay_file, self.registry) if None is not self.overlay_file else None
		self.has_overlay = None is not self.overlay
		self.tracked: bool | None = self.overlay.get('tracked') if self.overlay else None
		ov_fs_ver = self.overlay.get('fs_version') if self.overlay else None
		self.profile = (self.overlay.get('profile') if self.overlay else None) or _infer_default_profile(self.root, self.overlay_file, self.registry, explicit_fs_version=ov_fs_ver)
		prof_spec = self.registry._resolve_profile_chain(self.profile)
		self.fs_version = ov_fs_ver if None is not ov_fs_ver else prof_spec['fs_version']
		ws_ovr = self.registry.workspace_overrides.get(_path_key(self.root))
		raw_paths = dict(prof_spec['paths'])
		if ws_ovr:
			for k in ('data_dir', 'cleanup_log_dir', 'browser_locks_dir'):
				if k in ws_ovr and isinstance(ws_ovr[k], str):
					raw_paths[k] = ws_ovr[k]
		self._explicit_overlay_paths: set[str] = set()
		if self.overlay:
			raw_paths.update(self.overlay['paths'])
			self._explicit_overlay_paths = set(self.overlay['paths'])
		merged_vars = dict(self.registry.raw_variables)
		merged_vars.update(prof_spec['variables'])
		if self.overlay:
			merged_vars.update(self.overlay['variables'])
		ov_vars = self.overlay['variables'] if self.overlay else {}
		if 2 == self.fs_version and 'ARTIFACTS_DIR_NAME' not in ov_vars and 'ARTIFACTS_DIR' not in ov_vars:
			cur_art = self.registry.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
			if not (self.root / cur_art).exists() and (self.root / 'Artifacts').is_dir():
				merged_vars['ARTIFACTS_DIR_NAME'] = 'Artifacts'
				art_out = self.registry.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
				if 'DELIVERABLES_DIR_NAME' not in ov_vars and (self.root / 'Artifacts' / art_out / 'Deliverables').is_dir():
					merged_vars['DELIVERABLES_DIR_NAME'] = 'Deliverables'
				if 'INTERMEDIARY_DIR_NAME' not in ov_vars and (self.root / 'Artifacts' / art_out / 'Intermediary').is_dir():
					merged_vars['INTERMEDIARY_DIR_NAME'] = 'Intermediary'
		merged_vars['PROJECT_ROOT'] = escape_template_literal(self.root.as_posix())
		eff_slot_tpls: dict[str, str] = {}
		slot_vars: dict[str, str] = {}
		var_to_slot: dict[str, str] = {}
		for slot_key, slot_tpl in raw_paths.items():
			slot_var = re.sub('[^A-Za-z0-9_]', '_', slot_key).upper()
			eff_tpl = slot_tpl
			if _VAR_NAME_RE.match(slot_var):
				self_tok = f'${{{slot_var}}}'
				if self_tok in eff_tpl and slot_var in merged_vars:
					eff_tpl = eff_tpl.replace(self_tok, merged_vars[slot_var])
				slot_vars[slot_key] = slot_var
				var_to_slot[slot_var] = slot_key
			eff_slot_tpls[slot_key] = eff_tpl
		self._variables = merged_vars
		self.paths_str: dict[str, str] = {}
		def _resolve_slot(slot_key: str, resolving_vars: tuple[str, ...]=()) -> str:
			if slot_key in self.paths_str:
				return self.paths_str[slot_key]
			slot_var = slot_vars.get(slot_key)
			eff_tpl = eff_slot_tpls[slot_key]
			next_chain = (*resolving_vars, slot_var) if slot_var else resolving_vars
			for m in _TOKEN_RE.finditer(eff_tpl):
				ref = (m.group(1) or '').strip()
				if not ref or ref.upper().startswith('ENV:'):
					continue
				if ref in next_chain:
					raise ValueError(f"Cyclic path template variable reference: {' -> '.join((*next_chain, ref))}")
				if ref in var_to_slot:
					_resolve_slot(var_to_slot[ref], next_chain)
			had_trailing = eff_tpl.endswith(('/', '\\'))
			resolved_val = expand_template(eff_tpl, merged_vars, env=self.registry.env, normalize=True)
			if not Path(resolved_val).is_absolute() and (not _URI_SCHEME_RE.match(resolved_val)):
				resolved_val = normalize_path_str(f'{self.root.as_posix()}/{resolved_val}')
			self.paths_str[slot_key] = resolved_val
			if slot_var:
				var_val = resolved_val + ('/' if had_trailing and (not resolved_val.endswith('/')) else '')
				merged_vars[slot_var] = escape_template_literal(var_val)
			return resolved_val
		for slot_key in raw_paths:
			_resolve_slot(slot_key)
		merged_tools = deepcopy(self.registry.tools)
		merged_tools.update(expand_structure(prof_spec['tools'], merged_vars, env=self.registry.env))
		if self.overlay and self.overlay['tools']:
			merged_tools.update(expand_structure(self.overlay['tools'], merged_vars, env=self.registry.env))
		self.tools = merged_tools
		raw_code = self.overlay['code_repos'] if self.overlay and self.overlay['code_repos'] else prof_spec['code_repos']
		self.code_repos = tuple((Path(self._resolve_rel_to_root(item)).resolve() for item in raw_code))
		raw_aux = {**prof_spec['auxiliary_repos'], **(self.overlay['auxiliary_repos'] if self.overlay else {})}
		self.auxiliary_repos = {k: Path(self._resolve_rel_to_root(v)).resolve() for k, v in raw_aux.items()}
		raw_links = self.overlay['linked_roots'] if self.overlay and self.overlay['linked_roots'] else prof_spec['linked_roots']
		self.linked_roots = tuple((Path(self._resolve_rel_to_root(item)).resolve() for item in raw_links))
		raw_sim = self.overlay['similar_projects'] if self.overlay and self.overlay['similar_projects'] else prof_spec['similar_projects']
		direct_sim: list[Path] = []
		seen_sim: set[str] = {_path_key(self.root)}
		def _push_sim(cand: Path) -> None:
			ck = _path_key(cand)
			if ck not in seen_sim:
				seen_sim.add(ck)
				direct_sim.append(cand)
		for item in raw_sim:
			_push_sim(canonicalize_root_dir(self._resolve_rel_to_root(item), registry=self.registry))
		self_key = _path_key(self.root)
		for grp in self.registry.similar_project_groups:
			mem_roots = [canonicalize_root_dir(mem['project'], registry=self.registry) for mem in grp['members']]
			if any((_path_key(mr) == self_key for mr in mem_roots)):
				for mr in mem_roots:
					_push_sim(mr)
		self._direct_similar_projects = tuple(direct_sim)
		self._include_reverse_similar = _register_links
		self.journal_legacy_fallbacks = tuple((Path(self._resolve_rel_to_root(item)) for item in prof_spec['journal_legacy_fallbacks']))
		ov_j_ver = self.overlay.get('journal_version') if self.overlay else None
		cfg_j_ver = ov_j_ver if None is not ov_j_ver else prof_spec['journal_version']
		j_root = Path(self.paths_str['journal_root_dir'])
		j_cur = self.journal_dir
		if self.has_explicit_path('journal_dir') or self.journal_glob:
			if not j_cur.is_dir() and j_cur.parent == j_root and j_cur.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437') and (None is not _inspect_journal_dir_on_disk(j_root, self.registry)[0]):
				j_eff = j_root
				self.paths_str['journal_dir'] = j_eff.as_posix()
			else:
				j_eff = j_cur
		elif None is not _inspect_journal_dir_on_disk(j_root, self.registry)[0]:
			j_eff = j_root
		else:
			fb_hit = next((fb for fb in self.journal_legacy_fallbacks if fb != j_root and fb.is_dir()), None)
			if None is not fb_hit:
				j_eff = fb_hit
				self.paths_str['journal_dir'] = normalize_path_str(j_eff.as_posix())
			else:
				j_eff = j_cur
		disk_j_ver, disk_j_pair = _inspect_journal_dir_on_disk(j_eff, self.registry)
		self.journal_version = disk_j_ver if None is not disk_j_ver else cfg_j_ver
		eff_j_pair = disk_j_pair if None is not disk_j_pair else ((self.registry.resolved_variables.get('JOURNAL_OUT_DIR_NAME', '\u227b'), self.registry.resolved_variables.get('JOURNAL_IN_DIR_NAME', '\u227a')) if 2 <= self.journal_version else ('req', 'res'))
		if 'journal_req_dir' not in self._explicit_overlay_paths:
			self.paths_str['journal_req_dir'] = normalize_path_str(f'{j_eff.as_posix()}/{eff_j_pair[0]}')
		if 'journal_res_dir' not in self._explicit_overlay_paths:
			self.paths_str['journal_res_dir'] = normalize_path_str(f'{j_eff.as_posix()}/{eff_j_pair[1]}')
		self.deliverable_segments = tuple((self.overlay['deliverable_segments'] if self.overlay and self.overlay['deliverable_segments'] else ('/letters/', '/result/', '/defects/', '/articles/', '/\u2c3f/\u227b/\u2655/', '/artifacts/\u227b/deliverables/')))
		self.source_dirs = tuple((Path(self._resolve_rel_to_root(item)) for item in (self.overlay['source_dirs'] if self.overlay else ())))
		if _register_links and (self.has_overlay or self._direct_similar_projects):
			self._register_reverse_links()
	def _register_reverse_links(self) -> None:
		rk = _path_key(self.root)
		if self.has_overlay:
			for ext in (*self.linked_roots, *self.code_repos, *self.auxiliary_repos.values()):
				ek = _path_key(ext)
				if ek != rk:
					_OVERLAY_REVERSE_MAP[ek] = self.root
		reg_key = _path_key(self.registry.source_path)
		for sp in self._direct_similar_projects:
			sk = (reg_key, _path_key(sp))
			peers = _SIMILAR_REVERSE_MAP.setdefault(sk, [])
			if all((_path_key(p) != rk for p in peers)):
				peers.append(self.root)
	def rel_to_root(self, target: str | Path) -> str:
		p = Path(target).resolve()
		return p.relative_to(self.root).as_posix() if p.is_relative_to(self.root) else p.as_posix()
	def _resolve_rel_to_root(self, tpl: str) -> str:
		val = expand_template(tpl, self._variables, env=self.registry.env, normalize=True)
		if not Path(val).is_absolute() and (not _URI_SCHEME_RE.match(val)):
			val = normalize_path_str(f'{self.root.as_posix()}/{val}')
		return val
	def has_explicit_path(self, name: str) -> bool:
		return name in self._explicit_overlay_paths
	def path(self, name: str, default: str | Path | None=None) -> Path | None:
		if name in self.paths_str:
			return Path(self.paths_str[name])
		return Path(default) if None is not default else None
	def var(self, name: str, default: str | None=None) -> str | None:
		if name in self._variables:
			return expand_template(f'${{{name}}}', self._variables, env=self.registry.env, normalize=True)
		return default
	def expand(self, template: str) -> str:
		return self._resolve_rel_to_root(template)
	@property
	def agents_config_dir(self) -> Path:
		return Path(self.paths_str['agents_config_dir'])
	@property
	def codex_config_toml(self) -> Path:
		return Path(self.paths_str['codex_config_toml'])
	@property
	def agent_dir(self) -> Path:
		return Path(self.paths_str['agent_dir'])
	@property
	def data_dir(self) -> Path:
		return Path(self.paths_str['data_dir'])
	@property
	def kb_dir(self) -> Path:
		return Path(self.paths_str['kb_dir'])
	@property
	def manual_kb_dir(self) -> Path:
		return Path(self.paths_str['manual_kb_dir'])
	@property
	def source_dir(self) -> Path:
		return Path(self.paths_str['source_dir'])
	@property
	def evidence_dir(self) -> Path:
		return Path(self.paths_str['evidence_dir'])
	@property
	def scratch_dir(self) -> Path:
		return Path(self.paths_str['scratch_dir'])
	@property
	def turns_dir(self) -> Path:
		return Path(self.paths_str['turns_dir'])
	@property
	def worktrees_dir(self) -> Path:
		return Path(self.paths_str['worktrees_dir'])
	@property
	def journal_root_dir(self) -> Path:
		return Path(self.paths_str['journal_root_dir'])
	@property
	def journal_dir(self) -> Path:
		if not self.has_explicit_path('journal_dir') and self.journal_glob:
			matches = sorted((Path(m).resolve() for m in glob.glob(self.journal_glob, recursive=True) if Path(m).is_dir()))
			if matches:
				return matches[-1]
		return Path(self.paths_str['journal_dir'])
	@property
	def journal_glob(self) -> str | None:
		return self.paths_str.get('journal_glob')
	@property
	def context_output(self) -> Path:
		return Path(self.paths_str['context_output'])
	@property
	def context_config(self) -> Path:
		return Path(self.paths_str['context_config'])
	@property
	def project_json(self) -> Path:
		return Path(self.paths_str['project_json'])
	@property
	def text_project_json(self) -> Path:
		return Path(self.paths_str['text_project_json'])
	@property
	def workflow_json(self) -> Path:
		return Path(self.paths_str['workflow_json'])
	@property
	def continuation_md(self) -> Path:
		return Path(self.paths_str['continuation_md'])
	@property
	def registrations_json(self) -> Path:
		return Path(self.paths_str['registrations_json'])
	@property
	def verified_claims_json(self) -> Path:
		return Path(self.paths_str['verified_claims_json'])
	@property
	def facts_json(self) -> Path:
		return Path(self.paths_str['facts_json'])
	@property
	def grounding_cache_json(self) -> Path:
		return Path(self.paths_str['grounding_cache_json'])
	@property
	def metrics_json(self) -> Path:
		return Path(self.paths_str['metrics_json'])
	@property
	def executors_json(self) -> Path:
		return Path(self.paths_str['executors_json'])
	@property
	def rendered_json(self) -> Path:
		return Path(self.paths_str['rendered_json'])
	@property
	def http_index_json(self) -> Path:
		return Path(self.paths_str['http_index_json'])
	@property
	def similar_projects(self) -> tuple[Path, ...]:
		out: list[Path] = list(self._direct_similar_projects)
		seen: set[str] = {_path_key(self.root), *(_path_key(p) for p in out)}
		if self._include_reverse_similar:
			_refresh_known_overlay_links(self.registry)
			rk = _path_key(self.root)
			reg_key = _path_key(self.registry.source_path)
			rev_peers = [*_DISCOVERY_STATE['similar_links'].get(rk, ()), *_SIMILAR_REVERSE_MAP.get((reg_key, rk), ())]
			for peer in rev_peers:
				pk = _path_key(peer)
				if pk not in seen:
					seen.add(pk)
					out.append(peer)
		return tuple(out)
	def to_dict(self, *, check_exists: bool=True) -> dict[str, Any]:
		def _exists(p_str: str) -> bool:
			if '*' in p_str or '?' in p_str:
				return any((Path(m).exists() for m in glob.glob(p_str, recursive=True)))
			return Path(p_str).exists()
		paths_view = dict(self.paths_str)
		paths_view['journal_dir'] = self.journal_dir.as_posix()
		sim_projects = self.similar_projects
		out: dict[str, Any] = {
			'project_root': self.root.as_posix(),
			'fs_version': self.fs_version,
			'journal_version': self.journal_version,
			'profile': self.profile,
			'has_overlay': self.has_overlay,
			'overlay_file': self.overlay_file.as_posix() if self.overlay_file else None,
			'paths': paths_view,
			'code_repos': [p.as_posix() for p in self.code_repos],
			'auxiliary_repos': {k: p.as_posix() for k, p in self.auxiliary_repos.items()},
			'linked_roots': [p.as_posix() for p in self.linked_roots],
			'similar_projects': [p.as_posix() for p in sim_projects],
			'tools': deepcopy(self.tools),
		}
		if check_exists:
			out['paths_exist'] = {k: _exists(v) for k, v in paths_view.items()}
			out['code_repos_exist'] = {p.as_posix(): p.is_dir() for p in self.code_repos}
			out['linked_roots_exist'] = {p.as_posix(): p.exists() for p in self.linked_roots}
			out['similar_projects_exist'] = {p.as_posix(): p.is_dir() for p in sim_projects}
		return out
def project_paths(path_or_root: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None, exact_root: bool=False) -> ProjectPaths:
	reg = registry or load_registry(env=env)
	fast_key = (id(reg), str(path_or_root), bool(exact_root))
	fast_hit = lookup_fast_project_paths(fast_key, reg, len(_OVERLAY_REVERSE_MAP))
	if None is not fast_hit:
		if fast_hit.has_overlay or fast_hit._direct_similar_projects:
			fast_hit._register_reverse_links()
		return fast_hit
	root = canonicalize_root_dir(path_or_root, registry=reg) if exact_root else resolve_project_root(path_or_root, registry=reg, env=env)
	ov_file = discover_overlay_file(root, registry=reg, _resolved_root=True)
	ov_sig = (ov_file.as_posix(), (st := ov_file.stat()).st_mtime_ns, st.st_size, hash(ov_file.read_bytes())) if None is not ov_file else None
	cache_key = (id(reg), root.as_posix(), ov_sig, _infer_default_profile(root, ov_file, reg), _journal_cache_sig(root, reg))
	pp = lru_get(_PROJECT_PATHS_CACHE, cache_key)
	if None is pp:
		pp = ProjectPaths(root, registry=reg, env=env)
		lru_put(_PROJECT_PATHS_CACHE, cache_key, pp)
	elif pp.has_overlay or pp._direct_similar_projects:
		pp._register_reverse_links()
	store_fast_project_paths(fast_key, pp, reg, len(_OVERLAY_REVERSE_MAP))
	return pp
_EXCLUDED_PROJECT_IDS = frozenset(('outside-of-project', 'default-cli-project'))
def _is_registered_single_project(canon: Path, *, registry: PathRegistry, projects_dirs=None) -> bool:
	dirs: list[Path] = []
	if None is not projects_dirs:
		for d in projects_dirs:
			if d:
				dirs.append(Path(d))
	else:
		seen_dirs: set[str] = set()
		def _add_dir(raw_d: str | Path | None) -> None:
			if not raw_d:
				return
			p = Path(raw_d)
			dk = _path_key(p)
			if dk not in seen_dirs:
				seen_dirs.add(dk)
				dirs.append(p)
		try:
			from . import runtime as rt_mod
			cfg = rt_mod.settings()
			if 'antigravity' in (cfg.get('platforms') or {}):
				for inst in rt_mod.platform_instances('antigravity', config=cfg, include_disabled=False).values():
					_add_dir((inst.get('system_paths') or {}).get('projects_dir'))
		except Exception:
			pass
		if not dirs:
			try:
				_add_dir(default_platform_paths('antigravity', registry=registry).get('projects_dir'))
			except Exception:
				pass
	target_key = _path_key(canon)
	from .platforms.trace_common import extract_resource_uri, local_uri_to_path
	for pdir in dirs:
		if not pdir.is_dir():
			continue
		try:
			files = sorted(pdir.glob('*.json'))
		except OSError:
			continue
		for pf in files:
			if pf.stem.casefold() in _EXCLUDED_PROJECT_IDS:
				continue
			try:
				data = json.loads(pf.read_text(encoding='utf-8-sig'))
			except (OSError, ValueError):
				continue
			if not isinstance(data, dict):
				continue
			pid = str(data.get('id') or '').strip().casefold()
			if pid in _EXCLUDED_PROJECT_IDS:
				continue
			resources = (data.get('projectResources') or {}).get('resources') if isinstance(data.get('projectResources'), dict) else None
			if not isinstance(resources, list) or 1 != len(resources):
				continue
			uri = extract_resource_uri(resources[0])
			if not uri:
				continue
			try:
				res_path = canonicalize_root_dir(local_uri_to_path(uri), registry=registry)
			except (OSError, ValueError):
				continue
			if _path_key(res_path) == target_key:
				return True
	return False
def is_tracked_workspace(root: str | Path, *, registry: PathRegistry | None=None, projects_dirs=None) -> tuple[bool, Path]:
	reg = registry or load_registry()
	raw_canon = canonicalize_root_dir(root, registry=reg)
	raw_key = _path_key(raw_canon)
	if raw_key in reg.untracked_workspaces or None is not workspace_override(raw_canon, registry=reg):
		return (False, raw_canon)
	pp_exact = project_paths(raw_canon, registry=reg, exact_root=True)
	if False is pp_exact.tracked:
		return (False, raw_canon)
	if pp_exact.has_overlay or pp_exact.project_json.is_file() or pp_exact.journal_dir.is_dir() or pp_exact.turns_dir.is_dir():
		return (True, raw_canon)
	resolved = resolve_project_root(raw_canon, registry=reg)
	if _path_key(resolved) != raw_key:
		res_key = _path_key(resolved)
		if res_key in reg.untracked_workspaces or None is not workspace_override(resolved, registry=reg):
			return (False, resolved)
		pp_res = project_paths(resolved, registry=reg, exact_root=True)
		if False is pp_res.tracked:
			return (False, resolved)
		if pp_res.has_overlay or pp_res.project_json.is_file() or pp_res.journal_dir.is_dir() or pp_res.turns_dir.is_dir():
			return (True, resolved)
	if _is_registered_single_project(raw_canon, registry=reg, projects_dirs=projects_dirs):
		return (True, raw_canon)
	return (False, raw_canon)
def evaluate_similar_project_touches(touched_repo_files: list[Path] | tuple[Path, ...] | set[Path], *, registry: PathRegistry | None=None) -> list[dict[str, Any]]:
	reg = registry or load_registry()
	resolved_files: list[Path] = []
	seen_files: set[str] = set()
	for raw_f in touched_repo_files or ():
		if not raw_f:
			continue
		try:
			fp = Path(raw_f).resolve()
		except OSError:
			continue
		fk = _path_key(fp)
		if fk not in seen_files:
			seen_files.add(fk)
			resolved_files.append(fp)
	if not resolved_files:
		return []
	def _project_match_roots(proj_root: Path) -> list[Path]:
		roots = [proj_root]
		try:
			pp_m = project_paths(proj_root, registry=reg, exact_root=True)
			for cr in (*pp_m.code_repos, *pp_m.auxiliary_repos.values()):
				if all((_path_key(cr) != _path_key(x) for x in roots)):
					roots.append(cr)
		except (OSError, ValueError):
			pass
		return roots
	emitted: dict[str, dict[str, Any]] = {}
	def _record_peer(peer_root: Path, *, group_id: str | None, source_projects: list[Path], source_label: str, peer_touched: bool) -> None:
		pk = _path_key(peer_root)
		prev = emitted.get(pk)
		if None is prev:
			emitted[pk] = {'group_id': group_id, 'source_projects': list(source_projects), 'source_label': source_label, 'peer_root': peer_root, 'peer_touched': bool(peer_touched)}
		else:
			if None is prev['group_id'] and None is not group_id:
				prev['group_id'] = group_id
			prev['peer_touched'] = prev['peer_touched'] or bool(peer_touched)
			for sp in source_projects:
				if all((_path_key(sp) != _path_key(x) for x in prev['source_projects'])):
					prev['source_projects'].append(sp)
	file_project_roots: dict[str, Path] = {}
	for fp in resolved_files:
		try:
			file_project_roots[_path_key(fp)] = project_paths(fp, registry=reg).root
		except (OSError, ValueError):
			file_project_roots[_path_key(fp)] = canonicalize_root_dir(fp.parent, registry=reg)
	for grp in reg.similar_project_groups:
		members_state: list[dict[str, Any]] = []
		for mem in grp['members']:
			m_root = canonicalize_root_dir(mem['project'], registry=reg)
			m_roots = _project_match_roots(m_root)
			m_affs = [Path(a).resolve() for a in mem['affiliated_paths']]
			hits: list[Path] = []
			for fp in resolved_files:
				if any((fp == r or fp.is_relative_to(r) for r in m_roots)) or any((fp == a or fp.is_relative_to(a) for a in m_affs)):
					hits.append(fp)
			members_state.append({'root': m_root, 'hits': hits})
		touched_members = [ms for ms in members_state if ms['hits']]
		if touched_members:
			for ms in members_state:
				src_mems = [tm for tm in touched_members if _path_key(tm['root']) != _path_key(ms['root'])]
				if not src_mems:
					continue
				src_parts = []
				for tm in src_mems:
					names = sorted({h.name for h in tm['hits']})[:3]
					src_parts.append(f"{tm['root'].as_posix()} ({', '.join(names)})")
				_record_peer(ms['root'], group_id=grp['id'], source_projects=[tm['root'] for tm in src_mems], source_label='; '.join(src_parts), peer_touched=bool(ms['hits']))
	touched_root_keys = {_path_key(r) for r in file_project_roots.values()}
	for fp in resolved_files:
		src_root = file_project_roots[_path_key(fp)]
		try:
			pp_f = project_paths(src_root, registry=reg, exact_root=True)
		except (OSError, ValueError):
			continue
		for peer_root in pp_f.similar_projects:
			pk = _path_key(peer_root)
			if pk == _path_key(src_root):
				continue
			peer_roots = _project_match_roots(peer_root)
			peer_hit = pk in touched_root_keys or any((f2 == pr or f2.is_relative_to(pr) for f2 in resolved_files for pr in peer_roots))
			_record_peer(peer_root, group_id=None, source_projects=[src_root], source_label=f'{src_root.as_posix()} ({fp.name})', peer_touched=peer_hit)
	return [emitted[k] for k in sorted(emitted, key=lambda key: str(emitted[key]['peer_root']))]
def paths_report(project: str | Path | None=None, *, expand: str | None=None, check: bool=False, registry: PathRegistry | None=None) -> dict[str, Any]:
	reg = registry or load_registry()
	issues: list[dict[str, str]] = []
	discovered_overlays: list[dict[str, Any]] = []
	if check:
		for grp in reg.similar_project_groups:
			for mem in grp['members']:
				m_proj = Path(mem['project'])
				if not m_proj.is_dir():
					issues.append({'file': reg.source_path.as_posix(), 'message': f"Missing similar_projects member directory in group '{grp['id']}': {m_proj.as_posix()}"})
				for aff in mem['affiliated_paths']:
					aff_p = Path(os.path.abspath(aff))
					aff_ok = aff_p.exists() or (reg.has_synthetic_primary and aff_p.is_relative_to(Path(os.path.abspath(reg.anchor_code))) and (reg.source_path.parent / aff_p.relative_to(Path(os.path.abspath(reg.anchor_code)))).exists())
					if not aff_ok:
						issues.append({'file': reg.source_path.as_posix(), 'message': f"Missing similar_projects affiliated path in group '{grp['id']}': {aff_p.as_posix()}"})
	if check or None is project:
		roots_to_check: list[Path] = []
		for r_str in reg.overlay_discovery_roots:
			if Path(r_str).is_dir():
				roots_to_check.append(Path(r_str).resolve())
		for g_str in reg.overlay_discovery_globs:
			for m in sorted(glob.glob(g_str)):
				if Path(m).is_dir():
					roots_to_check.append(Path(m).resolve())
		idx_str = reg.harness_stores.get('upwork_projects_index')
		daily_str = reg.resolved_variables.get('UPWORK_DAILY_ROOT')
		if isinstance(idx_str, str) and isinstance(daily_str, str) and Path(idx_str).is_file() and Path(daily_str).is_dir():
			try:
				entries = json.loads(Path(idx_str).read_text(encoding='utf-8'))
				if isinstance(entries, dict):
					for rel in entries.values():
						if isinstance(rel, str) and (Path(daily_str) / rel).is_dir():
							roots_to_check.append((Path(daily_str) / rel).resolve())
			except (OSError, ValueError) as exc:
				issues.append({'file': idx_str, 'message': str(exc)})
		seen: set[str] = set()
		for rp in roots_to_check:
			rk = _path_key(rp)
			if rk in seen:
				continue
			seen.add(rk)
			try:
				ov = discover_overlay_file(rp, registry=reg)
				if None is not ov:
					pp_i = ProjectPaths(rp, registry=reg)
					sim_list = [p.as_posix() for p in pp_i.similar_projects]
					if check:
						for sp in pp_i.similar_projects:
							if not sp.is_dir():
								issues.append({'file': ov.as_posix(), 'message': f'Missing similar_projects target directory: {sp.as_posix()}'})
					discovered_overlays.append({'project_root': pp_i.root.as_posix(), 'overlay_file': ov.as_posix(), 'profile': pp_i.profile, 'fs_version': pp_i.fs_version, 'journal_version': pp_i.journal_version, 'similar_projects': sim_list})
			except (OSError, ValueError) as exc:
				issues.append({'file': rp.as_posix(), 'message': str(exc)})
	if None is not project:
		try:
			pp = project_paths(project, registry=reg)
			if check:
				for sp in pp.similar_projects:
					if not sp.is_dir():
						msg = f'Missing similar_projects target directory: {sp.as_posix()}'
						if all((it.get('message') != msg for it in issues)):
							issues.append({'file': (pp.overlay_file or reg.source_path).as_posix(), 'message': msg})
			payload = pp.to_dict(check_exists=True)
			if None is not expand:
				payload['expanded'] = pp.expand(expand)
			payload['registry_file'] = reg.source_path.as_posix()
			if check:
				payload['valid'] = not issues
				payload['issues'] = issues
			return payload
		except (OSError, ValueError) as exc:
			if check:
				return {'valid': False, 'registry_file': reg.source_path.as_posix(), 'issues': [*issues, {'file': str(project), 'message': str(exc)}]}
			raise
	out: dict[str, Any] = {
		'valid': not issues,
		'registry_file': reg.source_path.as_posix(),
		'variables': dict(reg.resolved_variables),
		'tools': deepcopy(reg.tools),
		'harness_stores': deepcopy(reg.harness_stores),
		'workspace_overrides': deepcopy(reg.workspace_overrides),
		'relocations': dict(reg.relocations),
		'similar_projects': [deepcopy(g) for g in reg.similar_project_groups],
		'profiles': list(reg.project_profiles),
		'discovered_overlays': discovered_overlays,
		'issues': issues,
	}
	if None is not expand:
		out['expanded'] = reg.expand(expand)
	return out
