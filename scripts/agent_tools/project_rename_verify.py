# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Auto-detect launcher root and enforce post-rename invariant verification with rollback":
# https://github.com/dmitry-ai/harness/issues/288
from __future__ import annotations
from pathlib import Path
import json
from . import journal
from .journal_integrity import journal_validation_errors
from .path_registry import project_paths
from .project_rename_state import _path_pairs
# @used-by :func:`capture_pre_rename_snapshot()`
# @used-by :func:`verify_post_rename()`
def _check_config_status(root: Path) -> tuple[bool, list]:
	from .upwork_project import check_configuration
	try:
		res = check_configuration(root)
		r = (bool(res.get('valid')), list(res.get('issues') or ()))
	except (OSError, ValueError) as exc:
		r = (False, [{'message': str(exc)}])
	return r
# @used-by :func:`_verify_journal_regression()`
# @used-by :func:`capture_pre_rename_snapshot()`
def _collect_journal_errors(root: Path) -> list[str]:
	jdir = journal.resolve_journal_dir(root)
	errs: list[str] = []
	if jdir.is_dir():
		steps = sorted(journal.get_existing_step_ids(jdir))
		for step in steps:
			errs.extend(journal.step_errors(jdir, step))
		if steps:
			errs.extend(journal_validation_errors(jdir, project_root=root, strict_sequence=True))
	return errs
# @used-by :func:`verify_post_rename()`
def _launcher_stale_files(launcher_root: Path | None, old_root: Path, new_root: Path) -> list[str]:
	stale: list[str] = []
	if None is not launcher_root and old_root != new_root:
		turns_dir = project_paths(Path(launcher_root).resolve(), exact_root=True).turns_dir
		needles = [old_s.casefold() for old_s, _ in _path_pairs(old_root, new_root, None, None)]
		if turns_dir.is_dir():
			for sf in sorted(turns_dir.glob('*.json')):
				try:
					blob = json.dumps(json.loads(sf.read_text(encoding='utf-8-sig')), ensure_ascii=False).casefold()
				except (OSError, ValueError):
					continue
				if any((n in blob for n in needles)):
					stale.append(sf.name)
	return stale
# @used-by :func:`capture_pre_rename_snapshot()`
# @used-by :func:`verify_post_rename()`
def _probe_review_auth(root: Path, wf_state: dict) -> tuple[bool, str | None]:
	from . import review
	if not wf_state.get('reviews'):
		r: tuple[bool, str | None] = (True, None)
	else:
		try:
			review.authorize(root, wf_state)
			r = (True, None)
		except (OSError, ValueError) as exc:
			r = (False, str(exc))
	return r
# @used-by :func:`capture_pre_rename_snapshot()`
# @used-by :func:`verify_post_rename()`
def _probe_workflow(root: Path) -> tuple[dict | None, dict[str, str]]:
	from . import workflow
	wf_path = project_paths(root, exact_root=True).workflow_json
	if not wf_path.is_file():
		r: tuple[dict | None, dict[str, str]] = (None, {})
	else:
		wf_state = workflow.load(root)
		r = (wf_state, workflow.stage_statuses(root, wf_state))
	return r
# @used-by :func:`verify_post_rename()`
def _verify_journal_regression(old_root: Path, new_root: Path, pre_errors: list[str], errors: list[str]) -> list[str]:
	post_j = _collect_journal_errors(new_root)
	pairs = _path_pairs(old_root, new_root, None, None)
	norm_pre = set(pre_errors)
	for err in pre_errors:
		mapped = err
		for old_s, new_s in pairs:
			mapped = mapped.replace(old_s, new_s)
		norm_pre.add(mapped)
	for err in post_j:
		if err not in norm_pre:
			errors.append(f'validate_step regression after rename: {err}')
	return post_j
# @used-by :func:`verify_post_rename()`
def _verify_stage_regression(pre_stages: dict[str, str], post_stages: dict[str, str], errors: list[str]) -> None:
	for stage, prev in pre_stages.items():
		cur = post_stages.get(stage)
		if 'complete' == prev and 'complete' != cur:
			errors.append(f'workflow stage regression: {stage} degraded from complete to {cur}')
# @used-by :func:`agent_tools.project_rename.rename_project()`
# @used-by :func:`agent_tools.shadow_replay_command._run_generic_command()`
# @used-by :mod:`agent_tools.project_rename_verify`
def capture_pre_rename_snapshot(old_root: Path) -> dict:
	wf_state, stages = _probe_workflow(old_root)
	has_reviews = bool(wf_state and wf_state.get('reviews'))
	rev_ok, _ = _probe_review_auth(old_root, wf_state) if has_reviews else (True, None)
	cfg_ok, _ = _check_config_status(old_root)
	return {'workflow_stages': stages, 'has_reviews': has_reviews, 'review_auth_ok': rev_ok, 'configure_valid': cfg_ok, 'journal_errors': _collect_journal_errors(old_root)}
# @used-by :func:`agent_tools.project_rename.rename_project()`
# @used-by :func:`agent_tools.shadow_replay_command.resolve_shadow_launcher()`
# @used-by :mod:`agent_tools.project_rename_verify`
def infer_launcher_root(old_root: Path, daily_root: Path | None, launcher_root: Path | None) -> Path | None:
	if None is not launcher_root:
		r: Path | None = Path(launcher_root).resolve()
	elif None is not daily_root:
		cand = (Path(daily_root).resolve().parent / 'init').resolve()
		r = cand if (cand / '\ua616/data/turns').is_dir() else None
	else:
		r = None
	return r
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
# @used-by :func:`agent_tools.shadow_replay_command._verify_shadow_command_post()`
# @used-by :mod:`agent_tools.project_rename_verify`
def verify_post_rename(old_root: Path, new_root: Path, pre: dict, *, launcher_root: Path | None=None) -> dict:
	errors: list[str] = []
	post_wf, post_stages = _probe_workflow(new_root)
	_verify_stage_regression(pre.get('workflow_stages') or {}, post_stages, errors)
	rev_ok = True
	if pre.get('has_reviews') and pre.get('review_auth_ok') and None is not post_wf:
		rev_ok, rev_err = _probe_review_auth(new_root, post_wf)
		if not rev_ok:
			errors.append(f'review.authorize failed after rename: {rev_err}')
	cfg_ok, cfg_issues = _check_config_status(new_root)
	if pre.get('configure_valid') and (not cfg_ok):
		errors.append(f'configure --check regressed after rename: {cfg_issues[:3]}')
	post_j = _verify_journal_regression(old_root, new_root, list(pre.get('journal_errors') or ()), errors)
	stale_l = _launcher_stale_files(launcher_root, old_root, new_root)
	if stale_l:
		joined = ', '.join(stale_l[:5])
		errors.append(f'launcher handoffs retain stale project path: {joined}')
	return {'valid': not errors, 'errors': errors, 'workflow_stages': post_stages, 'review_authorized': rev_ok, 'configure_valid': cfg_ok, 'journal_errors': post_j, 'stale_launcher_files': stale_l}
__all__ = ['capture_pre_rename_snapshot', 'infer_launcher_root', 'verify_post_rename']
