# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import os
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
ESC_DOLLAR = '\x00HARNESS_DOLLAR_LBRACE\x00'
ESC_PERCENT = '\x00HARNESS_PERCENT\x00'
EXCLUDED_PROJECT_IDS = frozenset(('outside-of-project', 'default-cli-project'))
INITIAL_HOME = Path.home().as_posix().rstrip('/')
JOURNAL_BUCKET_DIR_RE = re.compile('^(\\d+)[-\\u2013](\\d+)$')
SIMILAR_GROUP_ID_RE = re.compile('^[A-Za-z0-9_.-]+$')
TOKEN_RE = re.compile('\\$\\$\\{|%%|\\$\\{([^}]*)\\}|%([A-Za-z_][A-Za-z0-9_]*)%')
URI_SCHEME_RE = re.compile('^[A-Za-z][A-Za-z0-9+.-]*://')
VAR_NAME_RE = re.compile('^[A-Za-z_][A-Za-z0-9_]*$')
# @used-by :func:`dfh_normalize_path_str()`
def _collapse_path_parts(parts: list[str], is_abs: bool) -> str:
	resolved: list[str] = []
	for seg in parts:
		if '..' == seg:
			if resolved and '..' != resolved[-1] and ('*' not in resolved[-1]) and ('?' not in resolved[-1]):
				resolved.pop()
			elif not is_abs:
				resolved.append(seg)
		else:
			resolved.append(seg)
	return '/'.join(resolved)
# @used-by :func:`_expand_match()`
def _expand_braced_token(braced: str | None, variables: dict[str, str], env: dict[str, str] | None, resolving: tuple[str, ...]) -> str:
	expr = (braced or '').strip()
	if expr.upper().startswith('ENV:'):
		env_name = expr[4:].strip()
		if not VAR_NAME_RE.match(env_name):
			raise ValueError(f'Invalid environment variable name in template: ${{{braced}}}')
		val = dfh_lookup_env(env_name, env)
		if None is val:
			raise ValueError(f'Unresolved environment variable in path template: ${{{braced}}}')
		r = val.replace('${', ESC_DOLLAR).replace('%', ESC_PERCENT)
	else:
		if not VAR_NAME_RE.match(expr):
			raise ValueError(f'Invalid path template variable syntax: ${{{braced}}}')
		if expr in resolving:
			raise ValueError(f"Cyclic path template variable reference: {' -> '.join((*resolving, expr))}")
		if expr not in variables:
			raise ValueError(f'Unknown path template variable: ${{{expr}}}')
		target = dfh_expand_template(variables[expr], variables, env=env, normalize=False, _resolving=(*resolving, expr))
		r = dfh_normalize_path_str(target, preserve_trailing_slash=True)
	return r
# @used-by :func:`_substitute_template()`
def _expand_match(match: re.Match, variables: dict[str, str], env: dict[str, str] | None, resolving: tuple[str, ...]) -> str:
	full = match.group(0)
	if '$${' == full:
		r = ESC_DOLLAR
	elif '%%' == full:
		r = ESC_PERCENT
	elif None is not match.group(2):
		pct = match.group(2)
		val = dfh_lookup_env(pct, env)
		if None is val:
			raise ValueError(f'Unresolved environment variable in path template: %{pct}%')
		r = val.replace('${', ESC_DOLLAR).replace('%', ESC_PERCENT)
	else:
		r = _expand_braced_token(match.group(1), variables, env, resolving)
	return r
# @used-by :func:`dfh_normalize_path_str()`
def _format_normalized_path(joined: str, is_unc: bool, drive: str, is_abs: bool, preserve_trailing: bool) -> str:
	if is_unc:
		out = '//' + joined
	elif drive:
		out = f'{drive}/{joined}' if joined else f'{drive}/'
	elif is_abs:
		out = '/' + joined
	else:
		out = joined or '.'
	return out + '/' if preserve_trailing and (not out.endswith('/')) else out
# @used-by :func:`dfh_lookup_env()`
def _lookup_fallback_env(upper: str, environ: dict[str, str] | os._Environ) -> str | None:
	if 'OS_USER_HOME' == upper:
		r: str | None = dfh_resolve_os_user_home(environ)
	else:
		home = dfh_resolve_process_home(environ)
		defaults = {'APPDATA': f'{home}/AppData/Roaming', 'HOME': home, 'LOCALAPPDATA': f'{home}/AppData/Local', 'PROGRAMFILES': 'C:/Program Files', 'SYSTEMROOT': 'C:/Windows', 'USERPROFILE': home, 'WINDIR': 'C:/Windows'}
		r = defaults.get(upper)
	return r
# @used-by :func:`dfh_normalize_path_str()`
def _split_path_root(text: str) -> tuple[bool, str, str]:
	is_unc = text.startswith('//') and (not text.startswith('///'))
	drive, rest = ('', text)
	if is_unc:
		rest = text[2:]
	elif re.match('^[A-Za-z]:(?:/|$)', text):
		drive, rest = (text[:2], text[2:])
	return (is_unc, drive, rest)
# @used-by :func:`dfh_expand_template()`
def _substitute_template(template: str, variables: dict[str, str], env: dict[str, str] | None, resolving: tuple[str, ...]) -> str:
	unclosed = template.replace('$${', '')
	if '${' in unclosed and None is re.search('\\$\\{[^}]*\\}', unclosed):
		raise ValueError(f'Unclosed template variable in {template!r}')
	expanded = TOKEN_RE.sub(lambda m: _expand_match(m, variables, env, resolving), template)
	if '${' in expanded.replace(ESC_DOLLAR, ''):
		raise ValueError(f'Malformed template variable syntax in {template!r}')
	return expanded if resolving else expanded.replace(ESC_DOLLAR, '${').replace(ESC_PERCENT, '%')
# @used-by :func:`Df.Harness.lib.path_schema._is_non_canonical_bucket()`
def dfh_canonical_journal_bucket(step: int, bucket_size: int=20) -> str:
	start = ((step - 1) // bucket_size) * bucket_size + 1
	return f'{start}\u2013{start + bucket_size - 1}'
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_load_registry()`
def dfh_env_fingerprint(env: dict[str, str] | None) -> tuple:
	if None is env:
		keys = ('OS_USER_HOME', 'USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'SYSTEMROOT', 'HARNESS_PATHS_FILE')
		r: tuple = tuple(((k, os.environ.get(k)) for k in keys))
	else:
		r = tuple(sorted(((str(k), str(v)) for k, v in env.items())))
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._default_user_home_vars()`
# @used-by :func:`agent_tools.path_registry.escape_template_literal()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_raw_paths_and_vars()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__anchor_overrides()`
# @used-by :meth:`Df.Harness.Path.SlotResolver.SlotResolver.__resolve_one()`
# @used-by :meth:`Df.Harness.Runtime.AddonsProfileAdapter.AddonsProfileAdapter.__attach_optional_fields()`
# @used-by :meth:`Df.Harness.Runtime.AddonsProfileAdapter.AddonsProfileAdapter.__build_instance()`
def dfh_escape_template_literal(value: str) -> str:
	return str(value).replace('%', '%%').replace('${', '$${')
# @used-by :func:`agent_tools.path_registry.expand_structure()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_tools_and_repos()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_core_maps()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__parse_workspace_overrides()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.expand_data()`
def dfh_expand_structure(value: Any, variables: dict[str, str], *, env: dict[str, str] | None=None) -> Any:
	if isinstance(value, str):
		r: Any = dfh_expand_template(value, variables, env=env, normalize=True) if '${' in value or '$${' in value or '%%' in value or re.search('%[A-Za-z_][A-Za-z0-9_]*%', value) else value
	elif isinstance(value, list):
		r = [dfh_expand_structure(item, variables, env=env) for item in value]
	elif isinstance(value, tuple):
		r = tuple((dfh_expand_structure(item, variables, env=env) for item in value))
	elif isinstance(value, dict):
		r = {dfh_expand_structure(k, variables, env=env) if isinstance(k, str) else k: dfh_expand_structure(v, variables, env=env) for k, v in value.items()}
	else:
		r = value
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._add_ag_defaults()`
# @used-by :func:`Df.Harness.lib.path_discovery._expand_platform_slots()`
# @used-by :func:`Df.Harness.lib.path_discovery._resolve_ag_backend_dir()`
# @used-by :func:`Df.Harness.lib.path_discovery._resolve_ag_cfg_dir()`
# @used-by :func:`Df.Harness.lib.path_schema._build_similar_members()`
# @used-by :func:`Df.Harness.lib.path_schema._collect_member_affiliates()`
# @used-by :func:`_expand_braced_token()`
# @used-by :func:`agent_tools.path_registry.expand_template()`
# @used-by :func:`dfh_expand_structure()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__resolve_rel_to_root()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.var()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__anchor_overrides()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_core_maps()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_overlays_and_profiles()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_variables()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__parse_workspace_overrides()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.expand()`
# @used-by :meth:`Df.Harness.Path.SlotResolver.SlotResolver.__resolve_one()`
def dfh_expand_template(template: str, variables: dict[str, str], *, env: dict[str, str] | None=None, normalize: bool=True, _resolving: tuple[str, ...]=()) -> str:
	if not isinstance(template, str):
		raise TypeError(f'Template must be a string, got {type(template).__name__}')
	if 32 < len(_resolving):
		raise ValueError(f"Path template recursion depth exceeded: {' -> '.join(_resolving)}")
	raw = template if '$' not in template and '%' not in template else _substitute_template(template, variables, env, _resolving)
	return dfh_normalize_path_str(raw) if normalize else raw
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_candidate_discovery_roots()`
def dfh_glob_parent_stat(pattern: str) -> tuple:
	prefix = re.split('[*?\\[]', pattern, maxsplit=1)[0].rstrip('/\\')
	parent = Path(prefix) if prefix else Path('.')
	if not parent.is_dir():
		parent = parent.parent
	try:
		st = os.stat(parent)
		r: tuple = (str(parent), st.st_mtime_ns, st.st_size)
	except OSError:
		r = (str(parent), None, None)
	return r
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__anchor_overrides()`
def dfh_infer_harness_anchor(anchor_code: Path) -> tuple[Path, Path, int]:
	if '\u26ef' == anchor_code.name and 4 <= len(anchor_code.parents) and (anchor_code.parent.name, anchor_code.parents[1].name, anchor_code.parents[2].name) in (('\u2655', '\u227b', '\u2c0f'), ('Deliverables', '\u227b', 'Artifacts')):
		root = anchor_code.parents[3].resolve()
		r = (root, root, 2)
	else:
		root = anchor_code.parent.resolve()
		r = (root, (root / '_').resolve() if (root / '_').is_dir() else root, 1)
	return r
# @used-by :func:`Df.Harness.lib.path_resolve._stat_unlinked_registry()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_load_registry()`
# @used-by :func:`Df.Harness.lib.path_schema._collect_overlay_files()`
# @used-by :func:`Df.Harness.lib.trace_review._arch_index_packages()`
# @used-by :func:`Df.Harness.lib.trace_review._arch_target_repo_roots()`
# @used-by :func:`Df.Harness.lib.trace_review._read_verified_package_repo()`
# @used-by :func:`Df.Harness.lib.trace_review._validated_target_roots()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__normalize_repo()`
# @used-by :meth:`Df.Harness.Runtime.AddonsProfileAdapter.AddonsProfileAdapter.__read_profiles_file()`
def dfh_is_linked(path: Path, stop_at: Path | None=None) -> bool:
	stop_norm = os.path.normcase(os.path.abspath(stop_at)) if None is not stop_at else None
	cur = Path(os.path.abspath(path))
	r = False
	while True:
		if None is not stop_norm and os.path.normcase(str(cur)) == stop_norm:
			break
		try:
			if os.path.lexists(cur) and (cur.is_symlink() or cur.is_junction()):
				r = True
				break
		except OSError:
			pass
		if cur.parent == cur:
			break
		cur = cur.parent
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._default_user_home_vars()`
# @used-by :func:`_expand_braced_token()`
# @used-by :func:`_expand_match()`
def dfh_lookup_env(name: str, env: dict[str, str] | None=None) -> str | None:
	environ = os.environ if None is env else env
	if name in environ and str(environ[name]).strip():
		r: str | None = str(environ[name]).replace('\\', '/')
	else:
		upper = name.upper()
		matched = next((str(v).replace('\\', '/') for k, v in environ.items() if k.upper() == upper and str(v).strip()), None)
		r = matched if None is not matched else _lookup_fallback_env(upper, environ)
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._resolve_initial_home()`
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_default_platform_paths()`
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_derive_platform_system_paths()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._active_home_match_info()`
# @used-by :func:`Df.Harness.lib.runtime_validate.dfh_expand_path()`
# @used-by :func:`_expand_braced_token()`
# @used-by :func:`agent_tools.path_registry.normalize_path_str()`
# @used-by :func:`dfh_expand_template()`
# @used-by :func:`dfh_resolve_os_user_home()`
# @used-by :func:`dfh_resolve_process_home()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_journal()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__resolve_effective_journal_dir()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__resolve_rel_to_root()`
# @used-by :meth:`Df.Harness.Path.SlotResolver.SlotResolver.__resolve_one()`
def dfh_normalize_path_str(raw: str, *, preserve_trailing_slash: bool=False) -> str:
	if not isinstance(raw, str):
		raise TypeError('Path template value must be a string')
	if not raw or URI_SCHEME_RE.match(raw) or raw.startswith('mailto:'):
		r = raw
	else:
		text = raw.replace('\\', '/')
		if text.startswith('~'):
			text = os.path.expanduser(text).replace('\\', '/')
		is_unc, drive, rest = _split_path_root(text)
		is_abs = bool(drive) or is_unc or rest.startswith('/')
		joined = _collapse_path_parts([seg for seg in rest.split('/') if seg and '.' != seg], is_abs)
		r = _format_normalized_path(joined, is_unc, drive, is_abs, preserve_trailing_slash and raw.endswith(('/', '\\')))
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._collect_candidate_dirs()`
# @used-by :func:`Df.Harness.lib.path_discovery._match_journal_fallback()`
# @used-by :func:`Df.Harness.lib.path_discovery._match_primary_marker()`
# @used-by :func:`Df.Harness.lib.path_discovery._project_file_matches_root()`
# @used-by :func:`Df.Harness.lib.path_discovery._push_index_entry()`
# @used-by :func:`Df.Harness.lib.path_discovery._runtime_ag_projects_dirs()`
# @used-by :func:`Df.Harness.lib.path_discovery._scan_overlay_links()`
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_find_local_marker_root()`
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_is_registered_single_project()`
# @used-by :func:`Df.Harness.lib.path_resolve._find_overlay_ancestor()`
# @used-by :func:`Df.Harness.lib.path_resolve._resolve_from_markers_or_reverse()`
# @used-by :func:`Df.Harness.lib.path_resolve._workspace_is_explicitly_tracked()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_is_tracked_workspace()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_relocated_harness_code_dirs()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_resolve_project_root()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_same_project_root()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_workspace_override()`
# @used-by :func:`Df.Harness.lib.path_schema._apply_relocations()`
# @used-by :func:`Df.Harness.lib.path_schema._build_similar_members()`
# @used-by :func:`Df.Harness.lib.path_schema._collect_member_affiliates()`
# @used-by :func:`Df.Harness.lib.shadow_clone._journal_identity_hook()`
# @used-by :func:`Df.Harness.lib.shadow_clone._shadow_registry_wrapper()`
# @used-by :func:`agent_tools.path_registry._path_key()`
# @used-by :func:`agent_tools.shadow_replay_clone._legacy_shadow_patch_ctx()`
# @used-by :func:`dfh_resolve_os_user_home()`
# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__discover_overlays()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_raw_paths_and_vars()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_similar_projects()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.register_reverse_links()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.similar_projects()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__anchor_overrides()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_core_maps()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_variables()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__parse_workspace_overrides()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__eval_overlay_peers()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__match_roots()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__record_group_peers()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__record_peer()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__resolve_input_files()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.run()`
def dfh_path_key(value: str | Path) -> str:
	return str(value).replace('\\', '/').rstrip('/').casefold()
# @used-by :func:`_lookup_fallback_env()`
def dfh_resolve_os_user_home(environ) -> str:
	proc_home = dfh_resolve_process_home(environ)
	raw_ad = next((dfh_normalize_path_str(str(v)).rstrip('/') for k, v in environ.items() if 'APPDATA' == k.upper() and str(v).strip()), None)
	r = proc_home
	if raw_ad and raw_ad.casefold().endswith('/appdata/roaming'):
		proc_key, app_key = (dfh_path_key(proc_home), dfh_path_key(raw_ad))
		if proc_key == app_key or proc_key.startswith(app_key + '/'):
			app_p = Path(raw_ad)
			if 2 <= len(app_p.parents):
				cand = app_p.parents[1].as_posix().rstrip('/')
				if cand and Path(cand).parent != Path(cand):
					r = cand
	return r
# @used-by :func:`_lookup_fallback_env()`
# @used-by :func:`dfh_resolve_os_user_home()`
def dfh_resolve_process_home(environ) -> str:
	home = None
	for hk in ('USERPROFILE', 'HOME'):
		home = next((dfh_normalize_path_str(str(v)).rstrip('/') for k, v in environ.items() if k.upper() == hk and str(v).strip()), None)
		if home:
			break
	if not home:
		try:
			home = Path.home().as_posix().rstrip('/')
		except RuntimeError:
			home = INITIAL_HOME
	return home
# @used-by :func:`Df.Harness.lib.path_schema._parse_similar_member()`
# @used-by :func:`Df.Harness.lib.path_schema.dfh_validate_overlay()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__build_profile_spec()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_core_maps()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_overlays_and_profiles()`
def dfh_validate_string_list(raw: Any, label: str) -> list[str]:
	if None is raw:
		r: list[str] = []
	elif not isinstance(raw, list) or any((not isinstance(x, str) or not x.strip() for x in raw)):
		raise ValueError(f'{label} must be a list of non-empty path strings')
	else:
		r = list(raw)
	return r
# @used-by :func:`Df.Harness.lib.path_schema.dfh_validate_overlay()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__build_profile_spec()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_core_maps()`
def dfh_validate_string_map(raw: Any, label: str) -> dict[str, str]:
	if None is raw:
		r: dict[str, str] = {}
	elif not isinstance(raw, dict):
		raise ValueError(f'{label} must be an object')
	else:
		r = {}
		for k, v in raw.items():
			if not isinstance(k, str) or not k.strip() or (not isinstance(v, str)) or (not v.strip()):
				raise ValueError(f'{label} entries must map non-empty keys to non-empty path strings')
			r[k] = v
	return r
# @used-by :func:`Df.Harness.lib.path_schema.dfh_validate_overlay()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__build_profile_spec()`
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_variables()`
def dfh_validate_variables_map(raw: Any, label: str) -> dict[str, str]:
	if None is raw:
		r: dict[str, str] = {}
	elif not isinstance(raw, dict):
		raise ValueError(f'{label} must be an object mapping variable names to strings')
	else:
		r = {}
		for k, v in raw.items():
			if not isinstance(k, str) or not VAR_NAME_RE.match(k):
				raise ValueError(f'{label} contains invalid variable name: {k!r}')
			if not isinstance(v, str) or not v.strip():
				raise ValueError(f'{label}.{k} must be a non-empty string')
			r[k] = v
	return r
