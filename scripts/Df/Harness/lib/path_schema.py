# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_template import JOURNAL_BUCKET_DIR_RE, SIMILAR_GROUP_ID_RE, dfh_canonical_journal_bucket, dfh_expand_template, dfh_is_linked, dfh_path_key, dfh_validate_string_list, dfh_validate_string_map, dfh_validate_variables_map
import json
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_canonicalize_root_dir()`
def _apply_relocations(path: Path, relocations: dict[str, str]) -> Path:
	cur = path
	for _ in range(4):
		key = dfh_path_key(cur)
		if key not in relocations:
			break
		next_p = Path(relocations[key]).resolve()
		if next_p == cur:
			break
		cur = next_p
	return cur
# @used-by :func:`_validate_one_similar_group()`
def _build_similar_members(raw_members: list[Any], gid: str, variables: dict[str, str], env: dict[str, str] | None) -> tuple[dict[str, Any], ...]:
	member_keys, aff_owners, out = (set(), [], [])
	for m_idx, item in enumerate(raw_members):
		proj_tpl, raw_aff = _parse_similar_member(item, gid, m_idx)
		proj_res = dfh_expand_template(proj_tpl, variables, env=env, normalize=True)
		proj_abs = Path(os.path.abspath(proj_res)).as_posix()
		m_key = dfh_path_key(proj_abs)
		if m_key in member_keys:
			raise ValueError(f'Duplicate member project {proj_res} in similar_projects.{gid}')
		member_keys.add(m_key)
		out.append({'affiliated_paths': _collect_member_affiliates(raw_aff, variables, env, gid, m_key, aff_owners), 'project': proj_abs})
	return tuple(out)
# @used-by :func:`_build_similar_members()`
def _collect_member_affiliates(raw_aff: list[str], variables: dict[str, str], env: dict[str, str] | None, gid: str, m_key: str, aff_owners: list[tuple[Path, str]]) -> tuple[str, ...]:
	out: list[str] = []
	seen: set[str] = set()
	for aff_tpl in raw_aff:
		aff_res = dfh_expand_template(aff_tpl, variables, env=env, normalize=True)
		aff_p = Path(os.path.abspath(aff_res))
		a_key = dfh_path_key(aff_p)
		for prev_p, prev_owner in aff_owners:
			if prev_owner != m_key and (a_key == dfh_path_key(prev_p) or aff_p.is_relative_to(prev_p) or prev_p.is_relative_to(aff_p)):
				raise ValueError(f'Overlapping affiliated_paths in similar_projects.{gid}: {aff_res}')
		if a_key not in seen:
			seen.add(a_key)
			aff_owners.append((aff_p, m_key))
			out.append(aff_p.as_posix())
	return tuple(out)
# @used-by :func:`dfh_discover_overlay_file()`
def _collect_overlay_files(root_p: Path, candidates: list[str] | tuple[str, ...]) -> list[Path]:
	found: list[Path] = []
	for rel in candidates:
		cand = root_p / rel
		if os.path.lexists(cand):
			if dfh_is_linked(cand, stop_at=root_p):
				raise ValueError(f'Linked project paths.json overlay preserved and refused: {cand}')
			if cand.is_file():
				found.append(cand.resolve())
	return found
# @used-by :func:`dfh_inspect_journal_dir_on_disk()`
def _inspect_v2_journal_side(side_p: Path, b_size: int) -> bool:
	is_v2_flat = False
	if side_p.is_dir():
		try:
			children = list(side_p.iterdir())
		except OSError:
			children = []
		for child in children:
			if _is_step_md_file(child) or (child.is_dir() and JOURNAL_BUCKET_DIR_RE.fullmatch(child.name) and _is_non_canonical_bucket(child, b_size)):
				is_v2_flat = True
				break
	return is_v2_flat
# @used-by :func:`_inspect_v2_journal_side()`
def _is_non_canonical_bucket(child: Path, b_size: int) -> bool:
	try:
		b_files = [bf for bf in child.iterdir() if _is_step_md_file(bf)]
	except OSError:
		b_files = []
	return (not b_files) or any((child.name != dfh_canonical_journal_bucket(int(bf.stem), b_size) for bf in b_files))
# @used-by :func:`_inspect_v2_journal_side()`
# @used-by :func:`_is_non_canonical_bucket()`
def _is_step_md_file(path: Path) -> bool:
	return path.is_file() and '.md' == path.suffix.lower() and path.stem.isascii() and path.stem.isdigit() and 1 <= int(path.stem)
# @used-by :func:`_validate_one_similar_group()`
def _parse_similar_group_header(grp: Any, idx: int, seen_ids: set[str]) -> tuple[str, list[Any]]:
	if not isinstance(grp, dict):
		raise ValueError(f'paths.json similar_projects[{idx}] must be an object')
	unknown_g = set(grp) - {'id', 'members', 'notes', 'projects'}
	if unknown_g:
		raise ValueError(f"Unknown keys in similar_projects[{idx}]: {', '.join(sorted(unknown_g))}")
	gid = grp.get('id')
	if not isinstance(gid, str) or not SIMILAR_GROUP_ID_RE.fullmatch(gid.strip()):
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
	return (gid, raw_members)
# @used-by :func:`_build_similar_members()`
def _parse_similar_member(item: Any, gid: str, m_idx: int) -> tuple[str, list[str]]:
	if isinstance(item, str):
		proj_tpl, raw_aff = (item, [])
	elif isinstance(item, dict):
		unknown_m = set(item) - {'affiliated_paths', 'notes', 'project'}
		if unknown_m:
			raise ValueError(f"Unknown keys in similar_projects.{gid}.members[{m_idx}]: {', '.join(sorted(unknown_m))}")
		proj_tpl = item.get('project')
		raw_aff = dfh_validate_string_list(item.get('affiliated_paths'), f'similar_projects.{gid}.members[{m_idx}].affiliated_paths')
	else:
		raise ValueError(f'similar_projects.{gid}.members[{m_idx}] must be a path string or member object')
	if not isinstance(proj_tpl, str) or not proj_tpl.strip():
		raise ValueError(f'similar_projects.{gid}.members[{m_idx}].project must be a non-empty path string')
	return (proj_tpl, raw_aff)
# @used-by :func:`dfh_infer_default_profile()`
def _project_json_fs_profile(root: Path, agent_name: str, reg: Any, explicit_fs_version: int | None) -> str | None:
	pjson = root / agent_name / 'project.json'
	r: str | None = None
	if pjson.is_file():
		r = 'upwork'
		if 1 != explicit_fs_version and 'v2' in reg.project_profiles:
			try:
				pdata = json.loads(pjson.read_text(encoding='utf-8-sig'))
				if isinstance(pdata, dict) and 2 == pdata.get('fs_version'):
					r = 'v2'
			except (OSError, ValueError):
				pass
	return r
# @used-by :func:`dfh_canonicalize_root_dir()`
def _unwrap_v2_nested_node(path: Path, reg: Any, names: dict[str, str]) -> Path:
	r = path
	chain = (path, *path.parents)
	for idx, node in enumerate(chain):
		if node.name in (names['srv'], names['web']) and idx + 5 < len(chain):
			if chain[idx + 1].name == names['sw'] and (chain[idx + 2].name, chain[idx + 3].name) in ((names['deliv'], names['art_out']), ('Deliverables', names['art_out'])) and chain[idx + 4].name in (names['art'], 'Artifacts'):
				cand = chain[idx + 5].resolve()
				if (cand / names['agent']).is_dir() or (cand / '.agents').is_dir() or dfh_has_v2_markers(cand, reg):
					r = cand
					break
	return r
# @used-by :func:`dfh_validate_overlay()`
def _validate_overlay_scalars(fs_ver: Any, j_ver: Any, tracked: Any, profile: Any, overlay_path: Path, reg: Any) -> None:
	if None is not fs_ver and (int is not type(fs_ver) or fs_ver not in (1, 2)):
		raise ValueError(f'{overlay_path} fs_version must be 1 or 2')
	if None is not j_ver and (int is not type(j_ver) or j_ver not in (1, 2, 3)):
		raise ValueError(f'{overlay_path} journal_version must be 1, 2, or 3')
	if None is not tracked and bool is not type(tracked):
		raise ValueError(f'{overlay_path} tracked must be a boolean')
	if None is not profile and (not isinstance(profile, str) or profile not in reg.project_profiles):
		raise ValueError(f'Unknown profile {profile!r} in project overlay {overlay_path}')
# @used-by :func:`dfh_validate_similar_project_groups()`
def _validate_one_similar_group(grp: Any, idx: int, seen_ids: set[str], variables: dict[str, str], env: dict[str, str] | None) -> dict[str, Any]:
	gid, raw_members = _parse_similar_group_header(grp, idx, seen_ids)
	return {'id': gid, 'members': _build_similar_members(raw_members, gid, variables, env)}
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_resolve_admission_proof_file()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_analysis_root()`
# @used-by :func:`Df.Harness.lib.codex_metadata.dfh_codex_review_inputs()`
# @used-by :func:`Df.Harness.lib.completion_checks._collect_group_peers()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_gate_resolved()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_similar_projects_metadata()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_begin()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_conversation_journal_steps()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_same_turn_artifact_path()`
# @used-by :func:`Df.Harness.lib.completion_recovery._allowed_similar_peers()`
# @used-by :func:`Df.Harness.lib.completion_recovery._normalize_peer_path()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_recover_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_similar_project_exempt()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_load_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.journal_core.dfh_canonicalize_journal_dir_identity()`
# @used-by :func:`Df.Harness.lib.path_discovery._match_primary_marker()`
# @used-by :func:`Df.Harness.lib.path_discovery._project_file_matches_root()`
# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
# @used-by :func:`Df.Harness.lib.path_resolve._find_overlay_ancestor()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_is_tracked_workspace()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_resolve_project_root()`
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_same_project_root()`
# @used-by :func:`Df.Harness.lib.request_binding.dfh_canonical_path()`
# @used-by :func:`agent_tools.path_registry.canonicalize_root_dir()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__init__()`
# @used-by :meth:`Df.Harness.Journal.OpenTurnSyncer.OpenTurnSyncer.run()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init__()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_similar_projects()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__eval_groups()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.run()`
def dfh_canonicalize_root_dir(value: str | Path, reg: Any) -> Path:
	rv = reg.resolved_variables
	names = {'agent': rv.get('AGENT_DIR_NAME', '\ua616'), 'art': rv.get('ARTIFACTS_DIR_NAME', '\u2c0f'), 'art_out': rv.get('ARTIFACTS_OUT_DIR_NAME', '\u227b'), 'deliv': rv.get('DELIVERABLES_DIR_NAME', '\u2655'), 'meta': rv.get('META_DIR_NAME', '_'), 'srv': rv.get('SERVER_DIR_NAME', '\U0001d412'), 'sw': rv.get('SOFTWARE_DIR_NAME', '\u26ef'), 'web': rv.get('WEBSITE_DIR_NAME', '\U0001d416')}
	path = Path(value).resolve()
	if path.name in ('code', names['meta']) and (path.parent / 'code').is_dir() and (path.parent / names['meta']).is_dir():
		path = path.parent.resolve()
	elif path.name == names['sw'] and 4 <= len(path.parents) and (path.parent.name, path.parents[1].name, path.parents[2].name) in ((names['deliv'], names['art_out'], names['art']), ('Deliverables', names['art_out'], 'Artifacts')):
		cand = path.parents[3].resolve()
		if (cand / names['agent']).is_dir() or (cand / '.agents').is_dir() or dfh_has_v2_markers(cand, reg):
			path = cand
	elif path.name in (names['sw'], names['srv']) or (path / '.git').exists():
		path = _unwrap_v2_nested_node(path, reg, names)
	return _apply_relocations(path, reg.relocations)
# @used-by :func:`Df.Harness.lib.journal_upgrade._overlay_needs_sync()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._sync_overlay_journal_slot()`
# @used-by :func:`Df.Harness.lib.path_discovery._scan_overlay_links()`
# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
# @used-by :func:`Df.Harness.lib.path_resolve._find_overlay_ancestor()`
# @used-by :func:`agent_tools.path_registry.discover_overlay_file()`
# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__discover_overlays()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_overlay_and_profile()`
def dfh_discover_overlay_file(root: str | Path, reg: Any, *, _resolved_root: bool=False) -> Path | None:
	root_p = Path(root) if _resolved_root else Path(root).resolve()
	r: Path | None = None
	if root_p.is_dir():
		found = _collect_overlay_files(root_p, reg.overlay_candidates)
		if 1 < len(found) and 1 < len({p.read_bytes() for p in found}):
			raise ValueError(f"Conflicting project paths.json overlays in {root_p}: {', '.join((str(p) for p in found))}")
		r = found[0] if found else None
	return r
# @used-by :func:`_unwrap_v2_nested_node()`
# @used-by :func:`dfh_canonicalize_root_dir()`
# @used-by :func:`dfh_infer_default_profile()`
def dfh_has_v2_markers(root: Path, reg: Any) -> bool:
	rv = reg.resolved_variables
	book, art, art_out, art_in = (rv.get('BOOK_DIR_NAME', '\U0001f56e'), rv.get('ARTIFACTS_DIR_NAME', '\u2c0f'), rv.get('ARTIFACTS_OUT_DIR_NAME', '\u227b'), rv.get('ARTIFACTS_IN_DIR_NAME', '\u227a'))
	return (root / book).is_dir() or (root / art / art_out).is_dir() or (root / art / art_in).is_dir() or (root / 'Artifacts' / art_out).is_dir() or (root / 'Artifacts' / art_in).is_dir()
# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_overlay_and_profile()`
def dfh_infer_default_profile(root: Path, overlay_file: Path | None, reg: Any, *, explicit_fs_version: int | None=None) -> str:
	rv = reg.resolved_variables
	meta, agent, j_name = (rv.get('META_DIR_NAME', '_'), rv.get('AGENT_DIR_NAME', '\ua616'), rv.get('JOURNAL_DIR_NAME', '\ua66e'))
	has_v2_sw = (dfh_v2_software_deliverable_dir(root, reg) / '.git').exists() and 'v2_software' in reg.project_profiles
	if 2 == explicit_fs_version:
		r = 'v2_software' if has_v2_sw else ('v2' if 'v2' in reg.project_profiles else 'default')
	elif (None is not overlay_file and overlay_file.parent.name == agent and overlay_file.parent.parent.name == meta) or ((root / meta).is_dir() and ((root / 'code').is_dir() or (root / meta / j_name).is_dir() or (root / meta / agent).is_dir())):
		r = 'dual_repo'
	elif 1 != explicit_fs_version and dfh_has_v2_markers(root, reg) and (has_v2_sw or 'v2' in reg.project_profiles):
		r = 'v2_software' if has_v2_sw else 'v2'
	else:
		pjson_prof = _project_json_fs_profile(root, agent, reg, explicit_fs_version)
		r = pjson_prof if None is not pjson_prof else 'default'
	return r
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_journal()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__resolve_effective_journal_dir()`
def dfh_inspect_journal_dir_on_disk(j_dir: Path, reg: Any) -> tuple[int | None, tuple[str, str] | None]:
	rv = reg.resolved_variables
	j_out, j_in, b_raw = (rv.get('JOURNAL_OUT_DIR_NAME', '\u227b'), rv.get('JOURNAL_IN_DIR_NAME', '\u227a'), rv.get('JOURNAL_BUCKET_SIZE', '20'))
	b_size = int(b_raw) if str(b_raw).isdigit() and 0 < int(b_raw) else 20
	has_v2 = (j_dir / j_out).is_dir() or (j_dir / j_in).is_dir()
	has_v1 = (j_dir / 'req').is_dir() or (j_dir / 'res').is_dir()
	if has_v2 and (not has_v1):
		is_flat = any((_inspect_v2_journal_side(j_dir / s, b_size) for s in (j_out, j_in)))
		r: tuple[int | None, tuple[str, str] | None] = (2 if is_flat else 3, (j_out, j_in))
	elif has_v1 or j_dir.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
		r = (1, ('req', 'res'))
	else:
		r = (None, None)
	return r
# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
# @used-by :func:`agent_tools.path_registry._journal_cache_sig()`
def dfh_journal_cache_sig(root: Path, reg: Any) -> tuple:
	rv = reg.resolved_variables
	j_name, j_out, j_in, meta = (rv.get('JOURNAL_DIR_NAME', '\ua66e'), rv.get('JOURNAL_OUT_DIR_NAME', '\u227b'), rv.get('JOURNAL_IN_DIR_NAME', '\u227a'), rv.get('META_DIR_NAME', '_'))
	sig: list[tuple] = []
	for base in (root / j_name, root / meta / j_name):
		for rel in ('', j_out, j_in, 'req', 'res', '1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
			cand = base / rel if rel else base
			try:
				sig.append((rel, True, os.stat(cand).st_mtime_ns))
			except OSError:
				sig.append((rel, False, 0))
	return tuple(sig)
# @used-by :func:`dfh_infer_default_profile()`
def dfh_v2_software_deliverable_dir(root: Path, reg: Any) -> Path:
	rv = reg.resolved_variables
	art, art_out, deliv, sw = (rv.get('ARTIFACTS_DIR_NAME', '\u2c0f'), rv.get('ARTIFACTS_OUT_DIR_NAME', '\u227b'), rv.get('DELIVERABLES_DIR_NAME', '\u2655'), rv.get('SOFTWARE_DIR_NAME', '\u26ef'))
	cand = root / art / art_out / deliv / sw
	alt = root / 'Artifacts' / art_out / 'Deliverables' / sw
	return alt if (not cand.exists()) and alt.exists() else cand
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init_overlay_and_profile()`
def dfh_validate_overlay(raw: Any, overlay_path: Path, reg: Any) -> dict[str, Any]:
	if not isinstance(raw, dict):
		raise ValueError(f'Project overlay {overlay_path} must be a JSON object')
	if 1 != raw.get('version', 1):
		raise ValueError(f'Project overlay {overlay_path} requires version 1')
	unknown = set(raw) - {'auxiliary_repos', 'code_repos', 'deliverable_segments', 'extends', 'fs_version', 'journal_version', 'linked_roots', 'notes', 'paths', 'profile', 'similar_projects', 'source_dirs', 'tools', 'tracked', 'variables', 'version'}
	if unknown:
		raise ValueError(f"Unknown keys in project overlay {overlay_path}: {', '.join(sorted(unknown))}")
	fs_ver, j_ver, tracked, profile = (raw.get('fs_version'), raw.get('journal_version'), raw.get('tracked'), raw.get('profile') or raw.get('extends'))
	_validate_overlay_scalars(fs_ver, j_ver, tracked, profile, overlay_path, reg)
	raw_tools = raw.get('tools') or {}
	if not isinstance(raw_tools, dict):
		raise ValueError(f'{overlay_path} tools must be an object')
	return {'auxiliary_repos': dfh_validate_string_map(raw.get('auxiliary_repos'), f'{overlay_path} auxiliary_repos'), 'code_repos': dfh_validate_string_list(raw.get('code_repos'), f'{overlay_path} code_repos'), 'deliverable_segments': dfh_validate_string_list(raw.get('deliverable_segments'), f'{overlay_path} deliverable_segments'), 'fs_version': fs_ver, 'journal_version': j_ver, 'linked_roots': dfh_validate_string_list(raw.get('linked_roots'), f'{overlay_path} linked_roots'), 'paths': dfh_validate_string_map(raw.get('paths'), f'{overlay_path} paths'), 'profile': profile, 'similar_projects': dfh_validate_string_list(raw.get('similar_projects'), f'{overlay_path} similar_projects'), 'source_dirs': dfh_validate_string_list(raw.get('source_dirs'), f'{overlay_path} source_dirs'), 'tools': deepcopy(raw_tools), 'tracked': tracked, 'variables': dfh_validate_variables_map(raw.get('variables'), f'{overlay_path} variables'), 'version': 1}
# @used-by :meth:`Df.Harness.Path.Registry.Registry.__init_overlays_and_profiles()`
def dfh_validate_similar_project_groups(raw: Any, variables: dict[str, str], *, env: dict[str, str] | None=None) -> tuple[dict[str, Any], ...]:
	if None is raw:
		r: tuple[dict[str, Any], ...] = ()
	elif not isinstance(raw, list):
		raise ValueError('paths.json similar_projects must be a list of group objects')
	else:
		seen_ids: set[str] = set()
		r = tuple((_validate_one_similar_group(grp, idx, seen_ids, variables, env) for idx, grp in enumerate(raw)))
	return r
