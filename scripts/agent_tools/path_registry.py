# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from collections import OrderedDict
from copy import deepcopy
import glob
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
# 2026-11-24
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
# 2026-11-24
# "Fix worktree scope resolution for new files in TDD classifier":
# https://github.com/dmitry-ai/harness/issues/188
from .path_cache import clear_path_cache, default_runtime_file, get_ttl_overlay_links, lookup_fast_project_paths, lru_get, lru_put, mark_overlay_links_refreshed, overlay_signature_for_roots, resolve_code_anchor, resolve_reverse_map, store_fast_project_paths
# 2026-11-24
# "Fix worktree scope resolution for new files in TDD classifier":
# https://github.com/dmitry-ai/harness/issues/188
_CODE_ANCHOR = resolve_code_anchor(Path(__file__).resolve().parents[2])
DEFAULT_REGISTRY_FILE = Path(__file__).resolve().parents[2] / 'paths.json'
_VAR_NAME_RE = re.compile('^[A-Za-z_][A-Za-z0-9_]*$')
_TOKEN_RE = re.compile('\\$\\$\\{|%%|\\$\\{([^}]*)\\}|%([A-Za-z_][A-Za-z0-9_]*)%')
_URI_SCHEME_RE = re.compile('^[A-Za-z][A-Za-z0-9+.-]*://')
_ESC_DOLLAR = '\x00HARNESS_DOLLAR_LBRACE\x00'
_ESC_PERCENT = '\x00HARNESS_PERCENT\x00'
_INITIAL_HOME = Path.home().as_posix().rstrip('/')
_REGISTRY_CACHE: dict[tuple, 'PathRegistry'] = {}
# 2026-11-24
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
_PROJECT_PATHS_CACHE: OrderedDict[tuple, 'ProjectPaths'] = OrderedDict()
_OVERLAY_REVERSE_MAP: dict[str, Path] = {}
# 2026-11-22
# "Add declarative similar_projects registry groups and project overlay resolution":
# https://github.com/dmitry-ai/harness/issues/122
_SIMILAR_REVERSE_MAP: dict[tuple[str, str], list[Path]] = {}
_DISCOVERY_STATE: dict[str, Any] = {'roots_key': None, 'candidate_roots': (), 'fingerprint': None, 'links': {}, 'similar_links': {}}
# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
# @used-by :func:`agent_tools.journal.upgrade_journal()`
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
# @used-by :func:`agent_tools.project_rename._rollback_rename()`
# @used-by :func:`git_fixture_cache._clear_harness_caches()`
# @used-by :func:`test_historical_admission._restore_tree_in_place()`
# @used-by :meth:`test_path_registry.PathRegistryTests.tearDown()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.tearDown()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_lru_retains_more_than_256_entries()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.tearDown()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_pruned_walk_skips_heavy_dirs_and_respects_ttl_cache_and_reset()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations()`
def clear_registry_cache() -> None:
	# 2026-11-24
	# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
	# https://github.com/dmitry-ai/harness/issues/172
	from .issues.repo_locator import clear_repo_locator_cache
	_REGISTRY_CACHE.clear()
	_PROJECT_PATHS_CACHE.clear()
	_OVERLAY_REVERSE_MAP.clear()
	_SIMILAR_REVERSE_MAP.clear()
	_DISCOVERY_STATE.update({'roots_key': None, 'candidate_roots': (), 'fingerprint': None, 'links': {}, 'similar_links': {}})
	# 2026-11-24
	# "Accelerate project_paths and overlay link resolution with fast-path caching":
	# https://github.com/dmitry-ai/harness/issues/174
	clear_path_cache()
	clear_repo_locator_cache()
# @used-by :func:`default_platform_paths()`
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`ProjectPaths.__init__()`
def escape_template_literal(value: str) -> str:
	return str(value).replace('%', '%%').replace('${', '$${')
# @used-by :func:`discover_overlay_file()`
# @used-by :func:`load_registry()`
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
# @used-by :func:`_candidate_discovery_roots()`
# @used-by :func:`_find_local_marker_root()`
# @used-by :func:`_is_registered_single_project()`
# @used-by :func:`_refresh_known_overlay_links()`
# @used-by :func:`_resolve_os_user_home()`
# @used-by :func:`_validate_similar_project_groups()`
# @used-by :func:`agent_tools.research.inside()`
# @used-by :func:`agent_tools.shadow_replay_clone._journal_identity_matcher()`
# @used-by :func:`agent_tools.shadow_replay_clone._wrapped_shadow_registry()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :func:`canonicalize_root_dir()`
# @used-by :func:`evaluate_similar_project_touches()`
# @used-by :func:`is_tracked_workspace()`
# @used-by :func:`paths_report()`
# @used-by :func:`relocated_harness_code_dirs()`
# @used-by :func:`resolve_project_root()`
# @used-by :func:`same_project_root()`
# @used-by :func:`workspace_override()`
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`ProjectPaths.__init__()`
# @used-by :meth:`ProjectPaths._register_reverse_links()`
# @used-by :meth:`ProjectPaths.similar_projects()`
def _path_key(value: str | Path) -> str:
	return str(value).replace('\\', '/').rstrip('/').casefold()
# 2026-11-21
# "Separate OS user home from instance USERPROFILE and auto-detect active Antigravity instance":
# https://github.com/dmitry-ai/harness/issues/115
# @used-by :func:`_lookup_env()`
# @used-by :func:`_resolve_os_user_home()`
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
# @used-by :func:`_lookup_env()`
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
# @used-by :func:`default_platform_paths()`
# @used-by :func:`expand_template()`
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
# @used-by :func:`_resolve_os_user_home()`
# @used-by :func:`_resolve_process_home()`
# @used-by :func:`agent_tools.runtime._expand_path()`
# @used-by :func:`agent_tools.runtime.resolve_antigravity_paths()`
# @used-by :func:`default_platform_paths()`
# @used-by :func:`derive_platform_system_paths()`
# @used-by :func:`expand_template()`
# @used-by :meth:`ProjectPaths.__init__()`
# @used-by :meth:`ProjectPaths._resolve_rel_to_root()`
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
# @used-by :func:`_validate_similar_project_groups()`
# @used-by :func:`agent_tools.polyglot_land._expand_token()`
# @used-by :func:`derive_platform_system_paths()`
# @used-by :func:`expand_structure()`
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`PathRegistry.expand()`
# @used-by :meth:`ProjectPaths.__init__()`
# @used-by :meth:`ProjectPaths._resolve_rel_to_root()`
# @used-by :meth:`ProjectPaths.var()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_apache_prefix_concatenation_windows_env_vars_globs_and_escapes()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
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
	# @used-by :func:`expand_template()`
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
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`PathRegistry.expand_data()`
# @used-by :meth:`ProjectPaths.__init__()`
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
# @used-by :func:`_validate_overlay()`
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`PathRegistry._resolve_profile_chain()`
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
# @used-by :func:`_validate_overlay()`
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`PathRegistry._resolve_profile_chain()`
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
# @used-by :func:`_validate_overlay()`
# @used-by :func:`_validate_similar_project_groups()`
# @used-by :meth:`PathRegistry.__init__()`
# @used-by :meth:`PathRegistry._resolve_profile_chain()`
def _validate_string_list(raw: Any, label: str) -> list[str]:
	if None is raw:
		return []
	if not isinstance(raw, list) or any((not isinstance(x, str) or not x.strip() for x in raw)):
		raise ValueError(f'{label} must be a list of non-empty path strings')
	return list(raw)
# 2026-11-22
# "Add declarative similar_projects registry groups and project overlay resolution":
# https://github.com/dmitry-ai/harness/issues/122
_SIMILAR_GROUP_ID_RE = re.compile('^[A-Za-z0-9_.-]+$')
# @used-by :meth:`PathRegistry.__init__()`
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
# 2026-11-20
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-20
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# @used-by :meth:`PathRegistry.__init__()`
def _infer_harness_anchor(anchor_code: Path) -> tuple[Path, Path, int]:
	if '\u26ef' == anchor_code.name and 4 <= len(anchor_code.parents) and (anchor_code.parent.name, anchor_code.parents[1].name, anchor_code.parents[2].name) in (('\u2655', '\u227b', '\u2c0f'), ('Deliverables', '\u227b', 'Artifacts')):
		root = anchor_code.parents[3].resolve()
		return (root, root, 2)
	root = anchor_code.parent.resolve()
	meta = (root / '_').resolve() if (root / '_').is_dir() else root
	return (root, meta, 1)
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
class PathRegistry:
	# @used-by :func:`load_registry()`
	def __init__(self, source_path: Path, raw: dict[str, Any], *, primary: Path | None=None, env: dict[str, str] | None=None):
		self.source_path = Path(source_path).resolve()
		self.env = dict(env) if None is not env else None
		if not isinstance(raw, dict) or 1 != raw.get('version'):
			raise ValueError(f'{self.source_path.name} requires version 1')
		variables = _validate_variables_map(raw.get('variables'), 'paths.json variables')
		if not variables:
			raise ValueError('paths.json requires non-empty variables')
		# 2026-11-24
		# "Fix worktree scope resolution for new files in TDD classifier":
		# https://github.com/dmitry-ai/harness/issues/188
		anchor_code = Path(primary).resolve() if None is not primary else resolve_code_anchor(self.source_path.parent.resolve())
		# 2026-11-22
		# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
		# https://github.com/dmitry-ai/harness/issues/123
		self.anchor_code = anchor_code
		self.has_synthetic_primary = None is not primary and _path_key(anchor_code) != _path_key(self.source_path.parent.resolve())
		# 2026-11-20
		# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
		# https://github.com/dmitry-ai/harness/issues/100
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
		# 2026-11-23
		# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
		# https://github.com/dmitry-ai/harness/issues/132
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
		# 2026-11-22
		# "Add declarative similar_projects registry groups and project overlay resolution":
		# https://github.com/dmitry-ai/harness/issues/122
		self.similar_project_groups = _validate_similar_project_groups(raw.get('similar_projects'), variables, env=self.env)
		raw_profiles = raw.get('project_profiles') or {}
		if not isinstance(raw_profiles, dict) or 'default' not in raw_profiles:
			raise ValueError('paths.json project_profiles must define at least "default"')
		self.project_profiles = deepcopy(raw_profiles)
		for prof_name in self.project_profiles:
			self._resolve_profile_chain(prof_name)
	# @used-by :meth:`PathRegistry.__init__()`
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
		# 2026-11-20
		# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
		# https://github.com/dmitry-ai/harness/issues/100
		raw_fs_ver = cfg.get('fs_version', base['fs_version'])
		if int is not type(raw_fs_ver) or raw_fs_ver not in (1, 2):
			raise ValueError(f'project_profiles.{name}.fs_version must be 1 or 2')
		# 2026-11-21
		# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
		# https://github.com/dmitry-ai/harness/issues/108
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
		# 2026-11-22
		# "Add declarative similar_projects registry groups and project overlay resolution":
		# https://github.com/dmitry-ai/harness/issues/122
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
	# @used-by :func:`agent_tools.runtime._expand_path()`
	def expand(self, template: str, extra_variables: dict[str, str] | None=None) -> str:
		merged = self.raw_variables if not extra_variables else {**self.raw_variables, **extra_variables}
		return expand_template(template, merged, env=self.env, normalize=True)
	# @used-by :func:`agent_tools.runtime_cache._load_uncached_settings()`
	def expand_data(self, data: Any, extra_variables: dict[str, str] | None=None) -> Any:
		merged = self.raw_variables if not extra_variables else {**self.raw_variables, **extra_variables}
		return expand_structure(data, merged, env=self.env)
# @used-by :func:`load_registry()`
def _env_fingerprint(env: dict[str, str] | None) -> tuple:
	if None is env:
		# 2026-11-21
		# "Separate OS user home from instance USERPROFILE and auto-detect active Antigravity instance":
		# https://github.com/dmitry-ai/harness/issues/115
		keys = ('OS_USER_HOME', 'USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'SYSTEMROOT', 'HARNESS_PATHS_FILE')
		return tuple(((k, os.environ.get(k)) for k in keys))
	return tuple(sorted(((str(k), str(v)) for k, v in env.items())))
# @used-by :func:`agent_tools.addon_observability.is_live_runtime_data_file()`
# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :func:`agent_tools.issues.repo_locator._search_registry_and_roots()`
# @used-by :func:`agent_tools.polyglot_land.resolve_repo_verification_spec()`
# @used-by :func:`agent_tools.research.inside()`
# @used-by :func:`agent_tools.runtime._expand_path()`
# @used-by :func:`agent_tools.runtime_cache._load_uncached_settings()`
# @used-by :func:`agent_tools.shadow_replay_clone.shadow_isolation_context()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :func:`canonicalize_root_dir()`
# @used-by :func:`default_platform_paths()`
# @used-by :func:`derive_platform_system_paths()`
# @used-by :func:`discover_overlay_file()`
# @used-by :func:`evaluate_similar_project_touches()`
# @used-by :func:`is_tracked_workspace()`
# @used-by :func:`paths_report()`
# @used-by :func:`project_paths()`
# @used-by :func:`relocated_harness_code_dirs()`
# @used-by :func:`relocated_roots()`
# @used-by :func:`resolve_project_root()`
# @used-by :func:`same_project_root()`
# @used-by :func:`store_value()`
# @used-by :func:`tool_value()`
# @used-by :func:`var_value()`
# @used-by :func:`workspace_override()`
# @used-by :meth:`ProjectPaths.__init__()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
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
# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
# @used-by :mod:`agent_tools.runtime`
def var_value(name: str, *, registry: PathRegistry | None=None) -> str:
	reg = registry or load_registry()
	if name not in reg.resolved_variables:
		raise KeyError(f'Unknown registry variable: {name}')
	return reg.resolved_variables[name]
# @used-by :func:`agent_tools.cleanup_audit.resolve_cleanup_log_root()`
# @used-by :func:`agent_tools.issues.repo_locator._search_registry_and_roots()`
# @used-by :func:`store_path()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.resolve_issue_targets()`
def store_value(name: str, *, registry: PathRegistry | None=None) -> Any:
	reg = registry or load_registry()
	if name not in reg.harness_stores:
		raise KeyError(f'Unknown harness store entry: {name}')
	return deepcopy(reg.harness_stores[name])
# @used-by :func:`agent_tools.intake._project()`
# @used-by :func:`agent_tools.project_rename._update_projects_index()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.run()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_files()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.resolve_issue_targets()`
# @used-by :mod:`agent_tools.intake`
# @used-by :mod:`agent_tools.runtime`
def store_path(name: str, *, registry: PathRegistry | None=None) -> Path:
	val = store_value(name, registry=registry)
	if not isinstance(val, str):
		raise TypeError(f'Harness store {name!r} is not a single path string')
	return Path(val)
# @used-by :func:`tool_list()`
# @used-by :func:`tool_path()`
def tool_value(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> Any:
	reg = registry or load_registry()
	if None is not project_root:
		pp = project_paths(project_root, registry=reg)
		if name in pp.tools:
			return deepcopy(pp.tools[name])
	if name not in reg.tools:
		raise KeyError(f'Unknown tool entry in paths.json: {name}')
	return deepcopy(reg.tools[name])
# @used-by :func:`agent_tools.polyglot_land._resolve_node_exe()`
# @used-by :func:`agent_tools.runtime_snapshot.effective_git_hooks_dir()`
# @used-by :func:`git_shim.resolve_system_git()`
# @used-by :mod:`agent_tools.git_gate`
# @used-by :mod:`agent_tools.runtime`
def tool_path(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> Path:
	val = tool_value(name, project_root=project_root, registry=registry)
	if not isinstance(val, str):
		raise TypeError(f'Tool entry {name!r} is not a single path string')
	return Path(val)
# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
# @used-by :func:`agent_tools.text_core.default_shell()`
# @used-by :func:`agent_tools.upwork_data._find_poppler_tool()`
# @used-by :func:`git_shim._normalize_arg_token()`
# @used-by :func:`git_shim.resolve_system_git()`
def tool_list(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> list[str]:
	val = tool_value(name, project_root=project_root, registry=registry)
	if isinstance(val, list):
		return [str(x) for x in val]
	if isinstance(val, str):
		return [val]
	raise TypeError(f'Tool entry {name!r} is not a list of strings')
# @used-by :func:`agent_tools.cleanup_audit.resolve_cleanup_log_root()`
# @used-by :func:`agent_tools.path_cache.resolve_journal_data_dir()`
# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
# @used-by :func:`is_tracked_workspace()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
def workspace_override(path: str | Path, key: str | None=None, *, registry: PathRegistry | None=None) -> Any:
	reg = registry or load_registry()
	entry = reg.workspace_overrides.get(_path_key(Path(path).resolve()))
	if None is entry:
		return None
	return entry.get(key) if None is not key else deepcopy(entry)
# @used-by :mod:`agent_tools.platforms.request_binding`
def relocated_roots(*, registry: PathRegistry | None=None) -> dict[str, str]:
	reg = registry or load_registry()
	return dict(reg.relocations)
# 2026-11-20
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-20
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# @used-by :func:`agent_tools.configuration._project_rule_paths()`
# @used-by :func:`agent_tools.native_profiles._relocated_primaries()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
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
# @used-by :func:`agent_tools.runtime.default_system_paths()`
# @used-by :func:`default_platform_paths()`
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
# @used-by :func:`_is_registered_single_project()`
# @used-by :func:`agent_tools.cleanup_lifecycle._probe_disabled_ag_db()`
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :func:`agent_tools.platforms.antigravity.native_tool_trace()`
# @used-by :func:`agent_tools.runtime.resolve_antigravity_paths()`
# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
# @used-by :func:`check_stop_gate._resolve_stop_paths()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :mod:`agent_tools.platforms.antigravity`
def default_platform_paths(adapter_kind: str, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, registry: PathRegistry | None=None) -> dict[str, str]:
	reg = registry or load_registry()
	layout = reg.platform_layouts.get(adapter_kind) or {}
	extra_vars = None
	# 2026-11-21
	# "Separate OS user home from instance USERPROFILE and auto-detect active Antigravity instance":
	# https://github.com/dmitry-ai/harness/issues/115
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
# @used-by :func:`_refresh_known_overlay_links()`
# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
# @used-by :func:`agent_tools.journal.upgrade_journal()`
# @used-by :func:`paths_report()`
# @used-by :func:`project_paths()`
# @used-by :func:`resolve_project_root()`
# @used-by :meth:`ProjectPaths.__init__()`
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
# @used-by :meth:`ProjectPaths.__init__()`
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
	# 2026-11-20
	# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
	# https://github.com/dmitry-ai/harness/issues/100
	fs_ver = raw.get('fs_version')
	if None is not fs_ver and (int is not type(fs_ver) or fs_ver not in (1, 2)):
		raise ValueError(f'Project overlay {overlay_path} fs_version must be 1 or 2')
	# 2026-11-21
	# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
	# https://github.com/dmitry-ai/harness/issues/108
	j_ver = raw.get('journal_version')
	if None is not j_ver and (int is not type(j_ver) or j_ver not in (1, 2, 3)):
		raise ValueError(f'Project overlay {overlay_path} journal_version must be 1, 2, or 3')
	# 2026-11-23
	# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
	# https://github.com/dmitry-ai/harness/issues/132
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
# 2026-11-21
# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
# https://github.com/dmitry-ai/harness/issues/108
_JOURNAL_BUCKET_DIR_RE = re.compile('^(\\d+)[-\\u2013](\\d+)$')
# @used-by :func:`_inspect_journal_dir_on_disk()`
def _canonical_journal_bucket(step: int, bucket_size: int=20) -> str:
	start = ((step - 1) // bucket_size) * bucket_size + 1
	return f'{start}\u2013{start + bucket_size - 1}'
# @used-by :meth:`ProjectPaths.__init__()`
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
# @used-by :func:`project_paths()`
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
# 2026-11-20
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-20
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# @used-by :func:`_infer_default_profile()`
# @used-by :func:`canonicalize_root_dir()`
def _has_v2_markers(root: Path, reg: PathRegistry) -> bool:
	book_name = reg.resolved_variables.get('BOOK_DIR_NAME', '\U0001f56e')
	art_name = reg.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
	art_out = reg.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
	art_in = reg.resolved_variables.get('ARTIFACTS_IN_DIR_NAME', '\u227a')
	return (root / book_name).is_dir() or (root / art_name / art_out).is_dir() or (root / art_name / art_in).is_dir() or (root / 'Artifacts' / art_out).is_dir() or (root / 'Artifacts' / art_in).is_dir()
# 2026-11-20
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-20
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# @used-by :func:`_infer_default_profile()`
def _v2_software_deliverable_dir(root: Path, reg: PathRegistry) -> Path:
	art_name = reg.resolved_variables.get('ARTIFACTS_DIR_NAME', '\u2c0f')
	art_out = reg.resolved_variables.get('ARTIFACTS_OUT_DIR_NAME', '\u227b')
	deliv_name = reg.resolved_variables.get('DELIVERABLES_DIR_NAME', '\u2655')
	sw_name = reg.resolved_variables.get('SOFTWARE_DIR_NAME', '\u26ef')
	cand = root / art_name / art_out / deliv_name / sw_name
	if not cand.exists() and (root / 'Artifacts' / art_out / 'Deliverables' / sw_name).exists():
		return root / 'Artifacts' / art_out / 'Deliverables' / sw_name
	return cand
# @used-by :func:`_find_local_marker_root()`
# @used-by :func:`_is_registered_single_project()`
# @used-by :func:`agent_tools.admission._resolve_proof_file()`
# @used-by :func:`agent_tools.completion._conflict()`
# @used-by :func:`agent_tools.completion._gate_resolved()`
# @used-by :func:`agent_tools.completion._new()`
# @used-by :func:`agent_tools.completion._persist_turn_recovery()`
# @used-by :func:`agent_tools.completion._prepare_once()`
# @used-by :func:`agent_tools.completion._same_turn_artifact_path()`
# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
# @used-by :func:`agent_tools.completion._state()`
# @used-by :func:`agent_tools.completion.begin()`
# @used-by :func:`agent_tools.completion.check_answer()`
# @used-by :func:`agent_tools.completion.conversation_journal_steps()`
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
# @used-by :func:`agent_tools.completion.issue_first_check_turn()`
# @used-by :func:`agent_tools.completion.ratchet_ok()`
# @used-by :func:`agent_tools.completion.recover_checkpoint()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :func:`agent_tools.completion.sync_conversation_title()`
# @used-by :func:`agent_tools.completion.tdd_check_turn()`
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
# @used-by :func:`agent_tools.journal.canonicalize_journal_dir_identity()`
# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
# @used-by :func:`agent_tools.meta.builders.build_github_issue_metadata()`
# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
# @used-by :func:`agent_tools.meta.builders.build_problem_metadata()`
# @used-by :func:`agent_tools.meta.identity.resolve_project_identity()`
# @used-by :func:`agent_tools.operations.analysis_root()`
# @used-by :func:`agent_tools.platforms.codex._review_inputs()`
# @used-by :func:`agent_tools.platforms.request_binding.canonical_path()`
# @used-by :func:`agent_tools.review.read_package_envelope()`
# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
# @used-by :func:`agent_tools.text_workflow._roots()`
# @used-by :func:`evaluate_similar_project_touches()`
# @used-by :func:`is_tracked_workspace()`
# @used-by :func:`project_paths()`
# @used-by :func:`resolve_project_root()`
# @used-by :func:`same_project_root()`
# @used-by :meth:`ProjectPaths.__init__()`
# @used-by :meth:`agent_tools.completion.TurnJournalReconciler.__init__()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.is_issue_tracked()`
# @used-by :meth:`agent_tools.review.ReviewReportValidator.__init__()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.__init__()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
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
		# 2026-11-21
		# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
		# https://github.com/dmitry-ai/harness/issues/113
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
# 2026-11-21
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-26 "Preserve finalized workflow and review lineage across rename-project": https://github.com/dmitry-ai/harness/issues/277
# @used-by :func:`agent_tools.completion._same_saved_request()`
# @used-by :func:`agent_tools.completion._same_turn_artifact_path()`
# @used-by :func:`agent_tools.completion._state()`
# @used-by :func:`agent_tools.completion.begin()`
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
# @used-by :func:`agent_tools.platforms.antigravity._project_item_matches_root()`
# @used-by :func:`agent_tools.platforms.codex._review_inputs()`
# @used-by :func:`agent_tools.research.inside()`
# @used-by :func:`agent_tools.review.read_package_envelope()`
# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore._is_plan_commit()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.operation_meta()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.read_check()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.reconciled_integrity()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.load()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
def same_project_root(first: str | Path | None, second: str | Path | None, *, registry: PathRegistry | None=None) -> bool:
	from .project_rename_state import same_project_root_check
	return same_project_root_check(first, second, lambda s: canonicalize_root_dir(s, registry=registry or load_registry()), _path_key)
# @used-by :func:`_candidate_discovery_roots()`
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
# @used-by :func:`_refresh_known_overlay_links()`
# @used-by :func:`agent_tools.issues.repo_locator._index_discovery_roots()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
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
	# @used-by :func:`_candidate_discovery_roots()`
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
								# 2026-11-21
								# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
								# https://github.com/dmitry-ai/harness/issues/113
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
# @used-by :func:`resolve_project_root()`
# @used-by :meth:`ProjectPaths.similar_projects()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
def _refresh_known_overlay_links(reg: PathRegistry) -> dict[str, Path]:
	# 2026-11-24
	# "Accelerate project_paths and overlay link resolution with fast-path caching":
	# https://github.com/dmitry-ai/harness/issues/174
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
	# 2026-11-22
	# "Add declarative similar_projects registry groups and project overlay resolution":
	# https://github.com/dmitry-ai/harness/issues/122
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
# @used-by :func:`resolve_project_root()`
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
# @used-by :func:`agent_tools.analysis.publish_analysis()`
# @used-by :func:`agent_tools.issues.comment_grounding._resolve_grounding_root()`
# @used-by :func:`agent_tools.issues.service_helpers.resolve_metadata_project_root()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`check_markdown_slop._infer_project_root()`
# @used-by :func:`is_tracked_workspace()`
# @used-by :func:`project_paths()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_resolve_project_root_skips_host_overlay_scan_for_temp_subdirs()`
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
	# 2026-11-24
	# "Accelerate project_paths and overlay link resolution with fast-path caching":
	# https://github.com/dmitry-ai/harness/issues/174
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
# 2026-11-20
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# @used-by :func:`project_paths()`
# @used-by :meth:`ProjectPaths.__init__()`
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
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
class ProjectPaths:
	# @used-by :func:`_refresh_known_overlay_links()`
	# @used-by :func:`paths_report()`
	# @used-by :func:`project_paths()`
	def __init__(self, root: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None, _register_links: bool=True):
		self.registry = registry or load_registry(env=env)
		self.root = canonicalize_root_dir(root, registry=self.registry)
		self.overlay_file = discover_overlay_file(self.root, registry=self.registry)
		self.overlay = _validate_overlay(json.loads(self.overlay_file.read_text(encoding='utf-8-sig')), self.overlay_file, self.registry) if None is not self.overlay_file else None
		self.has_overlay = None is not self.overlay
		# 2026-11-23
		# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
		# https://github.com/dmitry-ai/harness/issues/132
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
		# 2026-11-20
		# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
		# https://github.com/dmitry-ai/harness/issues/103
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
		# @used-by :meth:`ProjectPaths.__init__()`
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
		# 2026-11-22
		# "Add declarative similar_projects registry groups and project overlay resolution":
		# https://github.com/dmitry-ai/harness/issues/122
		raw_sim = self.overlay['similar_projects'] if self.overlay and self.overlay['similar_projects'] else prof_spec['similar_projects']
		direct_sim: list[Path] = []
		seen_sim: set[str] = {_path_key(self.root)}
		# @used-by :meth:`ProjectPaths.__init__()`
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
		# 2026-11-21
		# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
		# https://github.com/dmitry-ai/harness/issues/108
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
	# @used-by :func:`project_paths()`
	# @used-by :meth:`ProjectPaths.__init__()`
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
	# @used-by :func:`agent_tools.intake._index()`
	# @used-by :func:`agent_tools.intake._project()`
	# @used-by :func:`agent_tools.intake._receipt()`
	# @used-by :func:`agent_tools.intake._snapshot()`
	# @used-by :func:`agent_tools.intake._validate_receipt()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.journal_integrity.check_project_journal_problems()`
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :func:`agent_tools.project_drift._kb_identity_mismatch_issues()`
	# @used-by :func:`agent_tools.project_drift.analysis_card_sync_issues()`
	# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	def rel_to_root(self, target: str | Path) -> str:
		p = Path(target).resolve()
		return p.relative_to(self.root).as_posix() if p.is_relative_to(self.root) else p.as_posix()
	# @used-by :meth:`ProjectPaths.__init__()`
	# @used-by :meth:`ProjectPaths.expand()`
	def _resolve_rel_to_root(self, tpl: str) -> str:
		val = expand_template(tpl, self._variables, env=self.registry.env, normalize=True)
		if not Path(val).is_absolute() and (not _URI_SCHEME_RE.match(val)):
			val = normalize_path_str(f'{self.root.as_posix()}/{val}')
		return val
	# @used-by :func:`agent_tools.completion._folder()`
	# @used-by :func:`check_pre_invocation._turns_dir()`
	# @used-by :meth:`ProjectPaths.__init__()`
	# @used-by :meth:`ProjectPaths.journal_dir()`
	def has_explicit_path(self, name: str) -> bool:
		return name in self._explicit_overlay_paths
	# @used-by :func:`_candidate_discovery_roots()`
	# @used-by :func:`_is_linked()`
	# @used-by :func:`_validate_similar_project_groups()`
	# @used-by :func:`agent_tools.completion._is_client_deliverable_path()`
	# @used-by :func:`agent_tools.completion._response_link_issues()`
	# @used-by :func:`agent_tools.configuration.has_linked_ancestor()`
	# @used-by :func:`agent_tools.evidence_loader._resolve_html_data()`
	# @used-by :func:`agent_tools.intake._plain()`
	# @used-by :func:`agent_tools.journal._assert_not_linked_tree()`
	# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :func:`agent_tools.links.readable_reference()`
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :func:`agent_tools.markdown_links.decode_file_uri()`
	# @used-by :func:`agent_tools.markdown_links.display_address()`
	# @used-by :func:`agent_tools.native_profiles._absolute()`
	# @used-by :func:`agent_tools.native_profiles._apply()`
	# @used-by :func:`agent_tools.native_profiles._direct_link_matches_target()`
	# @used-by :func:`agent_tools.native_profiles._exists()`
	# @used-by :func:`agent_tools.native_profiles._is_relocated_owned_link()`
	# @used-by :func:`agent_tools.native_profiles._link_matches_target()`
	# @used-by :func:`agent_tools.native_profiles._plan_codex_link()`
	# @used-by :func:`agent_tools.native_profiles._rollback()`
	# @used-by :func:`agent_tools.path_cache._fast_sig()`
	# @used-by :func:`agent_tools.perf.suite_worker.main()`
	# @used-by :func:`agent_tools.platforms.trace_common.local_uri_to_path()`
	# @used-by :func:`agent_tools.polyglot_land._expand_token()`
	# @used-by :func:`agent_tools.project_drift.analysis_card_sync_issues()`
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :func:`agent_tools.repo_link_gate._enclosing_github_repo()`
	# @used-by :func:`agent_tools.repo_link_gate._validate_file_uri()`
	# @used-by :func:`agent_tools.repo_link_gate._validate_relative_cross_repo()`
	# @used-by :func:`agent_tools.runtime._expand_path()`
	# @used-by :func:`agent_tools.runtime_cache._file_stat_key()`
	# @used-by :func:`agent_tools.shadow_replay._ensure_scripts_path()`
	# @used-by :func:`agent_tools.statements.is_documentation_url()`
	# @used-by :func:`agent_tools.tdd.diff_coverage._find_uncovered()`
	# @used-by :func:`agent_tools.tdd.diff_coverage_hook.prepare_single_pass_coverage_env()`
	# @used-by :func:`agent_tools.tdd.outcomes._uri_to_local_path()`
	# @used-by :func:`agent_tools.text_browser._endpoint_with_meta()`
	# @used-by :func:`agent_tools.upwork_data.extract_upwork_job_url_id()`
	# @used-by :func:`agent_tools.upwork_extract.download_attachment()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :func:`check_pre_invocation._ensure_scripts_on_path()`
	# @used-by :func:`check_stop_gate._ensure_scripts_on_path()`
	# @used-by :func:`check_stop_gate._resolve_stop_paths()`
	# @used-by :func:`conftest.configure_test_environment()`
	# @used-by :func:`discover_overlay_file()`
	# @used-by :func:`load_registry()`
	# @used-by :func:`normalize_path_str()`
	# @used-by :func:`paths_report()`
	# @used-by :func:`relocated_harness_code_dirs()`
	# @used-by :meth:`PathRegistry.__init__()`
	# @used-by :meth:`agent_tools.completion.TurnJournalReconciler._prune_delivered_checkpoint_recovery()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.publish_progress()`
	# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_df_bootstrap_loads_dotpy_packages_and_sibling_modules()`
	# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :mod:`check_markdown_slop`
	# @used-by :mod:`check_rules_and_server_gate`
	# @used-by :mod:`df_article`
	# @used-by :mod:`df_github_issue`
	# @used-by :mod:`generate_context`
	# @used-by :mod:`git_fixture_cache`
	# @used-by :mod:`git_shim`
	# @used-by :mod:`harness`
	# @used-by :mod:`safe_commit`
	# @used-by :mod:`snapshot_draft`
	# @used-by :mod:`test_addon_observability`
	# @used-by :mod:`test_agent_tools`
	# @used-by :mod:`test_ask_question_clarifications_m8`
	# @used-by :mod:`test_atomic_prepare_and_narrowed_reconcile_m7`
	# @used-by :mod:`test_background_wait_and_tdd_inheritance`
	# @used-by :mod:`test_blocked_report_hygiene_and_doc5_m2`
	# @used-by :mod:`test_blocked_report_m2`
	# @used-by :mod:`test_bounded_foreign_sync`
	# @used-by :mod:`test_chat_reply_link_issues_m5`
	# @used-by :mod:`test_cleanup_audit`
	# @used-by :mod:`test_cleanup_integration`
	# @used-by :mod:`test_cleanup_lifecycle`
	# @used-by :mod:`test_cli_command_grounding`
	# @used-by :mod:`test_cli_common`
	# @used-by :mod:`test_cli_registry`
	# @used-by :mod:`test_code_fanout_gates`
	# @used-by :mod:`test_code_formatting_rules`
	# @used-by :mod:`test_code_size_gate`
	# @used-by :mod:`test_code_style_gate`
	# @used-by :mod:`test_comment_exemption_and_denied_writes`
	# @used-by :mod:`test_context_and_storage_determinism`
	# @used-by :mod:`test_contract_invariants`
	# @used-by :mod:`test_cross_repo_issue_urls`
	# @used-by :mod:`test_df_analysis_companion_tracks`
	# @used-by :mod:`test_df_analysis_rules_contract`
	# @used-by :mod:`test_df_analysis`
	# @used-by :mod:`test_df_core_array`
	# @used-by :mod:`test_df_core_base`
	# @used-by :mod:`test_df_core_text_misc`
	# @used-by :mod:`test_df_dotpy_bootstrap`
	# @used-by :mod:`test_df_qa`
	# @used-by :mod:`test_df_upstream_fixes`
	# @used-by :mod:`test_diff_coverage_gate`
	# @used-by :mod:`test_dirty_diff_issue_scope`
	# @used-by :mod:`test_doc5_context_trigger`
	# @used-by :mod:`test_evidence_unification`
	# @used-by :mod:`test_executor_metadata`
	# @used-by :mod:`test_experiments`
	# @used-by :mod:`test_failfast_and_schedule_gate`
	# @used-by :mod:`test_falsifier_and_schedule_subagent_gate_m8`
	# @used-by :mod:`test_falsifier_default_send_message_and_schedule_m8`
	# @used-by :mod:`test_finalized_project_contract`
	# @used-by :mod:`test_gate_registry`
	# @used-by :mod:`test_git_fixture_cache`
	# @used-by :mod:`test_git_ignore`
	# @used-by :mod:`test_git_lifecycle_memoization`
	# @used-by :mod:`test_github_issue`
	# @used-by :mod:`test_grounding_corpus_cache_m9`
	# @used-by :mod:`test_harness_xref_compliance`
	# @used-by :mod:`test_hook_lazy_imports`
	# @used-by :mod:`test_hook_runner_e2e_budget`
	# @used-by :mod:`test_hook_runner_watchdog`
	# @used-by :mod:`test_hook_trace_cache_and_watchdog`
	# @used-by :mod:`test_hook_unification`
	# @used-by :mod:`test_issue44`
	# @used-by :mod:`test_issue45_to_48`
	# @used-by :mod:`test_issue_close_acceptance`
	# @used-by :mod:`test_issue_comment_gate`
	# @used-by :mod:`test_issue_conversation_isolation`
	# @used-by :mod:`test_issue_decomposition`
	# @used-by :mod:`test_issue_first_completion`
	# @used-by :mod:`test_issue_first_gate`
	# @used-by :mod:`test_issue_first_github_cli`
	# @used-by :mod:`test_issue_first_pre_tool_use`
	# @used-by :mod:`test_issue_first_rules_contract`
	# @used-by :mod:`test_issue_preflight_and_batch`
	# @used-by :mod:`test_java_xref`
	# @used-by :mod:`test_journal_idle_sync_and_liveness`
	# @used-by :mod:`test_journal_integrity`
	# @used-by :mod:`test_journal_metadata`
	# @used-by :mod:`test_js_xref`
	# @used-by :mod:`test_landing_lease`
	# @used-by :mod:`test_metadata_decomposition`
	# @used-by :mod:`test_metadata_rules_contract`
	# @used-by :mod:`test_metadata`
	# @used-by :mod:`test_multiturn_handoff_stop_guard_and_schedule_m1`
	# @used-by :mod:`test_native_review_binding_m4`
	# @used-by :mod:`test_observability_diagnostics`
	# @used-by :mod:`test_parallel_runner`
	# @used-by :mod:`test_parallel_test_runner`
	# @used-by :mod:`test_path_cache_and_diff_cov_perf`
	# @used-by :mod:`test_path_registry_perf`
	# @used-by :mod:`test_path_registry`
	# @used-by :mod:`test_perf_improvement_skill_contract`
	# @used-by :mod:`test_perf_profile_tests`
	# @used-by :mod:`test_perf_timesheet`
	# @used-by :mod:`test_polyglot_land`
	# @used-by :mod:`test_problem_metadata`
	# @used-by :mod:`test_project_domain_drift`
	# @used-by :mod:`test_project_labels`
	# @used-by :mod:`test_project_rename_verification`
	# @used-by :mod:`test_project_rename`
	# @used-by :mod:`test_pytest_xdist_runner`
	# @used-by :mod:`test_python_integrity_gate`
	# @used-by :mod:`test_python_xref`
	# @used-by :mod:`test_repo_link_gate`
	# @used-by :mod:`test_repo_locator_perf`
	# @used-by :mod:`test_repo_tag_close_gate`
	# @used-by :mod:`test_repo_tags_docs`
	# @used-by :mod:`test_repo_tags`
	# @used-by :mod:`test_repo_wait_and_retry`
	# @used-by :mod:`test_reused_reviewer_and_metadata_drift_m5`
	# @used-by :mod:`test_review_contract_package_and_paths_m6`
	# @used-by :mod:`test_review_target_claim_and_wait_m5`
	# @used-by :mod:`test_rules_architecture_m2`
	# @used-by :mod:`test_rules_audit`
	# @used-by :mod:`test_rules_progressive_disclosure`
	# @used-by :mod:`test_runtime_cache_and_evidence_fastpath_m9`
	# @used-by :mod:`test_runtime_snapshot`
	# @used-by :mod:`test_scatter_banner_gate`
	# @used-by :mod:`test_schema_help_and_analysis_merge_m10`
	# @used-by :mod:`test_scratch_slop_and_grounding_loc_m7`
	# @used-by :mod:`test_service_finalization_exempt_and_sync_all_open`
	# @used-by :mod:`test_shadow_replay_command`
	# @used-by :mod:`test_shadow_replay_m3`
	# @used-by :mod:`test_shell_herestring_write_targets_m4`
	# @used-by :mod:`test_snapshot_canary_and_hook_crash_audit`
	# @used-by :mod:`test_snapshot_latency_and_delegation_policy`
	# @used-by :mod:`test_source_diagnostics_scanner`
	# @used-by :mod:`test_source_grounding`
	# @used-by :mod:`test_stop_emergency_capture_and_foreign_sync`
	# @used-by :mod:`test_stop_gate_contract`
	# @used-by :mod:`test_stop_gate_subagents_m1`
	# @used-by :mod:`test_storage_fsync_guard`
	# @used-by :mod:`test_subprocess_hygiene_and_tree_kill`
	# @used-by :mod:`test_tdd_comment_exemption`
	# @used-by :mod:`test_tdd_completion`
	# @used-by :mod:`test_tdd_decomposition`
	# @used-by :mod:`test_tdd_fast_path`
	# @used-by :mod:`test_tdd_gate`
	# @used-by :mod:`test_tdd_git_gate`
	# @used-by :mod:`test_tdd_mechanical_exemption`
	# @used-by :mod:`test_tdd_pre_tool_use_perf`
	# @used-by :mod:`test_tdd_pre_tool_use`
	# @used-by :mod:`test_tdd_rules_contract`
	# @used-by :mod:`test_tdd_worktree_and_subagent_trace`
	# @used-by :mod:`test_text_browser`
	# @used-by :mod:`test_text_diagnostics`
	# @used-by :mod:`test_text_native_binding`
	# @used-by :mod:`test_turn_completion`
	# @used-by :mod:`test_turn_routing_and_handoff_m6`
	# @used-by :mod:`test_upwork_data`
	# @used-by :mod:`test_upwork_init_e2e`
	# @used-by :mod:`test_verification_observability`
	# @used-by :mod:`test_watchdog_and_timeout_gate`
	# @used-by :mod:`test_worker_semaphore_and_xdist`
	# @used-by :mod:`test_worktree_cleanup_guard`
	# @used-by :mod:`test_worktree_comment_exemption`
	# @used-by :mod:`test_worktree_flow`
	# @used-by :mod:`test_worktree_ignore`
	# @used-by :mod:`test_worktree_isolation_gate`
	# @used-by :mod:`test_worktree_lifecycle`
	# @used-by :mod:`test_xref_gate`
	# @used-by :mod:`upwork_project`
	# @used-by :mod:`validate_anchors`
	# @used-by :mod:`validate_links`
	# @used-by :mod:`validate_statements`
	# @used-by :mod:`validate_step`
	def path(self, name: str, default: str | Path | None=None) -> Path | None:
		if name in self.paths_str:
			return Path(self.paths_str[name])
		return Path(default) if None is not default else None
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
	def var(self, name: str, default: str | None=None) -> str | None:
		if name in self._variables:
			return expand_template(f'${{{name}}}', self._variables, env=self.registry.env, normalize=True)
		return default
	# @used-by :func:`agent_tools.journal.ensure_project_journal_upgraded()`
	# @used-by :func:`agent_tools.journal.resolve_journal_dir()`
	# @used-by :func:`paths_report()`
	def expand(self, template: str) -> str:
		return self._resolve_rel_to_root(template)
	# @used-by :func:`agent_tools.completion._instruction_snapshot()`
	# @used-by :func:`agent_tools.configuration._project_rule_paths()`
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :func:`agent_tools.configuration.configure_codex_project()`
	# @used-by :func:`agent_tools.upwork_project.check_configuration()`
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
	@property
	def agents_config_dir(self) -> Path:
		return Path(self.paths_str['agents_config_dir'])
	# @used-by :func:`agent_tools.configuration._native_config()`
	# @used-by :func:`agent_tools.configuration._publish()`
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :func:`agent_tools.configuration.configure_codex_project()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
	@property
	def codex_config_toml(self) -> Path:
		return Path(self.paths_str['codex_config_toml'])
	# @used-by :func:`agent_tools.completion._is_client_deliverable_path()`
	# @used-by :func:`agent_tools.path_cache._fast_sig()`
	# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.meta_dir_for_project_root()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_fast_cache_hits_and_invalidates_on_fs_mutations()`
	@property
	def agent_dir(self) -> Path:
		return Path(self.paths_str['agent_dir'])
	# @used-by :func:`agent_tools.analysis.publish_owned()`
	# @used-by :func:`agent_tools.analysis.save_analysis()`
	# @used-by :func:`agent_tools.analysis_merge._load_merge_base()`
	# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
	# @used-by :func:`agent_tools.blocked_report.evaluate_check_workflow_errors()`
	# @used-by :func:`agent_tools.completion._folder()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.journal.upgrade_journal()`
	# @used-by :func:`agent_tools.knowledge._load_media_descriptions()`
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :func:`agent_tools.landing_lease._lease_file_for()`
	# @used-by :func:`agent_tools.path_cache.resolve_journal_data_dir()`
	# @used-by :func:`agent_tools.polyglot_land._sandbox_root()`
	# @used-by :func:`agent_tools.project_card.sync_block()`
	# @used-by :func:`agent_tools.project_rename_state.migrate_journal_state()`
	# @used-by :func:`agent_tools.project_rename_state.refresh_workflow_file_hash()`
	# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :func:`agent_tools.registration._begin()`
	# @used-by :func:`agent_tools.registration.save_registration()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.observed_use()`
	# @used-by :func:`agent_tools.shadow_replay_command.persist_shadow_replay_receipt()`
	# @used-by :func:`agent_tools.storage.data_dir_for()`
	# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
	# @used-by :func:`agent_tools.text_claims.save_registry()`
	# @used-by :func:`agent_tools.text_workflow._folder()`
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	# @used-by :func:`agent_tools.worker_semaphore.default_slots_dir()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
	# @used-by :func:`check_pre_invocation._turns_dir()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.claim_snapshot()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def data_dir(self) -> Path:
		return Path(self.paths_str['data_dir'])
	# @used-by :func:`agent_tools.analysis.publish_analysis()`
	# @used-by :func:`agent_tools.analysis.save_analysis()`
	# @used-by :func:`agent_tools.analysis_merge._load_merge_base()`
	# @used-by :func:`agent_tools.completion._budget_status()`
	# @used-by :func:`agent_tools.completion._factual_kb_note_issues()`
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :func:`agent_tools.context.default_context_config()`
	# @used-by :func:`agent_tools.evidence.local_file()`
	# @used-by :func:`agent_tools.evidence.source_reference()`
	# @used-by :func:`agent_tools.experiments.result_issues()`
	# @used-by :func:`agent_tools.intake._index()`
	# @used-by :func:`agent_tools.intake._snapshot()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :func:`agent_tools.project_drift._kb_identity_mismatch_issues()`
	# @used-by :func:`agent_tools.project_drift.require_no_domain_drift_for_finalize()`
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.compute_site_summary()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_file()`
	# @used-by :func:`agent_tools.research.extract_observation()`
	# @used-by :func:`agent_tools.research.load_observation()`
	# @used-by :func:`agent_tools.review._analysis()`
	# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
	# @used-by :func:`agent_tools.text_claims.registry_path()`
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.workflow.kb_paths()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._verify_saved_artifacts()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.load()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def kb_dir(self) -> Path:
		return Path(self.paths_str['kb_dir'])
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
	# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
	# @used-by :func:`agent_tools.project_drift._kb_identity_mismatch_issues()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.workflow.evidence_paths()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	@property
	def manual_kb_dir(self) -> Path:
		return Path(self.paths_str['manual_kb_dir'])
	# @used-by :func:`agent_tools.evidence.local_file()`
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :func:`agent_tools.workflow.evidence_paths()`
	@property
	def source_dir(self) -> Path:
		return Path(self.paths_str['source_dir'])
	# @used-by :func:`agent_tools.claims._manifest_primary()`
	# @used-by :func:`agent_tools.completion._compaction_status()`
	# @used-by :func:`agent_tools.completion._factual_kb_note_issues()`
	# @used-by :func:`agent_tools.context.default_context_config()`
	# @used-by :func:`agent_tools.intake._index()`
	# @used-by :func:`agent_tools.intake._receipt()`
	# @used-by :func:`agent_tools.intake._snapshot()`
	# @used-by :func:`agent_tools.intake._validate_receipt()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
	# @used-by :func:`agent_tools.operations._execute_collect()`
	# @used-by :func:`agent_tools.platforms.trace_common.persist_review_proof()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_file()`
	# @used-by :func:`agent_tools.review.disposition()`
	# @used-by :func:`agent_tools.review.prepare()`
	# @used-by :func:`agent_tools.review.prepare_verdict_record()`
	# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :func:`agent_tools.workflow.evidence_paths()`
	# @used-by :func:`agent_tools.workflow.kb_paths()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.load()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_files()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_evidence_files()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def evidence_dir(self) -> Path:
		return Path(self.paths_str['evidence_dir'])
	# @used-by :func:`agent_tools.cli_common.verify_scratch_input_path()`
	# @used-by :func:`agent_tools.completion._find_evicted_cited_files()`
	# @used-by :func:`agent_tools.completion.check_answer()`
	# @used-by :func:`agent_tools.project_drift.require_no_domain_drift_for_finalize()`
	# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
	# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
	# @used-by :func:`check_pre_invocation._scratch_answer_path()`
	@property
	def scratch_dir(self) -> Path:
		return Path(self.paths_str['scratch_dir'])
	# @used-by :func:`agent_tools.completion._folder()`
	# @used-by :func:`agent_tools.gates.external_write._check_df_issue_turn_intent()`
	# @used-by :func:`agent_tools.hook_crash_audit._load_violation_receipt()`
	# @used-by :func:`agent_tools.issues.parity._load_similar_project_exemptions()`
	# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
	# @used-by :func:`agent_tools.issues.turn_scope._candidate_turns_dirs()`
	# @used-by :func:`agent_tools.meta.builders._find_issue_state_pair()`
	# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
	# @used-by :func:`agent_tools.project_rename_state.rewrite_launcher_handoffs()`
	# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
	# @used-by :func:`agent_tools.project_rename_verify._launcher_stale_files()`
	# @used-by :func:`agent_tools.shadow_replay._find_reply_path()`
	# @used-by :func:`agent_tools.shadow_replay._run_pre_invocation()`
	# @used-by :func:`agent_tools.tdd.mechanical._candidate_recipe_dirs()`
	# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
	# @used-by :func:`agent_tools.tdd.ratchet._turn_receipt_dirs()`
	# @used-by :func:`check_markdown_slop._check_turn_budget_gate()`
	# @used-by :func:`check_pre_invocation._turns_dir()`
	# @used-by :func:`check_stop_gate._turns_dir()`
	# @used-by :func:`is_tracked_workspace()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def turns_dir(self) -> Path:
		return Path(self.paths_str['turns_dir'])
	# @used-by :func:`agent_tools.cli_registry._exec_worktree_begin()`
	# @used-by :func:`agent_tools.git_ignore.prepare_worktrees_base_dir()`
	@property
	def worktrees_dir(self) -> Path:
		return Path(self.paths_str['worktrees_dir'])
	# @used-by :func:`agent_tools.completion._is_client_deliverable_path()`
	# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
	# @used-by :func:`agent_tools.journal.ensure_project_journal_upgraded()`
	# @used-by :func:`agent_tools.path_cache._fast_sig()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	@property
	def journal_root_dir(self) -> Path:
		return Path(self.paths_str['journal_root_dir'])
	# @used-by :func:`agent_tools.journal.canonicalize_journal_dir_identity()`
	# @used-by :func:`agent_tools.journal.ensure_project_journal_upgraded()`
	# @used-by :func:`agent_tools.journal.journal_pair_names()`
	# @used-by :func:`agent_tools.journal.resolve_journal_dir()`
	# @used-by :func:`agent_tools.journal_integrity.check_project_journal_problems()`
	# @used-by :func:`agent_tools.path_cache._fast_sig()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :func:`is_tracked_workspace()`
	# @used-by :meth:`ProjectPaths.__init__()`
	# @used-by :meth:`ProjectPaths.to_dict()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	@property
	def journal_dir(self) -> Path:
		if not self.has_explicit_path('journal_dir') and self.journal_glob:
			matches = sorted((Path(m).resolve() for m in glob.glob(self.journal_glob, recursive=True) if Path(m).is_dir()))
			if matches:
				return matches[-1]
		return Path(self.paths_str['journal_dir'])
	# @used-by :func:`agent_tools.journal.ensure_project_journal_upgraded()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :meth:`ProjectPaths.__init__()`
	# @used-by :meth:`ProjectPaths.journal_dir()`
	@property
	def journal_glob(self) -> str | None:
		return self.paths_str.get('journal_glob')
	# @used-by :func:`agent_tools.context.default_context_config()`
	# @used-by :func:`agent_tools.context.generate()`
	# @used-by :func:`agent_tools.upwork_project.default_context_config()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	@property
	def context_output(self) -> Path:
		return Path(self.paths_str['context_output'])
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	@property
	def context_config(self) -> Path:
		return Path(self.paths_str['context_config'])
	# @used-by :func:`agent_tools.blocked_report._authorize_workflow_errors()`
	# @used-by :func:`agent_tools.blocked_report.audit_runner_workflow_scope()`
	# @used-by :func:`agent_tools.claims._manifest_primary()`
	# @used-by :func:`agent_tools.completion._delegation_status()`
	# @used-by :func:`agent_tools.completion.begin()`
	# @used-by :func:`agent_tools.gates.external_write._match_upwork_root()`
	# @used-by :func:`agent_tools.intake._project()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
	# @used-by :func:`agent_tools.meta.identity._lookup_name_from_project_json()`
	# @used-by :func:`agent_tools.path_cache._fast_sig()`
	# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
	# @used-by :func:`agent_tools.platforms.request_binding.completion_project_id()`
	# @used-by :func:`agent_tools.platforms.request_binding.native_project_id()`
	# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
	# @used-by :func:`agent_tools.project_rename._validate_rename_inputs()`
	# @used-by :func:`agent_tools.project_rename.maybe_promote_project_domain()`
	# @used-by :func:`agent_tools.project_rename_state._update_project_json()`
	# @used-by :func:`agent_tools.registration._expected()`
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`is_tracked_workspace()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
	@property
	def project_json(self) -> Path:
		return Path(self.paths_str['project_json'])
	# @used-by :func:`agent_tools.platforms.request_binding.completion_project_id()`
	# @used-by :func:`agent_tools.platforms.request_binding.native_project_id()`
	@property
	def text_project_json(self) -> Path:
		return Path(self.paths_str['text_project_json'])
	# @used-by :func:`agent_tools.blocked_report.evaluate_check_workflow_errors()`
	# @used-by :func:`agent_tools.completion._workflow_gate_resolved()`
	# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
	@property
	def workflow_json(self) -> Path:
		return Path(self.paths_str['workflow_json'])
	# @used-by :func:`agent_tools.blocked_report.blocked_report_issues()`
	# @used-by :func:`agent_tools.completion._budget_status()`
	@property
	def continuation_md(self) -> Path:
		return Path(self.paths_str['continuation_md'])
	# @used-by :func:`agent_tools.project_drift._registered_title_mismatches()`
	# @used-by :func:`agent_tools.project_rename._ag_id_from_receipt()`
	# @used-by :func:`agent_tools.project_rename._sync_registrations()`
	# @used-by :func:`agent_tools.registration._read()`
	# @used-by :func:`agent_tools.shadow_replay_command._stage_ag_from_receipt()`
	@property
	def registrations_json(self) -> Path:
		return Path(self.paths_str['registrations_json'])
	# @used-by :func:`agent_tools.review.load_verified_claims_cache()`
	# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
	@property
	def verified_claims_json(self) -> Path:
		return Path(self.paths_str['verified_claims_json'])
	# @used-by :func:`agent_tools.source_grounding.load_fact_ledger()`
	@property
	def facts_json(self) -> Path:
		return Path(self.paths_str['facts_json'])
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.__init__()`
	@property
	def grounding_cache_json(self) -> Path:
		return Path(self.paths_str['grounding_cache_json'])
	# @used-by :func:`agent_tools.metrics.project_metrics()`
	# @used-by :func:`agent_tools.research.observed_use()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	@property
	def metrics_json(self) -> Path:
		return Path(self.paths_str['metrics_json'])
	# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
	# @used-by :func:`agent_tools.metrics.project_metrics()`
	@property
	def executors_json(self) -> Path:
		return Path(self.paths_str['executors_json'])
	# @used-by :func:`agent_tools.analysis.publish_owned()`
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :func:`agent_tools.operations._execute_collect()`
	# @used-by :func:`agent_tools.project_card.sync_block()`
	@property
	def rendered_json(self) -> Path:
		return Path(self.paths_str['rendered_json'])
	# @used-by :func:`agent_tools.evidence_loader.resolve_http_observation()`
	# @used-by :func:`agent_tools.research.collect()`
	@property
	def http_index_json(self) -> Path:
		return Path(self.paths_str['http_index_json'])
	# 2026-11-22
	# "Add declarative similar_projects registry groups and project overlay resolution":
	# https://github.com/dmitry-ai/harness/issues/122
	# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
	# @used-by :func:`agent_tools.completion.similar_project_exempt()`
	# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
	# @used-by :func:`evaluate_similar_project_touches()`
	# @used-by :func:`paths_report()`
	# @used-by :meth:`ProjectPaths.to_dict()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
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
	# @used-by :func:`paths_report()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
	def to_dict(self, *, check_exists: bool=True) -> dict[str, Any]:
		# @used-by :meth:`ProjectPaths.to_dict()`
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
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
# @used-by :func:`agent_tools.analysis.publish_analysis()`
# @used-by :func:`agent_tools.analysis.publish_owned()`
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
# @used-by :func:`agent_tools.claims._manifest_primary()`
# @used-by :func:`agent_tools.cli_common.verify_scratch_input_path()`
# @used-by :func:`agent_tools.completion._budget_status()`
# @used-by :func:`agent_tools.completion._compaction_status()`
# @used-by :func:`agent_tools.completion._delegation_status()`
# @used-by :func:`agent_tools.completion._factual_kb_note_issues()`
# @used-by :func:`agent_tools.completion._folder()`
# @used-by :func:`agent_tools.completion._instruction_snapshot()`
# @used-by :func:`agent_tools.completion._is_client_deliverable_path()`
# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
# @used-by :func:`agent_tools.completion._workflow_gate_resolved()`
# @used-by :func:`agent_tools.completion.begin()`
# @used-by :func:`agent_tools.completion.check_answer()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :func:`agent_tools.configuration._native_config()`
# @used-by :func:`agent_tools.configuration._project_rule_paths()`
# @used-by :func:`agent_tools.configuration._publish()`
# @used-by :func:`agent_tools.configuration.build_native()`
# @used-by :func:`agent_tools.configuration.configure_codex_project()`
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :func:`agent_tools.context.default_context_config()`
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.evidence.local_file()`
# @used-by :func:`agent_tools.evidence.source_reference()`
# @used-by :func:`agent_tools.evidence_loader.resolve_http_observation()`
# @used-by :func:`agent_tools.experiments.result_issues()`
# @used-by :func:`agent_tools.gates.external_write._check_df_issue_turn_intent()`
# @used-by :func:`agent_tools.gates.external_write._match_upwork_root()`
# @used-by :func:`agent_tools.git_ignore.prepare_worktrees_base_dir()`
# @used-by :func:`agent_tools.hook_crash_audit._load_violation_receipt()`
# @used-by :func:`agent_tools.intake._index()`
# @used-by :func:`agent_tools.intake._project()`
# @used-by :func:`agent_tools.intake._receipt()`
# @used-by :func:`agent_tools.intake._snapshot()`
# @used-by :func:`agent_tools.intake._validate_receipt()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.issue_first_inherit._candidate_project_roots()`
# @used-by :func:`agent_tools.issues.acceptance_gate._load_acceptance_receipt()`
# @used-by :func:`agent_tools.issues.comment_grounding._resolve_grounding_root()`
# @used-by :func:`agent_tools.issues.parity._load_similar_project_exemptions()`
# @used-by :func:`agent_tools.issues.parity._peer_code_repo_candidates()`
# @used-by :func:`agent_tools.issues.repo_locator._append_peer_repos()`
# @used-by :func:`agent_tools.issues.repo_locator._append_project_paths()`
# @used-by :func:`agent_tools.issues.repo_locator._index_discovery_roots()`
# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
# @used-by :func:`agent_tools.issues.service_helpers.resolve_metadata_project_root()`
# @used-by :func:`agent_tools.issues.turn_scope._candidate_turns_dirs()`
# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
# @used-by :func:`agent_tools.journal.canonicalize_journal_dir_identity()`
# @used-by :func:`agent_tools.journal.ensure_project_journal_upgraded()`
# @used-by :func:`agent_tools.journal.journal_pair_names()`
# @used-by :func:`agent_tools.journal.resolve_journal_dir()`
# @used-by :func:`agent_tools.journal.upgrade_journal()`
# @used-by :func:`agent_tools.knowledge._load_media_descriptions()`
# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
# @used-by :func:`agent_tools.knowledge.sync_website_card()`
# @used-by :func:`agent_tools.landing_lease._lease_file_for()`
# @used-by :func:`agent_tools.meta.builders._find_issue_state_pair()`
# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
# @used-by :func:`agent_tools.meta.identity._lookup_name_from_project_json()`
# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
# @used-by :func:`agent_tools.metrics.project_metrics()`
# @used-by :func:`agent_tools.operations._execute_collect()`
# @used-by :func:`agent_tools.path_cache.resolve_journal_data_dir()`
# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
# @used-by :func:`agent_tools.platforms.request_binding.completion_project_id()`
# @used-by :func:`agent_tools.platforms.request_binding.native_project_id()`
# @used-by :func:`agent_tools.platforms.trace_common.persist_review_proof()`
# @used-by :func:`agent_tools.polyglot_land._sandbox_root()`
# @used-by :func:`agent_tools.project_card.sync_block()`
# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
# @used-by :func:`agent_tools.project_drift.require_no_domain_drift_for_finalize()`
# @used-by :func:`agent_tools.project_rename._ag_id_from_receipt()`
# @used-by :func:`agent_tools.project_rename._sync_registrations()`
# @used-by :func:`agent_tools.project_rename._validate_rename_inputs()`
# @used-by :func:`agent_tools.project_rename.maybe_promote_project_domain()`
# @used-by :func:`agent_tools.project_rename_state._update_project_json()`
# @used-by :func:`agent_tools.project_rename_state.migrate_journal_state()`
# @used-by :func:`agent_tools.project_rename_state.refresh_workflow_file_hash()`
# @used-by :func:`agent_tools.project_rename_state.rewrite_launcher_handoffs()`
# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
# @used-by :func:`agent_tools.project_rename_verify._launcher_stale_files()`
# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`agent_tools.registration._begin()`
# @used-by :func:`agent_tools.registration._expected()`
# @used-by :func:`agent_tools.registration._read()`
# @used-by :func:`agent_tools.registration.save_registration()`
# @used-by :func:`agent_tools.repo_wait._workspace_code_repos()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.compute_site_summary()`
# @used-by :func:`agent_tools.research.evidence_query()`
# @used-by :func:`agent_tools.research.extract_file()`
# @used-by :func:`agent_tools.research.extract_observation()`
# @used-by :func:`agent_tools.research.load_observation()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.review._analysis()`
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.load_verified_claims_cache()`
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :func:`agent_tools.review.prepare_verdict_record()`
# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
# @used-by :func:`agent_tools.shadow_replay._find_reply_path()`
# @used-by :func:`agent_tools.shadow_replay._run_pre_invocation()`
# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
# @used-by :func:`agent_tools.shadow_replay_command._stage_ag_from_receipt()`
# @used-by :func:`agent_tools.shadow_replay_command.persist_shadow_replay_receipt()`
# @used-by :func:`agent_tools.source_grounding.load_fact_ledger()`
# @used-by :func:`agent_tools.storage.data_dir_for()`
# @used-by :func:`agent_tools.tdd.classifier._resolve_deleted_worktree_scope()`
# @used-by :func:`agent_tools.tdd.mechanical._candidate_recipe_dirs()`
# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
# @used-by :func:`agent_tools.tdd.ratchet._turn_receipt_dirs()`
# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
# @used-by :func:`agent_tools.text_claims.registry_path()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_workflow._folder()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`agent_tools.upwork_project.default_context_config()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`agent_tools.worker_semaphore.default_slots_dir()`
# @used-by :func:`agent_tools.workflow.evidence_paths()`
# @used-by :func:`agent_tools.workflow.kb_paths()`
# @used-by :func:`agent_tools.worktree_flow._resolve_deleted_worktree_file()`
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
# @used-by :func:`check_markdown_slop._check_turn_budget_gate()`
# @used-by :func:`check_pre_invocation._scratch_answer_path()`
# @used-by :func:`check_pre_invocation._turns_dir()`
# @used-by :func:`check_stop_gate._turns_dir()`
# @used-by :func:`evaluate_similar_project_touches()`
# @used-by :func:`is_tracked_workspace()`
# @used-by :func:`paths_report()`
# @used-by :func:`tool_value()`
# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner.__init__()`
# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore.__init__()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._verify_saved_artifacts()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.load()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate._tdd_project_root()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.is_issue_tracked()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_repos_and_issues()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_files()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.meta_dir_for_project_root()`
# @used-by :meth:`agent_tools.knowledge.AttachmentInventory.__init__()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_evidence_files()`
# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.__init__()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.__init__()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.__init__()`
# @used-by :meth:`agent_tools.workflow.ResearchQuestionRegistry.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.adopt_requests()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.record_current_answer()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.resume()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_still_rejects_client_claim_ids_inside_doc5()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_fast_cache_hits_and_invalidates_on_fs_mutations()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_lru_retains_more_than_256_entries()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_automatic_journal_only_upgrade_and_cli_subcommand()`
def project_paths(path_or_root: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None, exact_root: bool=False) -> ProjectPaths:
	reg = registry or load_registry(env=env)
	# 2026-11-24
	# "Accelerate project_paths and overlay link resolution with fast-path caching":
	# https://github.com/dmitry-ai/harness/issues/174
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
# 2026-11-23
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
_EXCLUDED_PROJECT_IDS = frozenset(('outside-of-project', 'default-cli-project'))
# @used-by :func:`is_tracked_workspace()`
def _is_registered_single_project(canon: Path, *, registry: PathRegistry, projects_dirs=None) -> bool:
	dirs: list[Path] = []
	if None is not projects_dirs:
		for d in projects_dirs:
			if d:
				dirs.append(Path(d))
	else:
		seen_dirs: set[str] = set()
		# @used-by :func:`_is_registered_single_project()`
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
# 2026-11-23
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
# @used-by :func:`check_pre_invocation._is_tracked_and_non_umbrella()`
# @used-by :func:`check_stop_gate._tracked_workspace()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
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
# 2026-11-22
# "Add declarative similar_projects registry groups and project overlay resolution":
# https://github.com/dmitry-ai/harness/issues/122
# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
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
	# @used-by :func:`evaluate_similar_project_touches()`
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
	# @used-by :func:`evaluate_similar_project_touches()`
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
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_registry_and_runtime_contain_no_hardcoded_host_paths_outside_r_and_validate_five_overlays()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
def paths_report(project: str | Path | None=None, *, expand: str | None=None, check: bool=False, registry: PathRegistry | None=None) -> dict[str, Any]:
	reg = registry or load_registry()
	issues: list[dict[str, str]] = []
	discovered_overlays: list[dict[str, Any]] = []
	# 2026-11-22
	# "Add declarative similar_projects registry groups and project overlay resolution":
	# https://github.com/dmitry-ai/harness/issues/122
	if check:
		for grp in reg.similar_project_groups:
			for mem in grp['members']:
				m_proj = Path(mem['project'])
				if not m_proj.is_dir():
					issues.append({'file': reg.source_path.as_posix(), 'message': f"Missing similar_projects member directory in group '{grp['id']}': {m_proj.as_posix()}"})
				for aff in mem['affiliated_paths']:
					# 2026-11-22
					# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
					# https://github.com/dmitry-ai/harness/issues/123
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
