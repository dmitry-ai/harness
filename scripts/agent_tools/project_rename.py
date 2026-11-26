# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add transactional rename-project command with automatic domain promotion":
# https://github.com/dmitry-ai/harness/issues/267
from __future__ import annotations
from pathlib import Path
import json
import os
import re
import uuid
from .path_cache import clear_path_cache
from .path_registry import clear_registry_cache, project_paths, store_path
from .project_labels import LabelValidationError, normalize_domain_host, resolve_init_label
from .project_rename_state import capture_file_sha, refresh_workflow_file_hash, rewrite_launcher_handoffs, rewrite_project_internal_state
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
from .project_rename_verify import capture_pre_rename_snapshot, infer_launcher_root, verify_post_rename
from .runtime import platform_instances, request_day
from .storage import locked, replace_bytes
_SEQ_PREFIX_RE = re.compile(r'^(\d+) - (.+)$')
# @used-by :func:`_build_ag_registrar()`
# @used-by :func:`_sync_registrations()`
def _antigravity_dirs_map(override: dict[str, Path] | None) -> dict[str, Path]:
	if None is not override:
		r = {k: Path(v) for k, v in override.items()}
	else:
		insts = platform_instances('antigravity', include_disabled=False)
		ordered = sorted(insts.items(), key=lambda kv: (0 if kv[1].get('primary') else 1, kv[0]))
		r = {iid: Path(inst['system_paths']['projects_dir']) for iid, inst in ordered if inst.get('system_paths', {}).get('projects_dir')}
	return r
# @used-by :func:`_sync_registrations()`
def _build_ag_registrar(ag_dirs: dict[str, Path] | None, folders_json: Path | None, preferred_id: str | None):
	from .platforms.antigravity import register as ag_default, register_antigravity_project
	if None is ag_dirs and None is folders_json:
		r = None
	else:
		dirs = _antigravity_dirs_map(ag_dirs)
		# @used-by :func:`_build_ag_registrar()`
		def _reg(project, label, day):
			per_inst, first, pid = ({}, None, preferred_id)
			for iid, pdir in dirs.items():
				rec = register_antigravity_project(project, label, day, projects_dir=pdir, folders_json_path=folders_json, preferred_id=pid)
				pid = pid or rec['project_id']
				per_inst[iid] = rec
				first = rec if None is first else first
			return {**first, 'instances': per_inst} if None is not first else ag_default(project, label, day)
		r = _reg
	return r
# @used-by :func:`_rename_dir_safe()`
def _do_dir_rename(old_root: Path, new_root: Path) -> None:
	if old_root.name.casefold() == new_root.name.casefold() and old_root.name != new_root.name:
		tmp_root = old_root.parent / f'.rename-tmp-{uuid.uuid4().hex[:10]}'
		os.rename(old_root, tmp_root)
		os.rename(tmp_root, new_root)
	else:
		os.rename(old_root, new_root)
# @used-by :func:`_sync_antigravity_native_files()`
def _extract_prior_ag_id(new_root: Path, ag_dirs: dict[str, Path], old_root: Path) -> str | None:
	pid = _ag_id_from_receipt(new_root)
	if None is pid:
		pid = _scan_ag_dirs_for_uri(ag_dirs, old_root.as_uri().casefold())
	return pid
# @used-by :func:`_extract_prior_ag_id()`
def _ag_id_from_receipt(new_root: Path) -> str | None:
	regs_f = project_paths(new_root, exact_root=True).registrations_json
	r = None
	if regs_f.is_file():
		try:
			ag = json.loads(regs_f.read_text(encoding='utf-8-sig')).get('antigravity') or {}
			r = ag.get('project_id') or (ag.get('last_success') or {}).get('project_id')
		except (OSError, ValueError):
			r = None
	return r
# @used-by :func:`_scan_ag_dirs_for_uri()`
def _item_matches_uri(cand: Path, old_uri: str) -> str | None:
	r = None
	try:
		item = json.loads(cand.read_text(encoding='utf-8-sig'))
		res = (item.get('projectResources') or {}).get('resources') or []
		if any((isinstance(x, dict) and str(x.get('folderUri') or '').casefold() == old_uri for x in res)):
			r = item.get('id') or cand.stem
	except (OSError, ValueError):
		r = None
	return r
# @used-by :func:`_extract_prior_ag_id()`
def _scan_ag_dirs_for_uri(ag_dirs: dict[str, Path], old_uri: str) -> str | None:
	r = None
	for pdir in ag_dirs.values():
		if not pdir.is_dir():
			continue
		for cand in sorted(pdir.glob('*.json')):
			r = _item_matches_uri(cand, old_uri)
			if None is not r:
				break
		if None is not r:
			break
	return r
# @used-by :func:`_update_projects_index()`
# @used-by :func:`agent_tools.shadow_replay_command.resolve_shadow_launcher()`
# @used-by :func:`agent_tools.shadow_replay_command.stage_command_shadow_copies()`
# @used-by :func:`rename_project()`
def _infer_daily_root(root: Path, daily_root: Path | None) -> Path | None:
	if None is not daily_root:
		r = Path(daily_root).resolve()
	elif 4 <= len(root.parents) and all((root.parents[i].name.isascii() and root.parents[i].name.isdigit() for i in (2, 1, 0))):
		r = root.parents[3].resolve()
	else:
		r = None
	return r
# @used-by :func:`rename_project()`
def _rename_dir_safe(old_root: Path, new_root: Path) -> Path | None:
	prev_cwd = Path.cwd().resolve()
	moved_cwd = prev_cwd if prev_cwd == old_root or prev_cwd.is_relative_to(old_root) else None
	if None is not moved_cwd:
		os.chdir(old_root.parent)
	try:
		_do_dir_rename(old_root, new_root)
	except PermissionError as exc:
		if None is not moved_cwd:
			os.chdir(moved_cwd)
		raise PermissionError(f'Cannot rename locked project directory "{old_root}" -> "{new_root}": close open handles referencing this folder and retry ({exc})') from exc
	except OSError:
		if None is not moved_cwd:
			os.chdir(moved_cwd)
		raise
	return moved_cwd
# @used-by :func:`_rollback_rename()`
def _restore_file_backups(backups: list[tuple[Path, bytes | None]]) -> None:
	for path, raw in reversed(backups):
		try:
			if None is raw:
				path.unlink(missing_ok=True)
			else:
				replace_bytes(path, raw)
		except OSError:
			pass
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`rename_project()`
def _rollback_rename(old_root: Path, new_root: Path, same_dir: bool, moved_cwd: Path | None, backups: list[tuple[Path, bytes | None]], state_moves: list[tuple[Path, Path]]=()) -> None:
	_restore_file_backups(backups)
	for old_st, new_st in reversed(state_moves):
		if new_st.is_dir() and (not old_st.exists()):
			os.replace(new_st, old_st)
	if (not same_dir) and new_root.is_dir() and (not old_root.exists()):
		os.rename(new_root, old_root)
	if None is not moved_cwd and old_root.is_dir():
		os.chdir(moved_cwd)
	clear_path_cache()
	clear_registry_cache()
# @used-by :func:`_sync_registrations()`
def _sync_antigravity_native_files(old_root: Path, new_root: Path, new_label: str, day_str: str, ag_dirs: dict[str, Path], backups: list[tuple[Path, bytes | None]]) -> str | None:
	day = request_day(day_str)
	new_name = f'{new_label} - U.P.{day:%Y.%m.%d}'
	pid = _extract_prior_ag_id(new_root, ag_dirs, old_root)
	if None is not pid:
		for pdir in ag_dirs.values():
			target = pdir / f'{pid}.json'
			if target.is_file():
				with locked(pdir / '\ua616' / 'data' / 'registration.lock'):
					raw = target.read_bytes()
					backups.append((target, raw))
					payload = json.loads(raw.decode('utf-8-sig'))
					payload['name'] = new_name
					payload['projectResources'] = {**(payload.get('projectResources') or {}), 'resources': [{'folderUri': new_root.as_uri()}]}
					replace_bytes(target, (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	return pid
# @used-by :func:`_apply_rename_mutations()`
def _sync_registrations(old_root: Path, new_root: Path, new_label: str, day_str: str, *, register_native: bool | None, ag_dirs: dict[str, Path] | None, folders_json: Path | None, targets: list[str] | None, registrars: dict | None, backups: list[tuple[Path, bytes | None]]) -> dict | None:
	from .registration import register_projects
	from .upwork_project import DAILY_PROPOSALS_ROOT
	regs_f = project_paths(new_root, exact_root=True).registrations_json
	should = register_native if None is not register_native else (regs_f.is_file() or new_root.is_relative_to(DAILY_PROPOSALS_ROOT.resolve()))
	r = None
	if should:
		eff_dirs = _antigravity_dirs_map(ag_dirs)
		pid = _sync_antigravity_native_files(old_root, new_root, new_label, day_str, eff_dirs, backups)
		eff_regs = dict(registrars or {})
		if 'antigravity' not in eff_regs:
			custom_ag = _build_ag_registrar(ag_dirs, folders_json, pid)
			if None is not custom_ag:
				eff_regs['antigravity'] = custom_ag
		# 2026-11-26 "Preserve finalized workflow and review lineage across rename-project": https://github.com/dmitry-ai/harness/issues/277
		# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
		backups.append((regs_f, regs_f.read_bytes() if regs_f.is_file() else None))
		old_reg_sha = capture_file_sha(regs_f)
		r = register_projects(new_root, new_label, day_str, targets=targets, registrars=eff_regs or None)
		refresh_workflow_file_hash(new_root, regs_f, old_reg_sha)
	return r
# @used-by :func:`_validate_rename_inputs()`
def _target_name_and_root(old_root: Path, new_label: str) -> Path:
	match = _SEQ_PREFIX_RE.match(old_root.name)
	new_name = f'{match.group(1)} - {new_label}' if match else new_label
	return old_root.parent / new_name
# @used-by :func:`_apply_rename_mutations()`
def _update_projects_index(old_root: Path, new_root: Path, job_id: str, daily_root: Path | None, backups: list[tuple[Path, bytes | None]]) -> str | None:
	from .upwork_project import DAILY_PROPOSALS_ROOT
	daily = _infer_daily_root(new_root, daily_root)
	r = None
	if None is not daily and new_root.is_relative_to(daily):
		use_central = daily == DAILY_PROPOSALS_ROOT.resolve() and (not (daily / '\ua616/data/projects.json').exists())
		state_dir = store_path('upwork_projects_dir') if use_central else daily / '\ua616/data'
		with locked(state_dir / 'projects.lock'):
			index_file = state_dir / 'projects.json'
			raw = index_file.read_bytes() if index_file.is_file() else None
			backups.append((index_file, raw))
			index = json.loads(raw.decode('utf-8')) if None is not raw else {}
			index[job_id] = new_root.relative_to(daily).as_posix()
			replace_bytes(index_file, (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
			r = str(index_file)
	return r
# @used-by :func:`rename_project()`
def _validate_rename_inputs(project_root: str | Path, domain: str | None, topic: str | None) -> tuple[Path, Path, str, str, dict]:
	old_root = Path(project_root).resolve()
	pj_path = project_paths(old_root, exact_root=True).project_json
	if not old_root.is_dir() or (not pj_path.is_file()):
		raise ValueError(f'Existing Upwork project with \ua616/project.json required: {old_root}')
	if not domain and (not topic):
		raise LabelValidationError('Specify --domain <host> or --topic "<Title>" for rename-project')
	new_label, new_kind, _ = resolve_init_label(domain=domain, topic=topic, strict_domain=bool(domain))
	pj_old = json.loads(pj_path.read_text(encoding='utf-8-sig'))
	new_root = _target_name_and_root(old_root, new_label)
	if new_root != old_root and new_root.exists() and old_root.name.casefold() != new_root.name.casefold():
		raise FileExistsError(f'Target project directory already exists: {new_root}')
	return (old_root, new_root, new_label, new_kind, pj_old)
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`agent_tools.cli_domains._op_render_analysis()`
# @used-by :func:`agent_tools.cli_domains._op_save_analysis()`
def apply_domain_promotion(project_root: Path, analysis_value: dict, result: dict, *, register_native: bool | None=None, launcher_root: Path | None=None) -> dict:
	promo = maybe_promote_project_domain(project_root, analysis_value, register_native=register_native, launcher_root=launcher_root)
	result['domain_promotion'] = promo
	if False is promo.get('valid'):
		result['valid'] = False
	elif promo.get('renamed'):
		new_root = Path(promo['project_dir'])
		result['project_dir'] = str(new_root)
		old_str = str(Path(project_root).resolve())
		for key in ('target', 'output'):
			if isinstance(result.get(key), str) and old_str in result[key]:
				result[key] = result[key].replace(old_str, str(new_root), 1)
	return result
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`apply_domain_promotion()`
def maybe_promote_project_domain(project_root: str | Path, analysis_value: dict, *, daily_root: Path | None=None, register_native: bool | None=None, launcher_root: Path | None=None) -> dict:
	root = Path(project_root).resolve()
	pj_path = project_paths(root, exact_root=True).project_json
	if not pj_path.is_file():
		r = {'renamed': False, 'reason': 'not_upwork_project', 'project_dir': str(root)}
	else:
		pj = json.loads(pj_path.read_text(encoding='utf-8-sig'))
		domain, basis_id = resolve_promotable_target_domain(analysis_value)
		cur_label = root.name.split(' - ', 1)[-1]
		if pj.get('domain_drift_exempt'):
			r = {'renamed': False, 'reason': 'domain_drift_exempt', 'project_dir': str(root)}
		elif None is domain:
			r = {'renamed': False, 'reason': 'no_high_confidence_target_domain', 'project_dir': str(root)}
		elif cur_label.casefold() == domain.casefold():
			r = {'renamed': False, 'reason': 'already_matches_domain', 'domain': domain, 'basis_id': basis_id, 'project_dir': str(root)}
		else:
			res = rename_project(root, domain=domain, daily_root=daily_root, register_native=register_native, launcher_root=launcher_root)
			r = {**res, 'basis_id': basis_id}
	return r
# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
# @used-by :func:`maybe_promote_project_domain()`
def resolve_promotable_target_domain(analysis_value: dict, *, min_probability: int=75) -> tuple[str | None, str | None]:
	r: tuple[str | None, str | None] = (None, None)
	if isinstance(analysis_value, dict):
		identities = {c['id']: c for c in (analysis_value.get('identity') or ()) if isinstance(c, dict) and isinstance(c.get('id'), str)}
		hits: dict[str, str] = {}
		for site in analysis_value.get('websites') or ():
			if isinstance(site, dict) and 'target' == site.get('role'):
				host = normalize_domain_host(site.get('url'))
				bid = site.get('basis_id')
				if host and isinstance(bid, str) and bid in identities:
					hits.setdefault(host, bid)
		if 1 == len(hits):
			host, bid = next(iter(hits.items()))
			claim = identities[bid]
			score = claim.get('probability_percent')
			if 'verified' == claim.get('verification_status') or (isinstance(score, int) and (not isinstance(score, bool)) and min_probability <= score):
				r = (host, bid)
	return r
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`rename_project()`
def _apply_rename_mutations(old_root: Path, new_root: Path, new_label: str, new_kind: str, pj_old: dict, *, daily_root: Path | None, eff_launcher: Path | None, pre_snap: dict, register_native: bool | None, ag_dirs: dict[str, Path] | None, folders_json: Path | None, targets: list[str] | None, registrars: dict | None, backups: list[tuple[Path, bytes | None]], state_moves: list[tuple[Path, Path]]) -> tuple[str | None, dict | None, dict]:
	clear_path_cache()
	clear_registry_cache()
	idx_file = _update_projects_index(old_root, new_root, pj_old['job_id'], daily_root, backups)
	rewrite_project_internal_state(old_root, new_root, new_label, new_kind, backups=backups, state_moves=state_moves)
	if None is not eff_launcher:
		rewrite_launcher_handoffs(eff_launcher, old_root, new_root, backups=backups)
	reg_info = _sync_registrations(old_root, new_root, new_label, pj_old.get('request_date'), register_native=register_native, ag_dirs=ag_dirs, folders_json=folders_json, targets=targets, registrars=registrars, backups=backups)
	post_ver = verify_post_rename(old_root, new_root, pre_snap, launcher_root=eff_launcher)
	return (idx_file, reg_info, post_ver)
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`agent_tools.cli_registry._exec_rename_project()`
# @used-by :func:`agent_tools.shadow_replay_command._run_exec_rename_domain()`
# @used-by :func:`maybe_promote_project_domain()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_rename_project_cleanup_recent_and_old_path_history()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_rolls_back_finalized_fixture_on_review_authorize_regression()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cleanup_integration()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_rolls_back_on_collision_or_failure()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
def rename_project(project_root: str | Path, *, domain: str | None=None, topic: str | None=None, daily_root: Path | None=None, register_native: bool | None=None, antigravity_projects_dirs: dict[str, Path] | None=None, antigravity_folders_json: Path | None=None, targets: list[str] | None=None, registrars: dict | None=None, launcher_root: Path | None=None) -> dict:
	old_root, new_root, new_label, new_kind, pj_old = _validate_rename_inputs(project_root, domain, topic)
	eff_launcher = infer_launcher_root(old_root, _infer_daily_root(old_root, daily_root), launcher_root)
	pre_snap = capture_pre_rename_snapshot(old_root)
	same_dir, backups, state_moves = (new_root == old_root, [], [])
	moved_cwd = None if same_dir else _rename_dir_safe(old_root, new_root)
	try:
		idx_file, reg_info, post_ver = _apply_rename_mutations(old_root, new_root, new_label, new_kind, pj_old, daily_root=daily_root, eff_launcher=eff_launcher, pre_snap=pre_snap, register_native=register_native, ag_dirs=antigravity_projects_dirs, folders_json=antigravity_folders_json, targets=targets, registrars=registrars, backups=backups, state_moves=state_moves)
	except Exception:
		_rollback_rename(old_root, new_root, same_dir, moved_cwd, backups, state_moves)
		raise
	if not post_ver['valid']:
		_rollback_rename(old_root, new_root, same_dir, moved_cwd, backups, state_moves)
		r = {'valid': False, 'renamed': False, 'rolled_back': True, 'old_project_dir': str(old_root), 'project_dir': str(old_root), 'job_id': pj_old['job_id'], 'label': pj_old.get('label'), 'launcher_root': str(eff_launcher) if None is not eff_launcher else None, 'post_verification': post_ver, 'errors': post_ver['errors']}
	else:
		if None is not moved_cwd and new_root.is_dir():
			os.chdir(new_root)
		r = {'valid': True, 'renamed': not same_dir, 'old_project_dir': str(old_root), 'project_dir': str(new_root), 'job_id': pj_old['job_id'], 'label': new_label, 'label_kind': new_kind, 'launcher_root': str(eff_launcher) if None is not eff_launcher else None, 'projects_index': idx_file, 'registration': reg_info, 'post_verification': post_ver}
	return r
